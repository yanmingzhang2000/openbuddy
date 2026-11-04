# sandbox-runtime

容器镜像定义,内含 `openhands-agent-server`。控制面的 `DockerSandboxProvider`
(`control-plane/app/sandbox/docker_provider.py`)在收到任务时用这个镜像启动一次性容器,
任务结束后立即销毁容器(一次性隔离工作区,见 `docs/ARCHITECTURE.md` 第 4 节「安全模型」)。

本地构建:

```powershell
docker build -t agentforge/sandbox-runtime:latest .
```

`docker-compose.yml` 中已配置自动构建,一般不需要手动执行此命令。
