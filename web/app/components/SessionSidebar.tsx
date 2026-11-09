/**
 * 会话侧边栏组件
 *
 * 显示品牌 Logo、新建任务按钮和会话历史列表
 */

"use client";

import { useMemo } from "react";
import BrandLogo from "./BrandLogo";
import type { Task } from "../lib/api";
import { getStatusLabel } from "../lib/status-helpers";

type Props = {
  tasks: Task[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
  onNewTask: () => void;
};

function groupTasksByDate(tasks: Task[]): { label: string; tasks: Task[] }[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const lastWeek = new Date(today);
  lastWeek.setDate(lastWeek.getDate() - 7);

  const groups: { label: string; tasks: Task[] }[] = [];
  const todayTasks: Task[] = [];
  const yesterdayTasks: Task[] = [];
  const thisWeekTasks: Task[] = [];
  const olderTasks: Task[] = [];

  for (const task of tasks) {
    const taskDate = new Date(task.created_at);
    if (taskDate >= today) {
      todayTasks.push(task);
    } else if (taskDate >= yesterday) {
      yesterdayTasks.push(task);
    } else if (taskDate >= lastWeek) {
      thisWeekTasks.push(task);
    } else {
      olderTasks.push(task);
    }
  }

  if (todayTasks.length > 0) {
    groups.push({ label: "今天", tasks: todayTasks });
  }
  if (yesterdayTasks.length > 0) {
    groups.push({ label: "昨天", tasks: yesterdayTasks });
  }
  if (thisWeekTasks.length > 0) {
    groups.push({ label: "本周", tasks: thisWeekTasks });
  }
  if (olderTasks.length > 0) {
    groups.push({ label: "更早", tasks: olderTasks });
  }

  return groups;
}

export default function SessionSidebar({
  tasks,
  selectedTaskId,
  onSelectTask,
  onNewTask,
}: Props) {
  const groupedTasks = useMemo(() => groupTasksByDate(tasks), [tasks]);

  return (
    <aside className="session-sidebar" aria-label="会话列表">
      <div className="session-sidebar-header">
        <BrandLogo size="small" />
        <button
          type="button"
          className="session-new-button secondary"
          onClick={onNewTask}
        >
          + 新建任务
        </button>
      </div>

      <div className="session-list">
        {groupedTasks.length === 0 && (
          <div className="empty-state">
            <div className="empty-state__message">暂无任务</div>
            <div className="empty-state__hint">创建第一个任务开始使用</div>
          </div>
        )}

        {groupedTasks.map((group) => (
          <div key={group.label}>
            <div className="session-group-title">{group.label}</div>
            {group.tasks.map((task) => {
              const isSelected = selectedTaskId === task.id;
              return (
                <button
                  key={task.id}
                  type="button"
                  className={`session-item${isSelected ? " is-selected" : ""}`}
                  aria-pressed={isSelected}
                  onClick={() => onSelectTask(task.id)}
                >
                  <span className="session-item__title">{task.title}</span>
                  <span className={`badge ${task.status}`}>
                    {getStatusLabel(task.status)}
                  </span>
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </aside>
  );
}
