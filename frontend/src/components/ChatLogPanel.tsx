"use client";

import { useState, useCallback, useEffect } from "react";
import AgentTabBar from "./AgentTabBar";
import ChatPanel from "./ChatPanel";
import LogPanel from "./LogPanel";
import { useProjectStore } from "@/store/projectStore";
import { useFlowStore, type NodeStatus } from "@/store/flowStore";
import { useWebSocket } from "@/hooks/useWebSocket";

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:28888";

export default function ChatLogPanel() {
  const [activeTab, setActiveTab] = useState<"chat" | "log">("chat");
  const selectedId = useProjectStore((s) => s.selectedId);
  const updateNodeStatus = useFlowStore((s) => s.updateNodeStatus);
  const updateNode = useFlowStore((s) => s.updateNode);
  const addNode = useFlowStore((s) => s.addNode);
  const addEdge = useFlowStore((s) => s.addEdge);
  const setFlow = useFlowStore((s) => s.setFlow);

  // Separate WebSocket for flow updates
  const flowWsUrl = selectedId
    ? `${WS_BASE}/ws/projects/${selectedId}/flow`
    : null;

  const handleFlowMessage = useCallback(
    (data: unknown) => {
      const msg = data as {
        type?: string;
        node_id?: string;
        node_status?: string;
        node_retry_count?: number;
        node_error?: string;
        node_agent?: string;
        node?: {
          id: string;
          label: string;
          status: string;
          agent?: string;
          retry_count?: number;
          error_message?: string;
        };
        edge?: { id: string; source: string; target: string };
        nodes?: {
          id: string;
          label: string;
          status: string;
          agent?: string;
          retry_count?: number;
          error_message?: string;
        }[];
        edges?: { id: string; source: string; target: string }[];
      };

      if (msg.type === "flow_update" && msg.node_id) {
        // Update with partial node data (status, retry, error)
        const patch: Record<string, unknown> = {};
        if (msg.node_status) patch.status = msg.node_status;
        if (msg.node_retry_count !== undefined) patch.retry_count = msg.node_retry_count;
        if (msg.node_error !== undefined) patch.error_message = msg.node_error;
        if (msg.node_agent) patch.agent = msg.node_agent;

        if (msg.node_status && Object.keys(patch).length === 1) {
          updateNodeStatus(msg.node_id, msg.node_status as NodeStatus);
        } else {
          updateNode(msg.node_id, patch);
        }
      } else if (msg.type === "flow_node_add" && msg.node) {
        addNode({
          id: msg.node.id,
          label: msg.node.label,
          status: msg.node.status as NodeStatus,
          agent: msg.node.agent,
          retry_count: msg.node.retry_count,
          error_message: msg.node.error_message,
        });
      } else if (msg.type === "flow_edge_add" && msg.edge) {
        addEdge(msg.edge);
      } else if (msg.type === "flow_full" && msg.nodes && msg.edges) {
        setFlow(
          msg.nodes.map((n) => ({
            id: n.id,
            label: n.label,
            status: n.status as NodeStatus,
            agent: n.agent,
            retry_count: n.retry_count,
            error_message: n.error_message,
          })),
          msg.edges
        );
      }
    },
    [updateNodeStatus, updateNode, addNode, addEdge, setFlow]
  );

  useWebSocket({
    url: flowWsUrl,
    onMessage: handleFlowMessage,
    enabled: !!selectedId,
  });

  // Refresh project list periodically to sync status
  const fetchProjects = useProjectStore((s) => s.fetchProjects);
  useEffect(() => {
    if (!selectedId) return;
    const interval = setInterval(fetchProjects, 5000);
    return () => clearInterval(interval);
  }, [selectedId, fetchProjects]);

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
