"""ORM 模型。

多租户隔离策略(双保险):
1. 应用层:每张业务表都有 tenant_id 列,所有查询(见 app/api/*.py)显式过滤。
2. 数据库层:对应的 Postgres Row-Level Security 策略在 alembic 迁移中创建,
   策略条件为 `tenant_id = current_setting('app.current_tenant_id')::uuid`。
   即使应用层查询遗漏过滤条件,数据库也会强制只返回当前事务 SET 过的租户的行。
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )
    # 预算配置(租户级默认值,任务可覆盖更严格的限制,但不能超过租户上限)
    max_cost_budget_usd: Mapped[float] = mapped_column(Float, default=50.0)
    max_concurrent_tasks: Mapped[int] = mapped_column(Integer, default=5)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    # 注意:users 表本身不启用 RLS 过滤 email 唯一性查找(登录场景需要跨租户按 email 查),
    # 但返回的凡是业务字段都会带 tenant_id,下游数据查询仍然走 RLS。
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )


class Task(Base):
    """对应一次用户下达的顶层任务,可能展开成多个 Agent 节点(见 TaskNode)。"""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(500))
    instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), default="queued"
    )  # queued|running|awaiting_approval|completed|failed|timeout|budget_exceeded|cancelled
    repo_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # 护栏配置(未显式传入则取租户/系统默认值)
    max_steps: Mapped[int] = mapped_column(Integer, default=50)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=1800)
    token_budget: Mapped[int] = mapped_column(Integer, default=200_000)
    cost_budget_usd: Mapped[float] = mapped_column(Float, default=5.0)

    # 运行时账本
    steps_used: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_used_usd: Mapped[float] = mapped_column(Float, default=0.0)

    sandbox_container_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class TaskNode(Base):
    """多 Agent 编排中的一个节点(LangGraph 图中的一个 vertex)。
    根节点对应用户原始任务;委派/并行产生的子任务各自一行,便于审计与回放定位到具体 Agent。
    """

    __tablename__ = "task_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    parent_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_nodes.id"), nullable=True
    )
    node_type: Mapped[str] = mapped_column(String(32))  # root|delegate|parallel_branch
    agent_role: Mapped[str] = mapped_column(String(100), default="default")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    conversation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )


class EventLog(Base):
    """OpenHands SDK 事件流的落库副本,供前端回放读取(确定性重放的数据来源)。"""

    __tablename__ = "event_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    task_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("task_nodes.id"))
    event_type: Mapped[str] = mapped_column(String(64))  # action|observation|message|state_update
    sequence: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )


class AuditLog(Base):
    """审计日志:记录敏感操作(凭证下发、预算越限、人工审核决策等)。只增不改不删。"""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )


class CredentialRef(Base):
    """凭证引用表:只存元数据(名称、作用域、提供方),绝不存明文凭证值。
    明文值存放在独立的 secret backend(默认实现:加密列;生产建议替换为 Vault/KMS)。
    """

    __tablename__ = "credential_refs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(50))  # github|gitlab|generic_api
    scope: Mapped[str] = mapped_column(String(200))
    encrypted_value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.UTC)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
