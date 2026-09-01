"""I-Contract / T4 不变量测试：E-CONTRACT-MUTATE。"""

import pytest
from pydantic import ValidationError

from fractal_kernel import guard
from fractal_kernel.models import CheckSpec, Contract
from fractal_kernel.store import EventLog, EventType, fold


def _contract(intent: str = "do a thing") -> Contract:
    check = CheckSpec(id="ch-1", kind="exec", spec={"command": "true"})
    return Contract(id="c-1", intent=intent, checks=(check,))


def test_frozen_model_blocks_mutation() -> None:
    contract = _contract()
    with pytest.raises(ValidationError):
        contract.intent = "changed"  # type: ignore[misc]


def test_reregistration_with_different_content_rejected() -> None:
    existing = {"c-1": _contract()}
    with pytest.raises(guard.GuardError) as excinfo:
        guard.check_contract_registration(existing, _contract(intent="changed"))
    assert excinfo.value.code is guard.ErrorCode.CONTRACT_MUTATE


def test_reregistration_identical_content_is_idempotent() -> None:
    existing = {"c-1": _contract()}
    guard.check_contract_registration(existing, _contract())


def test_fold_rejects_tampered_history(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    contract = _contract()
    log.append(EventType.CONTRACT_REGISTERED, {"contract": contract.model_dump()})
    conflicting = Contract(id=contract.id, intent="different", checks=())
    log.append(EventType.CONTRACT_REGISTERED, {"contract": conflicting.model_dump()})
    with pytest.raises(guard.GuardError) as excinfo:
        fold(log.events)
    assert excinfo.value.code is guard.ErrorCode.CONTRACT_MUTATE
