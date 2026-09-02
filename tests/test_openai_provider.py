"""OpenAI 兼容 provider 离线测试（httpx.MockTransport，无网络）。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
import pytest

from fractal_runtime.messages import (
    AssistantMessage,
    TextContent,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)
from fractal_runtime.openai_provider import (
    CONTEXT_OVERFLOW_MARKER,
    OpenAICompatibleProvider,
    _message_to_openai,
)
from fractal_runtime.provider_events import (
    AssistantDoneEvent,
    AssistantErrorEvent,
    TextEndEvent,
    ToolCallEndEvent,
)
from fractal_runtime.tools import AgentTool


def _sse(chunks: list[dict[str, object]]) -> bytes:
    lines = [f"data: {json.dumps(chunk)}" for chunk in chunks]
    lines.append("data: [DONE]")
    return ("\n\n".join(lines) + "\n\n").encode("utf-8")


def _text_chunks(text: str, finish: str = "stop") -> list[dict[str, object]]:
    return [
        {
            "id": "r1",
            "choices": [{"index": 0, "finish_reason": None, "delta": {"role": "assistant"}}],
        },
        {"id": "r1", "choices": [{"index": 0, "finish_reason": None, "delta": {"content": text}}]},
        {"id": "r1", "choices": [{"index": 0, "finish_reason": finish, "delta": {}}]},
        {
            "id": "r1",
            "choices": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    ]


async def collect(stream: AsyncIterator[object]) -> list[object]:
    return [event async for event in stream]


def _provider(handler: httpx.MockTransport) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="https://api.example.com/v1", api_key="k-test", transport=handler
    )


class TestTextStreaming:
    async def test_canonical_block_lifecycle(self) -> None:
        handler = httpx.MockTransport(
            lambda request: httpx.Response(200, content=_sse(_text_chunks("Hello")))
        )
        events = await collect(
            _provider(handler).stream_response(model="m", system="sys", messages=[], tools=[])
        )  # type: ignore[arg-type]

        assert [e.type for e in events] == ["start", "text_start", "text_delta", "text_end", "done"]
        done = events[-1]
        assert isinstance(done, AssistantDoneEvent)
        assert done.message.stop_reason == "stop"
        assert done.message.text == "Hello"
        assert done.message.usage.total_tokens == 15

    async def test_block_end_carries_accumulated_text(self) -> None:
        handler = httpx.MockTransport(
            lambda request: httpx.Response(200, content=_sse(_text_chunks("Hi")))
        )
        events = await collect(
            _provider(handler).stream_response(model="m", system="s", messages=[], tools=[])
        )  # type: ignore[arg-type]

        end = events[-2]
        assert isinstance(end, TextEndEvent)
        assert end.content == "Hi"


class TestToolCallStreaming:
    async def test_tool_call_accumulates_across_chunks(self) -> None:
        chunks: list[dict[str, object]] = [
            {
                "id": "r1",
                "choices": [{"index": 0, "finish_reason": None, "delta": {"role": "assistant"}}],
            },
            {
                "id": "r1",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": None,
                        "delta": {
                            "tool_calls": [
                                {"index": 0, "id": "call-9", "function": {"name": "write_file"}}
                            ]
                        },
                    }
                ],
            },
            {
                "id": "r1",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": None,
                        "delta": {
                            "tool_calls": [{"index": 0, "function": {"arguments": '{"path":'}}]
                        },
                    }
                ],
            },
            {
                "id": "r1",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": None,
                        "delta": {
                            "tool_calls": [{"index": 0, "function": {"arguments": ' "a.py"}'}}]
                        },
                    }
                ],
            },
            {"id": "r1", "choices": [{"index": 0, "finish_reason": "tool_calls", "delta": {}}]},
        ]
        handler = httpx.MockTransport(lambda request: httpx.Response(200, content=_sse(chunks)))
        events = await collect(
            _provider(handler).stream_response(model="m", system="s", messages=[], tools=[])
        )  # type: ignore[arg-type]

        assert [e.type for e in events] == ["start", "toolcall_start", "toolcall_end", "done"]
        end = events[2]
        assert isinstance(end, ToolCallEndEvent)
        assert end.tool_call.id == "call-9"
        assert end.tool_call.name == "write_file"
        assert end.tool_call.arguments == {"path": "a.py"}
        done = events[-1]
        assert isinstance(done, AssistantDoneEvent)
        assert done.message.stop_reason == "toolUse"


class TestErrorNormalization:
    async def test_http_400_context_overflow_gets_marker(self) -> None:
        body = json.dumps(
            {
                "error": {
                    "message": "This model's maximum context length is 8192 tokens",
                    "type": "invalid_request_error",
                    "code": "context_length_exceeded",
                }
            }
        )
        handler = httpx.MockTransport(lambda request: httpx.Response(400, text=body))
        events = await collect(
            _provider(handler).stream_response(model="m", system="s", messages=[], tools=[])
        )  # type: ignore[arg-type]

        assert len(events) == 1
        error = events[0]
        assert isinstance(error, AssistantErrorEvent)
        assert error.error.stop_reason == "error"
        assert error.error.error_message is not None
        assert error.error.error_message.startswith(f"{CONTEXT_OVERFLOW_MARKER}:")

    async def test_http_500_generic_error(self) -> None:
        handler = httpx.MockTransport(lambda request: httpx.Response(500, text="boom"))
        events = await collect(
            _provider(handler).stream_response(model="m", system="s", messages=[], tools=[])
        )  # type: ignore[arg-type]

        error = events[0]
        assert isinstance(error, AssistantErrorEvent)
        assert error.error.error_message == "provider HTTP 500: boom"

    async def test_network_error_surfaces(self) -> None:
        def fail(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        handler = httpx.MockTransport(fail)
        events = await collect(
            _provider(handler).stream_response(model="m", system="s", messages=[], tools=[])
        )  # type: ignore[arg-type]

        error = events[0]
        assert isinstance(error, AssistantErrorEvent)
        assert "connection refused" in (error.error.error_message or "")


class TestPayloadConstruction:
    async def test_payload_maps_messages_and_tools(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("Authorization")
            captured["payload"] = json.loads(request.content)
            return httpx.Response(200, content=_sse(_text_chunks("ok")))

        messages: list[object] = [
            UserMessage(content="do it"),
            AssistantMessage(
                content=[
                    TextContent(text="working"),
                    ToolCall(id="c1", name="t", arguments={"x": 1}),
                ]
            ),
            ToolResultMessage.model_validate(
                {"tool_call_id": "c1", "tool_name": "t", "content": "result text"}
            ),
        ]

        async def noop_execute(
            tool_call_id: str,
            arguments: dict[str, object],
            signal: object = None,
            on_update: object = None,
        ) -> object:
            del tool_call_id, arguments, signal, on_update
            raise AssertionError("payload test must not execute tools")

        tool = AgentTool(
            name="t",
            label="T",
            description="desc",
            parameters={"type": "object", "properties": {}},
            execute_fn=noop_execute,  # type: ignore[arg-type]
        )
        await collect(
            _provider(httpx.MockTransport(handler)).stream_response(
                model="m1",
                system="SYS",
                messages=messages,
                tools=[tool],  # type: ignore[arg-type]
            )
        )

        assert captured["url"] == "https://api.example.com/v1/chat/completions"
        assert captured["auth"] == "Bearer k-test"
        payload = captured["payload"]
        assert isinstance(payload, dict)
        assert payload["model"] == "m1"
        assert payload["stream"] is True
        assert payload["messages"][0] == {"role": "system", "content": "SYS"}
        assert payload["messages"][1] == {"role": "user", "content": "do it"}
        assistant_payload = payload["messages"][2]
        assert assistant_payload["role"] == "assistant"  # type: ignore[index]
        assert assistant_payload["content"] == "working"  # type: ignore[index]
        assert assistant_payload["tool_calls"][0]["function"]["name"] == "t"  # type: ignore[index]
        assert payload["messages"][3]["role"] == "tool"  # type: ignore[index]
        assert payload["messages"][3]["tool_call_id"] == "c1"  # type: ignore[index]
        assert payload["tools"][0]["function"]["name"] == "t"  # type: ignore[index]
        assert payload["stream_options"] == {"include_usage": True}


class TestUnknownRole:
    def test_unsupported_message_type_raises(self) -> None:
        with pytest.raises(TypeError):
            _message_to_openai("not a message")  # type: ignore[arg-type]
