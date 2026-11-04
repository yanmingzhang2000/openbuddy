"use client";

import { useEffect, useRef, useState } from "react";
import {
  getTask,
  getTaskEvents,
  openTaskEventsSocket,
  submitApproval,
  Task,
  TaskEvent,
} from "../lib/api";

type Props = {
  token: string;
  taskId: string;
  onChanged: () => void;
};

/**
 * 任务详情 + 实时动作流 + 历史回放。
 *
 * - 任务仍在运行(queued/running)时:通过 WebSocket 订阅实时事件流。
 * - 任务已结束:通过 REST 拉取完整历史事件列表做回放(逐条展示,
 *   对应验收标准"在 UI 中能逐步查看 Agent 的动作并回放历史任务")。
 */
export default function TaskDetail({ token, taskId, onChanged }: Props) {
  const [task, setTask] = useState<Task | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const t = await getTask(token, taskId);
      if (cancelled) return;
      setTask(t);

      const isLive = ["queued", "running"].includes(t.status);
      if (isLive) {
        const ws = openTaskEventsSocket(token, taskId, (evt) => {
          if (evt.type === "event") {
            setEvents((prev) => [...prev, evt]);
          } else if (evt.type === "task_finished") {
            onChanged();
            getTask(token, taskId).then(setTask);
          }
        });
        wsRef.current = ws;
      } else {
        const history = await getTaskEvents(token, taskId);
        if (!cancelled) {
          setEvents(
            history.map((e) => ({ type: "event", event_type: e.event_type, sequence: e.sequence, payload: e.payload }))
          );
        }
      }
    }

    setEvents([]);
    load();

    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  async function handleApproval(decision: "approved" | "rejected") {
    await submitApproval(token, taskId, decision);
    onChanged();
    setTask(await getTask(token, taskId));
  }

  if (!task) return <p>加载中...</p>;

  return (
    <div>
      <h3>
        {task.title} <span className={`badge ${task.status}`}>{task.status}</span>
      </h3>
      <p style={{ color: "var(--muted)", fontSize: 13 }}>{task.instruction}</p>

      <div className="cost-board panel">
        <div className="cost-item">
          <div className="value">{task.steps_used}</div>
          <div className="label">步数 / {task.max_steps}</div>
        </div>
        <div className="cost-item">
          <div className="value">{task.tokens_used}</div>
          <div className="label">Token / {task.token_budget}</div>
        </div>
        <div className="cost-item">
          <div className="value">${task.cost_used_usd.toFixed(4)}</div>
          <div className="label">成本 / ${task.cost_budget_usd}</div>
        </div>
      </div>

      {task.status === "awaiting_approval" && (
        <div className="panel" style={{ borderColor: "var(--warn)" }}>
          <p>此任务包含高风险操作,需要人工审核后才能继续。</p>
          <button onClick={() => handleApproval("approved")} style={{ marginRight: 8 }}>
            批准
          </button>
          <button className="danger" onClick={() => handleApproval("rejected")}>
            拒绝
          </button>
        </div>
      )}

      {task.error_message && (
        <div className="panel" style={{ borderColor: "var(--danger)" }}>
          {task.error_message}
        </div>
      )}

      <h4>动作流 / 回放</h4>
      <div className="panel" style={{ maxHeight: 400, overflowY: "auto" }}>
        {events.length === 0 && <p style={{ color: "var(--muted)" }}>暂无事件</p>}
        {events.map((e, idx) => (
          <div key={idx} className="event-line">
            [{e.sequence ?? idx}] {e.event_type}: {JSON.stringify(e.payload)}
          </div>
        ))}
      </div>
    </div>
  );
}
