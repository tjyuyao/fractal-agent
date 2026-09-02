"""Deterministic Pi-compatible model provider for tests.

Ported from huggingface/tau ``tau_ai/fake.py`` v0.4.1 (MIT), import paths
adjusted. Used for golden/deterministic loop tests; never touches a network.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

from fractal_runtime.messages import AgentMessage
from fractal_runtime.provider import CancellationToken
from fractal_runtime.provider_events import AssistantMessageEvent
from fractal_runtime.tools import AgentTool


class FakeProvider:
    """A provider that replays predefined assistant event streams."""

    def __init__(self, streams: Iterable[Iterable[AssistantMessageEvent]]) -> None:
        self._streams = [list(stream) for stream in streams]
        self.calls: list[tuple[str, str, list[AgentMessage], list[AgentTool]]] = []
        self.session_ids: list[str | None] = []

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
        self.calls.append((model, system, list(messages), list(tools)))
        self.session_ids.append(session_id)
        stream = self._streams.pop(0) if self._streams else []

        async def iterator() -> AsyncIterator[AssistantMessageEvent]:
            for event in stream:
                if signal is not None and signal.is_cancelled():
                    return
                yield event

        return iterator()
