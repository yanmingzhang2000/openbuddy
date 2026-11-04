"""数据库会话管理。

关键安全机制:`tenant_scoped_session` 在每次拿到连接后立即执行
`SET LOCAL app.current_tenant_id = :tenant_id`,这个值被 Postgres RLS 策略
(见 app/db/models.py 中各表的 POLICY 定义,以及 alembic 迁移脚本)用作过滤条件。

即使应用代码某个 SELECT 忘记显式写 `WHERE tenant_id = ...`,数据库也会在行级拒绝返回
其他租户的数据 —— 这是双保险的第二层(第一层是应用层每个 query 显式带 tenant_id)。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()

# 业务连接必须使用受限角色 agentforge_app(见 app/core/config.py 中 app_database_url 的注释):
# Postgres 对表 owner 默认豁免 RLS 检查,如果业务 API 用 owner 角色连接,
# RLS 策略完全不会生效,多租户隔离会被静默击穿。
engine = create_async_engine(_settings.app_database_url, pool_pre_ping=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def tenant_scoped_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """返回一个已绑定租户上下文的会话。所有业务查询必须通过这个入口获取会话。"""
    async with SessionLocal() as session:
        # set_config 的第三个参数 is_local=True 等价于 SET LOCAL:
        # 仅在当前事务内生效,事务结束自动清除,避免连接池复用时串租户。
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": tenant_id},
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def system_session() -> AsyncGenerator[AsyncSession, None]:
    """不绑定租户上下文的系统级会话,仅供迁移、后台任务的跨租户统计等受控场景使用。
    业务 API 代码禁止直接使用此函数读取租户业务数据。
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
