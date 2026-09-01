# ADR-0001: Boundary = Manifest 声明 + Worktree 载体

- 状态：已接受（2026-09-02）
- 关联：fractal.md A3 / D4 / D9；AM-0.1-05

## 背景

git worktree 提供隔离可写视图、commit checkpoint 与合并机制，但作为边界声明过宽：
实例可见整个仓库，两个实例是否冲突不可判定。不存在更成熟的现成方案。

## 决策

boundary 三层分离：

1. **载体**：git worktree（隔离视图 + commit + 合并）；
2. **声明**：可写路径 manifest，由 plan 在分解时产出，实例创建时固定；
3. **强制**：工具层拦截（write/edit 前校验）+ 提交时 diff 审计（bash 副作用兜底）。

冲突判定 = manifest 集合求交，静态可判。并行兄弟要求 manifest 两两不相交；
交集出路 = 加依赖边串行化，或抽集成契约独占交集。

## 后果

- 冲突可判定，但 shell 副作用只能事后审计（兜底非预防）。
- plan 负担增加：必须产出 manifest；Guard 校验（E-BOUNDARY-OVERLAP）。
- 横切变更（imports/配置）需集成契约承载，串行执行。
