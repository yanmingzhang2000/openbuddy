"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  login,
  signup,
  listTasks,
  createTask,
  getTask,
  getTaskEvents,
  openTaskEventsSocket,
  submitApproval,
  Task,
  TaskEvent,
} from "./lib/api";
import { getAuthToken, setAuthToken, removeAuthToken } from "./lib/auth";
import { isRunningStatus } from "./lib/status-helpers";
import AuthView from "./components/AuthView";
import SessionSidebar from "./components/SessionSidebar";
import ConversationWorkspace from "./components/ConversationWorkspace";

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // 初始化 token
  useEffect(() => {
    const saved = getAuthToken();
    if (saved) setToken(saved);
  }, []);

  // 刷新任务列表
  const refreshTasks = useCallback(async () => {
    if (!token) return;
    try {
      const taskList = await listTasks(token);
      setTasks(taskList);
    } catch (e) {
      console.error("Failed to refresh tasks:", e);
    }
  }, [token]);

  // 定期刷新任务列表
  useEffect(() => {
    if (!token) return;
    refreshTasks();
    const interval = setInterval(refreshTasks, 5000);
    return () => clearInterval(interval);
  }, [token, refreshTasks]);

  // 加载选中的任务详情和事件
  useEffect(() => {
    if (!token || !selectedTaskId) {
      setSelectedTask(null);
      setEvents([]);
      return;
    }

    let cancelled = false;

    async function loadTask() {
      try {
        const task = await getTask(token, selectedTaskId);
        if (cancelled) return;
        setSelectedTask(task);

        // 运行中的任务使用 WebSocket，已完成的任务拉取历史事件
        const isLive = isRunningStatus(task.status);
        if (isLive) {
          const ws = openTaskEventsSocket(token, selectedTaskId, (evt) => {
            if (evt.type === "event") {
              setEvents((prev) => [...prev, evt]);
            } else if (evt.type === "task_finished") {
              refreshTasks();
              getTask(token, selectedTaskId).then((updatedTask) => {
                if (!cancelled) setSelectedTask(updatedTask);
              });
            }
          });
          wsRef.current = ws;
        } else {
          const history = await getTaskEvents(token, selectedTaskId);
          if (!cancelled) {
            setEvents(
              history.map((e) => ({
                type: "event",
                event_type: e.event_type,
                sequence: e.sequence,
                payload: e.payload,
              }))
            );
          }
        }
      } catch (e) {
        console.error("Failed to load task:", e);
      }
    }

    setEvents([]);
    loadTask();

    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [token, selectedTaskId, refreshTasks]);

  // 认证成功
  function handleAuth(newToken: string) {
    setAuthToken(newToken);
    setToken(newToken);
  }

  // 登出
  function handleLogout() {
    removeAuthToken();
    setToken(null);
    setTasks([]);
    setSelectedTaskId(null);
    setSelectedTask(null);
    setEvents([]);
  }

  // 创建任务
  async function handleCreateTask(instruction: string) {
    if (!token || !instruction.trim() || isCreatingTask) return;

    setIsCreatingTask(true);
    setCreateError(null);

    try {
      // 自动生成标题
      const title = generateTaskTitle(instruction);
      const newTask = await createTask(token, title, instruction);
      
      // 刷新任务列表
      await refreshTasks();
      
      // 选中新任务
      setSelectedTaskId(newTask.id);
    } catch (e) {
      setCreateError(String(e));
    } finally {
      setIsCreatingTask(false);
    }
  }

  // 提交审批
  async function handleSubmitApproval(taskId: string, decision: "approved" | "rejected") {
    if (!token) return;
    try {
      await submitApproval(token, taskId, decision);
      await refreshTasks();
      const updatedTask = await getTask(token, taskId);
      setSelectedTask(updatedTask);
    } catch (e) {
      console.error("Failed to submit approval:", e);
    }
  }

  // 新建任务（清空选中）
  function handleNewTask() {
    setSelectedTaskId(null);
    setSelectedTask(null);
    setEvents([]);
    setIsMobileSidebarOpen(false);
  }

  // 未认证：显示认证页面
  if (!token) {
    return <AuthView onAuth={handleAuth} />;
  }

  // 已认证：显示工作台
  return (
    <div className="app-layout">
      {/* 移动端侧边栏遮罩 */}
      <div
        className={`mobile-sidebar-overlay${isMobileSidebarOpen ? " is-open" : ""}`}
        onClick={() => setIsMobileSidebarOpen(false)}
        aria-hidden="true"
      />

      {/* 移动端侧边栏 */}
      <div
        className={`mobile-sidebar${isMobileSidebarOpen ? " is-open" : ""}`}
        aria-label="会话列表"
      >
        <SessionSidebar
          tasks={tasks}
          selectedTaskId={selectedTaskId}
          onSelectTask={(id) => {
            setSelectedTaskId(id);
            setIsMobileSidebarOpen(false);
          }}
          onNewTask={handleNewTask}
        />
      </div>

      {/* 桌面端侧边栏 */}
      <SessionSidebar
        tasks={tasks}
        selectedTaskId={selectedTaskId}
        onSelectTask={setSelectedTaskId}
        onNewTask={handleNewTask}
      />

      {/* 主工作区 */}
      <ConversationWorkspace
        token={token}
        selectedTask={selectedTask}
        events={events}
        onOpenExecutionPanel={() => {}}
        onCreateTask={handleCreateTask}
        onSubmitApproval={handleSubmitApproval}
        isCreatingTask={isCreatingTask}
        createError={createError}
      />
    </div>
  );
}

/**
 * 自动生成任务标题
 * 1. 取第一行非空文本
 * 2. 最长 40 个字符
 * 3. 去掉多余空白
 * 4. 如果为空，使用"未命名任务"
 */
function generateTaskTitle(instruction: string): string {
  const lines = instruction.split("\n");
  const firstLine = lines.find((line) => line.trim().length > 0);
  if (!firstLine) return "未命名任务";

  const cleaned = firstLine.trim().replace(/\s+/g, " ");
  if (cleaned.length <= 40) return cleaned;

  return cleaned.slice(0, 37) + "...";
}
