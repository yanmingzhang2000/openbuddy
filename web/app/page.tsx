"use client";

import { useEffect, useState, type FormEvent } from "react";
import { login, signup, listTasks, createTask, Task } from "./lib/api";
import { getAuthToken, setAuthToken, removeAuthToken } from "./lib/auth";
import TaskDetail from "./components/TaskDetail";
import BrandLogo from "./components/BrandLogo";

const INTENT_STEPS = [
  { title: "Clarify", description: "理清真正需要解决的问题" },
  { title: "Align", description: "确认目标、边界与交付标准" },
  { title: "Act", description: "将清晰意图转化为实际行动" },
] as const;

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [mode, setMode] = useState<"login" | "signup">("signup");
  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newInstruction, setNewInstruction] = useState("");

  useEffect(() => {
    const saved = getAuthToken();
    if (saved) setToken(saved);
  }, []);

  useEffect(() => {
    if (!token) return;
    refreshTasks();
    const interval = setInterval(refreshTasks, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function refreshTasks() {
    if (!token) return;
    try {
      setTasks(await listTasks(token));
    } catch (e) {
      console.error(e);
    }
  }

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authLoading) return;

    setAuthError(null);
    setAuthLoading(true);
    try {
      const res =
        mode === "signup"
          ? await signup(tenantName, email, password)
          : await login(email, password);
      setAuthToken(res.access_token);
      setToken(res.access_token);
    } catch (e) {
      setAuthError(String(e));
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    removeAuthToken();
    setToken(null);
    setTasks([]);
    setSelectedTaskId(null);
  }

  async function handleCreateTask() {
    if (!token || !newTitle || !newInstruction) return;
    await createTask(token, newTitle, newInstruction);
    setNewTitle("");
    setNewInstruction("");
    refreshTasks();
  }

  if (!token) {
    return (
      <div className="auth-layout">
        <aside className="auth-brand-side">
          <div className="auth-brand-content">
            <BrandLogo size="large" showTagline />
            <p className="auth-brand-intro">
              一个会在行动前帮助你理清目标、约束与预期的 AI Agent 工作台。
            </p>

            <div className="auth-intent-list">
              {INTENT_STEPS.map((step) => (
                <div key={step.title} className="auth-intent">
                  <div className="auth-intent__title">{step.title}</div>
                  <div className="auth-intent__description">{step.description}</div>
                </div>
              ))}
            </div>

            <div className="auth-brand-footer">
              Powered by{" "}
              <a
                href="https://github.com/OpenHands/OpenHands"
                target="_blank"
                rel="noopener noreferrer"
              >
                OpenHands
              </a>
            </div>
          </div>
        </aside>

        <main className="auth-form-side">
          <div className="auth-mobile-logo">
            <BrandLogo size="medium" />
          </div>

          <section className="auth-card" aria-labelledby="auth-title">
            <h1 id="auth-title" className="auth-title">
              {mode === "signup" ? "创建工作空间" : "进入 FrameMind"}
            </h1>
            <p className="auth-subtitle">
              {mode === "signup" ? "开始新的 AI Agent 工作空间" : "继续你的 Agent 任务"}
            </p>

            <div className="auth-mode-toggle" role="group" aria-label="认证方式">
              <button
                type="button"
                className={mode === "signup" ? "auth-mode-button is-active" : "auth-mode-button"}
                aria-pressed={mode === "signup"}
                onClick={() => setMode("signup")}
                disabled={authLoading}
              >
                注册
              </button>
              <button
                type="button"
                className={mode === "login" ? "auth-mode-button is-active" : "auth-mode-button"}
                aria-pressed={mode === "login"}
                onClick={() => setMode("login")}
                disabled={authLoading}
              >
                登录
              </button>
            </div>

            <form className="auth-form" onSubmit={handleAuth}>
              {mode === "signup" && (
                <div className="auth-field">
                  <label htmlFor="tenant-name">工作空间名称</label>
                  <input
                    id="tenant-name"
                    name="tenant_name"
                    type="text"
                    value={tenantName}
                    onChange={(e) => setTenantName(e.target.value)}
                    autoComplete="organization"
                    required
                  />
                </div>
              )}

              <div className="auth-field">
                <label htmlFor="email">邮箱地址</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>

              <div className="auth-field">
                <label htmlFor="password">密码{mode === "signup" ? "（至少 8 位）" : ""}</label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={mode === "signup" ? "new-password" : "current-password"}
                  minLength={mode === "signup" ? 8 : undefined}
                  disabled={authLoading}
                  required
                />
              </div>

              <button
                className="auth-submit"
                type="submit"
                disabled={authLoading || !email || !password || (mode === "signup" && !tenantName)}
              >
                {authLoading
                  ? mode === "signup"
                    ? "正在创建工作空间..."
                    : "正在登录..."
                  : mode === "signup"
                    ? "创建工作空间"
                    : "登录"}
              </button>
            </form>

            {authError && (
              <div className="auth-error" role="alert">
                {authError}
              </div>
            )}
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="workspace-brand">
          <BrandLogo variant="compact" size="small" />
          <h1 className="workspace-title">任务工作台</h1>
        </div>
        <button className="secondary" type="button" onClick={handleLogout}>
          退出登录
        </button>
      </header>

      <main className="app-main">
        <section className="task-composer" aria-labelledby="task-composer-title">
          <h2 id="task-composer-title">描述你想完成的事情</h2>
          <p className="task-composer-help">
            为了让 Agent 更准确地行动，请尽量说明目标、背景、约束和预期结果。
          </p>

          <input
            aria-label="任务标题"
            placeholder="任务标题（例如：整理部署文档）"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />

          <textarea
            aria-label="任务指令"
            placeholder={`例如：

目标：整理当前项目的部署文档
背景：项目使用 Docker Compose 和本地模型
约束：不要修改现有数据库数据
预期结果：生成一份可直接执行的部署步骤`}
            rows={6}
            value={newInstruction}
            onChange={(e) => setNewInstruction(e.target.value)}
          />

          <button
            type="button"
            className="task-submit"
            onClick={handleCreateTask}
            disabled={!newTitle || !newInstruction}
          >
            交给 FrameMind
          </button>
        </section>

        <div className="task-workspace">
          <section className="task-list-pane" aria-labelledby="task-list-title">
            <h2 className="task-list-header" id="task-list-title">
              任务列表
            </h2>
            {tasks.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-icon" aria-hidden="true">
                  📋
                </div>
                <p>暂无任务</p>
                <p className="empty-state-help">在上方提交你的第一个任务</p>
              </div>
            )}
            {tasks.map((t) => {
              const selected = selectedTaskId === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  className={`task-row${selected ? " selected" : ""}`}
                  aria-pressed={selected}
                  onClick={() => setSelectedTaskId(t.id)}
                >
                  <span className="task-row__title">{t.title}</span>
                  <span className={`badge ${t.status}`}>{t.status}</span>
                </button>
              );
            })}
          </section>

          <section className="task-detail-pane" aria-label="任务详情">
            <div className="panel task-detail-panel">
              {selectedTaskId ? (
                <TaskDetail token={token} taskId={selectedTaskId} onChanged={refreshTasks} />
              ) : (
                <div className="empty-state">
                  <div className="empty-state-icon" aria-hidden="true">
                    🔍
                  </div>
                  <p>选择左侧任务查看详情</p>
                  <p className="empty-state-help">实时动作流与历史回放</p>
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
