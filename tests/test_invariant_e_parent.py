"""I-Parent / D4 不变量测试：E-PARENT。"""

import pytest

from fractal_kernel import guard
from fractal_kernel.models import Instance
from fractal_kernel.store import EventLog, EventType, fold


def test_missing_parent_rejected() -> None:
    instances = {"i-1": Instance(id="i-1")}
    orphan = Instance(id="i-2", parent="i-404")
    with pytest.raises(guard.GuardError) as excinfo:
        guard.check_instance_parent(instances, orphan)
    assert excinfo.value.code is guard.ErrorCode.PARENT


def test_root_and_valid_child_accepted() -> None:
    instances = {"i-1": Instance(id="i-1")}
    guard.check_instance_parent(instances, Instance(id="i-3"))
    guard.check_instance_parent(instances, Instance(id="i-2", parent="i-1"))


def test_fold_rejects_orphan_instance(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    log.append(EventType.INSTANCE_CREATED, {"instance": Instance(id="i-1").model_dump()})
    orphan = Instance(id="i-2", parent="i-404")
    log.append(EventType.INSTANCE_CREATED, {"instance": orphan.model_dump()})
    with pytest.raises(guard.GuardError) as excinfo:
        fold(log.events)
    assert excinfo.value.code is guard.ErrorCode.PARENT
