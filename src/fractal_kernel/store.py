"""Append-only 事件日志：唯一事实来源，状态 = fold(events)（ADR-0003）。

事件类型词汇表在此冻结（docs/architecture.md 事件日志节）；新增类型走
spec-amend。日志损坏（不可解析行）抛 EventLogError——篡改检测优先于静默容错。
fold 在重放路径上复验 Guard 不变量：任何违反不变量的历史都会在恢复时暴露。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from fractal_kernel import guard
from fractal_kernel.models import Contract, Evidence, Instance


class EventType(StrEnum):
    """事件词汇表（Phase 0 冻结）。"""

    SESSION_STARTED = "session.started"
    INSTANCE_CREATED = "instance.created"
    CONTRACT_REGISTERED = "contract.registered"
    DELEGATION_SPECIFIED = "delegation.specified"
    DELEGATION_LAUNCHED = "delegation.launched"
    ATTEMPT_STARTED = "attempt.started"
    ATTEMPT_FINISHED = "attempt.finished"
    CHECK_EXECUTED = "check.executed"
    EVIDENCE_RECORDED = "evidence.recorded"
    DECISION_MADE = "decision.made"
    GUARD_REJECTED = "guard.rejected"
    BUDGET_UPDATED = "budget.updated"
    SESSION_INHERITED = "session.inherited"


class Event(BaseModel):
    """日志条目 ⟨seq, type, run_id, payload⟩；append-only，永不改写。"""

    model_config = ConfigDict(frozen=True)

    seq: int
    type: EventType
    run_id: str
    payload: dict[str, Any]


class EventLogError(Exception):
    """事件日志损坏或不可读。"""


class EventLog:
    """JSONL append-only 日志；seq 从 1 连续递增，跨重开延续。"""

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[Event] = self._load()

    def _load(self) -> list[Event]:
        if not self._path.exists():
            return []
        events: list[Event] = []
        text = self._path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                events.append(Event.model_validate_json(line))
            except ValidationError as exc:
                msg = f"{self._path}:{lineno}: corrupt event log entry"
                raise EventLogError(msg) from exc
        return events

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def append(self, event_type: EventType, payload: dict[str, Any], run_id: str = "run") -> Event:
        event = Event(seq=len(self._events) + 1, type=event_type, run_id=run_id, payload=payload)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")
        self._events.append(event)
        return event


@dataclass(frozen=True)
class WorldState:
    """fold(events) 的恢复产物：派生状态视图，非规范对象。"""

    contracts: dict[str, Contract] = field(default_factory=dict)
    instances: dict[str, Instance] = field(default_factory=dict)
    handlers: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, tuple[Evidence, ...]] = field(default_factory=dict)


def fold(events: Sequence[Event]) -> WorldState:
    """重放事件折叠出状态；携带状态的恶意/损坏历史在此被 Guard 拒绝。"""
    contracts: dict[str, Contract] = {}
    instances: dict[str, Instance] = {}
    handlers: dict[str, str] = {}
    evidence: dict[str, list[Evidence]] = {}

    for event in events:
        payload = event.payload
        if event.type is EventType.CONTRACT_REGISTERED:
            contract = Contract.model_validate(payload["contract"])
            guard.check_contract_registration(contracts, contract)
            contracts[contract.id] = contract
        elif event.type is EventType.INSTANCE_CREATED:
            instance = Instance.model_validate(payload["instance"])
            guard.check_instance_parent(instances, instance)
            instances[instance.id] = instance
        elif event.type is EventType.DELEGATION_LAUNCHED:
            contract_id = str(payload["contract_id"])
            guard.check_one_handler(handlers, contract_id)
            handlers[contract_id] = str(payload["instance_id"])
        elif event.type is EventType.EVIDENCE_RECORDED:
            evidence_item = Evidence.model_validate(payload["evidence"])
            guard.check_evidence_binding(contracts, evidence_item)
            evidence.setdefault(evidence_item.contract_id, []).append(evidence_item)

    return WorldState(
        contracts=contracts,
        instances=instances,
        handlers=handlers,
        evidence={cid: tuple(items) for cid, items in evidence.items()},
    )
