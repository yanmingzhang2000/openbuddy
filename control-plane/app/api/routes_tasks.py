"""任务管理 REST API。

每个路由都通过 `Depends(get_db)` 拿到已绑定租户上下文的数据库会话(RLS 生效),
通过 `Depends(get_current_tenant)` 拿到当前请求的租户/用户身份。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import (
    ApprovalDecisionRequest,
    CreateTaskRequest,
    EventLogResponse,
    TaskResponse,
)
from app.core.budget_guard import (
    BudgetExceededError,
    assert_can_create_task,
    resolve_task_guardrails,
)
from app.core.security import TenantContext, get_current_tenant
from app.db.models import AuditLog, EventLog, Task, Tenant
from app.db.session import system_session
from app.queue.client import enqueue_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: CreateTaskRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_current_tenant),
) -> TaskResponse:
    async with system_session() as sys_db:
        tenant = await sys_db.get(Tenant, uuid.UUID(ctx.tenant_id))
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="租户不存在")

    try:
        await assert_can_create_task(db, tenant)
    except BudgetExceededError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    guardrails = resolve_task_guardrails(
        tenant,
        body.max_steps,
        body.timeout_seconds,
        body.token_budget,
        body.cost_budget_usd,
    )

    task = Task(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(ctx.tenant_id),
        created_by=uuid.UUID(ctx.user_id),
        title=body.title,
        instruction=body.instruction,
        repo_url=body.repo_url,
        status="queued",
        **guardrails,
    )
    db.add(task)
    db.add(
        AuditLog(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(ctx.tenant_id),
            actor_user_id=uuid.UUID(ctx.user_id),
            task_id=task.id,
            action="task_created",
            detail={"title": body.title, "guardrails": guardrails},
        )
    )
    await db.flush()

    await enqueue_task(str(task.id), ctx.tenant_id)

    return TaskResponse.model_validate(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)) -> list[TaskResponse]:
    # 注意:这里故意不手写 WHERE tenant_id = ...,目的是验证 RLS 在应用层"忘记加条件"
    # 的情况下仍然只返回当前租户数据(双保险的第二层)。生产代码仍建议显式加条件以提升可读性。
    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    return [TaskResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> TaskResponse:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return TaskResponse.model_validate(task)


@router.get("/{task_id}/events", response_model=list[EventLogResponse])
async def get_task_events(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[EventLogResponse]:
    """事件回放数据源:返回某任务按 sequence 排序的全部事件,供前端逐步重放。"""
    result = await db.execute(
        select(EventLog).where(EventLog.task_id == task_id).order_by(EventLog.sequence)
    )
    return [EventLogResponse.model_validate(e) for e in result.scalars().all()]


@router.post("/{task_id}/approval", response_model=TaskResponse)
async def submit_approval_decision(
    task_id: uuid.UUID,
    body: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_current_tenant),
) -> TaskResponse:
    """人工审核决策入口,对应 orchestrator.graph 中的 human_review_node interrupt。"""
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status != "awaiting_approval":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="任务当前不在待审核状态")

    if ctx.role not in ("owner", "member"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="当前角色无权审批任务")

    from app.orchestrator.checkpointer import get_checkpointer
    from app.orchestrator.graph import build_orchestrator_graph, resume_with_approval
    from app.sandbox.docker_provider import DockerSandboxProvider

    async with get_checkpointer() as checkpointer:
        graph = build_orchestrator_graph(DockerSandboxProvider(), checkpointer=checkpointer)
        config = {"configurable": {"thread_id": str(task_id)}}
        await graph.ainvoke(resume_with_approval(body.decision), config=config)

    task.status = "completed" if body.decision == "approved" else "failed"
    db.add(
        AuditLog(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(ctx.tenant_id),
            actor_user_id=uuid.UUID(ctx.user_id),
            task_id=task.id,
            action="human_approval_decision",
            detail={"decision": body.decision},
        )
    )
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_current_tenant),
) -> TaskResponse:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status in ("completed", "failed", "cancelled"):
        return TaskResponse.model_validate(task)

    task.status = "cancelled"
    db.add(
        AuditLog(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(ctx.tenant_id),
            actor_user_id=uuid.UUID(ctx.user_id),
            task_id=task.id,
            action="task_cancelled",
            detail={},
        )
    )
    return TaskResponse.model_validate(task)
