# 沙箱运行时镜像:容器内运行 openhands-agent-server,暴露给控制面调用。
# 每个任务创建一个该镜像的一次性容器实例,任务结束即销毁(一次性隔离工作区)。
FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    openhands-sdk \
    openhands-tools \
    openhands-agent-server

# 不在镜像里写入任何凭证或密钥;运行时也只接受白名单内的非敏感环境变量
# (见 control-plane/app/sandbox/docker_provider.py 的 _assert_no_credential_like_keys)。

EXPOSE 8001

CMD ["python", "-m", "openhands.agent_server", "--host", "0.0.0.0", "--port", "8001"]
