# Roadmap

验收标准直接映射定理与不变量；每阶段结束时由 `phase-verify` 技能核对并更新状态。

| Phase | 内容 | 验收 | 状态 |
|---|---|---|---|
| 0 | 冻结：schema、事件类型、不变量测试、依赖规则 lint | pytest/ruff/mypy 全绿；invariants.md 错误码与 Guard 一一对应 | 已完成 |
| 1 | 串行单实例：移植 agent loop 为 build 执行体（ADR-0006）、深度 ≤1、并发=1、仅 hard 检查、Interactive 模式 | 3 个真实小任务端到端完成且证据链完整（A1）；不变量测试全绿 | **进行中** |
| 2 | 递归：delegate + 子实例 + 父冻结/休眠恢复 + check_map + D_max | 深度 3 任务；T3/T4/T5 具名测试；杀进程后从事件日志恢复 | 未开始 |
| 3 | 并发与隔离：并行兄弟、manifest 校验、资源池、集成契约 | 3 分支并行任务；E-BOUNDARY-* fuzz 零漏检 | 未开始 |
| 4 | 交互层：discuss、steering 路由、ask_user 冒泡、模式切换、会话继承（AM-0.1-04） | Interactive/Autonomous 双模式端到端 | 未开始 |
| 5 | 治理与强化：预算记账、风险表、llm-judge 校准、故障注入、成本基准 | 故障注入套件通过；成本基准报告 | 未开始 |

## Phase 0 清单

- [x] 规范缺口裁决（`spec/amendments.md` 集合 0.1）
- [x] 不变量目录与 Guard 错误码（`spec/invariants.md`）
- [x] 项目骨架、依赖、文档系统、技能
- [x] 核心模型首批判（CheckSpec / Contract / Evidence / WorkPacket）
- [x] import 依赖规则 lint（kernel 纯净性 + src/ 全域禁 tau）
- [x] 依赖方式裁决：移植而非依赖 tau（ADR-0006，取代 ADR-0002 依赖条款）
- [x] 核心 schema 补全（Instance / Task / Attempt / Checkpoint / Policy / Event）
- [x] Guard 首批实现（E-CONTRACT-MUTATE / E-EVIDENCE-UNBOUND / E-DAG-CYCLE /
      E-CHECK-UNREGISTERED）+ 追加 E-PARENT / E-ONE-HANDLER，全部带不变量测试
- [x] 事件日志 v0（`store.py`）+ fold 恢复（重放路径复验 Guard）

## Phase 1 清单

- [x] D3 `sat` / D6 `g`/`v`/`r` 纯判定 + 串行驱动器（build/check 协议注入，事件全记录，
      overflow → replan 闭环即 AM-0.1-07）
- [ ] 移植 agent loop：messages / tools / loop / events + fake provider（ADR-0006）
- [ ] exec 检查执行器注册表（`fractal_runtime/checks.py`）+ sigma_ref 计算（boundary）
- [ ] discuss 最小入口（意图 → 顶层契约，checks 过注册表 lint）
- [ ] 端到端：3 个真实小任务证据链完整（A1）
