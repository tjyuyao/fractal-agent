"""核心规范对象：CheckSpec / Contract / Evidence / WorkPacket。

条款映射：D1（Contract）、D2（Evidence）、D4.5（WorkPacket）、Pr2（Check）。
不可变性：frozen 模型 + tuple 集合，在类型层面兑现 I-Contract / T4。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CheckSpec(BaseModel):
    """一条可判定的验收标准（Pr2、D1.checks）。

    kind 必须在执行器注册表内（E-CHECK-UNREGISTERED，ADR-0004）。
    """

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    spec: dict[str, str]


class Contract(BaseModel):
    """不可变契约三元组 ⟨id, intent, checks⟩（D1、I-Contract、T4）。

    需求变化时创建新契约，永不修改既有契约（E-CONTRACT-MUTATE）。
    """

    model_config = ConfigDict(frozen=True)

    id: str
    intent: str
    checks: tuple[CheckSpec, ...] = ()


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

    manifest（AM-0.1-05）与运行时上下文在 Phase 2 随 Instance 落地后并入。
    """

    model_config = ConfigDict(frozen=True)

    contract: Contract
    checkpoint_id: str | None = None
    tools: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
