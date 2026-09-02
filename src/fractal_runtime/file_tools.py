"""File tools: the manifest interception surface of the build loop (AM-0.1-05).

Fractal-original tools (not ports) built on the ported AgentTool framework
(tau_agent v0.4.1, ADR-0006). write/edit validate the target against the
instance manifest before touching the filesystem: out-of-boundary targets get
an error result carrying ``E-BOUNDARY-WRITE`` in text and details, so the loop
continues and the model can correct course — Guard REJECT semantics at the
tool layer, submission-time diff audit remains the second enforcement layer
(spec/invariants.md E-BOUNDARY-WRITE recovery path). Reads are unrestricted:
A3 constrains writes, not observations.

Successful writes/edits mark ``artifact_path`` (manifest-relative) in result
details for evidence collection (D2 artifacts).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path

from fractal_kernel.guard import ErrorCode, GuardError
from fractal_runtime.boundary import enforce_write
from fractal_runtime.messages import TextContent
from fractal_runtime.tools import (
    AgentTool,
    AgentToolResult,
    ToolCancellationToken,
    ToolExecutor,
    ToolUpdateCallback,
)
from fractal_runtime.types import JSONValue

GUARD_DETAIL_KEY = "guard"
ARTIFACT_PATH_KEY = "artifact_path"


def _error(code: ErrorCode, path: str, message: str) -> AgentToolResult:
    return AgentToolResult(
        content=[TextContent(text=f"[{code.value}] {message}")],
        details={GUARD_DETAIL_KEY: code.value, "path": path},
    )


def _tool_error(path: str, exc: Exception) -> AgentToolResult:
    return AgentToolResult(
        content=[TextContent(text=f"error: {path}: {exc}")],
        details={"path": path},
    )


def _string_arg(arguments: Mapping[str, object], key: str) -> str | None:
    value = arguments.get(key)
    return value if isinstance(value, str) else None


ToolFunc = Callable[[str, Mapping[str, JSONValue]], Awaitable[AgentToolResult]]


def build_file_tools(boundary: Sequence[str], cwd: Path) -> list[AgentTool]:
    """Build read/write/edit tools bound to one instance manifest and worktree."""

    def guarded(func: ToolFunc) -> ToolExecutor:
        async def execute(
            tool_call_id: str,
            arguments: Mapping[str, JSONValue],
            signal: ToolCancellationToken | None = None,
            on_update: ToolUpdateCallback | None = None,
        ) -> AgentToolResult:
            del tool_call_id, signal, on_update
            path = _string_arg(arguments, "path")
            if path is None:
                return _tool_error("", ValueError("missing string argument 'path'"))
            try:
                return await func(path, arguments)
            except GuardError as exc:
                if exc.code is ErrorCode.BOUNDARY_WRITE:
                    return _error(exc.code, path, exc.message)
                raise

        return execute

    async def read_file(
        tool_call_id: str,
        arguments: Mapping[str, object],
        signal: object = None,
        on_update: ToolUpdateCallback | None = None,
    ) -> AgentToolResult:
        del tool_call_id, signal, on_update
        path = _string_arg(arguments, "path")
        if path is None:
            return _tool_error("", ValueError("missing string argument 'path'"))
        try:
            content = (cwd / path).read_text(encoding="utf-8")
        except OSError as exc:
            return _tool_error(path, exc)
        return AgentToolResult(
            content=[TextContent(text=content)],
            details={"path": path},
        )

    @guarded
    async def write_file(path: str, arguments: Mapping[str, object]) -> AgentToolResult:
        target = enforce_write(boundary, path)
        content = _string_arg(arguments, "content")
        if content is None:
            return _tool_error(path, ValueError("missing string argument 'content'"))
        size = len(content.encode("utf-8"))
        full = cwd / target
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return AgentToolResult(
            content=[TextContent(text=f"wrote {path} ({size} bytes)")],
            details={"path": path, ARTIFACT_PATH_KEY: target, "bytes": size},
        )

    @guarded
    async def edit_file(path: str, arguments: Mapping[str, object]) -> AgentToolResult:
        target = enforce_write(boundary, path)
        old_text = _string_arg(arguments, "old_text")
        new_text = _string_arg(arguments, "new_text")
        if old_text is None or new_text is None:
            return _tool_error(path, ValueError("missing string arguments 'old_text'/'new_text'"))
        full = cwd / target
        try:
            current = full.read_text(encoding="utf-8")
        except OSError as exc:
            return _tool_error(path, exc)
        occurrences = current.count(old_text)
        if occurrences != 1:
            return _tool_error(
                path,
                ValueError(f"old_text matches {occurrences} times, expected exactly 1"),
            )
        full.write_text(current.replace(old_text, new_text, 1), encoding="utf-8")
        return AgentToolResult(
            content=[TextContent(text=f"edited {path}")],
            details={"path": path, ARTIFACT_PATH_KEY: target},
        )

    return [
        AgentTool(
            name="read_file",
            label="Read File",
            description="Read a UTF-8 text file inside the instance worktree.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            execute_fn=read_file,
        ),
        AgentTool(
            name="write_file",
            label="Write File",
            description=(
                "Create or overwrite a UTF-8 text file. The path must be inside the "
                "declared writable manifest; out-of-manifest writes are rejected."
            ),
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
            execute_fn=write_file,
        ),
        AgentTool(
            name="edit_file",
            label="Edit File",
            description=(
                "Replace exactly one occurrence of old_text with new_text in a file "
                "inside the declared writable manifest."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
            execute_fn=edit_file,
        ),
    ]


def artifact_path(result: AgentToolResult) -> str | None:
    """Return the manifest-relative artifact path marked by a write/edit result."""
    details = result.details
    if isinstance(details, dict):
        value = details.get(ARTIFACT_PATH_KEY)
        if isinstance(value, str):
            return value
    return None


def guard_rejection(result: AgentToolResult) -> str | None:
    """Return the Guard error code if this tool result is a Guard REJECT."""
    details = result.details
    if isinstance(details, dict):
        value = details.get(GUARD_DETAIL_KEY)
        if isinstance(value, str):
            return value
    return None
