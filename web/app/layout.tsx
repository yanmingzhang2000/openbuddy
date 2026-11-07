import "./globals.css";

export const metadata = {
  title: "FrameMind",
  description: "An intent-first AI agent workspace that clarifies goals before taking action.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
