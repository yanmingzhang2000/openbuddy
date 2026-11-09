/**
 * 执行详情面板组件
 *
 * 桌面端为右侧抽屉，移动端为底部面板
 */

"use client";

import { useEffect, useRef } from "react";
import type { Task, TaskEvent } from "../lib/api";
import { getStatusLabel, getEventSummary } from "../lib/status-helpers";

type Props = {
  task: Task | null;
  events: TaskEvent[];
  isOpen: boolean;
  onClose: () => void;
};

export default function ExecutionPanel({ task, events, isOpen, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // 打开时聚焦到关闭按钮
  useEffect(() => {
    if (isOpen && closeButtonRef.current) {
      closeButtonRef.current.focus();
    }
  }, [isOpen]);

  // ESC 关闭
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen) {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!task) return null;

  return (
    <>
      {/* 背景遮罩 */}
      <div
        className={`execution-panel-overlay${isOpen ? " is-open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 面板 */}
      <div
        ref={panelRef}
        className={`execution-panel${isOpen ? " is-open" : ""}`}
        role="dialog"
        aria-label="执行详情"
        aria-hidden={!isOpen}
      >
        <div className="execution-panel-header">
          <h2 className="execution-panel-title">执行详情</h2>
          <button
            ref={closeButtonRef}
            type="button"
            className="execution-panel-close"
            onClick={onClose}
            aria-label="关闭执行详情"
          >
            ✕
          </button>
        </div>

        <div className="execution-panel-body">
          {/* 任务信息 */}
          <section style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.75rem" }}>
              任务信息
            </h3>
            <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
              <div style={{ marginBottom: "0.5rem" }}>
                <strong>标题：</strong> {task.title}
              </div>
              <div style={{ marginBottom: "0.5rem" }}>
                <strong>状态：</strong>{" "}
                <span className={`badge ${task.status}`}>{getStatusLabel(task.status)}</span>
              </div>
              <div style={{ marginBottom: "0.5rem" }}>
                <strong>创建时间：</strong> {new Date(task.created_at).toLocaleString("zh-CN")}
              </div>
              {task.started_at && (
                <div style={{ marginBottom: "0.5rem" }}>
                  <strong>开始时间：</strong> {new Date(task.started_at).toLocaleString("zh-CN")}
                </div>
              )}
              {task.finished_at && (
                <div style={{ marginBottom: "0.5rem" }}>
                  <strong>完成时间：</strong> {new Date(task.finished_at).toLocaleString("zh-CN")}
                </div>
              )}
            </div>
          </section>

          {/* 护栏配置 */}
          <section style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.75rem" }}>
              护栏配置
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap: "0.75rem",
                fontSize: "0.875rem",
              }}
            >
              <div>
                <div style={{ color: "var(--text-muted)", marginBottom: "0.25rem" }}>
                  最大步数
                </div>
                <div style={{ fontWeight: 600 }}>{task.max_steps}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", marginBottom: "0.25rem" }}>
                  超时时间
                </div>
                <div style={{ fontWeight: 600 }}>{task.timeout_seconds} 秒</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", marginBottom: "0.25rem" }}>
                  Token 预算
                </div>
                <div style={{ fontWeight: 600 }}>{task.token_budget}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-muted)", marginBottom: "0.25rem" }}>
                  成本预算
                </div>
                <div style={{ fontWeight: 600 }}>${task.cost_budget_usd}</div>
              </div>
            </div>
          </section>

          {/* 使用情况 */}
          <section style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.75rem" }}>
              使用情况
            </h3>
            <div className="cost-panel">
              <div className="cost-item">
                <div className="cost-item__value">
                  {task.steps_used}
                </div>
                <div className="cost-item__label">步数 / {task.max_steps}</div>
              </div>
              <div className="cost-item">
                <div className="cost-item__value">
                  {task.tokens_used}
                </div>
                <div className="cost-item__label">Token / {task.token_budget}</div>
              </div>
              <div className="cost-item">
                <div className="cost-item__value">
                  ${task.cost_used_usd.toFixed(4)}
                </div>
                <div className="cost-item__label">成本 / ${task.cost_budget_usd}</div>
              </div>
            </div>
          </section>

          {/* 事件流 */}
          <section>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.75rem" }}>
              事件流
            </h3>
            {events.length === 0 ? (
              <div className="empty-state" style={{ padding: "2rem" }}>
                <div className="empty-state__message">暂无事件</div>
              </div>
            ) : (
              <div className="event-timeline" style={{ maxHeight: "none" }}>
                {events.map((event, idx) => (
                  <div key={idx} className="event-item">
                    <div className="event-item__header">
                      <span className="event-item__type">
                        {getEventSummary(event.event_type || "unknown")}
                      </span>
                      {event.sequence !== undefined && (
                        <span className="event-item__time">#{event.sequence}</span>
                      )}
                    </div>
                    {event.payload && (
                      <div className="event-item__payload">
                        {JSON.stringify(event.payload, null, 2)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </>
  );
}
