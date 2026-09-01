"""plan 输出无环不变量测试：E-DAG-CYCLE。"""

import pytest

from fractal_kernel import guard


def test_plan_output_with_cycle_rejected() -> None:
    with pytest.raises(guard.GuardError) as excinfo:
        guard.check_dag_acyclic({"a": ("b",), "b": ("a",)})
    assert excinfo.value.code is guard.ErrorCode.DAG_CYCLE


def test_plan_output_with_self_loop_rejected() -> None:
    with pytest.raises(guard.GuardError) as excinfo:
        guard.check_dag_acyclic({"a": ("a",)})
    assert excinfo.value.code is guard.ErrorCode.DAG_CYCLE


def test_acyclic_plan_output_accepted() -> None:
    guard.check_dag_acyclic({"a": ("b", "c"), "b": ("d",), "c": ("d",), "d": ()})
