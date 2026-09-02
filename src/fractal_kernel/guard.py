"""Guard：纯约束层（fractal.md D12）。

只校验不变量，不做业务决策、不执行恢复——恢复由调用方按 spec/invariants.md
的恢复路径执行。错误码与目录条目一一对应，随实现逐步扩充。
本模块在两条路径上生效：写入时校验（调度器/运行时调用）与重放时复验
（store.fold 调用，篡改检测）。
"""

from __future__ import annotations

import posixpath
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import PurePosixPath

from fractal_kernel import dag
from fractal_kernel.models import Contract, Evidence, Instance

KNOWN_CHECK_KINDS: frozenset[str] = frozenset(
    {"exec", "test", "typecheck", "lint", "diff", "llm-judge", "human"}
)


class ErrorCode(StrEnum):
    """Guard 错误码（spec/invariants.md；未列出的目录条目尚未实现）。"""

    CONTRACT_MUTATE = "E-CONTRACT-MUTATE"
    EVIDENCE_UNBOUND = "E-EVIDENCE-UNBOUND"
    PARENT = "E-PARENT"
    BOUNDARY_WRITE = "E-BOUNDARY-WRITE"
    ONE_HANDLER = "E-ONE-HANDLER"
    DAG_CYCLE = "E-DAG-CYCLE"
    CHECK_UNREGISTERED = "E-CHECK-UNREGISTERED"


class GuardError(Exception):
    """Guard REJECT：code 对应 invariants.md 目录条目，message 含定位信息。"""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message


def check_contract_registration(existing: Mapping[str, Contract], incoming: Contract) -> None:
    """I-Contract / T4：同 id 不同内容拒绝；同 id 同内容幂等放行。"""
    registered = existing.get(incoming.id)
    if registered is not None and registered != incoming:
        raise GuardError(
            ErrorCode.CONTRACT_MUTATE,
            f"contract {incoming.id} already registered with different content",
        )


def check_evidence_binding(contracts: Mapping[str, Contract], evidence: Evidence) -> None:
    """I-Evidence / D2：证据必须绑定已注册的契约。"""
    if evidence.contract_id not in contracts:
        raise GuardError(
            ErrorCode.EVIDENCE_UNBOUND,
            f"evidence references unregistered contract {evidence.contract_id}",
        )


def check_instance_parent(instances: Mapping[str, Instance], instance: Instance) -> None:
    """I-Parent / D4：根为 None；否则父实例必须已存在。"""
    if instance.parent is not None and instance.parent not in instances:
        raise GuardError(
            ErrorCode.PARENT,
            f"instance {instance.id} references missing parent {instance.parent}",
        )


def check_one_handler(handlers: Mapping[str, str], contract_id: str) -> None:
    """I-OneHandler / T1：running 契约最多一个处理者。

    v0 限制：reassign/retry 的处理者变更协议在 Phase 2 落地（AM-0.1-02）前，
    同一契约的第二次 launch 一律拒绝。
    """
    if contract_id in handlers:
        raise GuardError(
            ErrorCode.ONE_HANDLER,
            f"contract {contract_id} is already handled by {handlers[contract_id]}",
        )


def check_dag_acyclic(edges: Mapping[str, Sequence[str]]) -> None:
    """plan 输出的子契约 DAG 必须无环（E-DAG-CYCLE）。"""
    cycle = dag.find_cycle(edges)
    if cycle is not None:
        raise GuardError(ErrorCode.DAG_CYCLE, "cycle in contract DAG: " + " -> ".join(cycle))


def check_check_kinds(contract: Contract, allowed: frozenset[str] = KNOWN_CHECK_KINDS) -> None:
    """ADR-0004：契约内每个 check.kind 必须已注册。"""
    for check in contract.checks:
        if check.kind not in allowed:
            raise GuardError(
                ErrorCode.CHECK_UNREGISTERED,
                f"check {check.id} has unregistered kind '{check.kind}'",
            )


def check_boundary_write(boundary: Sequence[str], path: str) -> None:
    """A3 / AM-0.1-05：写目标必须 ∈ 本实例 manifest（boundary，D4）。

    纯字符串运算：posixpath 规范化 + 路径组件级包含判定（"src" 不得放行
    "srcfoo/…"）。绝对路径、根逃逸（".."）、空路径一律拒绝；空 manifest
    拒绝一切写。工具层拦截（write/edit 前）与提交审计共用本判定。
    """
    if not boundary:
        raise GuardError(ErrorCode.BOUNDARY_WRITE, f"manifest is empty; write '{path}' rejected")
    if not path or path.startswith("/"):
        raise GuardError(ErrorCode.BOUNDARY_WRITE, f"write target '{path}' must be relative")
    normalized = posixpath.normpath(path)
    if normalized == ".":
        raise GuardError(ErrorCode.BOUNDARY_WRITE, "write target must not be the worktree root")
    target = PurePosixPath(normalized)
    for root in boundary:
        root_path = PurePosixPath(posixpath.normpath(root))
        if target.is_relative_to(root_path):
            return
    raise GuardError(
        ErrorCode.BOUNDARY_WRITE,
        f"write target '{path}' is outside the instance manifest {tuple(boundary)}",
    )
