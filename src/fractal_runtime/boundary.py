"""实例边界：manifest 强制的工具层拦截（ADR-0001、AM-0.1-05）。

判定本体（组件级路径包含）在 fractal_kernel.guard.check_boundary_write，
本模块只做 runtime 侧的路径解析衔接：把工具调用目标解析为 worktree 相对
POSIX 路径并交给 Guard。越界抛 GuardError(E-BOUNDARY-WRITE)；worktree 载体
与提交时 diff 审计随 sigma_ref 工作落地。
"""

from __future__ import annotations

import posixpath
from collections.abc import Sequence

from fractal_kernel.guard import check_boundary_write


def enforce_write(boundary: Sequence[str], rel_path: str) -> str:
    """校验写目标 ∈ manifest（AM-0.1-05），返回规范化的 worktree 相对 POSIX 路径。

    rel_path 必须是 worktree 相对 POSIX 路径；绝对路径、根逃逸与越界均被
    Guard 拒绝（E-BOUNDARY-WRITE，恢复路径见 spec/invariants.md）。
    """
    check_boundary_write(boundary, rel_path)
    return posixpath.normpath(rel_path)
