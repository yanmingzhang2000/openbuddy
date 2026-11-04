"""FastAPI 依赖注入:提供按租户隔离的数据库会话。"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TenantContext, get_current_tenant
from app.db.session import tenant_scoped_session


async def get_db(
    ctx: TenantContext = Depends(get_current_tenant),
) -> AsyncGenerator[AsyncSession, None]:
    """所有需要租户隔离的路由都应通过这个依赖获取数据库会话,而不是直连 engine。"""
    async with tenant_scoped_session(ctx.tenant_id) as session:
        yield session
