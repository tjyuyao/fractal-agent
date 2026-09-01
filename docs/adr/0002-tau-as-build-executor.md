# ADR-0002: tau 作为 build 执行体与底层参考实现

- 状态：已被 ADR-0006 部分取代（依赖方式条款废止；"以 tau 为参考实现"的定位保留）
- 关联：fractal.md D5 build；上层目录 `../tau`

## 背景

build 能力需要真实编码执行体（读写文件、跑命令、会话循环）。自研即重复造轮子；
tau（Python，Pi 风格）分层清晰：`tau_agent` 是可移植 harness（AgentHarness、loop、
tools、events、session），事件流契约明确，且原生支持 AGENTS.md 与 `.agents/` 资源。

## 决策

- `tau-ai` 以 editable path dependency 引入（`[tool.uv.sources]` 指向 `../tau`），
  不 vendor。
- build = 在实例 worktree 内 headless 运行一个 tau AgentHarness；工具白名单与提示
  来自工作包；转录进 artifacts。
- 仅 `fractal_runtime/executor.py` 允许 import tau；kernel/cli 禁止。
- tau 同时是本项目开发参考：分层（brain / environment / frontend）、事件契约、
  JSONL 会话、dev-notes / ADR 文档习惯均向其看齐。

## 后果

- 依赖 `../tau` 的存在与 API 稳定性；升级 tau 需回归 golden 测试（Phase 2 起）。
- tau 的工具集（read/write/edit/bash）成为 manifest 强制的拦截面。
