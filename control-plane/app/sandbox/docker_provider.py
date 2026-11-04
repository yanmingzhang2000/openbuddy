"""Docker 沙箱实现:封装 openhands-workspace 的 DockerWorkspace。

设计说明:
- 我们不直接把业务逻辑塞进 DockerWorkspace,而是薄薄包一层生命周期管理
  (任务级一次性容器:创建、健康检查、销毁),保持 openhands-workspace 包原样不改。
- `openhands.workspace.DockerWorkspace` 在导入失败时(例如本地未安装 openhands-workspace
  的开发环境)会降级为一个占位实现,方便先跑通其余代码路径;生产部署必须装好真实依赖。
"""

from __future__ import annotations

import uuid

import structlog

from app.core.config import get_settings
from app.sandbox.provider import SandboxHandle, SandboxProvider

logger = structlog.get_logger(__name__)

try:
    from openhands.workspace import DockerWorkspace  # type: ignore

    _HAS_OPENHANDS_WORKSPACE = True
except ImportError:  # pragma: no cover - 允许在未安装真实依赖时导入本模块
    DockerWorkspace = None  # type: ignore
    _HAS_OPENHANDS_WORKSPACE = False


class DockerSandboxProvider(SandboxProvider):
    """每个任务对应一个一次性 Docker 容器,容器内运行 openhands-agent-server。"""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._workspaces: dict[str, DockerWorkspace] = {}

    async def create_workspace(
        self,
        task_id: str,
        *,
        non_sensitive_env: dict[str, str] | None = None,
        network_mode: str = "bridge",
    ) -> SandboxHandle:
        env = dict(non_sensitive_env or {})
        # 显式白名单:只允许这些非敏感 key 进入容器环境变量。
        _assert_no_credential_like_keys(env)

        container_name = f"agentforge-task-{task_id}-{uuid.uuid4().hex[:8]}"

        if not _HAS_OPENHANDS_WORKSPACE:
            logger.warning(
                "openhands_workspace_not_installed_using_stub",
                task_id=task_id,
                container_name=container_name,
            )
            handle = SandboxHandle(
                task_id=task_id,
                container_id=f"stub-{container_name}",
                agent_server_base_url="http://localhost:0",
                extra={"stub": True},
            )
            return handle

        workspace = DockerWorkspace(
            image=self._settings.sandbox_image,
            container_name=container_name,
            env=env,
            network_mode=network_mode,
        )
        await workspace.start()  # 假定 openhands-workspace 提供 async start()/stop()
        self._workspaces[task_id] = workspace

        handle = SandboxHandle(
            task_id=task_id,
            container_id=workspace.container_id,
            agent_server_base_url=workspace.agent_server_base_url,
        )
        logger.info("sandbox_created", task_id=task_id, container_id=handle.container_id)
        return handle

    async def destroy_workspace(self, handle: SandboxHandle) -> None:
        workspace = self._workspaces.pop(handle.task_id, None)
        if workspace is not None:
            await workspace.stop()
            logger.info("sandbox_destroyed", task_id=handle.task_id, container_id=handle.container_id)

    async def is_alive(self, handle: SandboxHandle) -> bool:
        workspace = self._workspaces.get(handle.task_id)
        if workspace is None:
            return False
        return await workspace.is_running()


_CREDENTIAL_KEY_MARKERS = ("token", "secret", "password", "key", "credential", "apikey")


def _assert_no_credential_like_keys(env: dict[str, str]) -> None:
    """运行时保护:阻止任何看起来像凭证的 key 被传入沙箱容器环境变量。
    这是「凭证不进沙箱」红线的代码层兜底,正常路径下凭证根本不应该走到这里。
    """
    for key in env:
        lowered = key.lower()
        if any(marker in lowered for marker in _CREDENTIAL_KEY_MARKERS):
            raise ValueError(
                f"拒绝将可能是凭证的环境变量 '{key}' 传入沙箱容器。"
                "凭证必须通过 app.tools.credential_gateway 在控制面侧代理使用,不能注入沙箱。"
            )
