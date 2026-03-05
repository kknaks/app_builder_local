"use client";

import { useEffect, useState } from "react";
import {
  Group,
  Panel,
  Separator,
} from "react-resizable-panels";
import ProjectListPanel from "@/components/ProjectListPanel";
import DashboardPanel from "@/components/DashboardPanel";
import ChatLogPanel from "@/components/ChatLogPanel";
import TokenModal from "@/components/TokenModal";
import CostTracker from "@/components/CostTracker";
import { getTokenStatus } from "@/lib/api";

export default function Home() {
  const [showTokenModal, setShowTokenModal] = useState(false);

  // Check token on mount
  useEffect(() => {
    getTokenStatus()
      .then((status) => {
        if (!status.configured) {
          setShowTokenModal(true);
        }
      })
      .catch(() => {
        // API not reachable — show modal anyway for first-time setup
        setShowTokenModal(true);
      });
  }, []);

  return (
    <div className="flex h-screen flex-col bg-gray-950">
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

      {/* Main panels */}
      <div className="flex-1 overflow-hidden">
        <Group orientation="horizontal" className="h-full">
          {/* Left Panel: Project List (20%) */}
          <Panel id="left" defaultSize={20} minSize={15} maxSize={35}>
            <ProjectListPanel />
          </Panel>

          <Separator className="w-1 bg-gray-700 hover:bg-blue-500 transition-colors" />

          {/* Center Panel: Dashboard (50%) */}
          <Panel id="center" defaultSize={50} minSize={30}>
            <DashboardPanel />
          </Panel>

          <Separator className="w-1 bg-gray-700 hover:bg-blue-500 transition-colors" />

          {/* Right Panel: Chat + Log (30%) */}
          <Panel id="right" defaultSize={30} minSize={20} maxSize={45}>
            <ChatLogPanel />
          </Panel>
        </Group>
      </div>

      <TokenModal
        open={showTokenModal}
        onClose={() => setShowTokenModal(false)}
      />
    </div>
  );
}
