"""核心规范对象的不变量冒烟测试（D1/D2/D4.5、I-Contract、T4）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fractal_kernel.models import (
    Attempt,
    AttemptStatus,
    Checkpoint,
    CheckSpec,
    Contract,
    Evidence,
    Instance,
    Mode,
    Policy,
    Task,
    TaskStatus,
    WorkPacket,
    contract_digest,
)


def _contract() -> Contract:
    check = CheckSpec(id="ch-1", kind="exec", spec={"command": "true"})
    return Contract(id="c-1", intent="do a thing", checks=(check,))


class TestContract:
    def test_frozen_honors_i_contract(self) -> None:
        contract = _contract()
        with pytest.raises(ValidationError):
            contract.intent = "changed"  # type: ignore[misc]

    def test_checks_is_tuple(self) -> None:
        assert isinstance(_contract().checks, tuple)


class TestEvidence:
    def test_binds_single_contract(self) -> None:
        evidence = Evidence(
            contract_id="c-1",
            results={"ch-1": True},
            artifacts=(),
            sigma_ref="0" * 40,
        )
        assert evidence.contract_id == "c-1"

    def test_frozen(self) -> None:
        evidence = Evidence(contract_id="c-1", results={}, sigma_ref="x")
        with pytest.raises(ValidationError):
            evidence.contract_id = "c-2"  # type: ignore[misc]


class TestWorkPacket:
    def test_wraps_contract(self) -> None:
        packet = WorkPacket(contract=_contract(), tools=("read", "write"))
        assert packet.contract.id == "c-1"
        assert packet.checkpoint_id is None


class TestContractCreate:
    def test_content_addressed_id_is_stable(self) -> None:
        checks = (CheckSpec(id="ch-1", kind="exec", spec={"command": "true"}),)
        a = Contract.create(intent="same intent", checks=checks)
        b = Contract.create(intent="same intent", checks=checks)
        assert a.id == b.id == f"c-{contract_digest('same intent', checks)[:16]}"

    def test_different_content_different_id(self) -> None:
        assert Contract.create(intent="x").id != Contract.create(intent="y").id


class TestInstance:
    def test_root_has_no_parent(self) -> None:
        assert Instance(id="i-1").parent is None

    def test_frozen_honors_i_parent_record(self) -> None:
        instance = Instance(id="i-2", parent="i-1", boundary=("src/",))
        with pytest.raises(ValidationError):
            instance.parent = None  # type: ignore[misc]


class TestTask:
    def test_defaults(self) -> None:
        task = Task(id="t-1", contract_id="c-1")
        assert task.status is TaskStatus.PENDING
        assert task.deps == ()

    def test_frozen(self) -> None:
        task = Task(id="t-1", contract_id="c-1")
        with pytest.raises(ValidationError):
            task.status = TaskStatus.ACCEPTED  # type: ignore[misc]


class TestAttempt:
    def test_status_vocabulary_matches_d8(self) -> None:
        assert {s.value for s in AttemptStatus} == {
            "pending",
            "running",
            "passed",
            "failed",
            "interrupted",
        }

    def test_defaults(self) -> None:
        attempt = Attempt(id="a-1", task_id="t-1", owner="i-1")
        assert attempt.status is AttemptStatus.PENDING
        assert attempt.checkpoint_id is None
        assert attempt.result is None


class TestCheckpoint:
    def test_bound_to_attempt_and_frozen(self) -> None:
        checkpoint = Checkpoint(id="ck-1", attempt_id="a-1", code_refs=("abc123",))
        with pytest.raises(ValidationError):
            checkpoint.code_refs = ()  # type: ignore[misc]


class TestPolicy:
    def test_v0_defaults_interactive(self) -> None:
        policy = Policy()
        assert policy.mode == "interactive"
        assert policy.max_depth == 4
        assert policy.can_reassign is False

    def test_frozen(self) -> None:
        with pytest.raises(ValidationError):
            Policy().max_depth = 99  # type: ignore[misc]


class TestMode:
    def test_four_capabilities_per_d5(self) -> None:
        assert {m.value for m in Mode} == {"plan", "build", "delegate", "supervise"}
