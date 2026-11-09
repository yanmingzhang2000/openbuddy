/**
 * 错误卡组件
 *
 * 任务失败时显示友好的错误信息
 */

"use client";

import { useState } from "react";

type Props = {
  errorMessage: string;
  onRetry?: () => void;
  onNewTask?: () => void;
};

export default function ErrorCard({ errorMessage, onRetry, onNewTask }: Props) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="error-card" role="alert" aria-live="polite">
      <div className="error-card__title">执行失败</div>
      <div className="error-card__message">
        任务执行过程中遇到问题。请检查任务描述是否清晰，或稍后重试。
      </div>

      <button
        type="button"
        className="ghost"
        onClick={() => setShowDetails(!showDetails)}
        aria-expanded={showDetails}
        style={{ marginTop: "0.5rem" }}
      >
        {showDetails ? "隐藏详细错误" : "查看详细错误"}
      </button>

      {showDetails && (
        <div className="error-card__details">{errorMessage}</div>
      )}

      <div className="error-card__actions">
        {onRetry && (
          <button type="button" onClick={onRetry}>
            重试任务
          </button>
        )}
        {onNewTask && (
          <button type="button" className="secondary" onClick={onNewTask}>
            创建新任务
          </button>
        )}
      </div>
    </div>
  );
}
