/**
 * 状态文案和辅助函数
 *
 * 将内部状态映射为用户友好的中文文案
 */

export const STATUS_LABELS: Record<string, string> = {
  queued: "等待执行",
  running: "正在执行",
  recovering: "正在恢复",
  awaiting_approval: "等待确认",
  awaiting_confirmation: "等待确认",
  awaiting_intent_approval: "等待意图确认",
  awaiting_manual_contract: "等待人工处理",
  clarifying: "正在理解需求",
  awaiting_clarification: "等待澄清问题",
  completed: "已完成",
  failed: "执行失败",
  timeout: "执行超时",
  budget_exceeded: "超出预算",
  max_steps_exceeded: "超出步数限制",
  cancelled: "已取消",
};

export function getStatusLabel(status: string): string {
  return STATUS_LABELS[status] || status;
}

export function isRunningStatus(status: string): boolean {
  return [
    "queued",
    "running",
    "recovering",
    "clarifying",
    "awaiting_clarification",
    "awaiting_intent_approval",
    "awaiting_manual_contract",
  ].includes(status);
}

export function isWaitingApproval(status: string): boolean {
  return [
    "awaiting_approval",
    "awaiting_confirmation",
    "awaiting_intent_approval",
  ].includes(status);
}

export function isFinishedStatus(status: string): boolean {
  return [
    "completed",
    "failed",
    "timeout",
    "budget_exceeded",
    "max_steps_exceeded",
    "cancelled",
  ].includes(status);
}

/**
 * 事件类型摘要映射
 */
export const EVENT_SUMMARIES: Record<string, string> = {
  action: "执行动作",
  observation: "获取结果",
  message: "消息",
  error: "错误",
  delegate: "委托执行",
  delegate_output: "委托结果",
  condensation: "信息压缩",
  summary: "摘要",
};

export function getEventSummary(eventType: string): string {
  return EVENT_SUMMARIES[eventType] || eventType;
}
