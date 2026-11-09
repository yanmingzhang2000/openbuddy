/**
 * 主对话工作区组件
 *
 * 包含欢迎页、用户消息、任务状态和输入区
 */

"use client";

import { useEffect, useRef, useState } from "react";
import type { Task, TaskEvent } from "../lib/api";
import { isWaitingApproval, isFinishedStatus, isRunningStatus } from "../lib/status-helpers";
import WelcomeView from "./WelcomeView";
import Composer from "./Composer";
import UserMessage from "./UserMessage";
import TaskStatusCard from "./TaskStatusCard";
import ApprovalCard from "./ApprovalCard";
import ErrorCard from "./ErrorCard";
import ExecutionPanel from "./ExecutionPanel";

type Props = {
  token: string;
  selectedTask: Task | null;
  events: TaskEvent[];
  onOpenExecutionPanel: () => void;
  onCreateTask: (instruction: string) => void;
  onSubmitApproval: (taskId: string, decision: "approved" | "rejected") => void;
  isCreatingTask: boolean;
  createError: string | null;
};

export default function ConversationWorkspace({
  token,
  selectedTask,
  events,
  onOpenExecutionPanel,
  onCreateTask,
  onSubmitApproval,
  isCreatingTask,
  createError,
}: Props) {
  const conversationRef = useRef<HTMLDivElement>(null);
  const [showExecutionPanel, setShowExecutionPanel] = useState(false);

  // 任务完成后自动关闭执行面板
  useEffect(() => {
    if (selectedTask && isFinishedStatus(selectedTask.status)) {
      // 可以选择保持打开或关闭
    }
  }, [selectedTask?.status]);

  function handleExampleClick(text: string) {
    onCreateTask(text);
  }

  function handleComposerSubmit(text: string) {
    onCreateTask(text);
  }

  function handleRetry() {
    if (selectedTask) {
      onCreateTask(selectedTask.instruction);
    }
  }

  function handleNewTask() {
    // 清空选中，回到欢迎页
    onCreateTask("");
  }

  return (
    <div className="main-workspace">
      {/* 头部 */}
      <header className="workspace-header">
        <div className="workspace-header-left">
          <button
            type="button"
            className="mobile-menu-button ghost"
            aria-label="打开菜单"
            // 移动端菜单逻辑由父组件处理
          >
            ☰
          </button>
          {selectedTask ? (
            <h1 className="workspace-title">{selectedTask.title}</h1>
          ) : (
            <h1 className="workspace-title">FrameMind</h1>
          )}
        </div>
        {selectedTask && (
          <button
            type="button"
            className="secondary"
            onClick={() => setShowExecutionPanel(true)}
          >
            执行详情
          </button>
        )}
      </header>

      {/* 对话区域 */}
      <div ref={conversationRef} className="conversation-area">
        {/* 欢迎页 */}
        {!selectedTask && (
          <WelcomeView onExampleClick={handleExampleClick} />
        )}

        {/* 用户消息 */}
        {selectedTask && (
          <UserMessage instruction={selectedTask.instruction} />
        )}

        {/* 审批卡 */}
        {selectedTask && isWaitingApproval(selectedTask.status) && (
          <ApprovalCard
            taskId={selectedTask.id}
            onApprove={(taskId) => onSubmitApproval(taskId, "approved")}
            onReject={(taskId) => onSubmitApproval(taskId, "rejected")}
          />
        )}

        {/* 错误卡 */}
        {selectedTask && selectedTask.status === "failed" && selectedTask.error_message && (
          <ErrorCard
            errorMessage={selectedTask.error_message}
            onRetry={handleRetry}
            onNewTask={handleNewTask}
          />
        )}

        {/* 其他失败状态 */}
        {selectedTask && (
          selectedTask.status === "timeout" ||
          selectedTask.status === "budget_exceeded" ||
          selectedTask.status === "max_steps_exceeded"
        ) && (
          <ErrorCard
            errorMessage={`任务因 ${selectedTask.status} 而终止`}
            onNewTask={handleNewTask}
          />
        )}

        {/* 任务状态卡 */}
        {selectedTask && !isWaitingApproval(selectedTask.status) && selectedTask.status !== "failed" && !(
          selectedTask.status === "timeout" ||
          selectedTask.status === "budget_exceeded" ||
          selectedTask.status === "max_steps_exceeded"
        ) && (
          <TaskStatusCard
            task={selectedTask}
            events={events}
            onOpenExecutionPanel={() => setShowExecutionPanel(true)}
          />
        )}

        {/* 创建任务错误 */}
        {createError && (
          <div className="error-card" role="alert">
            <div className="error-card__title">创建任务失败</div>
            <div className="error-card__message">{createError}</div>
          </div>
        )}
      </div>

      {/* 输入区 */}
      <Composer
        onSubmit={handleComposerSubmit}
        disabled={isCreatingTask || (selectedTask !== null && isRunningStatus(selectedTask.status))}
        placeholder={selectedTask ? "发送新消息将创建新任务" : "描述你想完成的事情..."}
      />

      {/* 执行详情面板 */}
      {selectedTask && (
        <ExecutionPanel
          task={selectedTask}
          events={events}
          isOpen={showExecutionPanel}
          onClose={() => setShowExecutionPanel(false)}
        />
      )}
    </div>
  );
}
