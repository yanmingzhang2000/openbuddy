"""预算配额护栏(控制面侧的账本校验,独立于 engine 层的实时步内检查)。

两层护栏的分工:
- `app.engine.conversation_runner.StepBudget`:Conversation 运行过程中逐步检查,
  发现超限立即终止当前 Conversation(进程内、低延迟)。
- 本模块:在任务创建、任务并发数检查等「入口」处做租户级配额校验,
  防止单个租户同时创建远超配额的并发任务耗尽全局资源。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import Task, Tenant


class BudgetExceededError(Exception):
    pass


async def assert_can_create_task(
    db: AsyncSession, tenant: Tenant, settings: Settings | None = None
) -> None:
    """创建任务前校验:当前运行中任务数是否超过租户并发上限。"""
    settings = settings or get_settings()

    stmt = select(func.count()).where(
        Task.tenant_id == tenant.id, Task.status.in_(["queued", "running", "awaiting_approval"])
    )
    running_count = (await db.execute(stmt)).scalar_one()

    if running_count >= tenant.max_concurrent_tasks:
        raise BudgetExceededError(
            f"租户 '{tenant.id}' 已达到并发任务上限 {tenant.max_concurrent_tasks},"
            f"当前运行中任务数 {running_count}"
        )


def resolve_task_guardrails(
    tenant: Tenant,
    requested_max_steps: int | None,
    requested_timeout_seconds: int | None,
    requested_token_budget: int | None,
    requested_cost_budget_usd: float | None,
    settings: Settings | None = None,
) -> dict:
    """合并系统默认值、租户上限与任务请求值,返回最终生效的护栏配置。
    任务请求的预算不能超过租户级别上限,超过则截断为租户上限(而不是报错拒绝),
    并在审计日志中记录发生了截断(调用方负责写审计日志)。
    """
    settings = settings or get_settings()

    cost_budget = min(
        requested_cost_budget_usd or settings.default_cost_budget_usd,
        tenant.max_cost_budget_usd,
    )
    return {
        "max_steps": requested_max_steps or settings.default_max_steps,
        "timeout_seconds": requested_timeout_seconds or settings.default_timeout_seconds,
        "token_budget": requested_token_budget or settings.default_token_budget,
        "cost_budget_usd": cost_budget,
    }
