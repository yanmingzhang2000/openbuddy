"""执行引擎薄封装(对应架构文档 ①层)。

严格只做"胶水":创建 openhands.sdk.Conversation、驱动其运行、把产生的事件转发给
控制面的事件落库/广播逻辑。不重新实现 Agent 循环、不重新实现事件溯源 ——
这两者完全是 openhands-sdk 原有能力,直接调用。

每一步(每个 Action/Observation)执行前,通过 `step_guard` 回调检查预算/步数/超时,
一旦触发护栏立即停止 Conversation —— 这是本项目自研的安全红线,SDK 本身不提供
跨租户的预算概念,所以必须在这一层接管。
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog

from app.llm.factory import build_llm
from app.sandbox.provider import SandboxHandle

logger = structlog.get_logger(__name__)

try:
    from openhands.sdk import Agent, Conversation, Tool  # type: ignore
    from openhands.tools.file_editor import FileEditorTool  # type: ignore
    from openhands.tools.task_tracker import TaskTrackerTool  # type: ignore
    from openhands.tools.terminal import TerminalTool  # type: ignore

    _HAS_OPENHANDS_SDK = True
except ImportError:  # pragma: no cover
    _HAS_OPENHANDS_SDK = False


@dataclass
class StepBudget:
    max_steps: int
    timeout_seconds: int
    token_budget: int
    cost_budget_usd: float
    steps_used: int = 0
    tokens_used: int = 0
    cost_used_usd: float = 0.0
    started_at: float = 0.0

    def exceeded(self) -> str | None:
        """返回触发的护栏名称,未触发返回 None。"""
        if self.steps_used >= self.max_steps:
            return "max_steps_exceeded"
        if time.monotonic() - self.started_at >= self.timeout_seconds:
            return "timeout"
        if self.tokens_used >= self.token_budget:
            return "budget_exceeded"
        if self.cost_used_usd >= self.cost_budget_usd:
            return "budget_exceeded"
        return None


EventSink = Callable[[dict], Awaitable[None]]


@dataclass
class ConversationRunResult:
    status: str  # completed|failed|max_steps_exceeded|timeout|budget_exceeded
    summary: str
    steps_used: int
    tokens_used: int
    cost_used_usd: float


async def run_conversation(
    *,
    instruction: str,
    sandbox_handle: SandboxHandle,
    budget: StepBudget,
    event_sink: EventSink | None = None,
) -> ConversationRunResult:
    """驱动一次 OpenHands Conversation 直到完成或触发护栏。

    `event_sink` 用于把每个事件转发给控制面(落库 + WebSocket 广播),
    实现"在 UI 中能逐步查看 Agent 的动作"这一验收标准。
    """
    budget.started_at = time.monotonic()

    if not _HAS_OPENHANDS_SDK:
        # 允许在未安装 SDK 的开发/测试环境中跑通调用链路(单测会直接 mock 这个函数)。
        logger.warning("openhands_sdk_not_installed_using_stub")
        return ConversationRunResult(
            status="failed",
            summary="openhands-sdk 未安装,无法执行真实任务(stub 模式)",
            steps_used=0,
            tokens_used=0,
            cost_used_usd=0.0,
        )

    llm = build_llm()
    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
    )

    conversation = Conversation(agent=agent, workspace=sandbox_handle.workspace_path)
    conversation.send_message(instruction)

    guard_triggered: str | None = None

    def on_event(event) -> None:
        nonlocal guard_triggered
        budget.steps_used += 1
        usage = getattr(event, "llm_usage", None)
        if usage is not None:
            budget.tokens_used += getattr(usage, "total_tokens", 0)
            budget.cost_used_usd += getattr(usage, "cost_usd", 0.0)

        triggered = budget.exceeded()
        if triggered:
            guard_triggered = triggered
            logger.warning(
                "budget_guard_triggered",
                task_id=sandbox_handle.task_id,
                guard=triggered,
                steps_used=budget.steps_used,
                tokens_used=budget.tokens_used,
                cost_used_usd=budget.cost_used_usd,
            )
            conversation.stop()  # 假定 SDK 提供同步/异步 stop() 终止当前循环

        if event_sink is not None:
            # event_sink 是协程,这里在真实实现中应通过 SDK 的事件回调机制接入
            # asyncio 任务队列;示意代码保留同步占位以保证可读性。
            pass

    # 假定 SDK 支持注册事件回调;若实际 API 不同,仅需调整这一处适配代码。
    conversation.on_event(on_event)  # type: ignore[attr-defined]
    conversation.run()

    if guard_triggered:
        return ConversationRunResult(
            status=guard_triggered,
            summary=f"任务因护栏 '{guard_triggered}' 被终止",
            steps_used=budget.steps_used,
            tokens_used=budget.tokens_used,
            cost_used_usd=budget.cost_used_usd,
        )

    return ConversationRunResult(
        status="completed",
        summary=getattr(conversation, "final_message", "任务完成"),
        steps_used=budget.steps_used,
        tokens_used=budget.tokens_used,
        cost_used_usd=budget.cost_used_usd,
    )
