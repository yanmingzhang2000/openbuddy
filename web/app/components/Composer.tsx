/**
 * 输入组件
 *
 * 底部自由文本输入框，支持多行输入和 IME 组合输入
 */

"use client";

import { useState, useRef, useEffect, type KeyboardEvent, type FormEvent } from "react";

type Props = {
  onSubmit: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
};

export default function Composer({
  onSubmit,
  disabled = false,
  placeholder = "描述你想完成的事情...",
}: Props) {
  const [text, setText] = useState("");
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动调整高度
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    const newHeight = Math.min(textarea.scrollHeight, 200);
    textarea.style.height = `${newHeight}px`;
  }, [text]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // IME 组合输入期间不发送
    if (isComposing) return;

    // Enter 发送，Shift+Enter 换行
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;

    onSubmit(trimmed);
    setText("");

    // 重置高度
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleFormSubmit(event: FormEvent) {
    event.preventDefault();
    handleSubmit();
  }

  return (
    <div className="composer-area">
      <form className="composer-wrapper" onSubmit={handleFormSubmit}>
        <textarea
          ref={textareaRef}
          className="composer-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          aria-label="任务输入"
        />

        <div className="composer-footer">
          <span className="composer-hint">Enter 发送，Shift+Enter 换行</span>
          <button
            type="submit"
            className="composer-send-button"
            disabled={disabled || !text.trim()}
          >
            发送
          </button>
        </div>
      </form>
    </div>
  );
}
