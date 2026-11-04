# AGENTS.md

本文件遵循 OpenHands 生态的 AGENTS.md 约定,供 Agent 在处理本仓库任务时参考。

## 项目结构

- `control-plane/`:FastAPI 控制平面(Python),多租户、任务队列、预算护栏、编排
- `web/`:Next.js 前端工作台
- `sandbox-runtime/`:沙箱容器镜像定义
- `docs/`:架构与设计文档

## 开发约定

- Python 代码遵循 `ruff` 格式化,行宽 100。
- 所有数据库查询必须通过 `app/db/session.py` 的 `tenant_scoped_session()` 获取会话,
  禁止绕过 RLS 直接用 `system_session()` 读写业务数据。
- 任何新增的环境变量 key 如果语义上是凭证,必须加入
  `app/sandbox/docker_provider.py::_CREDENTIAL_KEY_MARKERS` 的检测范围或走
  `app/tools/credential_gateway.py`,不得直接作为沙箱容器环境变量传递。
- 新增 Agent 工具需遵循 `openhands-tools` 的 Action/Observation/Executor 模式,不要绕过
  SDK 类型系统手写裸工具。

## 测试

- 后端测试:`cd control-plane && pytest`
- 关键安全测试位于 `control-plane/tests/test_tenant_isolation.py` 和
  `control-plane/tests/test_credential_gateway.py`,修改相关模块后必须重跑。
