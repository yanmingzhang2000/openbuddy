/**
 * 用户消息组件
 *
 * 显示用户的任务请求
 */

type Props = {
  instruction: string;
};

export default function UserMessage({ instruction }: Props) {
  return (
    <div className="message-card user-message">
      <div className="message-label">你的请求</div>
      <div className="message-content">{instruction}</div>
    </div>
  );
}
