"""E-BOUNDARY-WRITE 不变量测试：写目标必须 ∈ 本实例 manifest（A3 / AM-0.1-05）。

Guard 规则落在 kernel（纯字符串运算，无文件系统访问）；runtime 工具层
（write/edit 拦截）与提交审计共用本判定。
"""

from __future__ import annotations

import pytest

from fractal_kernel.guard import ErrorCode, GuardError, check_boundary_write


class TestBoundaryWrite:
    def test_empty_manifest_rejects_everything(self) -> None:
        with pytest.raises(GuardError) as excinfo:
            check_boundary_write((), "src/a.py")
        assert excinfo.value.code is ErrorCode.BOUNDARY_WRITE

    def test_write_inside_root_allowed(self) -> None:
        check_boundary_write(("src",), "src/a.py")
        check_boundary_write(("src",), "src/deep/nested/b.py")

    def test_write_root_itself_allowed(self) -> None:
        check_boundary_write(("src",), "src")

    def test_write_outside_rejected(self) -> None:
        with pytest.raises(GuardError) as excinfo:
            check_boundary_write(("src",), "docs/a.md")
        assert excinfo.value.code is ErrorCode.BOUNDARY_WRITE

    def test_prefix_confusion_rejected(self) -> None:
        """manifest 根 "src" 不得放行 "srcfoo/…"（按路径组件匹配，非字符串前缀）。"""
        with pytest.raises(GuardError) as excinfo:
            check_boundary_write(("src",), "srcfoo/a.py")
        assert excinfo.value.code is ErrorCode.BOUNDARY_WRITE

    def test_file_root_exact_match_allowed(self) -> None:
        check_boundary_write(("docs/notes.md",), "docs/notes.md")

    def test_file_root_sibling_rejected(self) -> None:
        with pytest.raises(GuardError):
            check_boundary_write(("docs/notes.md",), "docs/notes.md.bak")

    def test_parent_traversal_rejected(self) -> None:
        with pytest.raises(GuardError) as excinfo:
            check_boundary_write(("src",), "src/../secrets.env")
        assert excinfo.value.code is ErrorCode.BOUNDARY_WRITE

    def test_absolute_path_rejected(self) -> None:
        with pytest.raises(GuardError) as excinfo:
            check_boundary_write(("src",), "/etc/passwd")
        assert excinfo.value.code is ErrorCode.BOUNDARY_WRITE

    def test_root_escape_rejected(self) -> None:
        with pytest.raises(GuardError):
            check_boundary_write(("src",), "../outside.txt")

    def test_dot_path_rejected(self) -> None:
        with pytest.raises(GuardError):
            check_boundary_write(("src",), ".")

    def test_trailing_slash_normalized(self) -> None:
        check_boundary_write(("src",), "src/")
        with pytest.raises(GuardError):
            check_boundary_write(("src",), "docs/")

    def test_reject_message_contains_path(self) -> None:
        with pytest.raises(GuardError) as excinfo:
            check_boundary_write(("src",), "docs/a.md")
        assert "docs/a.md" in excinfo.value.message
