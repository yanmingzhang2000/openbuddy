# FrameMind

**Clarity before action.**

FrameMind 是一个 intent-first AI Agent 工作台。它不会急着执行模糊指令，而是帮助用户先明确目标、背景、约束和预期结果，再推进任务执行。

基于 [OpenHands](https://github.com/OpenHands/OpenHands)(MIT 协议)构建。软件授权费 0,支持纯本地 Ollama 零成本运行,也可插拔切换到 OpenAI 兼容端点 / Anthropic / DeepSeek。

> **品牌说明**: FrameMind 是对外产品品牌。agentforge 是现阶段为兼容已有部署而保留的内部技术标识。

> Intent-First 产品设计见 [`docs/INTENT_FIRST_PRODUCT.md`](docs/INTENT_FIRST_PRODUCT.md)，技术设计见 [`docs/INTENT_FIRST_TECHNICAL.md`](docs/INTENT_FIRST_TECHNICAL.md)。
> 架构细节、组件选型理由、复用与自研边界清单见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。
> 当前实现的能力边界(什么做了、什么没做)见本文末尾的[「当前实现边界」](#当前实现边界)章节,请务必在生产使用前阅读。

## 这是什么

用户在 Web 工作台下达任务,Agent 在一次性 Docker 沙箱里写代码、跑命令、调工具,直到完成或触发预算/步数/超时护栏。支持委派给多个子任务并行执行,高风险操作会暂停等待人工审核。

- **执行引擎、事件溯源、沙箱**:直接复用 OpenHands 的 `openhands-sdk` / `openhands-tools` / `openhands-workspace` / `openhands-agent-server`,未改动其内部实现。
- **多 Agent 委派/并行/人工审核**、**多租户控制平面**(认证、预算配额、审计日志、任务队列):本项目自研,OpenHands 官方生态目前没有提供面向这个场景的生产级实现。

## 快速开始

### 前置条件

- Docker Desktop(Windows/Mac)或 Docker Engine + Compose v2(Linux)
- 零成本路径:本机或局域网内有 [Ollama](https://ollama.com) 服务,并已拉取一个代码能力较好的模型

```powershell
# 安装 Ollama 后拉取模型(约 4-5GB,首次下载需要时间)
ollama pull qwen2.5-coder:7b
# 确认 Ollama 正在监听 11434 端口
ollama serve
```

### 启动

```powershell
Copy-Item .env.example .env
docker compose up --build
```

等待所有服务健康检查通过后,打开 http://localhost:3000。

服务组成:

| 服务 | 端口 | 作用 |
|---|---|---|
| `web` | 3000 | Next.js 前端工作台 |
| `control-plane` | 8000 | FastAPI 控制面(REST + WebSocket),`/docs` 为 OpenAPI 文档 |
| `worker` | - | arq 队列消费者,驱动 LangGraph 编排图执行任务 |
| `postgres` | 5432 | 任务/事件/审计数据,启用多租户 Row-Level Security |
| `valkey` | 6379 | 任务队列后端(Redis 协议兼容,BSD-3 许可) |
| `migrate` | - | 一次性运行 `alembic upgrade head` 后退出 |

### 配置模型

所有模型配置在 `.env` 中,核心是三个变量:`LLM_PROVIDER` / `LLM_MODEL` / `LLM_BASE_URL` / `LLM_API_KEY`。

#### 零成本路径(默认,纯本地 Ollama)

```ini
LLM_PROVIDER=ollama
LLM_MODEL=ollama/qwen2.5-coder:7b
LLM_BASE_URL=http://host.docker.internal:11434
LLM_API_KEY=ollama-local-no-key-needed
```

`host.docker.internal` 让容器访问宿主机的 Ollama 服务。Windows/Mac 的 Docker Desktop 原生支持这个域名;Linux 下 `docker-compose.yml` 已经加了 `extra_hosts: host-gateway` 映射,无需额外配置。

验证零成本配置是否生效:

```powershell
curl http://localhost:8000/api/health/llm-config
# 应返回 {"provider":"ollama", ..., "zero_cost": true}
```

#### 切换到付费厂商(可选)

修改 `.env` 中对应的四个变量,例如切到 OpenAI 兼容端点:

```ini
LLM_PROVIDER=openai
LLM_MODEL=openai/gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxx
```

Anthropic / DeepSeek / 智谱开放平台 的配置示例见 `.env.example` 中的注释。切换厂商不需要改任何代码,模型层统一通过 `openhands.sdk.LLM`(底层基于 LiteLLM)接入,核心逻辑不依赖任何厂商 SDK。

### 跑第一个任务

1. 打开 http://localhost:3000,选择「注册新租户」,填入租户名、邮箱、密码。
2. 在「提交新任务」面板填写标题和指令,例如:

   ```
   标题:写项目简介
   指令:在当前工作目录新建 FACTS.txt,写入 3 条关于本项目的事实
   ```

3. 点击「提交给 Agent」,任务进入 `queued` 状态,随后由后台 worker 取出执行。
4. 在任务列表点击该任务,右侧面板会实时显示 Agent 的动作流(逐条 Action/Observation)。
5. 任务完成后状态变为 `completed`,再次点击该任务可以看到完整的历史事件回放。

命令行验证(不通过 UI,直接调 API):

```powershell
# 注册
$resp = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/auth/signup `
  -ContentType "application/json" `
  -Body '{"tenant_name":"demo","email":"demo@example.com","password":"password123"}'
$token = $resp.access_token

# 创建任务
$task = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/tasks `
  -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" `
  -Body '{"title":"demo","instruction":"在当前工作目录新建 FACTS.txt,写入 3 条关于本项目的事实"}'

# 查询状态
Invoke-RestMethod -Uri "http://localhost:8000/api/tasks/$($task.id)" -Headers @{ Authorization = "Bearer $token" }
```

## 常见故障排查

| 现象 | 可能原因 | 排查方法 |
|---|---|---|
| `docker compose up` 后 `control-plane` 反复重启 | Postgres 还没完成健康检查 / 迁移未跑完 | `docker compose logs migrate` 确认迁移是否成功;`docker compose ps` 看 `postgres` 是否 healthy |
| 任务一直停在 `queued` | `worker` 服务没启动或连不上 Valkey | `docker compose logs worker`;确认 `REDIS_URL` 指向 `valkey:6379` |
| 任务执行失败,`error_message` 提示连接 Ollama 失败 | Ollama 没在宿主机运行,或 `host.docker.internal` 解析失败 | 宿主机执行 `curl http://localhost:11434` 确认 Ollama 在跑;Linux 下确认 `docker-compose.yml` 的 `extra_hosts` 配置生效(`docker exec` 进容器 `ping host.docker.internal`) |
| 创建任务返回 429 | 触发了 `max_concurrent_tasks` 租户并发配额 | 等待现有任务结束,或在 `tenants` 表调整该租户的 `max_concurrent_tasks`(当前无 UI,需要直连数据库) |
| WebSocket 连不上/一直 `pending` | token 过期或 `NEXT_PUBLIC_WS_BASE_URL` 配置错误 | 检查浏览器控制台网络面板的 WS 连接状态;确认 `.env` 中 `NEXT_PUBLIC_WS_BASE_URL` 使用 `ws://`(不是 `wss://`,除非配置了 TLS) |
| 容器沙箱创建失败 | 控制面容器没有挂载 Docker socket,或 `agentforge/sandbox-runtime` 镜像未构建 | 确认 `docker-compose.yml` 中 `control-plane`/`worker` 的 `volumes` 挂载了 `/var/run/docker.sock`;首次启动时手动 `docker build -t agentforge/sandbox-runtime:latest ./sandbox-runtime` |
| Postgres 启动失败,数据卷冲突 | 之前启动过不同 schema 版本 | 开发环境可以 `docker compose down -v` 清空数据卷重新开始(**会丢数据**,生产环境禁止) |

## 开发

```powershell
# 后端
cd control-plane
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\pytest

# 前端
cd web
npm install
npm run dev
```

详细开发约定见 [`AGENTS.md`](AGENTS.md)。

## 许可证

本项目新增代码使用 Apache-2.0 协议发布(见 [`LICENSE`](LICENSE))。依赖的 OpenHands 底座(`openhands-sdk` 等)为 MIT 协议。完整依赖许可证清单见 `docs/ARCHITECTURE.md` 第 5 节,不包含 Dify / n8n / AutoGen。

---

## 当前实现边界

这是一份诚实的差距清单。标注为「未实现」的能力请不要假设它们存在。

### 已实现并可验证

- ✅ `docker compose up` 一键启动全部服务
- ✅ 零成本路径:纯本地 Ollama 跑通任务(前提是本机已装好 Ollama 并拉取模型)
- ✅ Web UI 实时查看 Agent 动作流 + 历史任务回放(通过 WebSocket/REST 读取事件表)
- ✅ 多租户数据隔离:Postgres RLS + 受限数据库角色(`agentforge_app`),有集成测试验证
- ✅ 凭证不进沙箱:环境变量黑名单检测 + 策略网关代理执行模式,有单元测试验证
- ✅ 预算护栏(步数/超时/token/成本)+ 租户并发配额,有单元测试验证
- ✅ LangGraph 实现的委派/并行 fan-out/人工审核中断,状态可持久化到 Postgres
- ✅ 模型层可插拔(Ollama/OpenAI 兼容/Anthropic/DeepSeek/智谱开放平台),不依赖厂商 SDK

### 简化实现,生产化前需要加固

- ⚠️ **LangGraph 状态持久化默认关闭**:官方 `langgraph-checkpoint-postgres` 包硬依赖
  LGPLv3 许可证的 `psycopg`,与本项目"仅限 MIT/Apache-2.0"的约束冲突,因此默认不安装这两个包
  (`app/orchestrator/checkpointer.py` 中有完整说明和两个合规启用选项)。当前效果是:
  人工审核的暂停/恢复在**同一次进程调用内**正常工作,但不支持"审批发生在控制面重启之后"的
  跨进程状态恢复。如果需要这个能力,请按该文件顶部注释改用 BSD-3 的 `pg8000` 驱动方案。
- ⚠️ **多 Agent 委派规则是启发式的**(`app/orchestrator/graph.py::plan_node` 用关键词匹配判断是否拆分子任务),没有用 LLM 做结构化规划。生产场景建议替换为一次结构化输出的 LLM 调用。
- ⚠️ **WebSocket 鉴权用 URL query 参数传 JWT**,会被写入代理/访问日志,存在token 泄露到日志的风险。生产环境建议改为连接后首帧鉴权或短时一次性 ticket。
- ⚠️ **凭证加密密钥(Fernet key)在 `CredentialGateway` 中默认临时生成**,进程重启后旧密文无法解密。生产环境必须接入 KMS/Vault 或持久化密钥管理,当前仅为接口占位实现。
- ⚠️ **孤儿沙箱容器清理**(`app/queue/worker.py::reap_stale_sandboxes`)仅有定时任务骨架,没有实现真正扫描 Docker API 比对孤儿容器的逻辑。
- ⚠️ **`conversation_runner.py` 中对接 `openhands-sdk` 的事件回调接口**(`conversation.on_event`、`conversation.stop()`)是按 SDK 公开文档描述的能力编写的适配代码,如果实际 pip 包的方法签名有出入,需要对照已安装版本的真实 API 做一次适配校正(SDK 仍在快速迭代)。

### 尚未实现(与原始任务目标的差距)

- ❌ **MicroVM / E2B 沙箱**:仅定义了 `SandboxProvider` 抽象接口,只有 Docker 一种实现。
- ❌ **多租户内的用户邀请/成员管理**:注册即创建新租户,没有"邀请同事加入已有租户"的接口。
- ❌ **前端成本看板的可视化图表**:当前只有单任务的三项数字(步数/token/成本),没有跨任务/跨时间的汇总图表。
- ❌ **CLI 客户端**:架构文档中规划了 CLI,当前只实现了 REST/WebSocket API 和 Web UI,没有独立打包的命令行工具(可以直接用 `openhands-sdk` 自带 CLI 连接 Agent Server,但未与本项目的控制面/多租户集成)。
- ❌ **评测(evaluation)能力**:没有实现自动化的任务成功率评测或 benchmark 接入。
- ❌ **分布式/K8s 化部署**:当前 arq worker 是单机多进程模型,没有 K8s Job 化的沙箱调度。
- ❌ **MCP Server 的凭证管理 UI**:`app/tools/mcp_config.py` 只有代码层的默认 MCP server 列表,没有前端界面管理租户自定义 MCP server。
- ❌ **令牌刷新 / 登出黑名单**:JWT 过期后必须重新登录,没有 refresh token 机制。

### 后续演进建议(按优先级)

1. 把 `plan_node` 的启发式规划换成结构化 LLM 输出,提升委派决策质量。
2. 接入真实 KMS(如 HashiCorp Vault 的 Transit engine)替换 Fernet 临时密钥。
3. 补上孤儿容器清理的真实实现,防止长期运行后 Docker 资源泄漏。
4. 补充速率限制(目前只有并发任务数配额,没有按时间窗口的 QPS 限制)。
5. 加入 OpenTelemetry trace,把"确定性重放"能力从"读取事件表"升级为"真正重新驱动一次 Conversation 比对结果"。
