/**
 * 任务状态卡组件
 *
 * 显示任务状态、进度和基本信息
 */

"use client";

import { useState } from "react";
import type { Task, TaskEvent } from "../lib/api";
import { getStatusLabel, isRunningStatus, getEventSummary } from "../lib/status-helpers";

type Props = {
  task: Task;
  events: TaskEvent[];
  onOpenExecutionPanel: () => void;
};

export default function TaskStatusCard({ task, events, onOpenExecutionPanel }: Props) {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const isRunning = isRunningStatus(task.status);

  return (
    <div className="status-card">
      <div className="status-card-header">
        <div className="status-card-title">
          <h3 style={{ margin: 0, fontSize: "1.125rem" }}>{task.title}</h3>
          <span className={`badge ${task.status}`}>{getStatusLabel(task.status)}</span>
        </div>
      </div>

      {/* 进度步骤 - 仅在运行时显示 */}
      {isRunning && (
        <div className="progress-steps" aria-label="执行进度">
          <div className="progress-step is-active">
            <div className="progress-step-icon">1</div>
            <div className="progress-step-label">Clarify</div>
          </div>
          <div className="progress-connector" />
          <div className="progress-step">
            <div className="progress-step-icon">2</div>
            <div className="progress-step-label">Align</div>
          </div>
          <div className="progress-connector" />
          <div className="progress-step">
            <div className="progress-step-icon">3</div>
            <div className="progress-step-label">Act</div>
          </div>
        </div>
      )}

      {/* 成本面板 */}
      <div className="cost-panel">
        <div className="cost-item">
          <div className="cost-item__value">
            {task.steps_used} / {task.max_steps}
          </div>
          <div className="cost-item__label">步数</div>
        </div>
        <div className="cost-item">
          <div className="cost-item__value">
            {task.tokens_used} / {task.token_budget}
          </div>
          <div className="cost-item__label">Token</div>
        </div>
        <div className="cost-item">
          <div className="cost-item__value">
            ${task.cost_used_usd.toFixed(4)}
          </div>
          <div className="cost-item__label">成本</div>
        </div>
      </div>

      {/* 事件时间线 - 仅显示最近几条 */}
      {events.length > 0 && (
        <div className="event-timeline">
          {events.slice(-3).map((event, idx) => (
            <div key={idx} className="event-item">
              <div className="event-item__header">
                <span className="event-item__type">
                  {getEventSummary(event.event_type || "unknown")}
                </span>
                {event.sequence !== undefined && (
                  <span className="event-item__time">#{event.sequence}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 技术详情折叠 */}
      <button
        type="button"
        className="technical-details-toggle ghost"
        onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
        aria-expanded={showTechnicalDetails}
      >
        {showTechnicalDetails ? "隐藏技术详情" : "查看技术详情"}
      </button>

      {showTechnicalDetails && (
        <div className="technical-details">
          <div style={{ marginBottom: "0.5rem", fontWeight: 600 }}>任务 ID</div>
          <code
            style={{
              display: "block",
              padding: "0.5rem",
              background: "var(--bg-surface)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.75rem",
              fontFamily: "var(--font-mono)",
              wordBreak: "break-all",
            }}
          >
            {task.id}
          </code>

          {events.length > 0 && (
            <>
              <div style={{ marginTop: "1rem", marginBottom: "0.5rem", fontWeight: 600 }}>
                原始事件
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: "0.75rem",
                  background: "var(--bg-surface)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.75rem",
                  fontFamily: "var(--font-mono)",
                  overflow: "auto",
                  maxHeight: "300px",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {JSON.stringify(events, null, 2)}
              </pre>
            </>
          )}
        </div>
      )}

      {/* 查看执行详情按钮 */}
      <div style={{ marginTop: "1rem" }}>
        <button
          type="button"
          className="secondary"
          onClick={onOpenExecutionPanel}
        >
          查看执行详情
        </button>
      </div>
    </div>
  );
}
