"""Provider contract owned by the portable agent layer.

Ported from huggingface/tau ``tau_agent/provider.py`` v0.4.1 (MIT), unmodified
apart from import paths.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from fractal_runtime.messages import AgentMessage
from fractal_runtime.provider_events import AssistantMessageEvent
from fractal_runtime.tools import AgentTool


class CancellationToken(Protocol):
    def is_cancelled(self) -> bool:
        """Return whether the current stream should stop."""
        ...


class ModelProvider(Protocol):
    """Provider-neutral Pi-compatible model stream interface."""

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
        """Stream one model response as assistant message events.

        Providers may use ``session_id`` for request routing or prompt-cache
        affinity. Unsupported providers ignore it.
        """
        ...
