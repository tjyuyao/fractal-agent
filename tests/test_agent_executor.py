"""LoopBuildBody 测试：BuildBody 协议、产物收集、溢出信号、Guard 拒绝事件。"""

from __future__ import annotations

from pathlib import Path

from agent_helpers import assistant_done, assistant_start, tool_call_end
from fractal_kernel.models import CheckSpec, Contract, Policy, WorkPacket
from fractal_kernel.scheduler import CheckOutcome, SerialDriver
from fractal_kernel.store import EventLog, EventType
from fractal_runtime.executor import LoopBuildBody, LoopBuildConfig, build_system_prompt
from fractal_runtime.fake_provider import FakeProvider
from fractal_runtime.messages import AssistantMessage, ToolCall
from fractal_runtime.provider_events import (
    AssistantErrorEvent,
)


def _contract(check_count: int = 1) -> Contract:
    checks = tuple(
        CheckSpec(id=f"ch-{i}", kind="exec", spec={"command": "true"}) for i in range(check_count)
    )
    return Contract.create(intent="write a module", checks=checks)


def _tool_call(call_id: str, name: str, arguments: dict[str, object]) -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments)


def _write_turn(call: ToolCall) -> list[object]:
    message = AssistantMessage(content=[call], stop_reason="toolUse", model="fake")
    return [
        assistant_start(),
        tool_call_end(call),
        assistant_done(message),
    ]


def _final_turn(text: str) -> list[object]:
    message = AssistantMessage(content=text, stop_reason="stop", model="fake")
    return [assistant_start(), assistant_done(message)]


class _PassRunner:
    def run(self, check: CheckSpec, packet: WorkPacket) -> CheckOutcome:
        return CheckOutcome(ok=True, artifact="log")


class TestLoopBuildBody:
    def _body(self, provider: FakeProvider, tmp_path: Path, **kw: object) -> LoopBuildBody:
        return LoopBuildBody(
            LoopBuildConfig(provider=provider, model="fake"),
            boundary=("src",),
            cwd=tmp_path,
        )

    def test_artifacts_collected_and_context_built(self, tmp_path: Path) -> None:
        call = _tool_call("c1", "write_file", {"path": "src/x.py", "content": "print(1)"})
        provider = FakeProvider([_write_turn(call), _final_turn("done")])
        body = self._body(provider, tmp_path)
        packet = WorkPacket(contract=_contract(), tools=("write_file", "read_file", "edit_file"))

        result = body.build(packet)

        assert result.artifacts == ("src/x.py",)
        assert result.overflow is False
        assert (tmp_path / "src/x.py").read_text() == "print(1)"
        model, system, _messages, tools = provider.calls[0]
        assert model == "fake"
        assert "Contract intent: write a module" in system
        assert "Writable paths (manifest): src" in system
        assert [t.name for t in tools] == ["write_file", "read_file", "edit_file"]

    def test_out_of_boundary_write_rejected_and_logged(self, tmp_path: Path) -> None:
        call = _tool_call("c1", "write_file", {"path": "README.md", "content": "evil"})
        provider = FakeProvider([_write_turn(call), _final_turn("done")])
        log = EventLog(tmp_path / "events.jsonl")
        body = LoopBuildBody(
            LoopBuildConfig(provider=provider, model="fake"),
            boundary=("src",),
            cwd=tmp_path,
            log=log,
        )
        packet = WorkPacket(contract=_contract(), tools=("write_file",))

        result = body.build(packet)

        assert result.artifacts == ()
        assert not (tmp_path / "README.md").exists()
        rejections = [e for e in log.events if e.type is EventType.GUARD_REJECTED]
        assert len(rejections) == 1
        assert rejections[0].payload["code"] == "E-BOUNDARY-WRITE"
        assert rejections[0].payload["path"] == "README.md"

    def test_tools_whitelist_filters_registry(self, tmp_path: Path) -> None:
        call = _tool_call("c1", "write_file", {"path": "src/x.py", "content": "x"})
        provider = FakeProvider([_write_turn(call), _final_turn("done")])
        body = self._body(provider, tmp_path)
        packet = WorkPacket(contract=_contract(), tools=("write_file",))

        body.build(packet)

        assert [t.name for t in provider.calls[0][3]] == ["write_file"]

    def test_context_overflow_signals_decompose(self, tmp_path: Path) -> None:
        error = AssistantMessage(
            stop_reason="error", error_message="context_length_exceeded: reduce input", model="fake"
        )
        provider = FakeProvider(
            [[assistant_start(), AssistantErrorEvent(reason="error", error=error)]]
        )
        body = self._body(provider, tmp_path)
        packet = WorkPacket(contract=_contract(), tools=("write_file",))

        result = body.build(packet)

        assert result.overflow is True
        assert result.artifacts == ()

    def test_plain_provider_error_is_not_overflow(self, tmp_path: Path) -> None:
        error = AssistantMessage(
            stop_reason="error", error_message="provider HTTP 500", model="fake"
        )
        provider = FakeProvider(
            [[assistant_start(), AssistantErrorEvent(reason="error", error=error)]]
        )
        body = self._body(provider, tmp_path)
        packet = WorkPacket(contract=_contract(), tools=())

        result = body.build(packet)

        assert result.overflow is False

    def test_overflow_routes_to_replan_via_serial_driver(self, tmp_path: Path) -> None:
        """AM-0.1-07 闭环：build 溢出 → 驱动器 attempt.interrupted + replan。"""
        error = AssistantMessage(
            stop_reason="error", error_message="context_length_exceeded: too long", model="fake"
        )
        provider = FakeProvider(
            [[assistant_start(), AssistantErrorEvent(reason="error", error=error)]]
        )
        body = LoopBuildBody(
            LoopBuildConfig(provider=provider, model="fake"), boundary=("src",), cwd=tmp_path
        )
        log = EventLog(tmp_path / "events.jsonl")
        driver = SerialDriver(log, body, _PassRunner())
        packet = WorkPacket(contract=_contract(), tools=())

        outcome = driver.process(packet, Policy(mode="autonomous", retry_count=3))

        assert not outcome.accepted
        assert outcome.decision == "replan"
        assert outcome.evidence is None
        finished = [e for e in log.events if e.type is EventType.ATTEMPT_FINISHED]
        assert finished[0].payload["status"] == "interrupted"


class TestSystemPrompt:
    def test_prompt_contains_constraints_and_checks(self) -> None:
        packet = WorkPacket(
            contract=_contract(2),
            constraints=("no network", "keep it small"),
        )

        prompt = build_system_prompt(packet, ("src", "docs"))

        assert "Acceptance checks: ch-0 [exec]; ch-1 [exec]" in prompt
        assert "Constraints: no network; keep it small" in prompt
        assert "Writable paths (manifest): src, docs" in prompt
        assert "E-BOUNDARY-WRITE" in prompt

    def test_prompt_declares_empty_manifest(self) -> None:
        prompt = build_system_prompt(WorkPacket(contract=_contract()), ())

        assert "none declared" in prompt
