"""ADR-0004 注册表不变量测试：E-CHECK-UNREGISTERED。"""

import pytest

from fractal_kernel import guard
from fractal_kernel.models import CheckSpec, Contract


def _contract_with_kinds(*kinds: str) -> Contract:
    checks = tuple(
        CheckSpec(id=f"ch-{i}", kind=kind, spec={"command": "true"}) for i, kind in enumerate(kinds)
    )
    return Contract(id="c-1", intent="i", checks=checks)


def test_unregistered_kind_rejected() -> None:
    with pytest.raises(guard.GuardError) as excinfo:
        guard.check_check_kinds(_contract_with_kinds("magic"))
    assert excinfo.value.code is guard.ErrorCode.CHECK_UNREGISTERED


def test_all_hard_kinds_accepted() -> None:
    guard.check_check_kinds(_contract_with_kinds("exec", "test", "typecheck", "lint", "diff"))


def test_empty_checks_contract_accepted() -> None:
    guard.check_check_kinds(Contract(id="c-1", intent="i", checks=()))
