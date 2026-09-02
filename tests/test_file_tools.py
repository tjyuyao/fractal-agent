"""file_tools 拦截面测试：write/edit 过 manifest（A3 / AM-0.1-05），read 不受限。

Guard REJECT 在工具结果上以 details.guard = E-BOUNDARY-WRITE 表达；executor
经 after_tool_call 钩子将其提升为 error 结果并记 guard.rejected 事件。
"""

from __future__ import annotations

from pathlib import Path

from fractal_runtime.file_tools import (
    ARTIFACT_PATH_KEY,
    GUARD_DETAIL_KEY,
    artifact_path,
    build_file_tools,
    guard_rejection,
)
from fractal_runtime.tools import AgentTool, AgentToolResult

BOUNDARY = ("src", "docs/notes.md")


def _tools(tmp_path: Path) -> dict[str, AgentTool]:
    return {tool.name: tool for tool in build_file_tools(BOUNDARY, tmp_path)}


async def _call(tool: AgentTool, **arguments: object) -> AgentToolResult:
    return await tool.execute("call-1", arguments)  # type: ignore[arg-type]


class TestWriteFile:
    async def test_write_inside_manifest_creates_file(self, tmp_path: Path) -> None:
        tool = _tools(tmp_path)["write_file"]

        result = await _call(tool, path="src/new/mod.py", content="x = 1")

        assert (tmp_path / "src/new/mod.py").read_text() == "x = 1"
        assert result.details[ARTIFACT_PATH_KEY] == "src/new/mod.py"  # type: ignore[index]
        assert artifact_path(result) == "src/new/mod.py"
        assert guard_rejection(result) is None

    async def test_write_outside_manifest_rejected(self, tmp_path: Path) -> None:
        tool = _tools(tmp_path)["write_file"]

        result = await _call(tool, path="README.md", content="evil")

        assert not (tmp_path / "README.md").exists()
        assert result.details[GUARD_DETAIL_KEY] == "E-BOUNDARY-WRITE"  # type: ignore[index]
        assert "E-BOUNDARY-WRITE" in result.text
        assert artifact_path(result) is None

    async def test_write_traversal_rejected(self, tmp_path: Path) -> None:
        tool = _tools(tmp_path)["write_file"]

        result = await _call(tool, path="src/../escape.txt", content="evil")

        assert not (tmp_path / "escape.txt").exists()
        assert guard_rejection(result) == "E-BOUNDARY-WRITE"

    async def test_write_file_root_exact_allowed(self, tmp_path: Path) -> None:
        tool = _tools(tmp_path)["write_file"]

        result = await _call(tool, path="docs/notes.md", content="notes")

        assert (tmp_path / "docs/notes.md").read_text() == "notes"
        assert artifact_path(result) == "docs/notes.md"


class TestEditFile:
    async def test_edit_replaces_single_occurrence(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src/a.py").write_text("value = 1\n")
        tool = _tools(tmp_path)["edit_file"]

        result = await _call(tool, path="src/a.py", old_text="value = 1", new_text="value = 2")

        assert (tmp_path / "src/a.py").read_text() == "value = 2\n"
        assert artifact_path(result) == "src/a.py"

    async def test_edit_ambiguous_match_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src/a.py").write_text("x\nx\n")
        tool = _tools(tmp_path)["edit_file"]

        result = await _call(tool, path="src/a.py", old_text="x", new_text="y")

        assert result.text.startswith("error:")
        assert "2 times" in result.text
        assert (tmp_path / "src/a.py").read_text() == "x\nx\n"

    async def test_edit_missing_file_is_tool_error(self, tmp_path: Path) -> None:
        tool = _tools(tmp_path)["edit_file"]

        result = await _call(tool, path="src/none.py", old_text="a", new_text="b")

        assert result.text.startswith("error:")
        assert guard_rejection(result) is None


class TestReadFile:
    async def test_read_outside_manifest_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "secrets").mkdir()
        (tmp_path / "secrets/env.txt").write_text("A=1")
        tool = _tools(tmp_path)["read_file"]

        result = await _call(tool, path="secrets/env.txt")

        assert result.text == "A=1"

    async def test_read_missing_file_is_error(self, tmp_path: Path) -> None:
        tool = _tools(tmp_path)["read_file"]

        result = await _call(tool, path="src/none.py")

        assert result.text.startswith("error:")
