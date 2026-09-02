"""调度器内核：D3 满足关系、D6 判定点（g/v/r）、串行驱动器（D9 串行特化）。

判定全部确定性（D6）；LLM 部分的 plan/supervise 在 fractal_runtime（ADR-0006）。
build 执行体与检查执行器以协议注入，内核不依赖任何 LLM/tau/git。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from fractal_kernel import guard
from fractal_kernel.models import CheckSpec, Contract, Evidence, Policy, WorkPacket
from fractal_kernel.store import EventLog, EventType

Granularity = Literal["direct", "decompose"]
Verdict = Literal["accept", "reject"]
Decision = Literal["retry", "reassign", "replan", "ask_user"]


def satisfied(contract: Contract, evidence: Evidence) -> bool:
    """D3 sat(c,e)：契约每个 check 均有 true 判定；缺项视为未满足。"""
    return all(evidence.results.get(check.id) is True for check in contract.checks)


def verify(contract: Contract, evidence: Evidence) -> Verdict:
    """D6 v(c,e)：确定性验收判定，由 checks 判定结果直接决定。"""
    return "accept" if satisfied(contract, evidence) else "reject"


def granularity(contract: Contract, policy: Policy) -> Granularity:
    """D6 g(c) v0：checks 数量代理（AM-0.1-07 硬上限之一）。

    LLM 软信号在 fractal_runtime 与本判定组合；build 上下文溢出由驱动器
    转为 replan 信号（AM-0.1-07 闭环）。
    """
    if len(contract.checks) > policy.granularity_threshold:
        return "decompose"
    return "direct"


def decide(contract: Contract, evidence: Evidence, policy: Policy) -> Decision:
    """D6 r(c,e,p)：reject 后续决策。

    Interactive 模式默认 ask_user（D5.5）；Autonomous 按 retry → reassign →
    replan → ask_user 阶梯（D6 明文）。c/e 参数保留以对齐规范签名，
    风险等级表（Phase 5）落地后参与判定。
    """
    if policy.mode == "interactive":
        return "ask_user"
    if policy.retry_count > 0:
        return "retry"
    if policy.can_reassign:
        return "reassign"
    if policy.can_replan:
        return "replan"
    return "ask_user"


@dataclass(frozen=True)
class BuildResult:
    """build 执行体的一次产出；overflow 是 AM-0.1-07 的"应分解"信号。"""

    artifacts: tuple[str, ...] = ()
    sigma_ref: str = ""
    overflow: bool = False


@dataclass(frozen=True)
class CheckOutcome:
    """单条 check 的执行结果。"""

    ok: bool
    artifact: str = ""


class BuildBody(Protocol):
    """build 能力执行体协议（Phase 1 由移植的 agent loop 实现）。"""

    def build(self, packet: WorkPacket) -> BuildResult: ...


class CheckRunner(Protocol):
    """检查执行协议（runtime 注册表实现，测试用假实现）。"""

    def run(self, check: CheckSpec, packet: WorkPacket) -> CheckOutcome: ...


@dataclass(frozen=True)
class ProcessingOutcome:
    """一次 process 的终态：accept 带证据；reject 带后续决策。"""

    accepted: bool
    attempts: int
    evidence: Evidence | None = None
    decision: Decision | None = None


class SerialDriver:
    """串行驱动器：深度 0、无委托、并发=1（Phase 1 特化）。

    事件序：delegation.launched（处理者登记；v0 复用为"契约进入处理"记录，
    子实例委托语义 Phase 2 细化）→ [attempt.started → check.executed* →
    evidence.recorded → attempt.finished] → decision.made（reject 时）。
    处理者唯一性（T1）：驱动器内存登记 + fold 重放复验双层保障。
    reassign / replan 在执行者池与 plan 能力（Phase 2）落地前为终止决策，
    交还调用方。
    """

    def __init__(self, log: EventLog, body: BuildBody, runner: CheckRunner) -> None:
        self._log = log
        self._body = body
        self._runner = runner
        self._handlers: dict[str, str] = {}

    def process(
        self, packet: WorkPacket, policy: Policy, owner: str = "i-root"
    ) -> ProcessingOutcome:
        contract = packet.contract
        guard.check_one_handler(self._handlers, contract.id)
        self._handlers[contract.id] = owner
        self._log.append(
            EventType.DELEGATION_LAUNCHED,
            {"contract_id": contract.id, "instance_id": owner},
        )

        current = policy
        attempt = 0
        while True:
            attempt += 1
            attempt_id = f"{owner}-a{attempt}"
            self._log.append(
                EventType.ATTEMPT_STARTED,
                {"attempt_id": attempt_id, "contract_id": contract.id, "owner": owner},
            )
            build_result = self._body.build(packet)
            if build_result.overflow:
                self._log.append(
                    EventType.ATTEMPT_FINISHED,
                    {
                        "attempt_id": attempt_id,
                        "status": "interrupted",
                        "reason": "context_overflow",
                    },
                )
                self._log.append(
                    EventType.DECISION_MADE,
                    {"contract_id": contract.id, "decision": "replan"},
                )
                return ProcessingOutcome(False, attempt, decision="replan")

            results: dict[str, bool] = {}
            artifacts = list(build_result.artifacts)
            for check in contract.checks:
                outcome = self._runner.run(check, packet)
                results[check.id] = outcome.ok
                if outcome.artifact:
                    artifacts.append(outcome.artifact)
                self._log.append(
                    EventType.CHECK_EXECUTED,
                    {"contract_id": contract.id, "check_id": check.id, "ok": outcome.ok},
                )

            evidence = Evidence(
                contract_id=contract.id,
                results=results,
                artifacts=tuple(artifacts),
                sigma_ref=build_result.sigma_ref,
            )
            self._log.append(EventType.EVIDENCE_RECORDED, {"evidence": evidence.model_dump()})
            verdict = verify(contract, evidence)
            self._log.append(
                EventType.ATTEMPT_FINISHED,
                {
                    "attempt_id": attempt_id,
                    "status": "passed" if verdict == "accept" else "failed",
                },
            )
            if verdict == "accept":
                return ProcessingOutcome(True, attempt, evidence=evidence)

            decision = decide(contract, evidence, current)
            self._log.append(
                EventType.DECISION_MADE,
                {"contract_id": contract.id, "decision": decision},
            )
            if decision == "retry":
                current = current.model_copy(update={"retry_count": current.retry_count - 1})
                continue
            return ProcessingOutcome(False, attempt, evidence=evidence, decision=decision)
