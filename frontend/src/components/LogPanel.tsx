"use client";

import { useEffect, useCallback, useMemo } from "react";
import { List, useListRef, type RowComponentProps } from "react-window";
import { useLogStore, type LogEntry } from "@/store/logStore";
import { useProjectStore } from "@/store/projectStore";
import { useWebSocket, type WSStatus } from "@/hooks/useWebSocket";
import { getLogWsUrl } from "@/lib/api";
import type { AgentId } from "@/store/agentStore";

// ─── Agent tag colors ─────────────────────────────────────
const AGENT_COLORS: Record<AgentId, string> = {
  pm: "text-purple-400",
  be: "text-green-400",
  fe: "text-blue-400",
  pl: "text-yellow-400",
  de: "text-pink-400",
};

const AGENT_BG_COLORS: Record<AgentId, string> = {
  pm: "bg-purple-900/30",
  be: "bg-green-900/30",
  fe: "bg-blue-900/30",
  pl: "bg-yellow-900/30",
  de: "bg-pink-900/30",
};

const LEVEL_COLORS: Record<string, string> = {
  info: "text-gray-300",
  warn: "text-yellow-300",
  error: "text-red-400",
  debug: "text-gray-500",
};

// ─── Filter Checkbox ──────────────────────────────────────
const AGENTS: { id: AgentId; label: string }[] = [
  { id: "pm", label: "PM" },
  { id: "be", label: "BE" },
  { id: "fe", label: "FE" },
  { id: "pl", label: "PL" },
  { id: "de", label: "DE" },
];

interface LogRowProps {
  entries: LogEntry[];
}

function LogRow({
  index,
  style,
  entries,
}: RowComponentProps<LogRowProps>) {
  const entry = entries[index];
  if (!entry) return null;

  const agentColor = AGENT_COLORS[entry.agentId] || "text-gray-400";
  const agentBg = AGENT_BG_COLORS[entry.agentId] || "";
  const levelColor = LEVEL_COLORS[entry.level] || "text-gray-300";
  const time = new Date(entry.timestamp).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div
      style={style}
      className={`flex items-start gap-2 px-3 py-0.5 text-xs font-mono hover:bg-gray-800/50 ${agentBg}`}
    >
      <span className="flex-shrink-0 text-gray-600">{time}</span>
      <span className={`flex-shrink-0 font-bold ${agentColor}`}>
        [{entry.agentId.toUpperCase()}]
      </span>
      <span className={`flex-1 break-all ${levelColor}`}>
        {entry.message}
      </span>
    </div>
  );
}

function ConnectionBadge({ status }: { status: WSStatus }) {
  const config: Record<WSStatus, { color: string; label: string }> = {
    connecting: { color: "bg-yellow-400", label: "연결중" },
    connected: { color: "bg-green-400", label: "연결됨" },
    reconnecting: { color: "bg-orange-400", label: "재연결중" },
    disconnected: { color: "bg-gray-500", label: "연결 끊김" },
  };
  const { color, label } = config[status];
  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-400">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      {label}
    </div>
  );
}

export default function LogPanel() {
  const selectedId = useProjectStore((s) => s.selectedId);
  const addLog = useLogStore((s) => s.addLog);
  const filters = useLogStore((s) => s.filters);
  const toggleFilter = useLogStore((s) => s.toggleFilter);
  const autoScroll = useLogStore((s) => s.autoScroll);
  const setAutoScroll = useLogStore((s) => s.setAutoScroll);
  const clearLogs = useLogStore((s) => s.clearLogs);
  const logs = useLogStore((s) => s.logs);

  const listRef = useListRef(null);

  // Compute filtered logs
  const filteredLogs = useMemo(
    () => logs.filter((log) => filters[log.agentId]),
    [logs, filters]
  );

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && listRef.current && filteredLogs.length > 0) {
      listRef.current.scrollToRow({
        index: filteredLogs.length - 1,
        align: "end",
      });
    }
  }, [filteredLogs.length, autoScroll, listRef]);

  // WebSocket URL
  const wsUrl = selectedId ? getLogWsUrl(selectedId) : null;

  const handleMessage = useCallback(
    (data: unknown) => {
      const msg = data as {
        type?: string;
        id?: string;
        agent_id?: string;
        level?: string;
        message?: string;
        timestamp?: string;
      };

      if (msg.type === "log" && msg.message) {
        const entry: LogEntry = {
          id: msg.id || crypto.randomUUID(),
          agentId: (msg.agent_id || "pm") as AgentId,
          level: (msg.level as LogEntry["level"]) || "info",
          message: msg.message,
          timestamp: msg.timestamp || new Date().toISOString(),
        };
        addLog(entry);
      }
    },
    [addLog]
  );

  const { status } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    enabled: !!selectedId,
  });

  // Memoize rowProps to avoid unnecessary re-renders
  const rowProps = useMemo<LogRowProps>(
    () => ({ entries: filteredLogs }),
    [filteredLogs]
  );

  return (
    <div className="flex h-full flex-col">
      {/* Header with filters */}
      <div className="flex items-center justify-between border-b border-gray-800 px-3 py-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-400">필터:</span>
          {AGENTS.map((agent) => (
            <label
              key={agent.id}
              className="flex cursor-pointer items-center gap-1 text-xs"
            >
              <input
                type="checkbox"
                checked={filters[agent.id]}
                onChange={() => toggleFilter(agent.id)}
                className="h-3 w-3 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-0 accent-blue-500"
              />
              <span className={`font-bold ${AGENT_COLORS[agent.id]}`}>
                {agent.label}
              </span>
            </label>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-1 text-xs text-gray-400">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="h-3 w-3 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-0 accent-blue-500"
            />
            자동 스크롤
          </label>
          <button
            onClick={clearLogs}
            className="text-xs text-gray-500 hover:text-gray-300 transition"
          >
            초기화
          </button>
          <ConnectionBadge status={status} />
        </div>
      </div>

      {/* Virtual scrolled log list */}
      <div className="flex-1 overflow-hidden">
        {filteredLogs.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-gray-600">
              {selectedId ? "로그가 없습니다" : "프로젝트를 선택하세요"}
            </p>
          </div>
        ) : (
          <List
            listRef={listRef}
            rowComponent={LogRow}
            rowCount={filteredLogs.length}
            rowHeight={24}
            rowProps={rowProps}
            overscanCount={10}
            style={{ height: "100%" }}
          />
        )}
      </div>
    </div>
  );
}
