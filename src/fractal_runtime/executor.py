"""build 能力执行体：在实例 boundary 内 headless 运行移植的 agent loop（ADR-0006）。

agent loop 移植自 tau_agent v0.4.1（MIT，huggingface/tau），落于 fractal_runtime；
执行前打 checkpoint（commit worktree），执行后收集变更路径供提交审计。
"""
