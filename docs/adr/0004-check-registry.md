# ADR-0004: Check 执行器注册表与确定性分级

- 状态：已接受（2026-09-02）
- 关联：fractal.md Pr2 / D3 / D6；AM-0.1-06

## 背景

规范假设 `⟦ch⟧ ∈ {true,false}`，但语义级验收标准无法机械判定；check 质量
（而非数量）决定全系统验收上限。

## 决策

- check.kind 必须注册（E-CHECK-UNREGISTERED）。
- 注册项声明 `{executor, timeout 默认, 成本等级, 确定性等级}`；确定性等级
  hard / soft / human。
- v0 只实现 hard（exec：命令退出码）；soft（llm-judge）/ human 在 Phase 5 引入，
  且 `v` 的聚合规则由 Policy 显式定义（hard 必须全过；soft 达阈值）。
- 结果缓存键 `(check.id, sigma_ref)`（AM-0.1-06）。

## 后果

- Phase 1 的"验收"全部可机器化、可重放。
- soft 引入后 `v` 的确定性弱化，由 Policy 显式承认而非隐藏。
