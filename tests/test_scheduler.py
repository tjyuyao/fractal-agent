"""D3 满足关系与 D6 判定点（g/v/r）的语义测试 + 串行驱动器（Phase 1 特化）。"""

from __future__ import annotations

import pytest

from fractal_kernel import guard
from fractal_kernel.models import CheckSpec, Contract, Evidence, Instance, Policy, WorkPacket
from fractal_kernel.scheduler import (
    BuildResult,
    CheckOutcome,
    SerialDriver,
    decide,
    granularity,
    satisfied,
    verify,
)
from fractal_kernel.store import EventLog, EventType, fold


def _contract(check_count: int = 1) -> Contract:
    checks = tuple(
        CheckSpec(id=f"ch-{i}", kind="exec", spec={"command": "true"}) for i in range(check_count)
    )
    return Contract.create(intent="i", checks=checks)


def _evidence(contract: Contract, value: bool) -> Evidence:
    return Evidence(
        contract_id=contract.id,
        results={ch.id: value for ch in contract.checks},
        sigma_ref="s",
    )


class _PassBody:
    def build(self, packet: WorkPacket) -> BuildResult:
        return BuildResult(artifacts=("out",), sigma_ref="sigma-1")


class _OverflowBody:
    def build(self, packet: WorkPacket) -> BuildResult:
        return BuildResult(overflow=True)


class _Runner:
    """前 fail_calls 次判定失败，之后全部通过（调用序 == 尝试序）。"""

    def __init__(self, fail_calls: int = 0) -> None:
        self.calls = 0
        self.fail_calls = fail_calls

    def run(self, check: CheckSpec, packet: WorkPacket) -> CheckOutcome:
        self.calls += 1
        return CheckOutcome(ok=self.calls > self.fail_calls, artifact="log")


class TestSatisfied:
    def test_all_true_is_satisfied(self) -> None:
        contract = _contract(2)
        assert satisfied(contract, _evidence(contract, True))

    def test_any_false_is_not_satisfied(self) -> None:
        contract = _contract(2)
        evidence = _evidence(contract, True)
        evidence.results["ch-1"] = False
        assert not satisfied(contract, evidence)

    def test_missing_result_is_not_satisfied(self) -> None:
        contract = _contract(2)
        partial = Evidence(contract_id=contract.id, results={"ch-0": True}, sigma_ref="s")
        assert not satisfied(contract, partial)

    def test_no_checks_contract_always_satisfied(self) -> None:
        assert satisfied(Contract.create(intent="i"), Evidence(contract_id="x", results={}))


class TestVerify:
    def test_deterministic_accept(self) -> None:
        contract = _contract()
        assert verify(contract, _evidence(contract, True)) == "accept"

    def test_deterministic_reject(self) -> None:
        contract = _contract()
        assert verify(contract, _evidence(contract, False)) == "reject"


class TestGranularity:
    def test_checks_over_threshold_decomposes(self) -> None:
        assert granularity(_contract(3), Policy(granularity_threshold=2)) == "decompose"

    def test_checks_under_threshold_direct(self) -> None:
        assert granularity(_contract(2), Policy(granularity_threshold=8)) == "direct"


class TestDecide:
    def test_autonomous_ladder_retry_first(self) -> None:
        contract = _contract()
        policy = Policy(mode="autonomous", retry_count=2)
        assert decide(contract, _evidence(contract, False), policy) == "retry"

    def test_autonomous_ladder_reassign_after_retry_exhausted(self) -> None:
        contract = _contract()
        policy = Policy(mode="autonomous", can_reassign=True)
        assert decide(contract, _evidence(contract, False), policy) == "reassign"

    def test_autonomous_ladder_replan_before_ask(self) -> None:
        contract = _contract()
        policy = Policy(mode="autonomous", can_replan=True)
        assert decide(contract, _evidence(contract, False), policy) == "replan"

    def test_autonomous_ladder_fallback_ask_user(self) -> None:
        contract = _contract()
        policy = Policy(mode="autonomous")
        assert decide(contract, _evidence(contract, False), policy) == "ask_user"

    def test_interactive_defaults_to_ask_user(self) -> None:
        contract = _contract()
        policy = Policy(mode="interactive", retry_count=5, can_reassign=True, can_replan=True)
        assert decide(contract, _evidence(contract, False), policy) == "ask_user"


class TestSerialDriver:
    def _log(self, tmp_path) -> EventLog:
        return EventLog(tmp_path / "events.jsonl")

    def test_accept_path_records_full_chain(self, tmp_path) -> None:
        log = self._log(tmp_path)
        driver = SerialDriver(log, _PassBody(), _Runner())
        packet = WorkPacket(contract=_contract(2))

        outcome = driver.process(packet, Policy(mode="autonomous"))

        assert outcome.accepted
        assert outcome.evidence is not None
        assert outcome.evidence.results == {"ch-0": True, "ch-1": True}
        assert outcome.evidence.sigma_ref == "sigma-1"
        assert outcome.decision is None
        assert outcome.attempts == 1
        types = [e.type for e in log.events]
        assert types == [
            EventType.DELEGATION_LAUNCHED,
            EventType.ATTEMPT_STARTED,
            EventType.CHECK_EXECUTED,
            EventType.CHECK_EXECUTED,
            EventType.EVIDENCE_RECORDED,
            EventType.ATTEMPT_FINISHED,
        ]

    def test_retry_consumes_budget_then_passes(self, tmp_path) -> None:
        log = self._log(tmp_path)
        driver = SerialDriver(log, _PassBody(), _Runner(fail_calls=1))
        packet = WorkPacket(contract=_contract())
        policy = Policy(mode="autonomous", retry_count=1)

        outcome = driver.process(packet, policy)

        assert outcome.accepted
        assert outcome.attempts == 2
        decisions = [e for e in log.events if e.type is EventType.DECISION_MADE]
        assert [e.payload["decision"] for e in decisions] == ["retry"]

    def test_retry_exhaustion_falls_through_ladder(self, tmp_path) -> None:
        log = self._log(tmp_path)
        driver = SerialDriver(log, _PassBody(), _Runner(fail_calls=99))
        packet = WorkPacket(contract=_contract())
        policy = Policy(mode="autonomous", retry_count=1)

        outcome = driver.process(packet, policy)

        assert not outcome.accepted
        assert outcome.attempts == 2
        assert outcome.decision == "ask_user"

    def test_interactive_rejects_immediately(self, tmp_path) -> None:
        log = self._log(tmp_path)
        driver = SerialDriver(log, _PassBody(), _Runner(fail_calls=99))
        packet = WorkPacket(contract=_contract())

        outcome = driver.process(packet, Policy(mode="interactive"))

        assert not outcome.accepted
        assert outcome.attempts == 1
        assert outcome.decision == "ask_user"

    def test_context_overflow_routes_to_replan(self, tmp_path) -> None:
        log = self._log(tmp_path)
        driver = SerialDriver(log, _OverflowBody(), _Runner())
        packet = WorkPacket(contract=_contract())
        policy = Policy(mode="autonomous", retry_count=3)

        outcome = driver.process(packet, policy)

        assert not outcome.accepted
        assert outcome.evidence is None
        assert outcome.decision == "replan"
        assert EventType.CHECK_EXECUTED not in [e.type for e in log.events]
        finished = [e for e in log.events if e.type is EventType.ATTEMPT_FINISHED]
        assert finished[0].payload["status"] == "interrupted"

    def test_reassign_and_replan_are_terminal_without_infra(self, tmp_path) -> None:
        log = self._log(tmp_path)
        driver = SerialDriver(log, _PassBody(), _Runner(fail_calls=99))
        packet = WorkPacket(contract=_contract())
        policy = Policy(mode="autonomous", can_reassign=True)

        outcome = driver.process(packet, policy)
        assert outcome.decision == "reassign"
        assert outcome.attempts == 1

    def test_events_replay_to_consistent_state(self, tmp_path) -> None:
        """驱动器产生的事件流可被 fold 完整恢复（A1 证据链）。"""
        log = self._log(tmp_path)
        log.append(EventType.INSTANCE_CREATED, {"instance": Instance(id="i-root").model_dump()})
        contract = _contract()
        log.append(EventType.CONTRACT_REGISTERED, {"contract": contract.model_dump()})
        driver = SerialDriver(log, _PassBody(), _Runner())
        outcome = driver.process(WorkPacket(contract=contract), Policy(mode="autonomous"))

        state = fold(log.events)
        assert outcome.accepted
        assert state.handlers == {contract.id: "i-root"}
        assert contract.id in state.evidence

    def test_double_processing_rejected(self, tmp_path) -> None:
        """同一契约二次 process 被驱动器拒绝（T1 写入路径）。"""
        log = self._log(tmp_path)
        driver = SerialDriver(log, _PassBody(), _Runner())
        packet = WorkPacket(contract=_contract())
        driver.process(packet, Policy(mode="autonomous"))

        with pytest.raises(guard.GuardError) as excinfo:
            driver.process(packet, Policy(mode="autonomous"))
        assert excinfo.value.code is guard.ErrorCode.ONE_HANDLER
