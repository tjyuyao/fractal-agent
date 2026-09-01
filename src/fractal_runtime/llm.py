"""plan / supervise / discuss 的结构化 LLM 调用（AM-0.1-01、ADR-0006）。

所有输出视为不可信输入：schema 校验 + 语义校验（无环、check_map 全覆盖），
修复预算 ≤2 次，超限交还调度器走 r(c,e,p)。
"""
