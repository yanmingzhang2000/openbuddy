"""多 Agent 编排图的共享状态定义。

这是 OpenHands 生态目前缺失、由本项目自研的核心部分(见 docs/ARCHITECTURE.md 2.2):
LangGraph 的 StateGraph 节点之间通过这个 TypedDict 传递状态,每个节点内部
调用 app.engine.conversation_runner 来驱动一个真正的 OpenHands Conversation。
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class SubtaskResult(TypedDict):
    node_id: str
    agent_role: str
    status: Literal["completed", "failed", "awaiting_approval"]
    summary: str
    steps_used: int
    tokens_used: int
    cost_used_usd: float


class OrchestratorState(TypedDict):
    """根图状态。`subtask_results` 用 operator.add 聚合,支持并行 fan-out 后的 fan-in 合并。"""

    task_id: str
    tenant_id: str
    root_instruction: str

    # 预算护栏快照(由控制面在每步前刷新,超限时 orchestrator 主动终止)
    max_steps: int
    timeout_seconds: int
    token_budget: int
    cost_budget_usd: float

    # 运行时账本(跨并行分支累加)
    steps_used: Annotated[int, operator.add]
    tokens_used: Annotated[int, operator.add]
    cost_used_usd: Annotated[float, operator.add]

    # 委派计划:根 Agent 产出的子任务列表,驱动 fan-out
    delegation_plan: list[dict]
    subtask_results: Annotated[list[SubtaskResult], operator.add]

    # 人工审核
    pending_approval: dict | None
    approval_decision: Literal["approved", "rejected"] | None

    final_status: Literal[
        "completed", "failed", "timeout", "budget_exceeded", "max_steps_exceeded", "cancelled"
    ] | None
    final_summary: str | None


class SubAgentState(TypedDict):
    """委派给子 Agent 的独立分支状态(并行执行,各分支互不共享除 budget 账本外的状态)。"""

    task_id: str
    tenant_id: str
    node_id: str
    agent_role: str
    instruction: str
    max_steps: int
    result: SubtaskResult | None
