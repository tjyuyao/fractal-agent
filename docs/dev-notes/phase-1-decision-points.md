# Phase 1 · D6 判定点与串行驱动器

日期：2026-09-02

## 加了什么

`fractal_kernel/scheduler.py`：

- D3 `satisfied(c,e)`：全 check 为 true 才满足，缺项视为未满足；
  无 check 契约恒满足（vacuous，与 D3 全称量词语义一致）。
- D6 三判定点纯函数：`granularity`（v0 checks 数量代理，AM-0.1-07）、
  `verify`（确定性）、`decide`（Interactive 默认 ask_user；
  Autonomous 阶梯 retry → reassign → replan → ask_user）。
- `SerialDriver`：build/check 以 Protocol 注入（内核零 LLM/tau/git 依赖）。
  事件序 delegation.launched → [attempt.started → check.executed* →
  evidence.recorded → attempt.finished] → decision.made。
- retry 预算用 `Policy.model_copy` 逐轮递减驱动阶梯（否则 decide 恒见
  retry_count>0，预算永不耗尽）。
- overflow 短路：build 报上下文溢出 → attempt.interrupted + replan 终止
  （AM-0.1-07 的"应分解"闭环）。
- T1 写入路径：驱动器内存登记处理者，二次 process 同契约直接
  GuardError(E-ONE-HANDLER)；fold 重放复验兜底。

## 关键取舍

- `delegation.launched` 在 v0 被复用为"契约进入处理"的登记事件——语义上
  它是 D9 的父→子委托，但串行特化下根实例自处理需要同一事件承载
  I-OneHandler 状态；Phase 2 引入真委托后拆分为 launched（子）与
  processing.started（自），或追加新事件类型（走 spec-amend）。
- reassign / replan 在执行者池与 plan 能力（Phase 2）落地前是终止决策，
  驱动器不循环，交还调用方。

## 如何测试

`tests/test_scheduler.py`（20 例）：sat 语义 4 例、v 确定性 2 例、
g 阈值 2 例、decide 阶梯 5 例、驱动器 7 例（含事件序精确断言、
retry 预算耗尽、interactive 立即上抛、overflow→replan、重放一致性、
二次处理拒绝）。

`uv run pytest` → 73 passed；ruff / format / mypy strict 全绿。

## 遗留

- delegation.launched 语义拆分（Phase 2，走 spec-amend）。
- sigma_ref 目前由 BuildBody 提供；exec 执行器 + boundary 落地后由
  runtime 统一计算（AM-0.1-06）。
- granularity 的 LLM 软信号组合（runtime/llm.py）。
