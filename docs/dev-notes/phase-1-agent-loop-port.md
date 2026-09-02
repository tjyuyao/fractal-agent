# Phase 1 · 移植 agent loop（tau_agent v0.4.1 → fractal_runtime，ADR-0006）

日期：2026-09-02

## 加了什么

### 移植子集（`fractal_runtime/`，平铺、保留上游文件名以便 diff）

| 文件 | 来源 | 说明 |
|---|---|---|
| `types.py` | tau_agent/types.py | 逐字移植 |
| `messages.py` | tau_agent/messages.py | 移植 + 裁剪（见偏差 1） |
| `tools.py` | tau_agent/tools.py | 逐字移植（AgentTool 框架） |
| `provider.py` | tau_agent/provider.py | 逐字移植（ModelProvider 协议） |
| `provider_events.py` | tau_agent/provider_events.py | 逐字移植 |
| `events.py` | tau_agent/events.py | 逐字移植（loop 级缓存事件） |
| `loop.py` | tau_agent/loop.py | 移植 + 偏差 2（去 tool_history） |
| `harness.py` | tau_agent/harness.py | 逐字移植（steering 队列 Phase 4 启用） |
| `fake_provider.py` | tau_ai/fake.py | 移植（golden/确定性测试用） |

### fractal 自有部分

- `fractal_kernel/guard.py`：新增 `E-BOUNDARY-WRITE` 错误码 + `check_boundary_write`——
  posixpath 规范化 + `PurePosixPath.is_relative_to` 组件级包含（"src" 不放行
  "srcfoo/"）；绝对路径、根逃逸、空路径、空 manifest 一律拒绝。纯字符串运算，
  无文件系统访问，kernel 纯净性不变。工具层拦截与提交审计共用本判定。
- `fractal_runtime/boundary.py`：`enforce_write` 把 worktree 相对路径交给 Guard，
  返回规范化 POSIX 路径。
- `fractal_runtime/file_tools.py`：read/write/edit 工具（fractal 原创，非移植），
  挂接 `AgentTool` 框架构成 manifest 拦截面（AM-0.1-05）。write/edit 前校验，
  越界返回结构化错误结果（`details.guard = E-BOUNDARY-WRITE`），loop 不中断、
  模型可自行纠正；成功写标记 `details.artifact_path` 供证据收集（D2 artifacts）。
  read 不受限——A3 约束写，不约束读。
- `fractal_runtime/executor.py`：`LoopBuildBody` 实现 kernel 的 `BuildBody` 协议。
  系统提示 = 契约 intent + checks + constraints + manifest 声明；用户消息 =
  contract.intent；工具白名单 = packet.tools ∩ 注册表（D4.5）。每轮 attempt 从
  工作包重建上下文（AM-0.1-02）。`after_tool_call` 钩子把 Guard 拒绝提升为
  error 结果并记 `guard.rejected` 事件；事件收集器聚合 `artifact_path` 为
  BuildResult.artifacts。溢出检测见下。sigma_ref 占位空串，worktree checkpoint
  落地后由 runtime 统一计算（AM-0.1-06）。
- `fractal_runtime/openai_provider.py`：OpenAI 兼容 chat-completions 流式适配，
  **最小重写**而非移植——取自 tau_ai/openai_compatible.py 的 SSE/工具调用增量
  累积 + tau_ai/stream.py 的 canonical 块生命周期，压缩为单层。排除（v0）：
  responses API、重试/退避（Phase 5 治理）、会话亲和、compat 旋钮、凭据解析、
  图像载荷。HTTP 400 且 error.code/message 指示上下文超限时归一化为
  `context_length_exceeded: …` 前缀。
- 溢出信号（AM-0.1-07）：`is_context_overflow(error_message)` 判定终态
  error_message 是否带稳定标记前缀；驱动器据 `BuildResult.overflow=True` 走
  interrupted + replan 闭环（SerialDriver 集成测试覆盖）。
- `pyproject.toml`：httpx>=0.27 加回运行时依赖（ADR-0006 预告）。

## 移植偏差记录（ADR-0006 纪律）

1. **session/UI 消息角色裁剪**：BashExecutionMessage / CustomMessage /
   BranchSummaryMessage / CompactionSummaryMessage 不移植，`AgentMessage`
   缩为 UserMessage | AssistantMessage | ToolResultMessage 三角色 union；
   `message_to_user` / `message_text` 渲染辅助随之删除。headless loop 不需要。
2. **tool_history 不移植**（ADR-0006 明文排除）：loop 的 `_provider_context`
   不再调用 `repair_tool_history`，仅保留"丢弃空 error/aborted 回合"过滤。
   安全性论证：fractal 每轮 attempt 从工作包重建对话（AM-0.1-02），不存在
   中途恢复的转录；call/result 配对由 loop 自身即时追加保证。
3. **语义性偏差：无。** 事件词汇、消息模型、loop 控制流、harness 行为与
   上游一致；若后续发现需要语义级偏离，另立 ADR。
4. `test_imports.py` 的 tau 禁令按 `fractal_*/*.py` 递归匹配已覆盖新文件
   （平铺布局），无需改动；kernel 禁 httpx 等规则不变。

## 关键取舍

- **拦截层语义**：GuardError 不在工具内向上抛（会被 loop 宽 except 吞成无结构
  文本），而是返回结构化 error 结果；executor 用 `after_tool_call` 钩子把
  `details.guard` 提升为 `is_error=True` 并记 guard.rejected——模型看到错误
  文本可纠正，审计事件同步落盘（spec/invariants.md E-BOUNDARY-WRITE 的
  REJECT 行为 + 恢复路径）。
- **executor 同步桥**：`build()` 内 `asyncio.run` 驱动一次性 headless 会话，
  保持 SerialDriver 同步协议；代价是不可在运行中的事件循环内调用（Phase 1
  CLI 场景成立，Phase 2 委托并发时重审）。
- **溢出检测的归属**：标记常量定义在 openai_provider（错误形态的知情者），
  判定函数在 executor（AM-0.1-07 的执行者）；fake provider 测试直接构造带
  标记的错误消息，不依赖 provider 内部。

## 如何测试

- `tests/test_invariant_e_boundary_write.py`（13 例，先红后绿）：空 manifest、
  越界、前缀混淆、文件根精确匹配、父目录逃逸、绝对路径、根逃逸、空路径、
  尾斜杠规范化。
- `tests/test_agent_loop.py`（9 例）：canonical 事件序精确断言、工具往返、
  未知工具、before_tool_call 拦截、provider error 终止、max_turns、工具异常
  隔离、消息规范化。FakeProvider 驱动，无网络。
- `tests/test_agent_harness.py`（4 例）：消息累积、steering 注入、监听器、
  运行互斥。
- `tests/test_file_tools.py`（9 例）：界内写/越界拒/逃逸拒/文件根、edit 唯一
  匹配与歧义拒绝、read 不受限。
- `tests/test_agent_executor.py`（8 例）：产物收集、拦截 → guard.rejected 事件、
  白名单过滤、溢出 → BuildResult.overflow、普通错误非溢出、**溢出 → SerialDriver
  replan 闭环（AM-0.1-07）**、系统提示内容。
- `tests/test_openai_provider.py`（8 例，httpx.MockTransport 离线）：SSE 文本/工具
  调用增量累积、usage 块、4xx 归一化（含溢出标记）、网络错误、载荷构造。

## 验证

`uv run pytest` → 124 passed；`uv run ruff check .` / `ruff format --check` /
`mypy`（strict，23 文件）全绿。

## 遗留

- sigma_ref 统一计算：worktree 载体 + 提交时 diff 审计（`fractal_runtime/boundary.py`
  预留）→ 与 exec 检查注册表一起落地。
- exec 检查执行器注册表（`fractal_runtime/checks.py`）与 (check.id, sigma_ref)
  缓存。
- discuss 最小入口（意图 → 顶层契约，checks 过注册表 lint）。
- executor 的 asyncio.run 桥在事件循环内不可用——Phase 2 委托并发时重审。
- openai_provider 的重试/退避与 `guard.rejected` 之外的事件记账（budget.updated）
  在 Phase 5 治理引入。
