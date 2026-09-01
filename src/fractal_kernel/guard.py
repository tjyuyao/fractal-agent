"""Guard：纯约束层（fractal.md D12）。

只校验不变量，不做业务决策；错误码、REJECT 行为与恢复路径见 spec/invariants.md。
每个 Guard 规则必须有对应的不变量测试（implement-concept 步骤 3）。
"""
