"""供 FastAPI 路由把任务投递到 arq 队列的客户端封装。"""

from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


async def enqueue_task(task_id: str, tenant_id: str) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job("run_task", task_id, tenant_id)
