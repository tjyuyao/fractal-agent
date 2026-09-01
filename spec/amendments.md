# Amendments to fractal.md

Base: fractal.md v0.1 (2026-08-31). 修正案与宪法共同生效；宪法文本本身不改。

## Amendment set 0.1 (2026-09-02, effective)

### AM-0.1-01 · supervise 的 check 映射（闭合 D5 汇总缺口）

- 修改对象：D5 supervise、D6 `v(c,e)`
- 决策：plan 的产出必须包含 `check_map`——对父契约的每个 check 给出二选一归属：
  `delegated(child_contract_id, child_check_id)` 或 `verify_after_merge`。
  supervise 依据 check_map 计算父证据中每个 `⟦ch⟧`：delegated 项取子证据对应判定，
  verify_after_merge 项在合并后的 Σ 上由父层直接执行。
- 理由：父 checks 与子 checks 不是 1:1；无映射则 supervise 的"汇总"不可实现。

### AM-0.1-02 · retry / reassign 语义（闭合 D6 `r(c,e,p)` 缺口）

- 修改对象：D6 r、D8 Attempt
- 决策：retry = 同一 Task 上的新 Attempt，执行者身份不变；reassign = 新 Attempt 且
  更换执行者身份。两者默认继承失败 Attempt 的 checkpoint（Policy 可设
  `checkpoint: resume | baseline`，默认 resume；baseline 则回到父基线）。
  上下文一律从工作包重建，不回放前任对话。
- 理由：Attempt 链是审计单位；执行者可变、契约与 Task 不变，证据绑定不受影响。

### AM-0.1-03 · steering 只能追加约束（闭合 D11 缺口）

- 修改对象：D11 steering、D4.5 constraints
- 决策：steering 产生的合法效果仅一种——向活跃实例的约束集追加条目（实例级
  append-only 约束日志，属于工作包上下文，不属于契约）。要求超出契约范围的工作 →
  拒绝；要求变更意图 → 转入新讨论（D3.5）产出新契约，旧契约标记废弃并归档其证据。
- 理由：契约不可变（T4）与 steering 的会话性质正交；约束是处理条件，落在实例层
  不破坏 T4。

### AM-0.1-04 · 会话继承的证据复用条件（闭合 D10 缺口）

- 修改对象：D10 session
- 决策：新 Session 继承前序 DAG 时，既有证据复用当且仅当：contract id 匹配（内容
  寻址不变）且该证据的全部 checks 在当前 Σ 指纹上复验通过（AM-0.1-06）。其余证据
  归档，对应契约重新处理。意图变更必然产出新契约（T4），不产生"修改后的旧契约"。
- 理由：证据的价值取决于 Σ 未变；指纹复验是复用的唯一安全条件。

### AM-0.1-05 · boundary 的具体化：声明、载体与双层强制

- 修改对象：D4 boundary、A3、D9 并发约束 2
- 决策：boundary 声明为可写路径集合（manifest），由 plan 在分解时为每个子契约产出，
  实例创建时随工作包固定。强制分两层：工具层拦截（write/edit 目标必须 ∈ manifest）；
  提交时 diff 审计（worktree 相对 checkpoint ref 的变更路径必须 ⊆ manifest，否则
  REJECT）。兄弟实例并行当且仅当 manifest 两两不相交；相交时合法出路仅两种——
  加依赖边串行化，或抽出拥有交集的集成契约（串行执行，独占交集文件）。
  git worktree 是物理载体，提供隔离视图、checkpoint（commit）与合并，
  不承担边界声明职责。
- 理由：把冲突判定从"猜测行为"变为"集合求交"，静态可判定；worktree 保留为唯一
  成熟的物理载体。

### AM-0.1-06 · Σ 指纹与检查缓存

- 修改对象：Pr4 Σ、D2 evidence
- 决策：evidence 必须携带 `sigma_ref` = 检查执行时 worktree 的 HEAD commit。
  检查结果按 `(check.id, sigma_ref)` 缓存复用。复核时若 verify_after_merge 项的
  sigma_ref 与当前合并基不一致，必须重跑；delegated 项按 check_map 取缓存判定。
- 理由：Σ 时间相关（Pr4）；无指纹则证据时效不可判定，缓存无键。

### AM-0.1-07 · 粒度判定 g(c) 的 v0 实现

- 修改对象：D6 g、D5.5 granularity_threshold
- 决策：v0 用代理指标组合：LLM 分类（依据 rubric）+ 硬上限（预估 token 超上下文
  窗口的 Policy 比例、涉及文件数、checks 数量任一越界 → 强制 decompose）。
  build 因上下文溢出失败视为"应分解"信号，走 `r → replan` 闭环校正。
- 理由：粒度无客观度量；代理 + 闭环校正可接受，阈值经 Phase 5 校准。
