"""全局配置。所有配置项从环境变量读取,不在代码中硬编码任何密钥或凭证。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM ---
    llm_provider: str = "ollama"
    llm_model: str = "ollama/qwen2.5-coder:7b"
    llm_base_url: str = "http://host.docker.internal:11434"
    llm_api_key: str = "ollama-local-no-key-needed"

    # --- 数据库 ---
    # database_url:owner 角色连接串,仅供 alembic 迁移使用。
    database_url: str = (
        "postgresql+asyncpg://agentforge:change-me@localhost:5432/agentforge"
    )
    # app_database_url:受限角色连接串,业务 API/worker 必须使用这个,
    # 否则 Postgres 对表 owner 的 RLS 豁免会让多租户隔离失效。
    app_database_url: str = (
        "postgresql+asyncpg://agentforge_app:change-me@localhost:5432/agentforge"
    )

    # --- 队列 ---
    redis_url: str = "redis://localhost:6379/0"

    # --- 控制平面 ---
    control_plane_secret_key: str = "dev-only-change-this"
    control_plane_host: str = "0.0.0.0"
    control_plane_port: int = 8000
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # --- 预算护栏默认值 ---
    default_max_steps: int = 50
    default_timeout_seconds: int = 1800
    default_token_budget: int = 200_000
    default_cost_budget_usd: float = 5.00

    # --- 沙箱 ---
    sandbox_image: str = "agentforge/sandbox-runtime:latest"
    sandbox_provider: str = "docker"
    sandbox_network_mode: str = "bridge"
    docker_host: str = "unix:///var/run/docker.sock"

    # --- 可观测 ---
    log_level: str = "INFO"
    audit_log_retention_days: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
