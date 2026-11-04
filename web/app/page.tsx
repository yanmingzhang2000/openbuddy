"use client";

import { useEffect, useState } from "react";
import { login, signup, listTasks, createTask, Task } from "./lib/api";
import TaskDetail from "./components/TaskDetail";

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [mode, setMode] = useState<"login" | "signup">("signup");
  const [tenantName, setTenantName] = useState("demo-tenant");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newInstruction, setNewInstruction] = useState("");

  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem("agentforge_token") : null;
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

  async function handleAuth() {
    setAuthError(null);
    try {
      const res =
        mode === "signup"
          ? await signup(tenantName, email, password)
          : await login(email, password);
      localStorage.setItem("agentforge_token", res.access_token);
      setToken(res.access_token);
    } catch (e) {
      setAuthError(String(e));
    }
  }

  function handleLogout() {
    localStorage.removeItem("agentforge_token");
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
      <div className="container">
        <h1>AgentForge</h1>
        <p style={{ color: "var(--muted)" }}>
          基于 <a href="https://github.com/OpenHands/OpenHands" target="_blank">OpenHands</a>{" "}
          (MIT) 构建的自有 AI Agent 平台
        </p>
        <div className="panel">
          <div style={{ marginBottom: 12 }}>
            <button
              className={mode === "signup" ? "" : "secondary"}
              onClick={() => setMode("signup")}
              style={{ marginRight: 8 }}
            >
              注册新租户
            </button>
            <button className={mode === "login" ? "" : "secondary"} onClick={() => setMode("login")}>
              登录
            </button>
          </div>
          {mode === "signup" && (
            <input
              placeholder="租户名称"
              value={tenantName}
              onChange={(e) => setTenantName(e.target.value)}
            />
          )}
          <input placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input
            placeholder="密码(至少 8 位)"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button onClick={handleAuth}>{mode === "signup" ? "注册并登录" : "登录"}</button>
          {authError && <p style={{ color: "var(--danger)" }}>{authError}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>AgentForge 工作台</h1>
        <button className="secondary" onClick={handleLogout}>
          退出登录
        </button>
      </div>

      <div className="panel">
        <h3>提交新任务</h3>
        <input
          placeholder="任务标题"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
        />
        <textarea
          placeholder="任务指令,例如:在当前仓库中新建 FACTS.txt,写入 3 条关于本项目的事实"
          rows={3}
          value={newInstruction}
          onChange={(e) => setNewInstruction(e.target.value)}
        />
        <button onClick={handleCreateTask}>提交给 Agent</button>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        <div className="panel" style={{ flex: 1 }}>
          <h3>任务列表</h3>
          {tasks.length === 0 && <p style={{ color: "var(--muted)" }}>暂无任务</p>}
          {tasks.map((t) => (
            <div key={t.id} className="task-row" onClick={() => setSelectedTaskId(t.id)}>
              <span>{t.title}</span>
              <span className={`badge ${t.status}`}>{t.status}</span>
            </div>
          ))}
        </div>

        <div className="panel" style={{ flex: 2 }}>
          {selectedTaskId ? (
            <TaskDetail token={token} taskId={selectedTaskId} onChanged={refreshTasks} />
          ) : (
            <p style={{ color: "var(--muted)" }}>选择左侧任务查看动作流与回放</p>
          )}
        </div>
      </div>
    </div>
  );
}
