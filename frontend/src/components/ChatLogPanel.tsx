"use client";

import { useState } from "react";

const AGENTS = [
  { id: "pm", label: "PM", color: "text-purple-400" },
  { id: "be", label: "BE", color: "text-green-400" },
  { id: "fe", label: "FE", color: "text-blue-400" },
  { id: "pl", label: "PL", color: "text-yellow-400" },
  { id: "de", label: "DE", color: "text-pink-400" },
];

export default function ChatLogPanel() {
  const [activeTab, setActiveTab] = useState<"chat" | "log">("chat");
  const [selectedAgent, setSelectedAgent] = useState("pm");
  const [message, setMessage] = useState("");

  return (
    <div className="flex h-full flex-col bg-gray-900 text-white">
      {/* Tab bar */}
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
        <>
          {/* Agent tabs */}
          <div className="flex gap-1 border-b border-gray-800 px-2 py-1.5">
            {AGENTS.map((agent) => (
              <button
                key={agent.id}
                onClick={() => setSelectedAgent(agent.id)}
                className={`rounded-md px-2.5 py-1 text-xs font-bold transition ${
                  selectedAgent === agent.id
                    ? `bg-gray-700 ${agent.color}`
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {agent.label}
              </button>
            ))}
          </div>

          {/* Chat messages */}
          <div className="flex-1 overflow-y-auto p-4">
            <p className="text-center text-sm text-gray-600">
              에이전트 채팅은 Sprint 3에서 구현됩니다.
            </p>
          </div>

          {/* Input */}
          <div className="border-t border-gray-700 p-3">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="메시지를 입력하세요..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="flex-1 rounded-lg border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
              <button
                disabled={!message.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition"
              >
                전송
              </button>
            </div>
          </div>
        </>
      ) : (
        /* Log panel placeholder */
        <div className="flex-1 overflow-y-auto p-4">
          <p className="text-center text-sm text-gray-600">
            실시간 로그는 Sprint 3에서 구현됩니다.
          </p>
        </div>
      )}
    </div>
  );
}
