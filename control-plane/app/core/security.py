"""认证与租户上下文。

设计要点(对应验收标准「两个不同租户/用户的任务互不可见」):
- JWT payload 中携带 tenant_id、user_id、role。
- 每次请求通过 FastAPI 依赖注入解析出 TenantContext。
- TenantContext 被传递给数据库会话,数据库会话建立时执行
  `SET LOCAL app.current_tenant_id = '<tenant_id>'`,交由 Postgres RLS 策略强制过滤。
  这样即使应用层某个查询忘记显式加 tenant_id 过滤条件,数据库也不会跨租户返回数据。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    user_id: str
    role: str  # "owner" | "member" | "viewer"


def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def create_access_token(tenant_id: str, user_id: str, role: str) -> str:
    settings = get_settings()
    now = dt.datetime.now(dt.UTC)
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "role": role,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.control_plane_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TenantContext:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.control_plane_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid token: {exc}"
        ) from exc
    return TenantContext(
        tenant_id=payload["tenant_id"], user_id=payload["user_id"], role=payload["role"]
    )


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TenantContext:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token"
        )
    return decode_access_token(credentials.credentials)


def require_role(*allowed_roles: str):
    """角色校验依赖工厂,用于限制预算配置/审计日志查看等敏感操作。"""

    def _dep(ctx: TenantContext = Depends(get_current_tenant)) -> TenantContext:
        if ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{ctx.role}' not permitted, requires one of {allowed_roles}",
            )
        return ctx

    return _dep
