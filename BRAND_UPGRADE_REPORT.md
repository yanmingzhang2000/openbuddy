# FrameMind 品牌升级修复报告

**日期**: 2026-11-07
**目标**: 保留 FrameMind 用户品牌，同时保留 agentforge 部署兼容标识；仅修复审核发现的问题，不重做整套升级。

## 1. 当前 Git 状态

工作区仍有未提交修改，未执行 `git reset --hard`、`git clean -fd`、`docker compose down -v`，未删除 Docker volume 或数据库，也未覆盖 `.env`。

### 已修改

```text
.env.example
LICENSE
README.md
control-plane/README.md
control-plane/app/__init__.py
control-plane/app/main.py
control-plane/pyproject.toml
docs/ARCHITECTURE.md
web/app/components/TaskDetail.tsx
web/app/globals.css
web/app/layout.tsx
web/app/page.tsx
```

### 新增

```text
BRAND_UPGRADE_REPORT.md
docs/INTENT_FIRST_PRODUCT.md
docs/INTENT_FIRST_TECHNICAL.md
web/app/components/BrandLogo.tsx
web/app/components/BrandMark.tsx
web/app/lib/auth.ts
```

## 2. 修复说明

### 2.1 移动端任务工作台

- `page.tsx` 中任务列表和详情改用 `.task-workspace` 布局类，不再使用内联横向 flex。
- `globals.css` 中桌面端使用横向 flex；`max-width: 768px` 时改为 `flex-direction: column`，两个 pane 均设置 `width: 100%` 和 `flex: none`。
- 任务标题、说明、错误信息、事件 JSON、长 URL 等补充 `overflow-wrap: anywhere` / `word-break: break-word`；事件区域禁止横向溢出。
- 390px 浏览器实测：`flexDirection: column`，`clientWidth = scrollWidth = 390`，无横向滚动。

### 2.2 按钮对比度

更新 `--primary`、`--primary-hover`、`--danger`、`--danger-hover`、`--button-text`、`--disabled-bg`、`--disabled-text` 和 `--focus-ring`，并保留 hover、focus-visible、active 和 disabled 的明确状态。危险按钮 hover 使用不透明深红背景，不依赖 opacity。

WCAG 2.x sRGB 实算结果：

| 前景 / 背景 | 对比度 |
|---|---:|
| #FFFFFF / #5B61D9（主按钮） | 5.05:1 |
| #FFFFFF / #5157CC（主按钮 hover） | 5.86:1 |
| #FFFFFF / #C23645（danger） | 5.37:1 |
| #FFFFFF / #B52D3C（danger hover） | 6.17:1 |
| #B4BAC8 / #252A3A（disabled） | 7.34:1 |
| #C8CBFF / #090B12（focus ring） | 12.58:1 |
| #7C83FF / #111521（accent） | 5.68:1 |

上述组合均达到普通文字 WCAG AA 的 4.5:1 要求。

### 2.3 BrandLogo / BrandMark

- 移除对不存在的 Tailwind 工具类的依赖，改用 `brand-logo`、`brand-logo__wordmark`、`brand-logo__tagline` 等组件级 class。
- `small` / `medium` / `large` 分别映射到 24 / 32 / 48px，并由 CSS 应用实际字号。
- 尺寸配置使用 `as const satisfies Record<...>`，BrandMark 的 `size` 使用明确联合类型，未使用 `as 24 | 32 | 48`。
- 移除纯展示组件的 `"use client"`。
- 完整 Logo 中的 BrandMark 使用 `decorative`，输出 `aria-hidden="true"`；独立 BrandMark 使用 `role="img"` 和 `aria-label="FrameMind"`。
- wordmark 使用 `span`，不再固定输出 `h1`；页面主标题由页面结构提供。
- 移动端 Logo 显隐统一由 CSS 媒体查询控制，未同时使用内联 display 和 `<style jsx>`。

### 2.4 任务列表键盘操作

任务行从带 `onClick` 的 `div` 改为真正的 `button type="button"`：

- 使用 `aria-pressed` 表达选中状态。
- 重置默认边框、背景、字体和宽度。
- 保留 hover、selected、focus-visible 样式。
- 浏览器实测鼠标、Tab、Enter、Space 均可选择任务。

### 2.5 登录与注册表单

- 登录/注册区域改为真正的 `form onSubmit`。
- 所有字段均有显式 `label` 和 `htmlFor`。
- email 使用 `autoComplete="email"`。
- 密码根据模式使用 `new-password` / `current-password`。
- 增加提交 loading 状态；提交期间禁用模式切换和提交按钮，避免重复请求。
- 保留现有错误提示和注册/登录模式切换行为。

### 2.6 CSS 整理与品牌一致性

- 删除重复的 `.task-row`、`.cost-board`、`.cost-item`、`.cost-item .value`、`.cost-item .label` 定义。
- 删除未使用的 `.min-h-screen` 和 `--surface-raised`。
- 新样式统一使用 `brand-*`、`auth-*`、`task-*`、`workspace-*` 命名空间。
- 所有 `transition: all` 已替换为明确的背景、边框、颜色、阴影或 transform 属性。
- 保留 `prefers-reduced-motion` 支持。
- 提取 `INTENT_STEPS` 数组，消除 Clarify / Align / Act 三段重复 markup。
- `layout.tsx` title 已改为精确的 `FrameMind`；FastAPI title、根接口和 `control-plane/app/__init__.py` 文档字符串已改为 FrameMind。

## 3. 实际验证结果

### 已通过

- `git diff --check`：退出码 0；仅有 Git 的 LF/CRLF 提示，无空白错误。
- Web 源码扫描：`web/app` 中无用户可见 `AgentForge`、无 `onKeyDown`、无 `transition: all`、无旧伪 Tailwind 工具类、无重复目标选择器。
- Docker builder 内执行 `npm run build`：Next.js 15.0.3 编译成功，lint/type check 和静态页面生成通过。
- Web runner 单独构建并部署：`docker build --target runner -t agentforge-web -f web/Dockerfile web`，随后 `docker compose up -d --no-build --no-deps web` 成功。
- Web 日志：Next.js 15.0.3，`Ready`。
- `http://localhost:3000`：HTTP 200，页面标题精确为 `FrameMind`，页面内容无 `AgentForge`。
- `http://localhost:8000/api/health`：`{"status":"ok"}`。
- `http://localhost:8000/api/health/llm-config`：Ollama，`qwen2.5-coder:7b`，`zero_cost: true`。
- 旧 `agentforge_token` 自动迁移到 `framemind_token`，旧 key 删除；新 token 使用新 key 写入；登出同时清理新旧 key。
- 浏览器 390px 布局、键盘选择和表单无障碍语义已实测通过。

### 未完成 / 被阻塞

1. **本地 npm 不在 PATH**：直接执行 `npm run build` 返回 `npm not recognized`。因此不能把“本地 npm 构建”标记为通过；构建结果来自 Docker builder 容器。
2. **control-plane / worker 新镜像未构建成功**：`docker compose up -d --build` 在 PyPI 安装阶段被 TLS 网络错误阻塞：

```text
pip install --no-cache-dir --upgrade pip
SSL: UNEXPECTED_EOF_WHILE_READING
Could not fetch URL https://pypi.org/simple/hatchling/
ERROR: No matching distribution found for hatchling
target control-plane: failed to solve
```

因此当前运行中的 control-plane / worker 仍是旧镜像：

- `http://localhost:8000/` 仍返回 `AgentForge`。
- `http://localhost:8000/docs` 仍显示 `AgentForge Control Plane`。

源码导入验证显示源码本身可正确输出 `FrameMind Control Plane`，但这不等于新后端镜像已部署，不能标记为线上通过。

3. 当前 PowerShell 会话中 `docker` CLI 不在 PATH，无法在本轮复核 `docker compose ps`、`docker compose logs` 和 `docker compose config --quiet`。此前已执行的 compose config 通过，容器日志显示 migrate 成功且 volume 保留；但当前 CLI 不可用本身应作为环境风险记录。

## 4. 后续手动操作

网络恢复后执行：

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs migrate
docker compose logs control-plane worker web
```

然后重新验证：

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod http://localhost:8000/api/health/llm-config
Invoke-RestMethod http://localhost:8000/
```

并确认 `http://localhost:8000/docs` 显示 FrameMind。不要执行 `docker compose down -v`。
