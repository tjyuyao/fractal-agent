---
description: 按 spec-first 流程实现一个规范概念：条款 → schema → 红色不变量测试 → 最小实现 → 全绿。在 fractal_kernel / fractal_runtime 中实现任何规范概念时使用。
---

# Implement Concept

把 fractal.md（或修正案）的一个概念落成代码，每一步有可验证的产出。

## 步骤

1. **定位条款**：读 fractal.md 对应 D/A/T 编号 + `spec/amendments.md` 相关 AM +
   `spec/invariants.md` 相关错误码。先列出不满足本概念将违反哪些不变量。
2. **schema 先行**：在 `fractal_kernel`（或 `fractal_runtime`）定义/扩展 pydantic
   模型。规范中的不可变对象用 frozen 模型 + tuple 集合。docstring 标注条款编号。
3. **红色测试**：`tests/` 写不变量测试，命名 `test_<invariant>_<error_code>.py`。
   测试不得调用 LLM、不得触网、不得依赖 tau。运行确认先红。
4. **最小实现**：恰好让测试变绿，不做条款之外的事。
5. **全绿**：`uv run pytest && uv run ruff check . && uv run ruff format . && uv run mypy`。
6. **依赖规则**：kernel 改动必须通过 `tests/test_imports.py` 的纯净性检查。
7. **登记**：新增 Guard 规则 → 追加 `spec/invariants.md` 条目（错误码 / REJECT 行为 /
   恢复路径三者必填）；新增事件类型 → `store.py` 事件表；发现规范缺口 → 转
   `spec-amend`，不得顺手偏离。
8. **dev-note**：`docs/dev-notes/<phase>-<slug>.md` 记录：加了什么、对应条款、
   如何测试。

## 禁止

- 在 kernel 中 import runtime/cli/tau/git/subprocess/LLM SDK。
- 跳过红色测试直接写实现。
- 静默偏离规范（见 `spec-amend`）。
