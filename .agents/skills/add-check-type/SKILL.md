---
description: 向 check 执行器注册表登记新的 check 类型（exec/test/typecheck/lint/...）时使用。
---

# Add Check Type

check.kind 必须注册（E-CHECK-UNREGISTERED，ADR-0004）。

## 步骤

1. **声明元数据**：`{kind, executor, timeout 默认, 成本等级, 确定性等级}`。
   确定性等级只能是 hard / soft / human；soft/human 在 Phase 5 前拒绝注册
   （需 Policy 聚合规则先行）。
2. **实现执行器**：`fractal_runtime/checks.py` 注册表内实现 runner，输入
   `(CheckSpec, boundary, sigma_ref)`，输出 CheckResult（bool + 日志引用 +
   sigma_ref）。执行器内禁止越出 boundary 写。
3. **测试**：`tests/` 用假 Σ（临时 git 目录）验证：通过 / 失败 / 超时 /
   sigma_ref 记录 / 缓存键 `(check.id, sigma_ref)` 命中。
4. **lint 规则**：契约入库时 kind ∈ 注册表（Guard 联测）。
5. **登记**：`spec/glossary.md`、`docs/architecture.md` 检查执行节；
   若改变了机制本身则先走 `spec-amend`。

## 禁止

- 注册不可判定真假或恒真的 kind。
- 在执行器里做业务决策（那是 Guard / Policy 的事）。
