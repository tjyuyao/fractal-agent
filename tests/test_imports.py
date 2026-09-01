"""Import 纯净性与包冒烟测试（AGENTS.md 依赖规则）。"""

from __future__ import annotations

import ast
from pathlib import Path

KERNEL_DIR = Path(__file__).resolve().parents[1] / "src" / "fractal_kernel"
SRC_DIR = Path(__file__).resolve().parents[1] / "src"

FORBIDDEN_IN_KERNEL = frozenset(
    {
        "fractal_runtime",
        "fractal_cli",
        "tau_agent",
        "tau_ai",
        "tau_coding",
        "subprocess",
        "git",
        "httpx",
        "openai",
        "anthropic",
    }
)

TAU_ROOTS = frozenset({"tau_agent", "tau_ai", "tau_coding"})


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_packages_importable() -> None:
    import fractal_cli
    import fractal_kernel
    import fractal_runtime

    assert fractal_kernel.__doc__
    assert fractal_runtime.__doc__
    assert fractal_cli.__doc__


def test_kernel_is_pure() -> None:
    """fractal_kernel 不得 import 被禁止的模块（ADR-0002、ADR-0003）。"""
    for path in sorted(KERNEL_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = _imported_roots(tree) & FORBIDDEN_IN_KERNEL
        assert not bad, f"{path.name}: forbidden import(s) {sorted(bad)}"


def test_no_tau_imports_anywhere() -> None:
    """src/ 全域禁止 import tau：移植而非依赖（ADR-0006）。"""
    for path in sorted(SRC_DIR.rglob("fractal_*/*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = _imported_roots(tree) & TAU_ROOTS
        assert not bad, f"{path.name}: forbidden tau import(s) {sorted(bad)}"
