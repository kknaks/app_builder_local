"use client";

import { useAgentStore, type AgentStatus } from "@/store/agentStore";

const STATUS_COLORS: Record<AgentStatus, { dot: string; text: string }> = {
  active: { dot: "bg-green-400", text: "text-green-400" },
  idle: { dot: "bg-blue-400", text: "text-blue-400" },
  waiting: { dot: "bg-yellow-400", text: "text-yellow-400" },
  inactive: { dot: "bg-gray-500", text: "text-gray-400" },
  error: { dot: "bg-red-400", text: "text-red-400" },
};

export default function AgentTabBar() {
  const agents = useAgentStore((s) => s.agents);
  const activeAgentId = useAgentStore((s) => s.activeAgentId);
  const setActiveAgent = useAgentStore((s) => s.setActiveAgent);

  return (
    <div className="flex items-center gap-1 border-b border-gray-800 px-2 py-1.5">
      {agents.map((agent) => {
        const isActive = activeAgentId === agent.id;
        const colors = STATUS_COLORS[agent.status];
        return (
          <button
            key={agent.id}
            onClick={() => setActiveAgent(agent.id)}
            className={`relative flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-bold transition ${
              isActive
                ? `bg-gray-700 ${colors.text}`
                : "text-gray-500 hover:bg-gray-800 hover:text-gray-300"
            }`}
          >
            {/* Status dot */}
            <span
              className={`inline-block h-2 w-2 rounded-full ${colors.dot}`}
            />
            {agent.label}

            {/* Unread badge */}
            {agent.unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                {agent.unreadCount > 99 ? "99+" : agent.unreadCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
