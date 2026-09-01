---
title: 一种基于分形的 Agent Harness 的设计构想
genre: 观点
theme: LLM
tags: [Agent, 分形, 架构]
date: 2026-08-31
summary: 从 4 个原语（Intent / Check / Work / World State）出发，经 13 个定义与 2 条公理，推出 6 条定理，构建一个分形自相似的 Agent Harness 架构规范。
---

# 一种基于分形的 Agent Harness 的设计构想

## 1. 记号与约定

| 记号 | 含义 |
|---|---|
| `∈` | 属于（集合成员） |
| `×` | 笛卡尔积（元组类型） |
| `⟶` | 函数：源 ⟶ 目标 |
| `⟨a, b, c⟩` | 元组 |
| `⊥` | 空值 / 无（根节点、空引用） |
| `Σ` | 世界状态（代码仓库、文件系统等一切可观察状态） |
| `⟦x⟧` | 谓词 `x` 的判定结果，`⟦x⟧ ∈ {true, false}` |
| `id(x)` | 实体 `x` 的唯一标识符 |
| `p(i)` | 实例 `i` 的父实例，`p(i) ∈ I ∪ {⊥}` |

所有集合与函数都显式声明类型。未加引号的标识符均在本节或正文定义。

---

## 2. 原语（Primitives）

本规范不对原语的内部结构做任何假设，只把它们作为构造材料（未定义）。

- **Pr1 · Intent（意图）** `In`：用户想要达成的目标，系统的输入端点。
- **Pr2 · Check（检查）** `Ch`：一个可判定的命题。对任意 `ch ∈ Ch`，
  `⟦ch⟧ ∈ {true, false}`。检查是"什么算完成"的最小判定单元。
- **Pr3 · Work（劳作）** `W`：一种改变世界状态的行动 `Σ ⟶ Σ`。劳作不可被
  判定为对错（它是动作，不是命题），但它产生可观察的副作用（产物、变更）。
- **Pr4 · World State（世界状态）** `Σ`：一切可观察状态的集合（代码、文件、
  运行结果）。状态是时间相关的：`Σ_t` 表示时刻 `t` 的状态。

**原语之间的关系**：
- 劳作**改变**状态；
- 检查**判定**状态（是否满足某个条件）；
- 意图是期望的目标状态——它是否达成，由检查来判定。

一句话：**意图是目的地，检查是尺子，劳作是脚步，状态是世界。**

---

## 3. 定义：第一层（规格层）

### D1 · Contract（契约）

一个契约 `c` 是一个不可变元组：

```text
c = ⟨id, intent, checks⟩
    id      : 唯一标识符
    intent  : In    （契约封装的目标；子契约的 intent 是父意图的细化，见 D5）
    checks  : 有序的 Ch 集合  （验收标准）
```

- **不可变性**（不变量 `I-Contract`）：契约一旦创建，`intent` 与 `checks`
  永不变更。若需求变化，则创建新契约。理由见 T4（对账需求）。
- **处理单位**：系统处理契约，不直接处理意图。意图经讨论（D3.5）转化为
  契约后，进入处理 / 分解体系。
- 契约的**类型**为 `C`（所有契约的集合）。

### D2 · Evidence（证据）

一个证据 `e` 是一个元组：

```text
e = ⟨contract_id, results, artifacts⟩
    contract_id : 所证明的契约 id
    results     : 对 c.checks 每个元素的判定结果集合
                  ∀ch ∈ c.checks: ⟦ch⟧ ∈ {true, false}
    artifacts   : 劳作产生的可观察产物集合
```

- 证据的**类型**为 `E`。
- **不变量 `I-Evidence`**：一个证据只对应一个契约（`e.contract_id` 唯一）。
  证据不能证明多个契约，否则无法对账（T4）。

### D3 · 完成（Satisfaction）

一个契约 `c` 被证据 `e` **完成**，当且仅当：

```text
e.contract_id = c.id ∧ ∀ch ∈ c.checks: ⟦ch⟧ = true
```

记为 `sat(c, e)`。若 `∃ch ∈ c.checks: ⟦ch⟧ = false`，则 `¬sat(c, e)`，
称证据**未完成**契约。

> 注：`sat` 定义的是"证据对契约的满足关系"，不含任何主观判断。它由检查的
> 判定结果直接决定——这是"验收"可机器化的基础。

### D3.5 · 讨论（Discussion）

意图（Pr1）不是契约（D1）——意图只有目标，没有 checks。**讨论**是系统
中从意图到契约的桥梁：

```text
discuss: In ⟶ 𝒫(C)    （意图 ⟶ 契约的幂集）
```

讨论是**用户与系统之间的交互过程**：用户表达意图，系统通过对话 / 澄清 /
确认，产出一个或多个契约。每个契约的 `intent` 是意图的细化，`checks` 是
讨论中确定的验收标准。

- **位置**：讨论发生在实例**创建之前**。意图经讨论产出契约后，契约才被
  交给实例处理（A2）。讨论是系统入口机制，不是实例的能力。
- **根实例形态**：根实例（`parent = ⊥`）和子实例**完全同构**（D4/D5）。
  它不负责封装意图——封装在讨论中完成。根实例只是一个接收了顶层契约的
  普通实例。
- **输出契约可多个**：一次讨论可以产出多个并行契约，每个契约独立进入
  处理体系。

---

## 4. 定义：第二层（实例层）

### D4 · Instance（实例）

一个实例 `i` 是一个处理单元，满足：

```text
i = ⟨id, parent, boundary, processing⟩
    id       : 唯一标识符
    parent   : I ∪ {⊥}   （⊥ = 根实例）
    boundary : 一组独立的可写状态空间（namespace）
    processing : 一组能力（见 D5）
```

- 实例的**类型**为 `I`。
- **不变量 `I-Parent`**：每个实例要么是根（`p(i) = ⊥`），要么有且只有一个
  父实例（`p(i) ∈ I`）。不存在"无父且非根"的实例。
- **不变量 `I-Boundary`**：实例 `i` 只能写自己的 `boundary`。写他人的
  boundary 一律禁止（见 A3）。

### D4.5 · Work Packet（工作包）

实例处理的输入不是裸契约，而是**工作包**——契约与处理上下文的打包：

```text
Wp = ⟨contract, checkpoint, tools, constraints⟩
    contract   : C         （要处理的契约）
    checkpoint : CK?       （执行基线，可选；首次处理时为空）
    tools      : 工具集    （实例可调用的能力）
    constraints : 约束集   （处理时须遵守的限制）
```

- 工作包是实例处理的**最小输入单元**。契约是处理的对象，其余三项是处理的
  条件。
- **委托时包装工作包**：delegate 把子契约包装成新的工作包（子契约 + 从父工作包
  继承的基线 / 工具 / 约束），交给子实例。子实例收到的也是工作包，不是裸契约。
- checkpoint 的类型 `CK`（Execution Checkpoint）在 D8 定义；这里只声明它
  作为工作包的一个字段存在。

### D5 · Processing（处理能力）

每个实例具备四种能力，它们是实例处理工作包的全部方式：

```text
processing = ⟨plan, build, delegate, supervise⟩
    plan      : Wp × Σ ⟶ (C 的 DAG) × Σ
                （分解：从工作包提取契约，拆分为子契约 DAG）
    build     : Wp × Σ ⟶ E × Σ
                （执行：从工作包提取契约和工具，直接劳作，产出证据）
    delegate  : Wp × (C 的 DAG) × I ⟶ Wp 的集合 × Σ
                （委托：把子契约 DAG 中的每个子契约包装成工作包，分派给子实例）
    supervise : Wp × (子契约的 E 集合) ⟶ E × Σ
                （验收：对每个子证据执行 v(c,e)，通过则汇总，未通过则依 Policy 决策）
```

- **plan**：输入工作包，提取其中的契约，执行分解（拆分 checks，产出子契约
  DAG）。plan 不委托——它只产出"要做什么"的结构，不决定"交给谁做"。
- **build**：输入工作包，提取契约和工具，直接劳作产出证据。build 是"粒度
  小到不需要分解"时的处理方式。
- **delegate**：输入工作包和子契约 DAG，把每个子契约包装成新的工作包（子契约 +
  继承的基线 / 工具 / 约束），分派给子实例。delegate 是递归的入口——
  它把子契约交给子实例处理（A2）。
- **supervise**：输入工作包和子证据集合，对每个子证据执行验收判定 `v(c,e)`
  （D6），通过则汇总产出父证据，未通过则依 Policy（D5.5）决定下一步
  （retry / reassign / replan / ask user）。supervise 的核心是验证 +
  决策的组合。
- **不变量 `I-OneMode`**：同一实例在同一时刻只启用一种能力。否则同一工作包
  会被重复处理（推导见 T1）。

### D5.5 · Policy（策略）

Processing 的配置参数，由人设定，实例执行时读取：

```text
P = ⟨granularity_threshold, max_depth, permissions, budget, risk_threshold, retry_count⟩
    granularity_threshold : 粒度门槛（g(c) 的阈值）
    max_depth             : 委托深度上限（D7）
    permissions           : 权限集（reassign / replan 等）
    budget                : 资源预算（时间 / 计算 / 金钱）
    risk_threshold        : 风险阈值（超过则必须 ask_user）
    retry_count           : 自动重试次数上限
```

- Policy 与处理机制正交——改变 Policy 不改变 A1/A2/T1–T5，只改变决策来源。
- `g(c)` 用 `granularity_threshold`；`r(c,e,p)` 用 `retry_count` /
  `permissions` / `budget` / `risk_threshold`（见 D6）。
- Policy 有两种应用模式：
  - **Interactive**（人在场）：`supervise` 将关键裁决暴露给用户，用户是最终
    决策者。`r` 的输出默认为 `ask_user`，自动决策只用于低风险项。
  - **Autonomous**（不在场）：`supervise` 依 Policy 自动裁决，`r` 的输出由
    Policy 参数决定，只在超出权限 / 预算 / 风险阈值时询问。
  - 两种模式共享同一公理与定理（A1–A2，T1–T5）。模式只改变 `supervise` 的
    决策来源（用户或 Policy），不改变机制本身。

### D6 · 判定点（Decision Points）

实例处理契约时有两个判定点：

**粒度判定** `g(c)`：在处理之前，决定是直接执行还是分解。

```text
g(c) ∈ {direct, decompose}
    direct      : 契约小到可直接劳作 → 启用 build
    decompose   : 契约大到需要分解 → 启用 plan，随后 supervise
```

`g` 是实例策略的一部分（阈值见 D5.5）。**关键：`g` 是第一个判定点**——实例对
一个契约，要么直接做，要么拆开做。不存在第三种处理方式。

**验收判定** `v(c, e)`：在处理之后，决定证据是否完成契约。

```text
v: C × E ⟶ {accept, reject}
    accept : sat(c, e) = true  → 证据通过，契约完成
    reject : sat(c, e) = false → 证据未通过，需要后续决策
```

`v` 是**确定性的**：由 checks 的判定结果直接决定（D3），不含主观判断。

**后续决策** `r(c, e, p)`：当 `v = reject` 时，决定下一步动作。

```text
r: C × E × Policy ⟶ {retry, reassign, replan, ask_user}

    if p.retry_count > 0      → retry      （同一契约再 build，新 Attempt）
    elif p.can_reassign       → reassign   （换一个实例 / 处理者）
    elif p.can_replan         → replan     （重新分解，回 plan）
    else                      → ask_user   （交给用户裁决）
```

`r` 的逻辑由 Policy（D5.5）参数驱动，是**确定性的**——给定 Policy 配置，
输出确定。但 Policy 本身由人配置，所以 `r` 是"人设定规则，机器执行"的决策。

**Interactive vs Autonomous 的区别**（D5.5）：
- **Interactive**（人在场）：`r` 的输出默认为 `ask_user`——关键裁决暴露给
  用户，自动决策只用于低风险项。
- **Autonomous**（不在场）：`r` 的输出由 Policy 参数决定——自动选
  retry / reassign / replan，只在超出 Policy 阈值（预算 / 权限 / 风险）时
  才 fallback 到 `ask_user`。

验收判定是 Supervise 的核心：`supervise` 聚合子证据后，对每个子契约执行
`v`，通过则汇总，未通过则执行 `r` 决定下一步。

---

## 5. 公理（Axioms）

### A1 · 处理公理

> 一次 `processing` 若达到完成态，则必须产出与该 Contract 绑定的 Evidence：
> ```text
> ∀i ∈ I, ∀c ∈ C: 若实例 i 处理 c 达到完成态 ⟹ 产出 e ∈ E 且 e.contract_id = c.id
> ```

即：处理完成必产证据，且证据绑定该契约。本公理确立"实例（处理单元）"的
性质，与 T5（存在不终止路径）完全兼容——处理可以不完成（如无限委托），但
一旦完成就必须产出证据。

### A2 · 递归公理

> 任何被处理的契约，要么来自讨论，要么由某个实例产出。
> ```text
> ∀c ∈ C, ∃j ∈ I (j 处理 c) ⟹ (c 来自讨论) ∨ (∃k ∈ I: k 分解产生了 c)
> ```

即：**契约只有两个来源**——讨论产出（顶层），或某个实例的分解产物（递归）。
不存在"凭空出现"的契约。

- **"来自讨论"的含义**：意图（Pr1）经讨论（D3.5）产出顶层契约。讨论
  把意图转化为带 checks 的契约——同一意图可被讨论产出一个复合契约（随后
  分解）或多个并行契约。无论哪种，一旦落为契约，就进入同一套处理 / 分解
  体系。
- **递归闭合**：意图层没有"再分"——意图只被讨论，不被处理；对意图的细分
  一律发生在契约层（D5 的分解）。因此递归链条 `契约 → 子契约 → 子子契约`
  在契约层无限可伸，不受意图原子性约束（底界由粒度门槛决定，T5）。

**推导（委托是递归的唯一形式）**：由 A1，实例处理契约就产证据。由 A2，
一个契约可能由实例 `k` 分解产生，交给出自 `k` 的另一个处理者。该处理者
与 `k` 的关系只有两种可能：同为 `k` 自身（实例内处理），或另一实例
（委托）。实例内处理受 `I-OneMode` 约束，因此**任何"非当前模式直接执行"的
处理，都是把子契约交给另一实例（委托）**。递归不发生在实例内部，而发生在
实例之间。

### A3 · 边界隔离公理

> 实例只能写自己的状态空间。
> ```text
> ∀i ∈ I: i 只能写 boundary(i)
> ```

边界隔离是**架构安全公理**：若实例 `i` 能写实例 `j` 的 boundary，则 `j`
产出的证据可能被 `i` 篡改，证据的可信性无法保证。边界隔离保证每个实例的
处理结果不被外部干扰。

---

## 6. 定理（Theorems）

### I-OneHandler（不变量）

> 一份契约同一时刻最多被一个实例处理。
> ```text
> ∀c ∈ C: c.status = running ⇒ ∃!i ∈ I (i 正在处理 c)
> ```

I-OneHandler 与 I-OneMode（D5）正交：
- I-OneMode：实例内唯一（同一实例同一时刻只启用一种能力）
- I-OneHandler：契约层面唯一（同一契约同一时刻最多被一个实例处理）

### T1 · 单激活模式

**断言**：一个契约在同一时刻最多被一个处理者处理。

**证明**：由 I-OneHandler，同一契约同一时刻最多被一个实例处理。∎

**推论 T1'**：实例内同一时刻只有一个能力活跃（即"单激活角色"）。这是 T1
在单实例内的特例（I-OneMode）。

### T3 · 验收权在父层

**断言**：实例 `k` 分解产出子契约后，子契约证据的**最终验收权**属于 `k`
（或其祖先）。

**证明**：由 A2，子契约由 `k` 分解产生。由 A1，子契约的处理者产出证据并
返回。谁验收？验收 = 判定 `sat(子契约, 证据)`。子契约的"完成标准"（其
`checks`）由 `k` 在分解时定义（D1/D5），故 `k` 是判定标准的定义者。判定
标准定义者保留最终裁决权；处理者自身的验收只算中间结论，不具最终性。∎

### T4 · 契约必须不可变

**断言**：契约不可变（`I-Contract` 是必要的）。

**证明**：由 A1，证据绑定契约 id。若契约可变，则一个已产出证据的契约
可在证据产出后被修改，使 `sat(c, e)`（D3）对同一 `(c, e)` 时真时假，
判定失去确定性。故契约必须不可变。∎

### T5 · 存在不终止的执行路径（如果允许无限委托）

**断言**：如果允许无限委托，存在某些执行路径不终止。

**证明**：构造一个无限委托链：实例 `i1` 处理契约 `c1`，选择 decompose，
产出子契约 `c2`，委托给 `i2`；`i2` 处理 `c2`，选择 decompose，产出子契约
`c3`，委托给 `i3`；……如此无限继续。这条执行路径永远不产出最终证据（A1
不满足），不终止。∎

**推论**：系统可通过 `D_max` 保证递归深度有界；`granularity_threshold` 进一步
保证在达到合理粒度后停止分解。两者合起来消除 T5 构造的无限委托链。

**定义 D7 · 委托深度**：实例 `i` 的委托深度 `d(i)` 递归定义为
`d(i) = 0` 若 `p(i) = ⊥`，否则 `d(i) = d(p(i)) + 1`。有界性要求：
`∀i ∈ I: d(i) ≤ D_max`。

---

## 7. 定义：第三层（对象与通信）

### D8 · 对象

处理过程产生三个工程对象，全部是**实例内**的（受 A3 约束，不跨边界）：

```text
Task      : 子契约在 DAG 中的节点记录
            ⟨id, contract_id, status, deps⟩
Attempt   : 对某个 Task 的一次执行尝试记录
            ⟨id, task_id, owner, checkpoint_id, status, result⟩
Checkpoint: 某次 Attempt 的执行基线快照
            ⟨id, attempt_id, plan_ref, code_refs⟩
```

- `Task` 与 `Contract` 的区别：契约是规格（不可变，D1），Task 是"该规格被
  纳入本实例处理队列"的记录（含状态）。
- `Attempt.status ∈ {pending, running, passed, failed, interrupted}`。
- `Checkpoint` 记录 `code_refs`（提交 / 工作树 / 分支），使 Attempt 失败后
  可被定位与重试。Checkpoint 绑定创建它的 Attempt（不可变历史）。

### D9 · Handoff（交接）

实例之间传递信息的动作，统称交接：

```text
Delegation（委托，父 ⟶ 子）: 传工作包（子契约 + 验收标准 + 工具 + 约束）
Submission（提交，子 ⟶ 父）: 传证据 + 结果
```

Handoff 隐含**执行流转移**（副作用）：
- Delegation 后，子实例开始处理，父实例冻结等待。
- Submission 后，父实例收到证据，恢复对该子契约的验收 / 后续处理。

Delegation / Submission 是执行性质的动作：谁在交接，谁就有执行权；
交接完成，执行权自然转移。

**并发约束**（并发数上限 = 1 时自动退化为串行）：

1. **DAG 前置验收**：任务的前置依赖必须先验收通过，才能开始处理。
2. **Boundary 包含关系**：子实例的 `boundary` 包含于父实例（`child.boundary ⊂ parent.boundary`）。
   推导：父与子不能同时写（否则子可能读到父的中间状态）。
3. **父冻结**：父实例委派后冻结，等**所有**子实例完成后才能继续。
   不能异步激活父实例——必须全部收集。
4. **委派原子操作**：委派通过两个原子操作完成——
   - **规定（Specify）**：定义子契约、验收标准、工具、约束；
   - **启动（Launch）**：创建子实例，开始处理。
   两个操作不可分割（原子性）。
5. **子实例之间可并行**：同一父实例的子实例可以并行处理（如果 `boundary`
   不相交），遵守共享资源池并发上限（如 LLM API 并发池），超过时排队。
6. **Steering 对话**：用户可以与任何一个活跃实例交互（steering），但
   非激活实例不可对话。
7. **新根对话**：用户可以开启新的根对话（新 Session）修改意图 / 契约，
   可选继承前一个 Session 的 DAG 状态，Agent 修改 DAG 后重新开始。
8. **范围限制**：steering 对话不能要求超出契约范围的工作；Agent 来拒绝，
   否则系统行为未定义。

**串行特化**：并发数上限 = 1 时，子实例串行执行，父冻结等待每个子实例
完成。这就是"单实例处理"的形态。

---

## 8. 定义：第四层（会话与约束）

### D10 · Session（会话）

```text
Session = ⟨root_instance, active_instances⟩
    root_instance   : 处理用户意图的根实例（p(i) = ⊥）
    active_instances : 当前可运行 / 未终止的实例集合
```

- 用户只能与**一个**活跃实例进行 steering 对话（非激活实例不可对话）。
- 多个活跃实例可以并行处理（如果满足 D9 并发约束），但用户只能 steering
  其中一个。
- 用户可以开启新的根对话（新 Session），修改意图 / 契约，可选继承前一个
  Session 的 DAG 状态，Agent 修改 DAG 后重新开始。

### D11 · Steering（定向对话）

用户与活跃实例的交互，称为 **steering**：

- steering 不能要求超出契约范围的工作；Agent 来拒绝，否则系统行为未定义。
- 用户切换 steering 到另一个实例时，不改变任何实例的执行状态（执行流由
  Delegation / Submission 隐式控制）。
- steering 是**会话性质**的动作——它只影响"用户在和谁说话"，不影响"谁在
  处理"。两者正交。

### D12 · Guard（守卫）

Guard 是一组**纯约束**，不做任何业务决策。它校验：

1. 实例边界（A3）：越界写操作 REJECT。
2. 验收权（T3）：子证据由父层裁决。
3. 单激活（T1）：同一契约不被重复处理。
4. 委托有界（T5）：`d(i) ≤ D_max`。
5. 证据绑定（D2/D3）：`e.contract_id` 存在且匹配。

Guard 的语义是"拒绝破坏不变量的一切操作"，不参与"任务怎么做、是否通过"。

---

## 9. 完整性

| 概念 | 定义 | 关键性质 |
|---|---|---|
| Intent | Pr1 | 系统输入端点，经讨论（D3.5）转化为契约 |
| Check | Pr2 | 判定真/假 |
| Work | Pr3 | 改变状态 |
| World State | Pr4 | 可观察状态 |
| Contract | D1 | 不可变，唯一 id |
| Evidence | D2 | 绑定契约，判定结果 |
| Satisfaction | D3 | 验收的可机器化基础 |
| Discussion | D3.5 | 意图→契约的桥梁，系统入口机制 |
| Instance | D4 | 处理单元，有 parent 与边界 |
| Work Packet | D4.5 | 工作包 = 契约 + 处理上下文，实例输入单元 |
| Processing | D5 | plan / build / delegate / supervise |
| Decision Points | D6 | 三个判定点：粒度 + 验收 + 后续 |
| Policy | D5.5 | Processing 的配置参数 + Interactive / Autonomous 两种应用模式 |
| Axiom: Processing | A1 | 完成态必产证据，与 T5 兼容 |
| Axiom: Recursion | A2 | 契约只有两个来源 |
| I-OneHandler | 不变量 | 一份契约同一时刻最多被一个实例处理 |
| Single-mode | T1 | 一契约一处理者（I-OneHandler 直接推出） |
| Boundary | A3 | 边界隔离公理 |
| Parent acceptance | T3 | 验收权在父层 |
| Immutability | T4 | 契约不可变 |
| Bounded recursion | T5 | 存在不终止路径（如果无限委托），需要 D_max 保证终止 |
| Depth | D7 | 深度定义 |
| Task/Attempt/Checkpoint | D8 | 实例内对象 |
| Handoff | D9 | Delegation / Submission + 并发约束（含串行特化） |
| Session | D10 | 用户与活跃实例对话，非激活不可对话 |
| Steering | D11 | 用户与活跃实例的交互，不能超出契约范围 |
| Guard | D12 | 纯约束层 |

---

## 10. 结论

本规范从 4 个原语（Intent / Check / Work / World State）出发，经 13 个
定义与 2 条公理，推出 6 条定理，覆盖了：

- **分解**（D5 plan + A2）：大契约 → 子契约 DAG；
- **执行**（D5 build + D3）：最小契约 → 可判定证据；
- **验收**（D5 supervise + T3）：父层裁决子层证据；
- **递归**（A2 + D7 + T5）：委托是唯一递归形式，且有界；
- **隔离与正交**（A3 + D9）：边界隔离、并发约束下的执行流控制。

**分形不是本规范的后置话题——它是公理 A2 的直接表达。** 整个系统就是
"一个实例处理契约、必要时委托子实例、父层验收证据"这一模式的任意深度
自相似。
