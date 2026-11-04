"""WebSocket 事件流:供前端"逐步查看 Agent 动作"实时订阅。

鉴权方式:WebSocket 握手阶段没有标准 Authorization header 支持,这里约定
客户端通过查询参数 `?token=<jwt>` 传递(生产环境建议改为 subprotocol 或首帧消息鉴权,
查询参数方式会被写入访问日志/代理日志,存在信息泄露风险,当前仅作为最小可用实现)。
"""

from __future__ import annotations

import asyncio
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.models import EventLog, Task
from app.db.session import tenant_scoped_session

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["ws"])

_POLL_INTERVAL_SECONDS = 1.0


@router.websocket("/ws/tasks/{task_id}/events")
async def task_events_ws(websocket: WebSocket, task_id: uuid.UUID, token: str = Query(...)) -> None:
    try:
        ctx = decode_access_token(token)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    last_sequence = -1

    try:
        while True:
            async with tenant_scoped_session(ctx.tenant_id) as db:
                task = await db.get(Task, task_id)
                if task is None:
                    await websocket.send_json({"type": "error", "detail": "任务不存在或无权限查看"})
                    break

                result = await db.execute(
                    select(EventLog)
                    .where(EventLog.task_id == task_id, EventLog.sequence > last_sequence)
                    .order_by(EventLog.sequence)
                )
                new_events = result.scalars().all()
                for event in new_events:
                    await websocket.send_json(
                        {
                            "type": "event",
                            "event_type": event.event_type,
                            "sequence": event.sequence,
                            "payload": event.payload,
                        }
                    )
                    last_sequence = event.sequence

                if task.status in (
                    "completed",
                    "failed",
                    "timeout",
                    "budget_exceeded",
                    "max_steps_exceeded",
                    "cancelled",
                ):
                    await websocket.send_json({"type": "task_finished", "status": task.status})
                    break

            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", task_id=str(task_id))
