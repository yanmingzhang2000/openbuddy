"""多租户隔离集成测试(对应验收标准:
"两个不同租户/用户的任务互不可见")。

验证点:
1. 租户 A 创建的 Task,用租户 B 的 tenant_scoped_session 查询不到(即使不加 WHERE 条件)。
2. 即使应用代码写了一个"忘记加 tenant_id 过滤条件"的裸 SELECT,RLS 仍然只返回当前
   SET 的租户的数据 —— 这验证的是数据库层兜底,而不仅仅是应用层过滤逻辑是否正确。
3. 用 owner 角色(迁移用的角色)连接时,RLS 不生效(用于对比,证明"必须用受限角色"
   这个结论不是凭空猜测)。

运行方式:
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://agentforge:change-me-in-production@localhost:5432/agentforge_test"
    $env:TEST_APP_DATABASE_URL = "postgresql+asyncpg://agentforge_app:change-me-in-production@localhost:5432/agentforge_test"
    pytest tests/test_tenant_isolation.py -v

需要先对 agentforge_test 数据库跑过 alembic upgrade head。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DATABASE_URL, TEST_OWNER_DATABASE_URL, requires_postgres


async def _insert_tenant_and_task(owner_engine, tenant_id: uuid.UUID, task_id: uuid.UUID) -> None:
    """用 owner 角色直接插入种子数据(绕开应用层逻辑,专注测试 RLS 本身)。"""
    async with owner_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO tenants (id, name, created_at) VALUES (:id, :name, now())"
            ),
            {"id": tenant_id, "name": f"tenant-{tenant_id}"},
        )
        user_id = uuid.uuid4()
        await conn.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, hashed_password, role, created_at) "
                "VALUES (:id, :tenant_id, :email, 'x', 'owner', now())"
            ),
            {"id": user_id, "tenant_id": tenant_id, "email": f"{tenant_id}@example.com"},
        )
        await conn.execute(
            text(
                "INSERT INTO tasks (id, tenant_id, created_by, title, instruction, status, "
                "max_steps, timeout_seconds, token_budget, cost_budget_usd, "
                "steps_used, tokens_used, cost_used_usd, created_at) "
                "VALUES (:id, :tenant_id, :created_by, 'seed task', 'noop', 'queued', "
                "50, 1800, 200000, 5.0, 0, 0, 0.0, now())"
            ),
            {"id": task_id, "tenant_id": tenant_id, "created_by": user_id},
        )


@requires_postgres
@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_read_even_without_where_clause():
    owner_engine = create_async_engine(TEST_OWNER_DATABASE_URL, pool_pre_ping=True)
    app_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    task_a, task_b = uuid.uuid4(), uuid.uuid4()

    await _insert_tenant_and_task(owner_engine, tenant_a, task_a)
    await _insert_tenant_and_task(owner_engine, tenant_b, task_b)

    try:
        # 以租户 A 的身份查询(SET LOCAL app.current_tenant_id),裸 SELECT 不加 WHERE。
        async with app_engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_a)},
            )
            result = await conn.execute(text("SELECT id, tenant_id FROM tasks"))
            rows = result.fetchall()

        visible_task_ids = {row[0] for row in rows}
        assert task_a in visible_task_ids, "租户 A 应该能看到自己的任务"
        assert task_b not in visible_task_ids, (
            "租户 A 不应该能看到租户 B 的任务——RLS 隔离失效!"
        )

        # 反过来验证租户 B 只看到自己的数据。
        async with app_engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_b)},
            )
            result = await conn.execute(text("SELECT id, tenant_id FROM tasks"))
            rows = result.fetchall()
        visible_task_ids = {row[0] for row in rows}
        assert task_b in visible_task_ids
        assert task_a not in visible_task_ids

    finally:
        async with owner_engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM tasks WHERE tenant_id = :a OR tenant_id = :b"),
                {"a": tenant_a, "b": tenant_b},
            )
            await conn.execute(
                text("DELETE FROM users WHERE tenant_id = :a OR tenant_id = :b"),
                {"a": tenant_a, "b": tenant_b},
            )
            await conn.execute(
                text("DELETE FROM tenants WHERE id = :a OR id = :b"),
                {"a": tenant_a, "b": tenant_b},
            )
        await owner_engine.dispose()
        await app_engine.dispose()


@requires_postgres
@pytest.mark.asyncio
async def test_no_tenant_context_returns_empty_not_all_rows():
    """未设置 app.current_tenant_id 时(例如代码遗漏调用),查询必须返回空集,
    绝不能'默认放行'返回全部租户的数据——这是"默认拒绝"安全设计的验证点。
    """
    app_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        async with app_engine.connect() as conn:
            # 不设置 app.current_tenant_id
            result = await conn.execute(text("SELECT id FROM tasks"))
            rows = result.fetchall()
        assert rows == [], "未设置租户上下文时必须返回空结果,而不是全部数据"
    finally:
        await app_engine.dispose()


@requires_postgres
@pytest.mark.asyncio
async def test_owner_role_bypasses_rls_demonstrating_why_app_role_is_required():
    """用迁移用的 owner 角色连接时,RLS 不生效(Postgres 对表 owner 默认豁免)。
    这个测试的目的不是验证"安全",而是作为文档性断言,证明
    app/db/session.py 中"业务连接必须用 agentforge_app 而不是 owner 角色"的说明成立,
    防止未来有人为了方便把 APP_DATABASE_URL 偷偷改回 owner 连接串。
    """
    owner_engine = create_async_engine(TEST_OWNER_DATABASE_URL, pool_pre_ping=True)
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    task_a, task_b = uuid.uuid4(), uuid.uuid4()
    await _insert_tenant_and_task(owner_engine, tenant_a, task_a)
    await _insert_tenant_and_task(owner_engine, tenant_b, task_b)

    try:
        async with owner_engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_a)},
            )
            result = await conn.execute(text("SELECT id FROM tasks"))
            rows = result.fetchall()
        visible_ids = {row[0] for row in rows}
        # owner 角色豁免 RLS,能看到两个租户的数据——这正说明了为什么业务连接不能用这个角色。
        assert task_a in visible_ids and task_b in visible_ids
    finally:
        async with owner_engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM tasks WHERE tenant_id = :a OR tenant_id = :b"),
                {"a": tenant_a, "b": tenant_b},
            )
            await conn.execute(
                text("DELETE FROM users WHERE tenant_id = :a OR tenant_id = :b"),
                {"a": tenant_a, "b": tenant_b},
            )
            await conn.execute(
                text("DELETE FROM tenants WHERE id = :a OR id = :b"),
                {"a": tenant_a, "b": tenant_b},
            )
        await owner_engine.dispose()
