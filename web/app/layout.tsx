import "./globals.css";

export const metadata = {
  title: "AgentForge",
  description: "基于 OpenHands 的自有 AI Agent 平台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
