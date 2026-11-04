"""模型层可插拔工厂。

硬性约束(任务要求 4):厂商 SDK 不得写进核心逻辑。本模块只通过
`openhands.sdk.LLM`(其底层即基于 LiteLLM 实现)构造模型客户端,
不直接 import openai / anthropic / ollama 等任何厂商专属 SDK。

支持的 provider(通过 LLM_PROVIDER 环境变量切换,模型名遵循 LiteLLM 的
`<provider>/<model>` 前缀约定):
- ollama      -> 本地 Ollama,零成本路径,默认配置
- openai      -> 任意 OpenAI 兼容端点(官方 / vLLM / LM Studio 等)
- anthropic   -> Anthropic 官方 API
- deepseek    -> DeepSeek 官方 API
"""

from __future__ import annotations

from app.core.config import Settings, get_settings

try:
    from openhands.sdk import LLM  # type: ignore

    _HAS_OPENHANDS_SDK = True
except ImportError:  # pragma: no cover
    LLM = None  # type: ignore
    _HAS_OPENHANDS_SDK = False


_SUPPORTED_PROVIDERS = {"ollama", "openai", "anthropic", "deepseek"}


def build_llm(settings: Settings | None = None):
    """根据环境变量构造一个 openhands.sdk.LLM 实例。

    零成本路径验证:当 LLM_PROVIDER=ollama 时,api_key 允许是任意占位字符串
    (Ollama 不校验),base_url 指向本地/局域网 Ollama 服务,不产生任何费用。
    """
    settings = settings or get_settings()

    if settings.llm_provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"不支持的 LLM_PROVIDER='{settings.llm_provider}',"
            f"必须是 {sorted(_SUPPORTED_PROVIDERS)} 之一"
        )

    if not _HAS_OPENHANDS_SDK:
        raise RuntimeError(
            "openhands-sdk 未安装,无法构造 LLM 客户端。请先 pip install openhands-sdk。"
        )

    # LiteLLM 约定:model 字符串本身带 provider 前缀(如 "ollama/qwen2.5-coder:7b"),
    # base_url/api_key 按 provider 语义传递。openhands.sdk.LLM 直接转发给 LiteLLM。
    return LLM(
        model=settings.llm_model,
        base_url=settings.llm_base_url if settings.llm_provider in ("ollama", "openai") else None,
        api_key=settings.llm_api_key,
    )


def is_zero_cost_configuration(settings: Settings | None = None) -> bool:
    """判断当前配置是否为零成本路径(纯本地 Ollama,未配置任何付费厂商)。"""
    settings = settings or get_settings()
    return settings.llm_provider == "ollama"
