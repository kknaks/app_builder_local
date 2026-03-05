"use client";

import { useState } from "react";
import AgentTabBar from "./AgentTabBar";
import ChatPanel from "./ChatPanel";
import LogPanel from "./LogPanel";

export default function ChatLogPanel() {
  const [activeTab, setActiveTab] = useState<"chat" | "log">("chat");

  return (
    <div className="flex h-full flex-col bg-gray-900 text-white">
      {/* Tab bar: Chat / Log */}
      <div className="flex border-b border-gray-700">
        <button
          onClick={() => setActiveTab("chat")}
          className={`flex-1 px-4 py-2 text-sm font-medium transition ${
            activeTab === "chat"
              ? "border-b-2 border-blue-500 text-white"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          채팅
        </button>
        <button
          onClick={() => setActiveTab("log")}
          className={`flex-1 px-4 py-2 text-sm font-medium transition ${
            activeTab === "log"
              ? "border-b-2 border-blue-500 text-white"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          로그
        </button>
      </div>

      {activeTab === "chat" ? (
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Agent tab bar */}
          <AgentTabBar />
          {/* Chat panel */}
          <ChatPanel />
        </div>
      ) : (
        <div className="flex flex-1 flex-col overflow-hidden">
          <LogPanel />
        </div>
      )}
    </div>
  );
}
