"""沙箱 Provider 抽象接口。

当前唯一实现是 DockerSandboxProvider(封装 openhands-workspace 的 DockerWorkspace)。
MicroVMSandboxProvider / E2BSandboxProvider 是预留接口,尚未实现 —— 见 docs/ARCHITECTURE.md
2.3 节「预留接口」。上层(orchestrator)只依赖这个抽象,不直接依赖 DockerWorkspace,
以后新增实现不需要改上层代码。

安全要点(对应任务红线「凭证不进沙箱」):
- `create_workspace()` 的 env 参数只接受*非敏感*的运行配置(模型 base_url、超时等)。
- 不接受凭证类参数。需要凭证的动作由 app/tools/credential_gateway.py 在控制面侧代理执行,
  结果以 Observation 形式返回给沙箱内的 Agent,凭证本身永远不会被写入容器的环境变量或文件系统。
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class SandboxHandle:
    """一次性沙箱实例的句柄。"""

    task_id: str
    container_id: str
    agent_server_base_url: str
    workspace_path: str = "/workspace"
    extra: dict = field(default_factory=dict)


class SandboxProvider(abc.ABC):
    """沙箱生命周期抽象接口。每个任务对应唯一一个 SandboxHandle,任务结束必须调用 destroy。"""

    @abc.abstractmethod
    async def create_workspace(
        self,
        task_id: str,
        *,
        non_sensitive_env: dict[str, str] | None = None,
        network_mode: str = "bridge",
    ) -> SandboxHandle: ...

    @abc.abstractmethod
    async def destroy_workspace(self, handle: SandboxHandle) -> None: ...

    @abc.abstractmethod
    async def is_alive(self, handle: SandboxHandle) -> bool: ...
