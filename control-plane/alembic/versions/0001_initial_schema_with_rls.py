"""初始表结构 + 多租户 Row-Level Security 策略

这是多租户隔离的数据库层实现(对应验收标准:
"两个不同租户/用户的任务互不可见")。

策略原理:
1. 每张业务表都有 tenant_id 列。
2. 对每张业务表启用 RLS 并创建 USING 策略:
   `tenant_id = current_setting('app.current_tenant_id', true)::uuid`
3. 应用层通过 `app/db/session.py::tenant_scoped_session()` 在每个事务开始时
   执行 `SET LOCAL app.current_tenant_id = '<tenant_id>'`。
4. 没有调用 SET 的连接(current_setting 返回 NULL)查询任何业务表都会得到空结果集,
   而不是报错或返回全部数据——这是故意设计成"默认拒绝"而不是"默认放行"。
5. 应用数据库角色本身不是 superuser/table owner,所以 RLS 无法被绕过
   (Postgres 对表 owner 默认豁免 RLS,因此迁移中显式创建一个受限角色 `agentforge_app`
   并 `ALTER TABLE ... FORCE ROW LEVEL SECURITY` 强制其也遵守策略)。

Revision ID: 0001
Revises:
Create Date: 2026-11-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_SCOPED_TABLES = [
    "tasks",
    "task_nodes",
    "event_logs",
    "audit_logs",
    "credential_refs",
]


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ---------- tenants ----------
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_cost_budget_usd", sa.Float, nullable=False, server_default="50.0"),
        sa.Column("max_concurrent_tasks", sa.Integer, nullable=False, server_default="5"),
    )

    # ---------- users ----------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ---------- tasks ----------
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("instruction", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("repo_url", sa.String(1000), nullable=True),
        sa.Column("max_steps", sa.Integer, nullable=False, server_default="50"),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="1800"),
        sa.Column("token_budget", sa.Integer, nullable=False, server_default="200000"),
        sa.Column("cost_budget_usd", sa.Float, nullable=False, server_default="5.0"),
        sa.Column("steps_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_used_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("sandbox_container_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])

    # ---------- task_nodes ----------
    op.create_table(
        "task_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("parent_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("task_nodes.id"), nullable=True),
        sa.Column("node_type", sa.String(32), nullable=False),
        sa.Column("agent_role", sa.String(100), nullable=False, server_default="default"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("conversation_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_nodes_tenant_id", "task_nodes", ["tenant_id"])
    op.create_index("ix_task_nodes_task_id", "task_nodes", ["task_id"])

    # ---------- event_logs ----------
    op.create_table(
        "event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("task_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("task_nodes.id"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_event_logs_tenant_id", "event_logs", ["tenant_id"])
    op.create_index("ix_event_logs_task_id_sequence", "event_logs", ["task_id", "sequence"])

    # ---------- audit_logs ----------
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("detail", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])

    # ---------- credential_refs ----------
    op.create_table(
        "credential_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("scope", sa.String(200), nullable=False),
        sa.Column("encrypted_value", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_credential_refs_tenant_id", "credential_refs", ["tenant_id"])

    # ---------- 受限应用角色(RLS 对表 owner 默认豁免,所以 API 必须用这个角色连接) ----------
    # 密码必须和 .env 中 APP_DATABASE_URL 使用的密码一致;生产环境部署时请同步修改两处。
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agentforge_app') THEN
                CREATE ROLE agentforge_app LOGIN PASSWORD 'change-me-in-production';
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO agentforge_app")

    for table in ["tenants", "users", *TENANT_SCOPED_TABLES]:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO agentforge_app")

    # ---------- 为每张租户业务表启用并强制 RLS ----------
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )


def downgrade() -> None:
    for table in TENANT_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
    op.drop_table("credential_refs")
    op.drop_table("audit_logs")
    op.drop_table("event_logs")
    op.drop_table("task_nodes")
    op.drop_table("tasks")
    op.drop_table("users")
    op.drop_table("tenants")
