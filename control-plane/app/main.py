"""FastAPI 应用入口。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_health import router as health_router
from app.api.routes_tasks import router as tasks_router
from app.api.routes_ws import router as ws_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="FrameMind Control Plane",
    description="基于 OpenHands 开源底座构建的 Intent-First AI Agent 平台控制面",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应收紧为前端实际部署域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "FrameMind",
        "description": "Intent-First AI Agent 工作台 (基于 OpenHands MIT 协议构建)",
        "docs": "/docs",
    }
