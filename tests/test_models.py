"""核心规范对象的不变量冒烟测试（D1/D2/D4.5、I-Contract、T4）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fractal_kernel.models import CheckSpec, Contract, Evidence, WorkPacket


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
