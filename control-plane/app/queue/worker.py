"""arq worker:消费任务队列,驱动 LangGraph 编排图执行。

启动方式:`arq app.queue.worker.WorkerSettings`(见 docker-compose.yml 中的 worker 服务)。
"""

from __future__ import annotations

import uuid

import structlog
from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.models import AuditLog, Task
from app.db.session import tenant_scoped_session
from app.orchestrator.checkpointer import get_checkpointer
from app.orchestrator.graph import build_orchestrator_graph
from app.sandbox.docker_provider import DockerSandboxProvider

logger = structlog.get_logger(__name__)


async def run_task(ctx: dict, task_id: str, tenant_id: str) -> None:
    """arq job:执行一个已入队的任务。

    职责边界:这里只做「取任务 -> 跑编排图 -> 写回状态」的胶水逻辑;
    真正的预算检查在 app.engine.conversation_runner.StepBudget 和编排图节点内部进行,
    任务队列本身只负责并发调度和重试策略,不重复实现护栏逻辑。
    """
    sandbox_provider = DockerSandboxProvider()

    async with tenant_scoped_session(tenant_id) as db:
        task = await db.get(Task, uuid.UUID(task_id))
        if task is None:
            logger.error("task_not_found", task_id=task_id)
            return
        task.status = "running"
        import datetime as dt

        task.started_at = dt.datetime.now(dt.UTC)
        await db.flush()

    async with get_checkpointer() as checkpointer:
        graph = build_orchestrator_graph(sandbox_provider, checkpointer=checkpointer)
        initial_state = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "root_instruction": task.instruction,
            "max_steps": task.max_steps,
            "timeout_seconds": task.timeout_seconds,
            "token_budget": task.token_budget,
            "cost_budget_usd": task.cost_budget_usd,
            "steps_used": 0,
            "tokens_used": 0,
            "cost_used_usd": 0.0,
            "delegation_plan": [],
            "subtask_results": [],
            "pending_approval": None,
            "approval_decision": None,
            "final_status": None,
            "final_summary": None,
        }
        config = {"configurable": {"thread_id": task_id}}

        try:
            result_state = await graph.ainvoke(initial_state, config=config)
        except Exception as exc:
            logger.exception("task_execution_failed", task_id=task_id)
            async with tenant_scoped_session(tenant_id) as db:
                task = await db.get(Task, uuid.UUID(task_id))
                task.status = "failed"
                task.error_message = str(exc)
            return

    final_status = result_state.get("final_status") or (
        "awaiting_approval" if result_state.get("pending_approval") else "completed"
    )

    async with tenant_scoped_session(tenant_id) as db:
        task = await db.get(Task, uuid.UUID(task_id))
        import datetime as dt

        task.status = final_status
        task.steps_used = result_state.get("steps_used", 0)
        task.tokens_used = result_state.get("tokens_used", 0)
        task.cost_used_usd = result_state.get("cost_used_usd", 0.0)
        task.error_message = result_state.get("final_summary")
        if final_status in ("completed", "failed", "timeout", "budget_exceeded", "max_steps_exceeded"):
            task.finished_at = dt.datetime.now(dt.UTC)
        db.add(
            AuditLog(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                task_id=uuid.UUID(task_id),
                action="task_execution_finished",
                detail={"final_status": final_status},
            )
        )

    logger.info("task_finished", task_id=task_id, final_status=final_status)


async def reap_stale_sandboxes(ctx: dict) -> None:
    """定时任务:清理超时未正常销毁的沙箱容器(防止资源泄漏)。
    最小可用实现:当前仅记录日志占位;生产化时查询 Docker API 比对 Task.sandbox_container_id
    与运行中容器列表,销毁找不到对应 running task 的孤儿容器。
    """
    logger.info("reap_stale_sandboxes_tick")


async def startup(ctx: dict) -> None:
    configure_logging(get_settings().log_level)
    logger.info("arq_worker_started")


class WorkerSettings:
    functions = [run_task]
    cron_jobs = [cron(reap_stale_sandboxes, minute=set(range(0, 60, 5)))]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
