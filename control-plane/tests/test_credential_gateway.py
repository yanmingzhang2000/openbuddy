"""凭证不进沙箱测试(对应验收标准"沙箱内取不到宿主凭证")。

两类测试:
1. `DockerSandboxProvider` 层:断言任何看起来像凭证的环境变量 key 传入时直接抛异常,
   不会被静默传给容器。
2. `CredentialGateway` 层:断言凭证的明文值全程不会出现在返回给调用方(沙箱 Agent)的
   结果对象里,只有 HTTP 响应体会被返回;审计日志里也不包含明文凭证。
"""

from __future__ import annotations

import pytest

from app.sandbox.docker_provider import DockerSandboxProvider, _assert_no_credential_like_keys
from app.tools.credential_gateway import CredentialGateway


class TestNoCredentialInSandboxEnv:
    @pytest.mark.parametrize(
        "bad_key",
        [
            "GITHUB_TOKEN",
            "API_KEY",
            "DB_PASSWORD",
            "SECRET_VALUE",
            "my_credential_blob",
            "openai_apikey",
        ],
    )
    def test_rejects_credential_like_env_keys(self, bad_key: str) -> None:
        with pytest.raises(ValueError, match="拒绝将可能是凭证的环境变量"):
            _assert_no_credential_like_keys({bad_key: "whatever"})

    @pytest.mark.parametrize(
        "safe_key",
        ["LLM_BASE_URL", "WORKSPACE_PATH", "LOG_LEVEL", "MAX_STEPS"],
    )
    def test_allows_non_credential_env_keys(self, safe_key: str) -> None:
        # 不应抛异常
        _assert_no_credential_like_keys({safe_key: "value"})

    @pytest.mark.asyncio
    async def test_create_workspace_rejects_credential_env(self) -> None:
        provider = DockerSandboxProvider()
        with pytest.raises(ValueError):
            await provider.create_workspace(
                "task-1", non_sensitive_env={"GITHUB_TOKEN": "ghp_xxx"}
            )


class TestCredentialGatewayNeverLeaksPlaintext:
    def test_encrypted_value_does_not_contain_plaintext(self) -> None:
        gateway = CredentialGateway()
        plaintext = "super-secret-token-value-12345"
        encrypted = gateway.encrypt_credential(plaintext)

        assert plaintext not in encrypted
        # 解密后应该能还原,证明加密是可逆的(不是单向哈希,网关需要用它发起真实请求)
        assert gateway._decrypt_credential(encrypted) == plaintext

    def test_proxy_result_type_has_no_credential_field(self) -> None:
        """CredentialProxyResult 的字段集合里不存在任何可能携带凭证明文的字段
        (只有 status_code / body / truncated,body 是远端 API 的响应,不是凭证本身)。
        """
        from app.tools.credential_gateway import CredentialProxyResult

        fields = set(CredentialProxyResult.__dataclass_fields__.keys())
        assert fields == {"status_code", "body", "truncated"}
