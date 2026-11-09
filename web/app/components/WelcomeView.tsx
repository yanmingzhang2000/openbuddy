/**
 * 欢迎视图组件
 *
 * 首次进入或没有选中任务时展示
 */

"use client";

import BrandLogo from "./BrandLogo";

const EXAMPLE_TASKS = [
  {
    icon: "🔍",
    title: "分析这个项目的部署方式",
    description: "了解 Docker Compose 配置和部署流程",
  },
  {
    icon: "📝",
    title: "整理一份开发文档",
    description: "生成 README 或 API 文档",
  },
  {
    icon: "🐛",
    title: "检查代码中的潜在问题",
    description: "识别安全风险、性能瓶颈或代码异味",
  },
  {
    icon: "✨",
    title: "帮我完成一个开发任务",
    description: "实现新功能、修复 Bug 或重构代码",
  },
] as const;

type Props = {
  onExampleClick: (text: string) => void;
};

export default function WelcomeView({ onExampleClick }: Props) {
  return (
    <div className="welcome-view">
      <div className="card" style={{ border: "none", background: "transparent" }}>
        <h2 className="welcome-title">今天想让 FrameMind 完成什么？</h2>
        <p className="welcome-subtitle">
          先确认目标与边界，再开始执行。FrameMind 会帮助你理清需求后再行动。
        </p>

        <div className="welcome-model-info">
          当前模型：Ollama · qwen2.5-coder:7b
        </div>

        <div className="example-cards">
          {EXAMPLE_TASKS.map((example) => (
            <button
              key={example.title}
              type="button"
              className="example-card"
              onClick={() => onExampleClick(example.title)}
            >
              <div className="example-card__icon" aria-hidden="true">
                {example.icon}
              </div>
              <div className="example-card__title">{example.title}</div>
              <div className="example-card__description">{example.description}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
