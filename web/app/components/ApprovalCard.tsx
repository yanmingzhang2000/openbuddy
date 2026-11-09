/**
 * 审批卡组件
 *
 * 当任务处于等待审批状态时显示
 */

"use client";

import { useState } from "react";

type Props = {
  taskId: string;
  onApprove: (taskId: string) => void;
  onReject: (taskId: string) => void;
};

export default function ApprovalCard({ taskId, onApprove, onReject }: Props) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(null);

  async function handleApprove() {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setDecision("approved");
    try {
      await onApprove(taskId);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReject() {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setDecision("rejected");
    try {
      await onReject(taskId);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="approval-card" role="alert" aria-live="polite">
      <div className="approval-card__title">需要人工确认</div>
      <div className="approval-card__message">
        此任务包含高风险操作，需要人工审核后才能继续执行。请仔细审查任务目标和预期结果后做出决定。
      </div>
      <div className="approval-card__actions">
        <button
          type="button"
          onClick={handleApprove}
          disabled={isSubmitting}
        >
          {isSubmitting && decision === "approved" ? "批准中..." : "批准执行"}
        </button>
        <button
          type="button"
          className="danger"
          onClick={handleReject}
          disabled={isSubmitting}
        >
          {isSubmitting && decision === "rejected" ? "拒绝中..." : "拒绝执行"}
        </button>
      </div>
    </div>
  );
}
