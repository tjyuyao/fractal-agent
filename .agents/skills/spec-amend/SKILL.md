---
description: 发现实现与 fractal.md 冲突、规范缺口或需要具体化时，按修订程序记录修正案/ADR，禁止静默偏离。需要修订规范时使用。
---

# Spec Amend

规范是宪法（fractal.md 永不编辑）；一切增量走 `spec/amendments.md` + `docs/adr/`
（ADR-0005）。

## 步骤

1. **陈述冲突**：引用条款（D/A/T 编号）与冲突的代码/测试/现实约束，一句话说清缺口。
2. **起草修正案**：`AM-<set>-<n>`（集合号见 `spec/amendments.md` 顶部）。必须包含
   修改对象、决策、理由；决策必须可在测试中验证。
3. **ADR（可选）**：若选择影响架构（模块边界、外部依赖、存储格式），另立
   `docs/adr/000N-<slug>.md`。
4. **联动更新**：新增 Guard 规则 → `spec/invariants.md` 追加错误码；新增事件类型 →
   `fractal_kernel/store.py` 事件表。
5. **测试先行**：按新语义先写红色测试，再改实现（`implement-concept` 步骤 3–5）。
6. **生效**：amendments.md 标记生效日期；`docs/roadmap.md` 受影响则同步更新。

## 禁止

- 编辑 fractal.md。
- 在未记录修正案前实现偏离规范的行为。
- 删除已生效修正案（只能追加新修正案覆盖）。
