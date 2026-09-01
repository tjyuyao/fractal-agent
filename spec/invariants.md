# Invariant Catalog & Guard Error Codes

Guard 是纯约束层（fractal.md D12）：只校验不变量，不做业务决策。
每个 REJECT 必须有定义的恢复路径；没有恢复路径的不变量视为设计缺陷，走 `spec-amend`。

| 错误码 | 不变量 | 规则 | REJECT 行为 | 恢复路径 |
|---|---|---|---|---|
| E-CONTRACT-MUTATE | I-Contract / T4 | 已存在契约的 intent/checks 不可写 | 拒绝写操作 | 经讨论/修正案创建新契约 |
| E-EVIDENCE-UNBOUND | I-Evidence / D2 | `e.contract_id` 必须指向存在且匹配的契约 | 拒绝证据入库 | 修正 contract_id 重新提交 |
| E-EVIDENCE-STALE | AM-0.1-06 | 复核时 sigma_ref 与当前基不一致的 verify_after_merge 项不得计入 | 判定无效 | 重跑检查 |
| E-PARENT | I-Parent / D4 | 实例必须有且仅有一个父（根为 ⊥） | 拒绝实例创建 | 修正 parent 引用 |
| E-BOUNDARY-WRITE | A3 / AM-0.1-05 | 写目标必须 ∈ 本实例 manifest | 工具层拦截；提交审计拒绝 | replan 扩 manifest（新契约）或转集成契约 |
| E-BOUNDARY-OVERLAP | AM-0.1-05 | 并行兄弟实例 manifest 两两不相交 | 拒绝并行启动 | 加依赖边串行化，或抽集成契约 |
| E-ONE-MODE | I-OneMode / D5 | 同一实例同一时刻只启用一种能力 | 拒绝能力激活 | 等当前能力结束 |
| E-ONE-HANDLER | I-OneHandler / T1 | running 契约最多一个处理者 | 拒绝第二个处理者 | 走 reassign 排队 |
| E-DEPTH | T5 / D7 | `d(i) ≤ D_max` | 拒绝 delegate | 强制 build 或 ask_user |
| E-DAG-CYCLE | D5 plan 输出 | 子契约 DAG 必须无环 | 拒绝 plan 产出 | LLM 修复（≤2 次）→ r |
| E-DAG-MAP | AM-0.1-01 | check_map 必须覆盖父契约全部 checks | 拒绝 plan 产出 | LLM 修复（≤2 次）→ r |
| E-CHECK-UNREGISTERED | ADR-0004 | check.kind 必须在执行器注册表内 | 拒绝契约入库 | 换已注册类型或注册新执行器 |
| E-BUDGET | D5.5 budget | 启动/委托不得超出预算配额 | 拒绝启动 | ask_user 调整预算 |

维护规则：新增不变量实现时同步追加本表条目（错误码、REJECT 行为、恢复路径三者
必填），由 `implement-concept` 工作流强制。
