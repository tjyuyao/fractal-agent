# Glossary: Spec ↔ Code

| 规范 | 符号/对象 | 代码位置 |
|---|---|---|
| Pr2 / D1 check | `CheckSpec` | `fractal_kernel/models.py` |
| D1 contract | `Contract` | `fractal_kernel/models.py` |
| D2 evidence | `Evidence`（含 sigma_ref，AM-0.1-06） | `fractal_kernel/models.py` |
| D4.5 work packet | `WorkPacket` | `fractal_kernel/models.py` |
| D4 instance | `Instance` | `fractal_kernel/models.py` |
| D5 plan/build/delegate/supervise | 四能力点 | plan/supervise→`fractal_runtime/llm.py`；build→`fractal_runtime/executor.py`；delegate/supervise 状态机→`fractal_kernel/scheduler.py` |
| D6 g/v/r 判定点 | `g(c)` / `v(c,e)` / `r(c,e,p)` | `fractal_kernel/scheduler.py`（已落地）+ llm 软信号（Phase 1） |
| D8 task/attempt/checkpoint | `Task` / `Attempt` / `Checkpoint` | `fractal_kernel/models.py` |
| D12 guard | Guard 规则集 | `fractal_kernel/guard.py`（首批 6 错误码已落地） |
| A3 / AM-0.1-05 boundary | manifest + worktree 载体 | `fractal_runtime/boundary.py` |
| Σ 指纹 | `sigma_ref` | `Evidence.sigma_ref`；`fractal_runtime` 计算 |
| 事件日志 | `EventLog` / `Event` / `EventType` / `fold` | `fractal_kernel/store.py`（已落地） |
| D7 委托深度 | `d(i) ≤ D_max` | `fractal_kernel/dag.py`（`depth_of`） |
| D5.5 policy | `Policy` | `fractal_kernel/models.py` |
