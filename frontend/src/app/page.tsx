"use client";

import { useEffect, useState } from "react";
import ProjectListPanel from "@/components/ProjectListPanel";
import DashboardPanel from "@/components/DashboardPanel";
import ChatLogPanel from "@/components/ChatLogPanel";
import TokenModal from "@/components/TokenModal";
import CostTracker from "@/components/CostTracker";
import NetworkErrorBanner from "@/components/NetworkErrorBanner";
import { getTokenStatus } from "@/lib/api";
import { toastWarning } from "@/store/toastStore";

export default function Home() {
  const [showTokenModal, setShowTokenModal] = useState(false);

  useEffect(() => {
    getTokenStatus()
      .then((status) => {
        if (!status.configured) {
          setShowTokenModal(true);
        }
      })
      .catch(() => {
        setShowTokenModal(true);
        toastWarning("백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.");
      });
  }, []);

  return (
    <div className="flex h-screen min-w-[1024px] flex-col bg-gray-950">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-bold text-white tracking-wide">
            🏗️ App Builder
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <CostTracker />
          <button
            onClick={() => setShowTokenModal(true)}
            className="rounded-md px-2.5 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-white transition"
            title="API 토큰 설정"
          >
            ⚙️ 설정
          </button>
        </div>
      </header>

      <NetworkErrorBanner />

      {/* Main panels */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel: Project List (20%) */}
        <div className="h-full overflow-hidden" style={{ width: "20%", minWidth: "200px" }}>
          <ProjectListPanel />
        </div>

        <div className="w-1 shrink-0 bg-gray-700" />

        {/* Center Panel: Dashboard (50%) */}
        <div className="h-full flex-1 overflow-hidden">
          <DashboardPanel />
        </div>

        <div className="w-1 shrink-0 bg-gray-700" />

        {/* Right Panel: Chat + Log (30%) */}
        <div className="h-full overflow-hidden" style={{ width: "30%", minWidth: "250px" }}>
          <ChatLogPanel />
        </div>
      </div>

      <TokenModal
        open={showTokenModal}
        onClose={() => setShowTokenModal(false)}
      />
    </div>
  );
}
