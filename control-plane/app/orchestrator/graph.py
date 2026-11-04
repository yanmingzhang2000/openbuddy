"""多 Agent 编排图(本项目自研核心,见 docs/ARCHITECTURE.md 2.2)。

图结构:

    START -> plan (根 Agent 规划是否需要委派/并行)
               │
               ├─ 不需要委派 ─────────────────────────┐
               │                                      │
               └─ 需要委派 ─> Send(fan-out 到多个 execute_subtask 分支) ─┐
                                                                        │
                                                                        ▼
                                                              join_results (fan-in)
                                                                        │
                                                                        ▼
                                                            human_review (interrupt,可选)
                                                                        │
                                                                        ▼
                                                                       END

- `plan` 节点:调用一次轻量 LLM 规划,决定是单任务直接执行还是拆解为多个子任务。
- `Send` API 实现并行 fan-out:每个子任务会创建独立的沙箱 Conversation,互不干扰。
- `join_results`:用 state 中 `Annotated[list, operator.add]` 的 reducer 自动合并并行分支结果。
- `human_review`:当任意子任务标记为高风险(如需要凭证的动作)时,用 `interrupt()`
  暂停图执行,等待控制面 API 收到人工审批后以 `Command(resume=...)` 恢复。
- 状态持久化:通过 `checkpointer`(Postgres)保存,支持跨进程恢复——
  这也是"崩溃恢复"验收点在多 Agent 层面的体现(单 Conversation 级别的崩溃恢复则由
  openhands-sdk 自身的事件溯源负责,见①层)。
"""

from __future__ import annotations

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt

from app.engine.conversation_runner import StepBudget, run_conversation
from app.orchestrator.state import OrchestratorState, SubAgentState, SubtaskResult
from app.sandbox.provider import SandboxProvider

logger = structlog.get_logger(__name__)

# 触发人工审核的子任务角色/关键词(可配置,这里给出一个最小可用的默认策略)
HIGH_RISK_ROLES = {"deploy", "release", "payment", "credential_sensitive"}


async def plan_node(state: OrchestratorState) -> dict:
    """根节点:判断是否需要拆解为多个子任务。

    最小可用实现:根据指令中的关键词做规则判断(避免再额外发一次 LLM 调用增加成本)。
    生产化时可替换为一次结构化输出的 LLM 调用(仍通过 app.llm.factory.build_llm 构造)。
    """
    instruction = state["root_instruction"]
    plan: list[dict] = []

    if "and" in instruction.lower() or "并且" in instruction or "同时" in instruction:
        # 简单启发式:包含多个并列子目标时拆分为并行子任务。
        parts = [p.strip() for p in instruction.replace("并且", "and").split(" and ") if p.strip()]
        if len(parts) > 1:
            plan = [
                {"agent_role": "default", "instruction": part} for part in parts
            ]

    logger.info("plan_resolved", task_id=state["task_id"], subtask_count=len(plan))
    return {"delegation_plan": plan}


def route_after_plan(state: OrchestratorState):
    """根据规划结果决定下一步:单任务直接执行 vs 并行 fan-out。"""
    plan = state.get("delegation_plan") or []
    if not plan:
        return "execute_single"
    return [
        Send(
            "execute_subtask",
            {
                "task_id": state["task_id"],
                "tenant_id": state["tenant_id"],
                "node_id": f"{state['task_id']}-{i}",
                "agent_role": item["agent_role"],
                "instruction": item["instruction"],
                "max_steps": max(state["max_steps"] // max(len(plan), 1), 5),
                "result": None,
            },
        )
        for i, item in enumerate(plan)
    ]


def _build_execute_single(sandbox_provider: SandboxProvider):
    async def execute_single(state: OrchestratorState) -> dict:
        """无需委派时,根任务本身在一个沙箱里直接执行。"""
        handle = await sandbox_provider.create_workspace(state["task_id"])
        try:
            budget = StepBudget(
                max_steps=state["max_steps"],
                timeout_seconds=state["timeout_seconds"],
                token_budget=state["token_budget"],
                cost_budget_usd=state["cost_budget_usd"],
            )
            result = await run_conversation(
                instruction=state["root_instruction"],
                sandbox_handle=handle,
                budget=budget,
            )
        finally:
            await sandbox_provider.destroy_workspace(handle)

        subtask: SubtaskResult = {
            "node_id": f"{state['task_id']}-root",
            "agent_role": "default",
            "status": "completed" if result.status == "completed" else "failed",
            "summary": result.summary,
            "steps_used": result.steps_used,
            "tokens_used": result.tokens_used,
            "cost_used_usd": result.cost_used_usd,
        }
        return {
            "subtask_results": [subtask],
            "steps_used": result.steps_used,
            "tokens_used": result.tokens_used,
            "cost_used_usd": result.cost_used_usd,
            "final_status": result.status if result.status != "completed" else None,
        }

    return execute_single


def _build_execute_subtask(sandbox_provider: SandboxProvider):
    async def execute_subtask(state: SubAgentState) -> dict:
        """并行分支:每个委派出去的子任务各自拥有独立沙箱。"""
        handle = await sandbox_provider.create_workspace(state["node_id"])
        try:
            budget = StepBudget(
                max_steps=state["max_steps"],
                timeout_seconds=1800,
                token_budget=100_000,
                cost_budget_usd=2.0,
            )
            result = await run_conversation(
                instruction=state["instruction"],
                sandbox_handle=handle,
                budget=budget,
            )
        finally:
            await sandbox_provider.destroy_workspace(handle)

        is_high_risk = state["agent_role"] in HIGH_RISK_ROLES
        subtask: SubtaskResult = {
            "node_id": state["node_id"],
            "agent_role": state["agent_role"],
            "status": "awaiting_approval" if is_high_risk else (
                "completed" if result.status == "completed" else "failed"
            ),
            "summary": result.summary,
            "steps_used": result.steps_used,
            "tokens_used": result.tokens_used,
            "cost_used_usd": result.cost_used_usd,
        }
        return {
            "subtask_results": [subtask],
            "steps_used": result.steps_used,
            "tokens_used": result.tokens_used,
            "cost_used_usd": result.cost_used_usd,
        }

    return execute_subtask


async def join_results(state: OrchestratorState) -> dict:
    """fan-in:所有并行分支结果已由 reducer 自动合并进 subtask_results,这里只做最终判定。"""
    results = state.get("subtask_results", [])
    any_awaiting = any(r["status"] == "awaiting_approval" for r in results)
    any_failed = any(r["status"] == "failed" for r in results)

    if any_awaiting:
        return {"pending_approval": {"subtasks": [r for r in results if r["status"] == "awaiting_approval"]}}
    if any_failed:
        return {"final_status": "failed", "final_summary": "部分子任务失败"}
    return {
        "final_status": "completed",
        "final_summary": "; ".join(r["summary"] for r in results),
    }


async def human_review_node(state: OrchestratorState) -> dict:
    """人工审核中断节点。暂停图执行,等待控制面 API 调用 `graph.ainvoke(Command(resume=...))`。"""
    pending = state.get("pending_approval")
    if not pending:
        return {}

    decision = interrupt(
        {
            "type": "human_approval_required",
            "task_id": state["task_id"],
            "subtasks": pending["subtasks"],
            "message": "以下子任务涉及高风险操作,需要人工审批后才能标记任务完成。",
        }
    )
    # `decision` 是外部通过 Command(resume=decision) 传入的值,约定为 "approved"/"rejected"。
    if decision == "approved":
        return {"approval_decision": "approved", "final_status": "completed"}
    return {"approval_decision": "rejected", "final_status": "failed", "final_summary": "人工审核拒绝"}


def route_after_join(state: OrchestratorState):
    if state.get("pending_approval"):
        return "human_review"
    return END


def build_orchestrator_graph(sandbox_provider: SandboxProvider, checkpointer=None):
    """构造并编译多 Agent 编排图。`checkpointer` 传入 Postgres checkpointer 以支持状态持久化
    与跨进程恢复;测试中可以不传(使用内存 checkpointer 或不持久化)。
    """
    graph = StateGraph(OrchestratorState)

    graph.add_node("plan", plan_node)
    graph.add_node("execute_single", _build_execute_single(sandbox_provider))
    graph.add_node("execute_subtask", _build_execute_subtask(sandbox_provider))
    graph.add_node("join_results", join_results)
    graph.add_node("human_review", human_review_node)

    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", route_after_plan, ["execute_single", "execute_subtask"])
    graph.add_edge("execute_single", END)
    graph.add_edge("execute_subtask", "join_results")
    graph.add_conditional_edges("join_results", route_after_join, ["human_review", END])
    graph.add_edge("human_review", END)

    return graph.compile(checkpointer=checkpointer)


def resume_with_approval(decision: str):
    """供控制面 API 调用:构造一个恢复人工审核中断的 Command。"""
    return Command(resume=decision)
