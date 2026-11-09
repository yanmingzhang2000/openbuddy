/**
 * 认证视图组件
 *
 * 包含登录和注册功能，浅色主题设计
 */

"use client";

import { useState, type FormEvent } from "react";
import { login, signup } from "../lib/api";
import BrandLogo from "./BrandLogo";

const INTENT_STEPS = [
  { title: "Clarify", description: "理清真正需要解决的问题" },
  { title: "Align", description: "确认目标、边界与交付标准" },
  { title: "Act", description: "将清晰意图转化为实际行动" },
] as const;

type Props = {
  onAuth: (token: string) => void;
};

export default function AuthView({ onAuth }: Props) {
  const [mode, setMode] = useState<"login" | "signup">("signup");
  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;

    setError(null);
    setLoading(true);

    try {
      const res =
        mode === "signup"
          ? await signup(tenantName, email, password)
          : await login(email, password);
      onAuth(res.access_token);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

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
              disabled={loading}
            >
              注册
            </button>
            <button
              type="button"
              className={mode === "login" ? "auth-mode-button is-active" : "auth-mode-button"}
              aria-pressed={mode === "login"}
              onClick={() => setMode("login")}
              disabled={loading}
            >
              登录
            </button>
          </div>

          <form onSubmit={handleSubmit}>
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
                disabled={loading}
                required
              />
            </div>

            <button
              className="auth-submit"
              type="submit"
              disabled={loading || !email || !password || (mode === "signup" && !tenantName)}
            >
              {loading
                ? mode === "signup"
                  ? "正在创建工作空间..."
                  : "正在登录..."
                : mode === "signup"
                  ? "创建工作空间"
                  : "登录"}
            </button>
          </form>

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
