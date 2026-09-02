"""Canonical event constructors for deterministic loop tests.

Adapted from huggingface/tau ``tests/pi_event_helpers.py`` v0.4.1 (MIT) for
the ported fractal_runtime event vocabulary.
"""

from __future__ import annotations

from fractal_runtime.messages import AssistantMessage, ToolCall
from fractal_runtime.provider_events import (
    AssistantDoneEvent,
    AssistantErrorEvent,
    AssistantStartEvent,
    TextDeltaEvent,
    ToolCallEndEvent,
)


def assistant_start(model: str = "fake") -> AssistantStartEvent:
    return AssistantStartEvent(partial=AssistantMessage(model=model))


def text_delta(delta: str) -> TextDeltaEvent:
    return TextDeltaEvent(content_index=0, delta=delta, partial=AssistantMessage(content=delta))


def tool_call_end(tool_call: ToolCall) -> ToolCallEndEvent:
    return ToolCallEndEvent(
        content_index=0,
        tool_call=tool_call,
        partial=AssistantMessage(content=[tool_call]),
    )


def assistant_done(
    message: AssistantMessage | dict[str, object],
    finish_reason: str | None = None,
) -> AssistantDoneEvent:
    final = (
        message
        if isinstance(message, AssistantMessage)
        else AssistantMessage.model_validate(message)
    )
    if final.tool_calls or finish_reason in {"tool_calls", "tool_use", "toolUse"}:
        reason = "toolUse"
    elif finish_reason in {"length", "max_tokens", "MAX_TOKENS", "incomplete"}:
        reason = "length"
    else:
        reason = "stop"
    final.stop_reason = reason  # type: ignore[assignment]
    return AssistantDoneEvent(reason=reason, message=final)  # type: ignore[arg-type]


def assistant_error(message: str) -> AssistantErrorEvent:
    error = AssistantMessage(stop_reason="error", error_message=message)
    return AssistantErrorEvent(reason="error", error=error)
