"""Check 执行器注册表（ADR-0004）。

kind → executor；注册项声明 {timeout, 成本等级, 确定性等级}；
v0 仅 hard（exec：命令退出码）。结果缓存键 (check.id, sigma_ref)（AM-0.1-06）。
新增类型走 add-check-type 技能。
"""
