"""build 能力执行体：在实例 boundary 内 headless 运行移植的 agent loop（ADR-0006）。

agent loop 移植自 tau_agent v0.4.1（MIT），落于 fractal_runtime；本模块把
它适配为 fractal_kernel.scheduler.BuildBody：build(packet) -> BuildResult。
每轮 attempt 从工作包重建上下文（AM-0.1-02），事件流是事实来源、对话只是
缓存（ADR-0003）。上下文溢出（AM-0.1-07）由终态 error_message 的稳定标记
判定，驱动器据此走 replan 闭环；sigma_ref 占位为空串，worktree checkpoint
（exec 执行器 + boundary 载体）落地后由 runtime 统一计算（AM-0.1-06）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from fractal_kernel.models import WorkPacket
from fractal_kernel.scheduler import BuildResult
from fractal_kernel.store import EventLog, EventType
from fractal_runtime.events import AgentEvent, ToolExecutionEndEvent
from fractal_runtime.file_tools import artifact_path, build_file_tools, guard_rejection
from fractal_runtime.harness import AgentHarness, AgentHarnessConfig
from fractal_runtime.loop import AfterToolCall
from fractal_runtime.messages import AgentMessage, AssistantMessage, ToolCall
from fractal_runtime.openai_provider import CONTEXT_OVERFLOW_MARKER
from fractal_runtime.provider import ModelProvider
from fractal_runtime.tools import AgentTool, AgentToolResult

OVERFLOW_SIGNAL = f"{CONTEXT_OVERFLOW_MARKER}:"


def is_context_overflow(error_message: str | None) -> bool:
    """AM-0.1-07：终态 provider 错误是否为上下文溢出（"应分解"信号）。"""
    return error_message is not None and error_message.startswith(OVERFLOW_SIGNAL)


def build_system_prompt(packet: WorkPacket, boundary: Sequence[str]) -> str:
    """系统提示 = 契约 intent + constraints + manifest 声明（docs/architecture.md）。"""
    lines = [
        "You are the build executor of a fractal agent instance.",
        f"Contract intent: {packet.contract.intent}",
    ]
    if packet.contract.checks:
        check_lines = "; ".join(f"{c.id} [{c.kind}]" for c in packet.contract.checks)
        lines.append(f"Acceptance checks: {check_lines}")
    constraints = "; ".join(packet.constraints) if packet.constraints else "none"
    lines.append(f"Constraints: {constraints}")
    manifest = ", ".join(boundary) if boundary else "none declared"
    lines.append(f"Writable paths (manifest): {manifest}")
    lines.append("Writes outside the manifest are rejected with E-BOUNDARY-WRITE.")
    return "\n".join(lines)


@dataclass(frozen=True)
class LoopBuildConfig:
    """LoopBuildBody 的运行配置：provider、模型与轮数上限。"""

    provider: ModelProvider
    model: str
    max_turns: int | None = 32
    session_id: str | None = None


class LoopBuildBody:
    """移植 agent loop 的 BuildBody 适配器（D5 build）。

    工具白名单来自工作包（D4.5 tools）；write/edit 经 manifest 校验
    （E-BOUNDARY-WRITE），Guard 拒绝记入事件日志（guard.rejected）；成功写
    产物进入 BuildResult.artifacts（D2）。串行驱动器同步调用 build——内部
    以 asyncio.run 驱动一次性 headless 会话，不可在运行中的事件循环内调用。
    """

    def __init__(
        self,
        config: LoopBuildConfig,
        *,
        boundary: Sequence[str],
        cwd: Path,
        extra_tools: Sequence[AgentTool] = (),
        log: EventLog | None = None,
    ) -> None:
        self._config = config
        self._boundary = tuple(boundary)
        self._cwd = cwd
        self._log = log
        self._registry: dict[str, AgentTool] = {}
        for tool in (*build_file_tools(self._boundary, cwd), *extra_tools):
            self._registry[tool.name] = tool

    def build(self, packet: WorkPacket) -> BuildResult:
        """执行一次 build attempt：从工作包重建上下文，跑 loop，收集产物。"""
        return asyncio.run(self._run(packet))

    async def _run(self, packet: WorkPacket) -> BuildResult:
        tools = [self._registry[name] for name in packet.tools if name in self._registry]
        artifacts: list[str] = []
        collector = _EventCollector(artifacts)
        harness = AgentHarness(
            AgentHarnessConfig(
                provider=self._config.provider,
                model=self._config.model,
                system=build_system_prompt(packet, self._boundary),
                tools=tools,
                max_turns=self._config.max_turns,
                session_id=self._config.session_id,
                after_tool_call=_guard_rejection_hook(packet.contract.id, self._log),
            )
        )
        harness.subscribe(collector)
        prompt = packet.contract.intent
        async for _event in harness.prompt(prompt):
            pass
        final = _final_assistant(harness.messages)
        overflow = final is not None and is_context_overflow(final.error_message)
        return BuildResult(artifacts=tuple(artifacts), sigma_ref="", overflow=overflow)


def _guard_rejection_hook(contract_id: str, log: EventLog | None) -> AfterToolCall:
    """把工具层 Guard REJECT 提升为 error 结果并记 guard.rejected 事件（AM-0.1-05）。"""

    async def hook(
        call: ToolCall, result: AgentToolResult, is_error: bool
    ) -> tuple[AgentToolResult, bool]:
        code = guard_rejection(result)
        if code is None:
            return result, is_error
        path = result.details.get("path") if isinstance(result.details, dict) else None
        if log is not None:
            log.append(
                EventType.GUARD_REJECTED,
                {
                    "contract_id": contract_id,
                    "tool": call.name,
                    "code": code,
                    "path": path if isinstance(path, str) else "",
                },
            )
        return result, True

    return hook


class _EventCollector:
    """从 loop 事件流收集写产物（write/edit 结果标记的 artifact_path，D2）。"""

    def __init__(self, artifacts: list[str]) -> None:
        self._artifacts = artifacts

    async def __call__(self, event: AgentEvent) -> None:
        if isinstance(event, ToolExecutionEndEvent) and not event.is_error:
            path = artifact_path(event.result)
            if path is not None and path not in self._artifacts:
                self._artifacts.append(path)


def _final_assistant(messages: tuple[AgentMessage, ...]) -> AssistantMessage | None:
    for message in reversed(messages):
        if isinstance(message, AssistantMessage):
            return message
    return None
