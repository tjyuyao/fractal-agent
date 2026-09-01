"""确定性内核：模型、事件日志、Guard、DAG、调度。

导入规则（AGENTS.md / ADR-0002 / ADR-0003）：本包不得 import fractal_runtime、
fractal_cli、tau、git、subprocess 或任何 LLM SDK；纯净性由 tests/test_imports.py 强制。
"""
