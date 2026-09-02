"""移植 agent loop 的确定性测试（FakeProvider，无网络无 tau）。

覆盖 canonical 事件序、工具往返、拦截钩子、终止路径（provider error /
max_turns）；事件类型即 fractal_runtime.events 的移植词汇表。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from agent_helpers import (
    assistant_done,
    assistant_error,
    assistant_start,
    text_delta,
    tool_call_end,
)
from fractal_runtime.events import (
    AgentEndEvent,
    AgentStartEvent,
    MessageEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    ToolExecutionEndEvent,
    TurnEndEvent,
    TurnStartEvent,
)
from fractal_runtime.fake_provider import FakeProvider
from fractal_runtime.loop import run_agent_loop
from fractal_runtime.messages import (
    AgentMessage,
    AssistantMessage,
    TextContent,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)
from fractal_runtime.tools import AgentTool, AgentToolResult


async def collect(stream: AsyncIterator[object]) -> list[object]:
    return [event async for event in stream]


def echo_tool(calls: list[str]) -> AgentTool:
    async def execute_fn(
        tool_call_id: str,
        arguments: dict[str, object],
        signal: object = None,
        on_update: object = None,
    ) -> AgentToolResult:
        calls.append(str(arguments.get("text", "")))
        return AgentToolResult(content=[TextContent(text=f"echo:{arguments.get('text', '')}")])

    return AgentTool(
        name="echo",
        label="Echo",
        description="Echo text.",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        execute_fn=execute_fn,
    )


def _tool_call(call_id: str, name: str, arguments: dict[str, object]) -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments)


class TestRunAgentLoop:
    async def test_canonical_event_sequence_single_turn(self) -> None:
        assistant = AssistantMessage(content="Hello", model="fake")
        provider = FakeProvider(
            [[assistant_start(), text_delta("Hel"), text_delta("lo"), assistant_done(assistant)]]
        )
        messages: list[AgentMessage] = [UserMessage(content="Say hello")]

        events = await collect(
            run_agent_loop(
                provider=provider, model="fake", system="sys", messages=messages, tools=[]
            )
        )

        assert [type(event) for event in events] == [
            AgentStartEvent,
            TurnStartEvent,
            MessageStartEvent,
            MessageUpdateEvent,  # text_delta Hel
            MessageUpdateEvent,  # text_delta lo
            MessageEndEvent,  # assistant
            TurnEndEvent,
            AgentEndEvent,
        ]
        assistant_end = events[5]
        assert isinstance(assistant_end, MessageEndEvent)
        assert isinstance(assistant_end.message, AssistantMessage)
        assert assistant_end.message.text == "Hello"
        assert isinstance(events[-1], AgentEndEvent)
        assert [m.role for m in events[-1].messages] == ["assistant"]

    async def test_tool_round_trip(self) -> None:
        calls: list[str] = []
        call = _tool_call("c1", "echo", {"text": "hi"})
        turn1 = AssistantMessage(content=[call], stop_reason="toolUse", model="fake")
        turn2 = AssistantMessage(content="done", stop_reason="stop", model="fake")
        provider = FakeProvider(
            [
                [assistant_start(), tool_call_end(call), assistant_done(turn1)],
                [assistant_start(), assistant_done(turn2)],
            ]
        )

        events = await collect(
            run_agent_loop(
                provider=provider,
                model="fake",
                system="sys",
                messages=[UserMessage(content="go")],
                tools=[echo_tool(calls)],
            )
        )

        assert calls == ["hi"]
        tool_ends = [e for e in events if isinstance(e, ToolExecutionEndEvent)]
        assert len(tool_ends) == 1
        assert not tool_ends[0].is_error
        results = [
            e
            for e in events
            if isinstance(e, MessageEndEvent) and isinstance(e.message, ToolResultMessage)
        ]
        assert results[0].message.text == "echo:hi"
        assert results[0].message.tool_call_id == "c1"
        last = events[-1]
        assert isinstance(last, AgentEndEvent)
        assert [m.role for m in last.messages] == ["assistant", "toolResult", "assistant"]

    async def test_unknown_tool_yields_error_result(self) -> None:
        call = _tool_call("c1", "nonexistent", {})
        turn1 = AssistantMessage(content=[call], stop_reason="toolUse", model="fake")
        turn2 = AssistantMessage(content="ok", stop_reason="stop", model="fake")
        provider = FakeProvider(
            [
                [assistant_start(), tool_call_end(call), assistant_done(turn1)],
                [assistant_start(), assistant_done(turn2)],
            ]
        )

        events = await collect(
            run_agent_loop(
                provider=provider,
                model="fake",
                system="sys",
                messages=[],
                tools=[],
            )
        )

        ends = [e for e in events if isinstance(e, ToolExecutionEndEvent)]
        assert ends[0].is_error
        assert ends[0].result.text == "Tool nonexistent not found"

    async def test_before_tool_call_blocks_execution(self) -> None:
        call = _tool_call("c1", "echo", {"text": "x"})
        turn1 = AssistantMessage(content=[call], stop_reason="toolUse", model="fake")
        turn2 = AssistantMessage(content="ok", stop_reason="stop", model="fake")
        provider = FakeProvider(
            [
                [assistant_start(), tool_call_end(call), assistant_done(turn1)],
                [assistant_start(), assistant_done(turn2)],
            ]
        )

        async def block(_call: ToolCall) -> tuple[bool, str | None]:
            return True, "blocked by manifest"

        events = await collect(
            run_agent_loop(
                provider=provider,
                model="fake",
                system="sys",
                messages=[],
                tools=[echo_tool([])],
                before_tool_call=block,
            )
        )

        ends = [e for e in events if isinstance(e, ToolExecutionEndEvent)]
        assert ends[0].is_error
        assert ends[0].result.text == "blocked by manifest"

    async def test_provider_error_terminates(self) -> None:
        provider = FakeProvider([[assistant_start(), assistant_error("provider failed")]])

        events = await collect(
            run_agent_loop(provider=provider, model="fake", system="sys", messages=[], tools=[])
        )

        assert isinstance(events[-1], AgentEndEvent)
        final = events[-1].messages[-1]
        assert isinstance(final, AssistantMessage)
        assert final.stop_reason == "error"
        assert final.error_message == "provider failed"

    async def test_max_turns_stops_loop(self) -> None:
        call = _tool_call("c1", "echo", {"text": "x"})
        turn = AssistantMessage(content=[call], stop_reason="toolUse", model="fake")
        provider = FakeProvider(
            [[assistant_start(), tool_call_end(call), assistant_done(turn)]] * 5
        )

        events = await collect(
            run_agent_loop(
                provider=provider,
                model="fake",
                system="sys",
                messages=[],
                tools=[echo_tool([])],
                max_turns=1,
            )
        )

        ends = [e for e in events if isinstance(e, ToolExecutionEndEvent)]
        assert len(ends) == 1
        assert isinstance(events[-1], AgentEndEvent)
        final = events[-1].messages[-1]
        assert isinstance(final, AssistantMessage)
        assert final.stop_reason == "error"
        assert "max_turns=1" in (final.error_message or "")

    async def test_tool_exception_becomes_error_result(self) -> None:
        async def boom(
            tool_call_id: str,
            arguments: dict[str, object],
            signal: object = None,
            on_update: object = None,
        ) -> AgentToolResult:
            del tool_call_id, arguments, signal, on_update
            raise RuntimeError("disk exploded")

        tool = AgentTool(
            name="boom",
            label="Boom",
            description="Explodes.",
            parameters={"type": "object"},
            execute_fn=boom,
        )
        call = _tool_call("c1", "boom", {})
        turn1 = AssistantMessage(content=[call], stop_reason="toolUse", model="fake")
        turn2 = AssistantMessage(content="ok", stop_reason="stop", model="fake")
        provider = FakeProvider(
            [
                [assistant_start(), tool_call_end(call), assistant_done(turn1)],
                [assistant_start(), assistant_done(turn2)],
            ]
        )

        events = await collect(
            run_agent_loop(provider=provider, model="fake", system="sys", messages=[], tools=[tool])
        )

        ends = [e for e in events if isinstance(e, ToolExecutionEndEvent)]
        assert ends[0].is_error
        assert "disk exploded" in ends[0].result.text


async def test_string_content_stays_string_on_user_message() -> None:
    message = UserMessage(content="plain string")
    assert message.content == "plain string"
    assert message.text == "plain string"


async def test_result_message_normalizes_string_content() -> None:
    message = ToolResultMessage.model_validate(
        {"tool_call_id": "c1", "tool_name": "echo", "content": "text"}
    )
    assert message.text == "text"
    assert isinstance(message.content[0], TextContent)
