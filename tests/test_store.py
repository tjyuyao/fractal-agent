"""事件日志往返、seq 连续性、损坏检测与 fold 恢复（ADR-0003）。"""

import pytest

from fractal_kernel.models import Contract, Evidence, Instance
from fractal_kernel.store import Event, EventLog, EventLogError, EventType, WorldState, fold


def _contract() -> Contract:
    return Contract(id="c-1", intent="i", checks=())


class TestRoundtrip:
    def test_append_and_reopen(self, tmp_path) -> None:
        path = tmp_path / "events.jsonl"
        log = EventLog(path)
        log.append(EventType.SESSION_STARTED, {"note": "hello"})
        log.append(EventType.CONTRACT_REGISTERED, {"contract": _contract().model_dump()})

        reopened = EventLog(path)
        assert [e.seq for e in reopened.events] == [1, 2]
        assert reopened.events[1].type is EventType.CONTRACT_REGISTERED
        assert reopened.events[1].payload["contract"]["id"] == "c-1"

    def test_seq_continues_across_reopen(self, tmp_path) -> None:
        path = tmp_path / "events.jsonl"
        EventLog(path).append(EventType.SESSION_STARTED, {})
        EventLog(path).append(EventType.SESSION_STARTED, {})

        log = EventLog(path)
        event = log.append(EventType.SESSION_STARTED, {})
        assert event.seq == 3

    def test_corrupt_line_raises(self, tmp_path) -> None:
        path = tmp_path / "events.jsonl"
        valid = Event(seq=1, type=EventType.SESSION_STARTED, run_id="r", payload={})
        path.write_text(valid.model_dump_json() + "\nnot-json\n", encoding="utf-8")
        with pytest.raises(EventLogError):
            EventLog(path)


class TestFold:
    def test_rebuilds_world_state(self, tmp_path) -> None:
        log = EventLog(tmp_path / "events.jsonl")
        log.append(EventType.INSTANCE_CREATED, {"instance": Instance(id="i-1").model_dump()})
        log.append(EventType.CONTRACT_REGISTERED, {"contract": _contract().model_dump()})
        log.append(EventType.DELEGATION_LAUNCHED, {"contract_id": "c-1", "instance_id": "i-1"})
        evidence = Evidence(contract_id="c-1", results={}, sigma_ref="s")
        log.append(EventType.EVIDENCE_RECORDED, {"evidence": evidence.model_dump()})

        state = fold(log.events)
        assert isinstance(state, WorldState)
        assert set(state.instances) == {"i-1"}
        assert set(state.contracts) == {"c-1"}
        assert state.handlers == {"c-1": "i-1"}
        assert state.evidence == {"c-1": (evidence,)}

    def test_stateless_events_are_ignored(self) -> None:
        events = [
            Event(seq=1, type=EventType.SESSION_STARTED, run_id="r", payload={}),
            Event(seq=2, type=EventType.DECISION_MADE, run_id="r", payload={"d": "retry"}),
        ]
        state = fold(events)
        assert not state.contracts
        assert not state.instances
        assert not state.handlers
        assert not state.evidence
