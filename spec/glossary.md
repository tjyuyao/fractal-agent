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
| D12 guard | Guard 规则集 | `fractal_kernel/guard.py`（7 错误码已落地，含 E-BOUNDARY-WRITE） |
| A3 / AM-0.1-05 boundary 判定 | `check_boundary_write` | `fractal_kernel/guard.py`（组件级包含，纯字符串） |
| A3 / AM-0.1-05 工具层拦截 | `enforce_write` / `build_file_tools` | `fractal_runtime/boundary.py` / `fractal_runtime/file_tools.py`（write/edit 前校验，E-BOUNDARY-WRITE） |
| D5 build 执行体 | `LoopBuildBody`（实现 `BuildBody`） | `fractal_runtime/executor.py`（移植 agent loop 适配，AM-0.1-07 溢出信号） |
| AM-0.1-07 溢出信号 | `is_context_overflow` / `CONTEXT_OVERFLOW_MARKER` | `fractal_runtime/executor.py`；标记由 `fractal_runtime/openai_provider.py` 归一化注入 |
| Σ 指纹 | `sigma_ref` | `Evidence.sigma_ref`；`fractal_runtime` 计算 |
| 事件日志 | `EventLog` / `Event` / `EventType` / `fold` | `fractal_kernel/store.py`（已落地） |
| D7 委托深度 | `d(i) ≤ D_max` | `fractal_kernel/dag.py`（`depth_of`） |
| D5.5 policy | `Policy` | `fractal_kernel/models.py` |
| 移植 agent loop（ADR-0006） | messages / tools / loop / events / harness / FakeProvider | `fractal_runtime/{messages,tools,loop,events,provider,provider_events,harness,fake_provider}.py`（tau_agent v0.4.1，MIT） |
| OpenAI 兼容适配 | `OpenAICompatibleProvider` | `fractal_runtime/openai_provider.py`（chat-completions 流式，最小重写） |
