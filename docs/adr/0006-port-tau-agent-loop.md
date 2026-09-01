# ADR-0006: 移植 tau_agent 最小子集，运行时零依赖 tau

- 状态：已接受（2026-09-02）
- 关联：取代 ADR-0002 的依赖方式条款；AM-0.1-05；ADR-0001
- 来源：huggingface/tau v0.4.1（MIT），仅作参考与移植来源，不作依赖

## 背景

ADR-0002 以 editable path dependency 引入 tau-ai 作为 build 执行体。实践暴露
三个问题：

1. **安全强制的位置错位**：manifest 强制（AM-0.1-05 工具层拦截）要求在
   write/edit 工具内部校验路径；这依赖 tau_agent 工具函数签名与事件 schema
   保持稳定——外部包的内部 API 成为 fractal 安全边界的一部分，tau 的无关重构
   会静默变成 fractal 的安全相关变更。
2. **依赖重量错配**：安装 tau-ai 拉入 textual / rich / typer / pillow /
   pygments 等为 TUI 应用服务的传递依赖；headless 编排器不需要其中任何一个，
   与"小而纯的 kernel"哲学矛盾。
3. **仓库不可移植**：`../tau` 兄弟目录是硬前提，独立 clone 后 `uv sync`
   失败；tau 处于 0.4.x 活跃开发期，API 无稳定性承诺。

## 决策

- **移植而非依赖**：把 build 执行体所需的 tau_agent 最小子集移植进
  `fractal_runtime`（messages / tools / loop / events / harness 配置 /
  provider 适配 + fake provider），fractal 运行时对 tau 零依赖、零 import。
- **最小移植清单**（取自 tau_agent v0.4.1）：
  - 需要：messages、tools（含 manifest 拦截面）、loop、events、harness 配置、
    fake provider（golden 测试用）、一个 OpenAI 兼容 provider 适配。
  - 不需要：`session/`（事件日志才是事实来源，对话只是 artifact）、
    `tool_history`、其余 provider（anthropic / openrouter / hf…）与
    `tau_ai` / `tau_coding` 全部。
- **移植纪律**：
  - 移植须记录来源版本（v0.4.1）与逐条偏差；语义性偏差另立 ADR。
  - 保留 MIT 版权与归属（README credits + 移植模块头注明 ported from）。
  - 重新同步上游是显式决策（新 ADR），不是顺手更新。
- tau 的角色收敛为两件事：移植参考实现；本项目日常开发的 dev agent
  （工具角色，与依赖无关）。

## 否决的替代方案

- **PyPI 锁版本依赖**：解决可移植性，但拦截面与依赖重量问题不变。
- **subprocess 包裹 tau CLI**（`tau -p --cwd <worktree>`）：进程边界干净，
  但失去工具层拦截——manifest 强制退化为仅提交审计，A3 从两层强制降为一层；
  工具白名单与事件流无法程序化控制。否决。
- **整体 vendoring tau_agent**：保留上游 diff 能力，但引入用不到的
  session / tool_history 死重，且"反正都在"会诱发范围蔓延。否决。

## 后果

- 依赖图收缩为：pydantic（kernel schema）+（Phase 1 起）httpx（provider 适配）。
- 上游演进不再自动流入：tau 的修复需人工判断是否移植——成本换控制。
- `tests/test_imports.py` 升级：src/ 全域禁 import tau（原规则只约束 kernel）。
- ADR-0002 的"仅 executor.py 可 import tau"条款废止；其"不 vendor、以 tau 为
  参考"的精神由本 ADR 延续。
