"""I-Evidence / D2 不变量测试：E-EVIDENCE-UNBOUND。"""

import pytest

from fractal_kernel import guard
from fractal_kernel.models import Contract, Evidence
from fractal_kernel.store import EventLog, EventType, fold


def _evidence(contract_id: str) -> Evidence:
    return Evidence(contract_id=contract_id, results={"ch-1": True}, sigma_ref="s1")


def test_evidence_for_unknown_contract_rejected() -> None:
    with pytest.raises(guard.GuardError) as excinfo:
        guard.check_evidence_binding({}, _evidence("c-404"))
    assert excinfo.value.code is guard.ErrorCode.EVIDENCE_UNBOUND


def test_fold_rejects_unbound_evidence(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    contract = Contract(id="c-1", intent="i", checks=())
    log.append(EventType.CONTRACT_REGISTERED, {"contract": contract.model_dump()})
    log.append(EventType.EVIDENCE_RECORDED, {"evidence": _evidence("c-404").model_dump()})
    with pytest.raises(guard.GuardError) as excinfo:
        fold(log.events)
    assert excinfo.value.code is guard.ErrorCode.EVIDENCE_UNBOUND


def test_fold_records_bound_evidence(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    contract = Contract(id="c-1", intent="i", checks=())
    log.append(EventType.CONTRACT_REGISTERED, {"contract": contract.model_dump()})
    log.append(EventType.EVIDENCE_RECORDED, {"evidence": _evidence("c-1").model_dump()})
    state = fold(log.events)
    assert state.evidence["c-1"] == (_evidence("c-1"),)
