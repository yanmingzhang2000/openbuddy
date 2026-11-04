# 架构方案:基于 OpenHands 的自有 AI Agent 平台

> 状态:v0.1(骨架实现阶段)。本文档是工程事实的来源,代码与文档不一致时以本文档描述的「复用/自研边界」为准进行修正。

## 0. 结论先行

| 问题 | 结论 |
|---|---|
| 底座 | [OpenHands](https://github.com/OpenHands/OpenHands)(MIT),具体消费 `openhands-sdk` / `openhands-tools` / `openhands-workspace` / `openhands-agent-server` 四个 PyPI 包 |
| 软件授权费 | 0(MIT 底座 + 自研代码均为 MIT/Apache-2.0 依赖) |
| 零成本运行路径 | 本地 Ollama,通过 LiteLLM 抽象以 OpenAI 兼容协议接入,无需任何付费 API Key |
| 本项目新增代码许可证 | Apache-2.0 |
| 命名 | 内部代号 `agentforge`(避免与 OpenHands 商标混淆,UI 中会明确标注"基于 OpenHands 构建") |

---

## 1. 分层架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⑥ 多端与可观测层                                              [自研]  │
│   Next.js Web 工作台 │ CLI(复用 openhands-sdk 自带 CLI) │ REST/WS SDK │
│   Trace 回放 UI(消费 SDK 事件流) │ 成本看板(消费审计日志)              │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ REST / WebSocket
┌───────────────────────────────▼──────────────────────────────────────┐
│ ⑤ 控制平面(Control Plane)                                   [自研]  │
│   FastAPI Gateway │ 认证(JWT+APIKey) │ 多租户隔离(Postgres RLS)      │
│   任务队列(arq+Redis) │ 预算/步数/超时护栏 │ 审计日志 │ 策略网关(凭证) │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ 内部调用(dispatch)
┌───────────────────────────────▼──────────────────────────────────────┐
│ ④ 多 Agent 编排层(Orchestrator)                              [自研]  │
│   LangGraph StateGraph:委派(delegate)节点 │ 并行 fan-out/fan-in       │
│   人工审核中断节点(interrupt) │ 检查点持久化(Postgres checkpointer)   │
│   —— 每个叶子节点 = 一个 OpenHands Conversation ——                   │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ 调用 Agent Server API
┌───────────────────────────────▼──────────────────────────────────────┐
│ ③ 工具与扩展层                                          [复用为主]   │
│   MCP Client(SDK 内置) │ Skills 目录(SDK 内置触发机制) │ AGENTS.md    │
│   凭证注入适配器(自研,凭证留在控制面,运行时按需短期令牌下发)          │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │
┌───────────────────────────────▼──────────────────────────────────────┐
│ ② 沙箱层                                                  [复用]     │
│   DockerWorkspace(openhands-workspace) → 每任务一次性容器              │
│   预留接口:MicroVMWorkspace / E2BWorkspace(未实现,仅定义协议)        │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │
┌───────────────────────────────▼──────────────────────────────────────┐
│ ① 执行引擎                                                 [复用]     │
│   openhands-sdk:Agent / Conversation / 事件溯源(确定性重放)           │
│   openhands-tools:Terminal / FileEditor / TaskTracker 等类型化工具     │
│   openhands-agent-server:容器内 FastAPI/WS 服务,暴露 SDK 能力         │
│   LiteLLM:厂商无关的模型层抽象(OpenAI兼容/Anthropic/DeepSeek/Ollama)  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 复用 vs 自研边界清单(逐项列出,防止含糊)

### 2.1 直接复用(不重写)

| 能力 | 来源 | 复用方式 |
|---|---|---|
| Agent 推理-行动循环 | `openhands-sdk` (`Agent`, `Conversation`) | pip 依赖,原样调用,不 fork |
| 事件溯源 / 确定性重放 / 崩溃恢复 | `openhands-sdk` Events 框架 | 原样使用其事件流,控制面只做存储转发 |
| 类型化工具系统(Action/Observation/Executor) | `openhands-tools` | 使用内置 TerminalTool / FileEditorTool / TaskTrackerTool,自定义工具时遵循其基类 |
| 对话历史压缩 | `openhands-sdk` Condenser | 原样使用 |
| 沙箱容器生命周期 | `openhands-workspace` DockerWorkspace | 原样使用,仅在其外层包一个"任务→容器"创建/销毁的编排 |
| 远程执行协议 | `openhands-agent-server`(FastAPI/WS) | 原样作为容器内服务运行,控制面作为其客户端 |
| MCP 客户端集成 | `openhands-sdk` 内置 MCP 支持 | 原样使用,控制面负责生成/分发 MCP server 配置 |
| Skills 触发机制 | `openhands-sdk` Skill / `AgentContext` | 原样使用,`load_public_skills` 可选 |
| AGENTS.md 项目级约定 | OpenHands 生态约定 | 直接沿用其文件格式和加载逻辑 |

### 2.2 自研(OpenHands 生态未提供生产级实现,或与我们的多租户/闭源商用场景冲突)

| 能力 | 为什么必须自研 | 自研方式 |
|---|---|---|
| **多 Agent 委派/并行/人工审核** | SDK 的 Agent/Conversation 面向单任务循环,官方未提供编排图;`OpenHands/automation` 仅做调度分发,不做 Agent 间协作状态机 | LangGraph(MIT)StateGraph,节点=子任务,边=委派/合并规则,`interrupt()` 实现人工审核暂停点 |
| **多租户数据隔离 + 配额 + 审计** | Agent Server 只做"会话级"隔离(API Key 区分连接),没有租户维度的数据库行级隔离、使用配额、审计留痕;这些是闭源商用 SaaS 的硬需求 | FastAPI 控制面 + Postgres,每张业务表带 `tenant_id`,启用 Row-Level Security,所有连接 `SET app.tenant_id`,双重保险 |
| **任务队列与调度** | 不直接 fork `OpenHands/automation`,因为它强耦合 OpenHands Cloud 的 SaaS 概念(webhook/cron 为主),与我们"用户在 Web 工作台直接下达任务"的交互模型不同;自己实现更简单可控 | arq(Redis-based asyncio 队列,MIT) |
| **预算/步数/超时护栏** | SDK 提供 `max_iterations` 等参数,但没有跨 Conversation、跨租户的**预算**(token/美元)账本和熔断 | 控制面维护预算账本,每步回调检查,超限则发送 stop 信号给 Conversation |
| **凭证不进沙箱的策略网关** | DockerWorkspace 默认会把环境变量/挂载传给容器;直接传凭证违反红线 | 控制面持有凭证,工具执行时若需要外部凭证(如 GitHub token),由策略网关代理请求并返回结果,不把明文凭证写入容器环境或文件系统 |
| **Web 工作台** | 不集成官方 `agent-canvas`(npm 独立项目,仍在快速演进,嵌入多租户/预算 UI 的定制成本高于自建) | Next.js 极简工作台,直连控制面 REST/WS |
| **Trace 回放 UI / 成本看板** | SDK 产生事件流,但没有面向多租户的回放前端和成本汇总 | 前端消费控制面透传的事件流 + 审计日志表 |

### 2.3 预留接口(本阶段不实现,仅定义协议)

| 能力 | 说明 |
|---|---|
| MicroVM / E2B 沙箱 | 定义 `WorkspaceProvider` 抽象接口,DockerWorkspace 是第一个实现;MicroVM(Firecracker)/E2B 可后续补第二个实现,不改上层代码 |
| 分布式多节点调度 | 当前 arq worker 单机多进程;K8s Job 化沙箱编排留作演进项 |

---

## 3. 组件选型理由

| 选型 | 候选对比 | 决策理由 |
|---|---|---|
| 多 Agent 编排:**LangGraph** | AutoGen(已归档,排除)/ CrewAI(MIT,但状态机能力弱于 LangGraph,人工审核中断支持不如 LangGraph 的 `interrupt`)/ 自研状态机(重复造轮子) | LangGraph 原生支持 `interrupt`/`Command(resume=...)` 做人工审核,`Send` API 做 fan-out 并行,`checkpointer` 做状态持久化,MIT 协议 |
| 模型抽象:**LiteLLM** | 直接用各厂商 SDK(违反约束 4,会把厂商逻辑写进核心) / OpenRouter(本身是代理服务,仍需额外抽象) | LiteLLM(MIT)统一 `completion()` 接口,原生支持 `ollama/*`、`openai/*`、`anthropic/*`、`deepseek/*` 前缀切换,OpenHands SDK 的 `LLM` 类本身也是基于 LiteLLM 实现,天然契合 |
| 任务队列:**arq** | Celery+Redis(功能更全但依赖更重,需要额外的 worker 编排和序列化配置) / Postgres SKIP LOCKED(零额外组件但吞吐与可观测性弱) | arq 纯 asyncio、原生 Pydantic 友好、和 FastAPI 技术栈一致,足够支撑任务级并发 |
| 数据库隔离:**Postgres RLS + 应用层 tenant_id** | 纯应用层过滤(一旦某个查询忘记加条件就泄露) / 每租户单独 schema(运维复杂度随租户数线性增长) | RLS 在数据库层强制兜底,即使应用代码有疏漏也不会跨租户泄露,是成本和安全性的平衡点 |
| 前端:**Next.js + 自建极简 UI** | 集成官方 Agent Canvas(耦合度高,定制成本大于收益) | 自建更可控,只需实现任务提交、事件流查看、回放三个核心页面 |
| 容器沙箱:**DockerWorkspace** | MicroVM/E2B(更强隔离但基础设施门槛高,不适合"docker compose 一键启动"的验收标准) | Docker 满足任务级隔离 + 一键部署的要求,MicroVM/E2B 留作接口预留 |

---

## 4. 安全模型(对应任务红线)

```
用户任务 → 控制面(持有凭证) → 生成"临时执行令牌/脱敏配置" → 下发给沙箱内 Agent Server
                                                              │
                                              Agent 只能"提议"动作(ActionEvent)
                                                              │
                                        策略网关(控制面侧,沙箱外)拦截高风险 Action
                                           - 需要凭证的动作(git push / 调用外部API)
                                           - 由网关代理执行,结果以 Observation 形式返回给沙箱
                                                              │
                                              沙箱容器本身：
                                                - 不挂载任何长期凭证文件
                                                - 不设置含密钥的环境变量
                                                - 任务结束即销毁,不持久化
```

- **一次性隔离工作区**:每个任务创建独立 DockerWorkspace 容器,`task_id` 对应唯一 container,任务结束(成功/失败/超时)后销毁。
- **max-steps / 超时 / 预算护栏**:在 LangGraph 节点的每一步执行前由控制面校验剩余步数、剩余时间、剩余预算,三者任一触底则主动中断 Conversation 并标记任务状态为 `budget_exceeded` / `timeout` / `max_steps_exceeded`。

---

## 5. 许可证合规清单

> 本清单已对 `control-plane/pyproject.toml` 和 `web/package.json` 中实际声明的每一个依赖
> 逐项核实许可证(而非假设),核实方式和结论见下表。

| 依赖 | 许可证 | 用途 |
|---|---|---|
| openhands-sdk / openhands-tools / openhands-workspace / openhands-agent-server | MIT | 执行引擎、沙箱 |
| LangGraph / LangChain-core | MIT | 多 Agent 编排 |
| ~~langgraph-checkpoint-postgres~~ | ~~LGPLv3(通过 psycopg 依赖引入)~~ | **默认不引入**,见下方说明 |
| LiteLLM | MIT | 模型抽象 |
| FastAPI | MIT | 控制面 API |
| arq | MIT | 任务队列 |
| SQLAlchemy | MIT | ORM |
| Postgres | PostgreSQL License(类 BSD) | 数据库 |
| Redis(或 Valkey) | Redis 7.x 为 RSALv2/SSPL,**改用 Valkey(BSD-3)** 或 Redis ≤7.2(BSD-3) 避免许可问题 | 队列/缓存后端 |
| Next.js / React | MIT | 前端 |
| redis(redis-py 客户端库) | MIT | 仅用作连接 Valkey 的客户端库,服务端本身用 Valkey 规避许可证问题 |
| asyncpg | Apache-2.0 | Postgres 异步驱动,业务数据库连接 |
| arq | MIT | 任务队列 |
| docker(Python SDK) | Apache-2.0 | 控制面调用 Docker API 创建/销毁沙箱容器 |
| cryptography | Apache-2.0 / BSD(双许可) | 凭证网关加密 |
| passlib | BSD-3-Clause | 密码哈希 |
| PyJWT | MIT | JWT 签发/校验 |

> 明确排除:Dify、n8n、AutoGen 均未引入,代码与依赖清单中不出现。Redis 许可证变更是真实存在的坑,见下方实现细节,将默认使用 **Valkey**(Linux Foundation 维护的 Redis 兼容分支,BSD-3-Clause)或钉死 `redis:7.2-alpine`(仍为 BSD-3 许可证的最后版本)。

> **已发现并规避的第二个许可证坑**:LangGraph 官方的 `langgraph-checkpoint-postgres` 包硬依赖
> `psycopg`(Psycopg 3),而 psycopg 的许可证是 **LGPLv3**,不满足"仅限 MIT/Apache-2.0"的约束。
> 本项目默认**不安装**这两个包,`app/orchestrator/checkpointer.py` 在未安装时优雅降级为
> 不持久化图状态(人工审核的 `interrupt`/`resume` 仍在同一进程调用内正常工作,只是不支持
> "审批发生在控制面重启之后"的跨进程恢复场景)。该文件顶部注释给出了两个可选的合规启用路径
> (改用 BSD-3 的 `pg8000` 驱动,或显式接受 LGPL 动态链接依赖),默认保持关闭。

---

## 6. 数据流示例(单任务,无多 Agent 委派)

1. 用户在 Web 工作台提交任务 → `POST /api/tasks`(带 JWT,控制面解析出 `tenant_id`)
2. 控制面写入任务记录(RLS 保护),预算账本初始化,任务入队(arq)
3. arq worker 取出任务 → 调用 Orchestrator(单节点 LangGraph 图,无委派时退化为一个节点)
4. Orchestrator 创建 DockerWorkspace → 启动容器内 `agent-server` → 创建 `Conversation`
5. Conversation 运行,每个 Event(Action/Observation)通过 WS 回传给控制面 → 控制面落审计日志 + 转发给前端
6. 每步检查预算/步数/超时护栏;触发高风险动作(需要凭证)时暂停,等待策略网关注入临时凭证或人工审核
7. 任务结束 → 容器销毁 → 状态落库 → 前端可随时拉取事件流做回放

---

## 7. 已知限制(详见 README 中的"实现边界"章节)

本文档描述的是目标架构。初始代码交付是以上架构的**最小可用骨架**,具体每层的完成度和已知差距见 `README.md` 的「当前实现边界」章节。
