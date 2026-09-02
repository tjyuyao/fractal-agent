"""Minimal OpenAI-compatible chat-completions streaming provider.

Not a verbatim port: a compact single-layer rewrite derived from
huggingface/tau ``tau_ai/openai_compatible.py`` v0.4.1 (MIT) — chat
completions path only — with the canonical block lifecycle semantics of
``tau_ai/stream.py``. Excluded for v0 (ADR-0006 port log): the responses API,
retry/backoff (Phase 5 治理), session affinity, compat knobs, credential
resolvers, image payloads.

Provider HTTP errors are normalized into ``AssistantErrorEvent`` with a
stable ``context_length_exceeded`` marker prefix (see
fractal_runtime.executor.is_context_overflow) so the build executor can turn
context overflow into the AM-0.1-07 "should decompose" signal.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

import httpx

from fractal_runtime.messages import (
    AgentMessage,
    AssistantMessage,
    TextContent,
    ThinkingContent,
    ToolCall,
    ToolResultMessage,
    Usage,
    UserMessage,
)
from fractal_runtime.provider import CancellationToken
from fractal_runtime.provider_events import (
    AssistantDoneEvent,
    AssistantErrorEvent,
    AssistantMessageEvent,
    AssistantStartEvent,
    DoneReason,
    TextDeltaEvent,
    TextEndEvent,
    TextStartEvent,
    ThinkingDeltaEvent,
    ThinkingEndEvent,
    ThinkingStartEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from fractal_runtime.tools import AgentTool

CONTEXT_LENGTH_ERROR_CODES = frozenset({"context_length_exceeded", "context_window_exceeded"})
CONTEXT_LENGTH_PHRASES = ("context length", "maximum context", "context_length_exceeded")
CONTEXT_OVERFLOW_MARKER = "context_length_exceeded"

_STOP_REASON_MAP = {"tool_calls": "toolUse", "function_call": "toolUse", "tool_use": "toolUse"}
_LENGTH_REASONS = frozenset({"length", "max_tokens", "MAX_TOKENS", "incomplete"})


class OpenAICompatibleProvider:
    """Stream one chat completion per call as canonical assistant events."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport
        self._headers = dict(headers or {})

    def stream_response(
        self,
        *,
        model: str,
        system: str,
        messages: list[AgentMessage],
        tools: list[AgentTool],
        signal: CancellationToken | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        del session_id
        payload = _build_payload(model=model, system=system, messages=messages, tools=tools)
        return self._stream(model=model, payload=payload, signal=signal)

    async def _stream(
        self,
        *,
        model: str,
        payload: dict[str, Any],
        signal: CancellationToken | None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        partial = AssistantMessage(api="openai-chat", provider="openai-compatible", model=model)
        parser = _ChunkParser(partial)
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._headers,
        }
        try:
            async with (
                httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client,
                client.stream("POST", url, json=payload, headers=headers) as response,
            ):
                if response.status_code >= 400:
                    body = (await response.aread()).decode(errors="replace")
                    yield _http_error_event(partial, response.status_code, body)
                    return
                yield AssistantStartEvent(partial=_snapshot(partial))
                async for line in response.aiter_lines():
                    if signal is not None and signal.is_cancelled():
                        return
                    for event in parser.feed(line):
                        yield event
                    if parser.done:
                        break
        except httpx.HTTPError as exc:
            yield _error_event(partial, f"provider network error: {exc}")
            return
        for event in parser.finalize():
            yield event


def _snapshot(message: AssistantMessage) -> AssistantMessage:
    return message.model_copy(deep=True)


def _error_event(partial: AssistantMessage, message: str) -> AssistantErrorEvent:
    error = _snapshot(partial)
    error.stop_reason = "error"
    error.error_message = message
    return AssistantErrorEvent(reason="error", error=error)


def _http_error_event(partial: AssistantMessage, status: int, body: str) -> AssistantErrorEvent:
    return _error_event(partial, _normalize_http_error(status, body))


def is_context_length_error(status: int, body: str) -> bool:
    """Return whether an HTTP error body indicates a context-window overflow."""
    if status != 400:
        return False
    lowered = body.lower()
    if any(phrase in lowered for phrase in CONTEXT_LENGTH_PHRASES):
        return True
    code = _error_code(body)
    return code in CONTEXT_LENGTH_ERROR_CODES


def _error_code(body: str) -> str:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return ""
    if isinstance(parsed, Mapping):
        error = parsed.get("error")
        if isinstance(error, Mapping):
            code = error.get("code")
            if isinstance(code, str):
                return code
    return ""


def _normalize_http_error(status: int, body: str) -> str:
    detail = body[:500]
    if is_context_length_error(status, body):
        return f"{CONTEXT_OVERFLOW_MARKER}: {detail}"
    return f"provider HTTP {status}: {detail}"


def _build_payload(
    *,
    model: str,
    system: str,
    messages: Sequence[AgentMessage],
    tools: Sequence[AgentTool],
) -> dict[str, Any]:
    converted = [_message_to_openai(message) for message in messages]
    payload: dict[str, Any] = {
        "model": model,
        "stream": True,
        "messages": [{"role": "system", "content": system}, *converted],
        "stream_options": {"include_usage": True},
    }
    if tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": dict(tool.parameters),
                },
            }
            for tool in tools
        ]
    return payload


def _message_to_openai(message: AgentMessage) -> dict[str, Any]:
    if isinstance(message, UserMessage):
        return {"role": "user", "content": message.text}
    if isinstance(message, AssistantMessage):
        payload: dict[str, Any] = {"role": "assistant", "content": message.text}
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in message.tool_calls
            ]
        return payload
    if isinstance(message, ToolResultMessage):
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.text,
        }
    raise TypeError(f"unsupported message role for chat payload: {type(message).__name__}")


class _ToolCallBuilder:
    __slots__ = ("id", "name", "arguments_parts")

    def __init__(self) -> None:
        self.id = ""
        self.name = ""
        self.arguments_parts: list[str] = []

    def add_delta(self, delta: Mapping[str, Any]) -> None:
        call_id = delta.get("id")
        if isinstance(call_id, str):
            self.id = call_id
        function = delta.get("function")
        if not isinstance(function, Mapping):
            return
        name = function.get("name")
        if isinstance(name, str):
            self.name = name
        arguments = function.get("arguments")
        if isinstance(arguments, str):
            self.arguments_parts.append(arguments)

    def build(self, index: int) -> ToolCall:
        arguments_text = "".join(self.arguments_parts)
        try:
            arguments = json.loads(arguments_text) if arguments_text else {}
        except json.JSONDecodeError:
            arguments = {"_raw_arguments": arguments_text}
        return ToolCall(id=self.id or f"tool-call-{index}", name=self.name, arguments=arguments)


class _ChunkParser:
    """Accumulate chat-completions SSE chunks into canonical block events."""

    def __init__(self, partial: AssistantMessage) -> None:
        self._partial = partial
        self._done = False
        self._errored = False
        self._active_kind: str | None = None
        self._finish_reason: str | None = None
        self._usage = Usage()
        self._tool_builders: dict[int, _ToolCallBuilder] = {}

    @property
    def done(self) -> bool:
        return self._done

    def feed(self, line: str) -> list[AssistantMessageEvent]:
        if self._done:
            return []
        data = line[5:].strip() if line.startswith("data:") else ""
        if not data:
            return []
        if data == "[DONE]":
            self._done = True
            return []
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError as exc:
            self._done = True
            self._errored = True
            return [_error_event(self._partial, f"provider returned invalid JSON chunk: {exc}")]
        usage = chunk.get("usage")
        if isinstance(usage, Mapping):
            self._usage = _parse_usage(usage)
        choices = chunk.get("choices")
        if not isinstance(choices, list) or not choices:
            return []
        choice = choices[0]
        if not isinstance(choice, Mapping):
            return []
        finish_reason = choice.get("finish_reason")
        if isinstance(finish_reason, str) and finish_reason:
            self._finish_reason = finish_reason
        delta = choice.get("delta")
        if not isinstance(delta, Mapping):
            return []
        events: list[AssistantMessageEvent] = []
        content = delta.get("content")
        if isinstance(content, str) and content:
            events.extend(self._text_delta(content))
        thinking = _thinking_delta(delta)
        if thinking is not None:
            events.extend(self._thinking_delta(thinking))
        for tool_delta in _tool_call_deltas(delta):
            raw_index = tool_delta.get("index", 0)
            index = raw_index if isinstance(raw_index, int) else 0
            builder = self._tool_builders.setdefault(index, _ToolCallBuilder())
            builder.add_delta(tool_delta)
        return events

    def _text_delta(self, delta: str) -> list[AssistantMessageEvent]:
        events: list[AssistantMessageEvent] = []
        if self._active_kind != "text":
            events.extend(self._close_active_block())
            self._active_kind = "text"
            self._partial.content.append(TextContent(text=""))
            events.append(
                TextStartEvent(
                    content_index=len(self._partial.content) - 1,
                    partial=_snapshot(self._partial),
                )
            )
        block = self._partial.content[-1]
        if isinstance(block, TextContent):
            block.text += delta
        events.append(
            TextDeltaEvent(
                content_index=len(self._partial.content) - 1,
                delta=delta,
                partial=_snapshot(self._partial),
            )
        )
        return events

    def _thinking_delta(self, delta: str) -> list[AssistantMessageEvent]:
        events: list[AssistantMessageEvent] = []
        if self._active_kind != "thinking":
            events.extend(self._close_active_block())
            self._active_kind = "thinking"
            self._partial.content.append(ThinkingContent(thinking=""))
            events.append(
                ThinkingStartEvent(
                    content_index=len(self._partial.content) - 1,
                    partial=_snapshot(self._partial),
                )
            )
        block = self._partial.content[-1]
        if isinstance(block, ThinkingContent):
            block.thinking += delta
        events.append(
            ThinkingDeltaEvent(
                content_index=len(self._partial.content) - 1,
                delta=delta,
                partial=_snapshot(self._partial),
            )
        )
        return events

    def _close_active_block(self) -> list[AssistantMessageEvent]:
        if self._active_kind is None or not self._partial.content:
            return []
        index = len(self._partial.content) - 1
        block = self._partial.content[index]
        self._active_kind = None
        if isinstance(block, TextContent):
            event: AssistantMessageEvent = TextEndEvent(
                content_index=index, content=block.text, partial=_snapshot(self._partial)
            )
            return [event]
        if isinstance(block, ThinkingContent):
            event = ThinkingEndEvent(
                content_index=index, content=block.thinking, partial=_snapshot(self._partial)
            )
            return [event]
        return []

    def finalize(self) -> list[AssistantMessageEvent]:
        if self._errored:
            return []
        events = self._close_active_block()
        tool_calls = [
            builder.build(index) for index, builder in sorted(self._tool_builders.items())
        ]
        for call in tool_calls:
            self._partial.content.append(call)
            index = len(self._partial.content) - 1
            snapshot = _snapshot(self._partial)
            events.append(ToolCallStartEvent(content_index=index, partial=snapshot))
            events.append(ToolCallEndEvent(content_index=index, tool_call=call, partial=snapshot))
        final = _snapshot(self._partial)
        final.usage = self._usage
        final.stop_reason = _finish_reason(self._finish_reason, has_tools=bool(tool_calls))
        events.append(AssistantDoneEvent(reason=final.stop_reason, message=final))
        return events


def _finish_reason(reason: str | None, *, has_tools: bool) -> DoneReason:
    if has_tools or reason in _STOP_REASON_MAP:
        return "toolUse"
    if reason in _LENGTH_REASONS:
        return "length"
    return "stop"


def _parse_usage(usage: Mapping[str, Any]) -> Usage:
    prompt_details = usage.get("prompt_tokens_details")
    completion_details = usage.get("completion_tokens_details")
    cache_read = 0
    if isinstance(prompt_details, Mapping):
        value = prompt_details.get("cached_tokens")
        if isinstance(value, int):
            cache_read = value
    reasoning = None
    if isinstance(completion_details, Mapping):
        value = completion_details.get("reasoning_tokens")
        if isinstance(value, int):
            reasoning = value
    return Usage(
        input=_int_or(usage.get("prompt_tokens"), 0),
        output=_int_or(usage.get("completion_tokens"), 0),
        cache_read=cache_read,
        reasoning=reasoning,
        total_tokens=_int_or(usage.get("total_tokens"), 0),
    )


def _int_or(value: object, default: int) -> int:
    return value if isinstance(value, int) else default


def _thinking_delta(delta: Mapping[str, Any]) -> str | None:
    for key in ("reasoning_content", "reasoning"):
        value = delta.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _tool_call_deltas(delta: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    tool_calls = delta.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    return [delta for delta in tool_calls if isinstance(delta, Mapping)]
