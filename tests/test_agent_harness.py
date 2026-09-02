"""AgentHarness 状态壳测试：消息累积、steering 队列、监听器、并发互斥。"""

from __future__ import annotations

from contextlib import suppress

import pytest

from agent_helpers import assistant_done, assistant_start, text_delta
from fractal_runtime.fake_provider import FakeProvider
from fractal_runtime.harness import AgentHarness, AgentHarnessConfig
from fractal_runtime.messages import AssistantMessage, UserMessage


def _harness(provider: FakeProvider) -> AgentHarness:
    return AgentHarness(
        AgentHarnessConfig(provider=provider, model="fake", system="sys", max_turns=8)
    )


async def test_prompt_accumulates_messages_and_emits_events() -> None:
    assistant = AssistantMessage(content="Hello", model="fake")
    provider = FakeProvider([[assistant_start(), text_delta("Hello"), assistant_done(assistant)]])
    harness = _harness(provider)

    events = [event async for event in harness.prompt("Say hello")]

    assert events[0].type == "agent_start"
    assert events[-1].type == "agent_end"
    assert [m.role for m in harness.messages] == ["user", "assistant"]
    assert harness.messages[-1].text == "Hello"


async def test_steering_message_injected_at_turn_boundary() -> None:
    assistant1 = AssistantMessage(content="first", stop_reason="stop", model="fake")
    assistant2 = AssistantMessage(content="second", stop_reason="stop", model="fake")
    provider = FakeProvider(
        [
            [assistant_start(), assistant_done(assistant1)],
            [assistant_start(), assistant_done(assistant2)],
        ]
    )
    harness = _harness(provider)
    harness.steer("focus on X")

    events = [event async for event in harness.prompt("go")]

    steering = [
        m for m in harness.messages if isinstance(m, UserMessage) and m.text == "focus on X"
    ]
    assert len(steering) == 1
    agent_ends = [e for e in events if e.type == "agent_end"]
    assert len(agent_ends) == 1
    assert not harness.has_queued_messages()


async def test_listener_receives_all_events() -> None:
    assistant = AssistantMessage(content="Hello", model="fake")
    provider = FakeProvider([[assistant_start(), assistant_done(assistant)]])
    harness = _harness(provider)
    seen: list[str] = []

    def listener(event: object) -> None:
        seen.append(getattr(event, "type", ""))

    harness.subscribe(listener)
    async for _event in harness.prompt("go"):
        pass

    assert seen[0] == "agent_start"
    assert seen[-1] == "agent_end"


async def test_double_run_rejected() -> None:
    assistant = AssistantMessage(content="Hello", stop_reason="stop", model="fake")
    provider = FakeProvider([[assistant_start(), assistant_done(assistant)]])
    harness = _harness(provider)
    stream = harness.prompt("go")
    await anext(stream)

    with pytest.raises(RuntimeError):
        harness.prompt("again")
    with suppress(StopAsyncIteration):
        await anext(stream)
