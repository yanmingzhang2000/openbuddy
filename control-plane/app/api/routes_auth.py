"""注册 / 登录。注册时自动创建一个新租户(简化版多租户 onboarding:一个注册用户即一个新租户的
owner;邀请同租户其他成员的接口留作后续演进项,见 README 的「实现边界」章节)。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.schemas import LoginRequest, SignupRequest, TokenResponse
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import Tenant, User
from app.db.session import system_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(body: SignupRequest) -> TokenResponse:
    async with system_session() as db:
        existing = await db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

        tenant = Tenant(id=uuid.uuid4(), name=body.tenant_name)
        db.add(tenant)
        await db.flush()

        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=body.email,
            hashed_password=hash_password(body.password),
            role="owner",
        )
        db.add(user)
        await db.flush()

        token = create_access_token(str(tenant.id), str(user.id), user.role)
        return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    async with system_session() as db:
        result = await db.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

        token = create_access_token(str(user.tenant_id), str(user.id), user.role)
        return TokenResponse(access_token=token)
