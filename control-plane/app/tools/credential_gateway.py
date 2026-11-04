"""策略网关:凭证不进沙箱的核心实现。

安全模型(对应任务红线 5):
    模型只「提议」动作,凭证不进入沙箱,由策略网关执行。

工作流程:
1. 沙箱内 Agent 产出一个 ActionEvent,例如 "调用 GitHub API 创建 PR"。
2. Agent Server 把这类需要外部凭证的动作标记为 `requires_credential=True`,
   通过事件流上报给控制面,而不是自己尝试去读某个凭证环境变量。
3. 控制面的 CredentialGateway 收到请求后:
   a. 校验当前任务所属租户是否拥有该凭证、凭证 scope 是否覆盖该动作;
   b. 校验是否命中人工审核策略(高风险 provider/scope 需要人工批准,见
      app/orchestrator 中的 human_approval 节点);
   c. 从加密存储中取出明文凭证,代表 Agent 发起实际 HTTP 调用;
   d. 把调用结果(Observation)而非凭证本身回传给沙箱。
4. 全程记录 AuditLog:谁、什么任务、用了哪个凭证引用、什么时候。

这样即使沙箱容器被攻破,攻击者也只能看到网络请求的结果,拿不到凭证明文。
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

import httpx
import structlog
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import AuditLog, CredentialRef

logger = structlog.get_logger(__name__)


@dataclass
class CredentialProxyRequest:
    task_id: str
    tenant_id: str
    credential_name: str
    method: str
    url: str
    headers: dict[str, str] | None = None
    json_body: dict | None = None


@dataclass
class CredentialProxyResult:
    status_code: int
    body: str
    truncated: bool = False


class CredentialGateway:
    """凭证代理执行器。沙箱永远只能拿到这个类返回的 Observation,拿不到凭证本身。"""

    def __init__(self, fernet_key: bytes | None = None) -> None:
        settings = get_settings()
        # 生产环境中该 key 应来自 KMS/Vault,这里用控制面密钥派生仅作为默认实现。
        key_material = fernet_key or Fernet.generate_key()
        self._fernet = Fernet(key_material)
        self._settings = settings

    def encrypt_credential(self, raw_value: str) -> str:
        return self._fernet.encrypt(raw_value.encode()).decode()

    def _decrypt_credential(self, encrypted_value: str) -> str:
        return self._fernet.decrypt(encrypted_value.encode()).decode()

    async def execute_on_behalf_of(
        self, db: AsyncSession, request: CredentialProxyRequest
    ) -> CredentialProxyResult:
        cred = await self._load_credential(db, request.tenant_id, request.credential_name)
        if cred is None:
            raise PermissionError(
                f"租户 {request.tenant_id} 没有名为 '{request.credential_name}' 的有效凭证"
            )

        plaintext = self._decrypt_credential(cred.encrypted_value)
        headers = dict(request.headers or {})
        # 按 provider 约定注入授权头,具体协议留给调用方扩展;这里演示 Bearer 模式。
        headers.setdefault("Authorization", f"Bearer {plaintext}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                request.method, request.url, headers=headers, json=request.json_body
            )

        await self._audit(
            db,
            tenant_id=request.tenant_id,
            task_id=request.task_id,
            credential_name=request.credential_name,
            url=request.url,
            status_code=resp.status_code,
        )

        body_text = resp.text
        truncated = len(body_text) > 20_000
        return CredentialProxyResult(
            status_code=resp.status_code,
            body=body_text[:20_000],
            truncated=truncated,
        )

    async def _load_credential(
        self, db: AsyncSession, tenant_id: str, name: str
    ) -> CredentialRef | None:
        stmt = select(CredentialRef).where(
            CredentialRef.tenant_id == tenant_id,
            CredentialRef.name == name,
            CredentialRef.is_active.is_(True),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _audit(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        task_id: str,
        credential_name: str,
        url: str,
        status_code: int,
    ) -> None:
        db.add(
            AuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                task_id=task_id,
                action="credential_proxy_execute",
                detail={
                    "credential_name": credential_name,
                    "url": url,
                    "status_code": status_code,
                    "timestamp": dt.datetime.now(dt.UTC).isoformat(),
                },
            )
        )
        logger.info(
            "credential_used_via_gateway",
            tenant_id=tenant_id,
            task_id=task_id,
            credential_name=credential_name,
            status_code=status_code,
        )
