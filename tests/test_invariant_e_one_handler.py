"""I-OneHandler / T1 不变量测试：E-ONE-HANDLER。"""

import pytest

from fractal_kernel import guard
from fractal_kernel.models import Contract
from fractal_kernel.store import EventLog, EventType, fold


def test_second_handler_rejected() -> None:
    handlers = {"c-1": "i-1"}
    with pytest.raises(guard.GuardError) as excinfo:
        guard.check_one_handler(handlers, "c-1")
    assert excinfo.value.code is guard.ErrorCode.ONE_HANDLER


def test_first_handler_accepted() -> None:
    guard.check_one_handler({}, "c-1")


def test_fold_rejects_double_launch(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    contract = Contract(id="c-1", intent="i", checks=())
    log.append(EventType.CONTRACT_REGISTERED, {"contract": contract.model_dump()})
    log.append(EventType.DELEGATION_LAUNCHED, {"contract_id": "c-1", "instance_id": "i-1"})
    log.append(EventType.DELEGATION_LAUNCHED, {"contract_id": "c-1", "instance_id": "i-2"})
    with pytest.raises(guard.GuardError) as excinfo:
        fold(log.events)
    assert excinfo.value.code is guard.ErrorCode.ONE_HANDLER
