"""实例边界：worktree 载体 + manifest 强制 + 提交时 diff 审计（ADR-0001、AM-0.1-05）。

工具层拦截（write/edit 前校验路径 ∈ manifest）与提交审计
（`git diff --name-only` 对照 checkpoint ref）在此实现；越界报 E-BOUNDARY-WRITE。
"""
