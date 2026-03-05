import type { Metadata } from "next";
import "./globals.css";
import ToastContainer from "@/components/ToastContainer";

export const metadata: Metadata = {
  title: "App Builder Local",
  description: "AI 에이전트 팀이 협업하여 앱을 만들어주는 로컬 플랫폼",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased">
        {children}
        <ToastContainer />
      </body>
    </html>
  );
}
