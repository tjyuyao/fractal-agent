# Architecture

## 层次与依赖

```text
fractal_cli      discuss / steering / session 入口              只在最上层
fractal_runtime  副作用层：boundary、checks、build 执行体、LLM
fractal_kernel   纯内核：模型、事件日志、Guard、DAG、调度          无 LLM / 无 git / 无 tau
外部             git = 载体与 checkpoint；LLM provider（OpenAI 兼容）
```

依赖方向单向向下（由 `tests/test_imports.py` 强制）。kernel 的纯净性是
"不变量测试不依赖 LLM/网络/tau" 的前提。

## 数据与控制流（一次处理）

1. **discuss**（Phase 4）：用户意图 → LLM 结构化对话 → 一个或多个顶层契约
   （checks 过注册表 lint）。
2. 实例收到工作包（契约 + checkpoint + tools + constraints + manifest）。
3. **粒度判定 `g(c)`**（AM-0.1-07）：
   - `direct` → build；
   - `decompose` → **plan**（LLM）产出子契约 DAG + `check_map`（AM-0.1-01）+
     每个子契约的 manifest（AM-0.1-05）→ Guard 校验（E-DAG-CYCLE / E-DAG-MAP /
     E-BOUNDARY-OVERLAP / E-DEPTH）→ **delegate**。
4. **delegate = Specify + Launch**（D9）：包装工作包，创建子实例（worktree +
   manifest），父冻结。
5. 子实例终态返回证据（含 sigma_ref）；全部子证据到齐后父解冻。
6. **supervise**：按 check_map 计算父证据每个判定 → `v(c,e)`；reject →
   `r(c,e,p)`（retry / reassign / replan / ask_user，Policy 驱动）。
7. 全程事件追加到日志（ADR-0003）：状态 = fold(events)。

## build 执行体（ADR-0006：移植的 agent loop）

- `fractal_runtime` 内含从 tau_agent v0.4.1 移植的最小 agent loop（messages /
  tools / loop / events / provider 适配 + fake provider），是 manifest 工具层
  拦截的实现位置。运行时对 tau 零依赖、零 import（`tests/test_imports.py` 强制）。
- 构造：cwd = 实例 worktree；工具白名单来自工作包 `tools`；write/edit 经 manifest
  校验（E-BOUNDARY-WRITE）；系统提示 = 契约 intent + constraints + manifest 声明。
- 执行前 runtime 打 checkpoint（commit worktree）；执行后收集
  `git diff --name-only` 供提交审计。
- tau（`../tau`）仅作移植参考与日常 dev agent（工具角色，非依赖）。

## 事件日志（ADR-0003）

- 格式：append-only JSONL，一行一事件；运行目录 `.fractal/sessions/<run-id>/events.jsonl`。
- 事件类型（v0 冻结于 Phase 0，`fractal_kernel/store.py`）：`session.started`、
  `instance.created`、`contract.registered`、`delegation.specified`、
  `delegation.launched`、`attempt.started`、`attempt.finished`、`check.executed`、
  `evidence.recorded`、`decision.made`、`guard.rejected`、`budget.updated`、
  `session.inherited`。
- 恢复 = 重放折叠；LLM 对话是缓存，不是事实来源。

## 边界机制（ADR-0001 / AM-0.1-05）

- 载体：每个实例一个 git worktree（`.fractal/worktrees/<instance-id>`），
  `child.boundary ⊂ parent.boundary` 由分支谱系表达。
- 声明：manifest（可写路径集合，plan 产出）；兄弟并行要求两两不相交。
- 强制：工具层拦截（write/edit 前校验）+ 提交时 diff 审计；bash 副作用由审计兜底。
- 交集出路：依赖边串行化，或集成契约独占交集。

## 检查执行（ADR-0004）

- 注册表：kind → executor；注册项声明 {timeout 默认, 成本等级, 确定性等级}。
- 确定性等级：hard / soft / human；v0 只实现 hard（exec：命令退出码）；
  soft/human 在 Phase 5 引入，聚合规则由 Policy 定义。
- 结果缓存键 `(check.id, sigma_ref)`（AM-0.1-06）。
