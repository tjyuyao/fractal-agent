"""核心规范对象与实例层记录。

条款映射：Pr2/D1（CheckSpec、Contract）、D2（Evidence）、D4.5（WorkPacket）、
D4（Instance）、D5（Mode）、D8（Task/Attempt/Checkpoint）、D5.5（Policy）、
AM-0.1-04（内容寻址）、AM-0.1-06（sigma_ref）。
不可变对象一律 frozen 模型 + tuple 集合，在类型层面兑现 I-Contract / T4。
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CheckSpec(BaseModel):
    """一条可判定的验收标准（Pr2、D1.checks）。

    kind 必须在注册表内（E-CHECK-UNREGISTERED，ADR-0004）。
    """

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    spec: dict[str, str]


def contract_digest(intent: str, checks: tuple[CheckSpec, ...]) -> str:
    """契约内容的规范 sha256（AM-0.1-04 内容寻址 id 的基础）。"""
    canonical = json.dumps(
        {"intent": intent, "checks": [check.model_dump() for check in checks]},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Contract(BaseModel):
    """不可变契约三元组 ⟨id, intent, checks⟩（D1、I-Contract、T4）。

    需求变化时创建新契约，永不修改既有契约（E-CONTRACT-MUTATE）。
    """

    model_config = ConfigDict(frozen=True)

    id: str
    intent: str
    checks: tuple[CheckSpec, ...] = ()

    @classmethod
    def create(cls, intent: str, checks: tuple[CheckSpec, ...] = ()) -> Contract:
        """按内容寻址创建契约：id = "c-" + sha256 前 16 位（AM-0.1-04）。"""
        return cls(id=f"c-{contract_digest(intent, checks)[:16]}", intent=intent, checks=checks)


class Evidence(BaseModel):
    """绑定单一契约的判定结果 ⟨contract_id, results, artifacts⟩（D2、I-Evidence）。

    sigma_ref 为检查执行时的 Σ 指纹（AM-0.1-06），缓存键为 (check.id, sigma_ref)。
    """

    model_config = ConfigDict(frozen=True)

    contract_id: str
    results: dict[str, bool]
    artifacts: tuple[str, ...] = ()
    sigma_ref: str = ""


class WorkPacket(BaseModel):
    """实例处理的最小输入单元 ⟨contract, checkpoint, tools, constraints⟩（D4.5）。

    manifest（AM-0.1-05）随 Instance.boundary 落地；运行时上下文由事件流承载。
    """

    model_config = ConfigDict(frozen=True)

    contract: Contract
    checkpoint_id: str | None = None
    tools: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()


class Mode(StrEnum):
    """D5 的四种处理能力；I-OneMode 要求同一实例同一时刻只激活一种（T1'）。"""

    PLAN = "plan"
    BUILD = "build"
    DELEGATE = "delegate"
    SUPERVISE = "supervise"


class Instance(BaseModel):
    """处理单元 ⟨id, parent, boundary⟩（D4）。

    parent=None 为根实例（I-Parent）；boundary 为可写路径 manifest（AM-0.1-05），
    并行兄弟要求两两不相交（E-BOUNDARY-OVERLAP）。当前激活能力（Mode）属运行时
    状态，由事件流记录，不入本模型。
    """

    model_config = ConfigDict(frozen=True)

    id: str
    parent: str | None = None
    boundary: tuple[str, ...] = ()


class TaskStatus(StrEnum):
    """Task 生命周期：契约被纳入处理队列后的状态（D8）。"""

    PENDING = "pending"
    RUNNING = "running"
    ACCEPTED = "accepted"
    FAILED = "failed"


class Task(BaseModel):
    """子契约在 DAG 中的节点记录 ⟨id, contract_id, status, deps⟩（D8）。"""

    model_config = ConfigDict(frozen=True)

    id: str
    contract_id: str
    status: TaskStatus = TaskStatus.PENDING
    deps: tuple[str, ...] = ()


class AttemptStatus(StrEnum):
    """Attempt 生命周期（D8 明文枚举）。"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class Attempt(BaseModel):
    """对某个 Task 的一次执行尝试 ⟨id, task_id, owner, checkpoint_id, status, result⟩（D8）。

    retry/reassign 产生新 Attempt（AM-0.1-02）；result 记证据 id 或失败说明。
    """

    model_config = ConfigDict(frozen=True)

    id: str
    task_id: str
    owner: str
    checkpoint_id: str | None = None
    status: AttemptStatus = AttemptStatus.PENDING
    result: str | None = None


class Checkpoint(BaseModel):
    """某次 Attempt 的执行基线快照（D8）；绑定创建它的 Attempt，不可变历史。"""

    model_config = ConfigDict(frozen=True)

    id: str
    attempt_id: str
    plan_ref: str | None = None
    code_refs: tuple[str, ...] = ()


class Policy(BaseModel):
    """Processing 的配置参数（D5.5），由人设定、实例执行时读取。

    v0 默认值为占位，Phase 1 CLI 显式设定；risk_threshold 的等级表在 Phase 5
    定义（AM-0.1-07 相关）。Interactive 模式下 r 默认 ask_user（D6）。
    """

    model_config = ConfigDict(frozen=True)

    granularity_threshold: int = 8
    max_depth: int = 4
    can_reassign: bool = False
    can_replan: bool = False
    budget_tokens: int | None = None
    risk_threshold: int = 2
    retry_count: int = 0
    mode: Literal["interactive", "autonomous"] = "interactive"
