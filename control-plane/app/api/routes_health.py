"""健康检查与运行配置自检(用于验证"零成本运行路径"是否生效)。"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.llm.factory import is_zero_cost_configuration

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/llm-config")
async def llm_config_check() -> dict:
    """暴露当前模型配置是否为零成本路径,不泄露 api_key 明文。"""
    settings = get_settings()
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "base_url": settings.llm_base_url,
        "zero_cost": is_zero_cost_configuration(settings),
    }
