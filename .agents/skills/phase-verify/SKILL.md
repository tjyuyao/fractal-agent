---
description: 核对当前 Phase 的验收清单并更新 roadmap 状态。阶段收尾或怀疑回归时使用。
---

# Phase Verify

1. **读清单**：`docs/roadmap.md` 当前 Phase 的验收列 + 未勾选项。
2. **跑全量**：`uv run pytest`、`uv run ruff check .`、`uv run ruff format --check .`、
   `uv run mypy` 全绿；把测试计数记录进 dev-note。
3. **定理映射核对**：逐条确认验收标准对应的定理/不变量有具名测试
   （T1 → 单处理者、T3 → 父层验收、T4 → 不可变、T5 → 深度截断、A1 → 证据链完整）。
4. **故障注入**（Phase 2 起）：kill -9 中途 → 从 `events.jsonl` 恢复并继续，
   状态一致才算过。
5. **收尾**：更新 roadmap 状态列；`docs/dev-notes/` 写阶段小结（完成 / 遗留 / 教训）；
   遗留项转入下一 Phase 清单。
