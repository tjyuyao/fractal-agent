# ADR-0003: Append-Only 事件日志为唯一事实来源

- 状态：已接受（2026-09-02）
- 关联：fractal.md A1 / A2 / T4、D8

## 背景

T4（契约不可变）+ A1（证据绑定）+ A2（来源可追溯）共同要求历史不可篡改、可重放。
崩溃恢复（T5 的中断路径、kill -9 后续跑）需要与 LLM 对话无关的状态重建。

## 决策

- append-only JSONL 事件日志（`.fractal/sessions/<run-id>/events.jsonl`）为唯一
  事实来源；内存/DB 状态 = fold(events)。
- LLM 对话只是缓存，不是事实来源。
- 事件类型表冻结于 `fractal_kernel/store.py`（Phase 0）；新增类型走 `spec-amend`。
- SQLite 索引在性能需要时再加，日志格式不变。

## 后果

- 恢复、审计、重放、golden 测试录制共用同一机制。
- 大 run 下 fold 性能退化，需要时加索引即可，不影响正确性。
