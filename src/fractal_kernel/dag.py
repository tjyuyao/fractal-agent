"""契约 DAG 与委托深度的纯图算法（D5 plan 输出、D7、T5）。

无环判定是 Guard 规则 E-DAG-CYCLE 的判定基础；depth_of 是 D7 的
d(i) 定义，供 E-DEPTH（Phase 1）使用。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

_WHITE, _GRAY, _BLACK = 0, 1, 2


def find_cycle(edges: Mapping[str, Sequence[str]]) -> tuple[str, ...] | None:
    """返回一条环路径（首尾相接的节点序列），无环返回 None。

    自环返回 (a, a)；悬空依赖（不在 edges 键中的节点）视为叶子。
    """
    color: dict[str, int] = dict.fromkeys(edges, _WHITE)
    parent: dict[str, str] = {}
    for start in edges:
        if color[start] != _WHITE:
            continue
        stack = [start]
        while stack:
            node = stack[-1]
            if color.get(node, _WHITE) == _WHITE:
                color[node] = _GRAY
            advanced = False
            for dep in edges.get(node, ()):
                state = color.get(dep, _WHITE)
                if state == _GRAY:
                    return _cycle_path(parent, node, dep)
                if state == _WHITE:
                    parent[dep] = node
                    stack.append(dep)
                    advanced = True
                    break
            if not advanced:
                color[node] = _BLACK
                stack.pop()
    return None


def _cycle_path(parent: dict[str, str], node: str, entry: str) -> tuple[str, ...]:
    """回溯 GRAY 链构造环路径：(entry, ..., node, entry)。"""
    path = [node]
    while path[-1] != entry:
        path.append(parent[path[-1]])
    path.reverse()
    path.append(entry)
    return tuple(path)


def depth_of(instance_id: str, parents: Mapping[str, str | None]) -> int:
    """委托深度 d(i)：根为 0，否则 d(p(i)) + 1（D7）。未知实例视为根。"""
    depth = 0
    current = parents.get(instance_id)
    while current is not None:
        depth += 1
        current = parents.get(current)
    return depth
