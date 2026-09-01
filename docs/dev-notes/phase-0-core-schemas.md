# Phase 0 · 核心 schema、Guard 首批与事件日志

日期：2026-09-02

## 加了什么

- `fractal_kernel/models.py`：Instance（D4）、Mode（D5 四能力枚举）、Task/TaskStatus、
  Attempt/AttemptStatus（D8 明文枚举）、Checkpoint（D8）、Policy（D5.5，v0 默认值为占位）、
  `contract_digest` + `Contract.create`（AM-0.1-04 内容寻址 id）。
- `fractal_kernel/dag.py`：`find_cycle`（迭代三色 DFS，自环与悬空依赖处理）+
  `depth_of`（D7 的 d(i)）。
- `fractal_kernel/guard.py`：ErrorCode 六项（首批四项 + E-PARENT / E-ONE-HANDLER），
  六个纯校验函数；写入时校验与重放复验共用同一套判定。
- `fractal_kernel/store.py`：EventType 词汇表冻结（13 类）、Event、EventLog
  （JSONL append、seq 连续跨重开、损坏行 EventLogError）、WorldState + fold。

## 对应条款

D4/D5/D7/D8/D5.5、I-Contract / I-Evidence / I-Parent / I-OneHandler、
AM-0.1-02 / AM-0.1-04、ADR-0003 / ADR-0004。

## 如何测试

- 每个错误码一个不变量测试文件：`tests/test_invariant_e_*.py`（含 fold 路径的
  篡改检测用例：历史中同 id 异内容契约、孤儿实例、双 launch、未绑定证据均被拒绝）。
- `tests/test_dag.py`（环检测 + 深度）、`tests/test_store.py`（往返 / seq / 损坏 /
  fold 恢复）、`tests/test_models.py`（frozen + 枚举词汇表 + 内容寻址稳定性）。
- `uv run pytest` → 52 passed；ruff / format / mypy strict 全绿。

## 遗留

- E-DAG-MAP / E-BOUNDARY-* / E-DEPTH / E-BUDGET 随 Phase 1–3 落地。
- fold 对 ONE-HANDLER 的严格判定在 reassign/retry 处理者变更协议（AM-0.1-02，
  Phase 2）落地后需放宽——届时 decision.made 事件要参与 fold。
- Policy 默认值为占位，Phase 1 CLI 显式化。
