"""Append-only 事件日志：唯一事实来源，状态 = fold(events)（ADR-0003）。

事件类型表在 Phase 0 冻结（docs/architecture.md 事件日志节）；
新增类型走 spec-amend。Phase 0 实现 JSONL 追加与重放折叠。
"""
