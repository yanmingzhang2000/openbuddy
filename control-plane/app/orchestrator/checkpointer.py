"""Postgres checkpointer 工厂。

用于 LangGraph 的状态持久化:每个任务对应一个 `thread_id`(=task_id),
checkpointer 把每一步的状态快照写入 Postgres,支持:
- 人工审核场景下的暂停/恢复(`Command(resume=...)` 需要能找到之前的状态)
- 控制面进程重启后继续未完成的任务(崩溃恢复,在多 Agent 编排层面的体现)

==============================================================================
许可证合规说明(重要,不要绕过这段注释直接加依赖)
==============================================================================
官方 `langgraph-checkpoint-postgres` 包硬依赖 `psycopg`(Psycopg 3),
而 psycopg 使用 **LGPLv3** 许可证,与本项目「依赖许可证仅限 MIT/Apache-2.0」的
硬性约束冲突(见 docs/ARCHITECTURE.md 第 5 节)。

因此默认实现 **不引入** `langgraph-checkpoint-postgres` 依赖,`get_checkpointer()`
在未安装该包时优雅降级为 `None`(不持久化状态,见下方代码)。这意味着默认配置下:
- LangGraph 图的执行状态只存在于单次 `graph.ainvoke()` 调用的进程内存中;
- 人工审核的 `interrupt()` 仍然能在同一次调用内正常工作(LangGraph 的
  interrupt/resume 机制不强制要求 checkpointer,但没有 checkpointer 时无法支持
  "审批发生在另一个进程/控制面重启之后"这种跨进程恢复场景)。
- 这是「实现边界」清单中记录的一个已知简化点,见 README.md。

如果你的合规政策认为 LGPL 作为*动态链接依赖*(不修改 psycopg 源码、不静态链接)
可以接受,有两个选项可以启用跨进程状态持久化:

选项 A(推荐,许可证更干净):使用社区包 `langgraph-checkpoint-postgres-pg8000`
    (基于 BSD-3-Clause 协议的 `pg8000` 驱动,而不是 psycopg)。
    `pip install langgraph-checkpoint-postgres-pg8000`,并将下方 import 改为
    `from langgraph_checkpoint_postgres_pg8000 import AsyncPgPostgresSaver as AsyncPostgresSaver`。
    注意:该包定位是"过渡方案"(用于 Cloud SQL Connector 尚不支持 psycopg 的场景),
    社区维护强度弱于官方包,生产使用前请自行评估。

选项 B:引入官方 `langgraph-checkpoint-postgres` + `psycopg[binary]`
    (取消 pyproject.toml 中对应依赖的注释),接受 LGPLv3 作为运行时依赖。
    适用于贵组织的许可证政策允许 LGPL 动态链接依赖的情况。

本项目默认选择"不引入"是为了严格满足任务书的硬性约束,而不是技术上无法实现。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from app.core.config import get_settings

try:
    # 默认不在 pyproject.toml 中声明这个依赖(见上方许可证说明),
    # 如果环境中碰巧装了(例如选择了选项 B),则正常启用。
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    _HAS_PG_CHECKPOINTER = True
except ImportError:
    AsyncPostgresSaver = None  # type: ignore
    _HAS_PG_CHECKPOINTER = False


@asynccontextmanager
async def get_checkpointer():
    """返回一个已完成 `setup()` 的 AsyncPostgresSaver 上下文,或 None(降级为不持久化)。"""
    if not _HAS_PG_CHECKPOINTER:
        yield None
        return

    settings = get_settings()
    # langgraph-checkpoint-postgres 使用 psycopg 连接串格式(非 asyncpg),这里做一次转换。
    conn_str = settings.app_database_url.replace("postgresql+asyncpg://", "postgresql://")
    async with AsyncPostgresSaver.from_conn_string(conn_str) as saver:
        await saver.setup()
        yield saver
