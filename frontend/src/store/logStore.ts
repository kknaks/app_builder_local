import { create } from "zustand";
import type { AgentId } from "./agentStore";

export interface LogEntry {
  id: string;
  agentId: AgentId;
  level: "info" | "warn" | "error" | "debug";
  message: string;
  timestamp: string;
}

const MAX_LOG_BUFFER = 1000;

interface LogState {
  /** All log entries (max 1000) */
  logs: LogEntry[];
  /** Agent filter state — which agents are visible */
  filters: Record<AgentId, boolean>;
  /** Add a log entry (auto-trims to MAX_LOG_BUFFER) */
  addLog: (entry: LogEntry) => void;
  /** Add multiple log entries */
  addLogs: (entries: LogEntry[]) => void;
  /** Toggle agent filter */
  toggleFilter: (agentId: AgentId) => void;
  /** Set specific filter */
  setFilter: (agentId: AgentId, enabled: boolean) => void;
  /** Get filtered logs */
  getFilteredLogs: () => LogEntry[];
  /** Clear all logs */
  clearLogs: () => void;
  /** Auto-scroll enabled */
  autoScroll: boolean;
  /** Toggle auto-scroll */
  setAutoScroll: (enabled: boolean) => void;
}

export const useLogStore = create<LogState>((set, get) => ({
  logs: [],
  filters: {
    pm: true,
    be: true,
    fe: true,
    pl: true,
    de: true,
  },
  autoScroll: true,

  addLog: (entry) => {
    const logs = [...get().logs, entry];
    // Trim to max buffer
    if (logs.length > MAX_LOG_BUFFER) {
      logs.splice(0, logs.length - MAX_LOG_BUFFER);
    }
    set({ logs });
  },

  addLogs: (entries) => {
    const logs = [...get().logs, ...entries];
    if (logs.length > MAX_LOG_BUFFER) {
      logs.splice(0, logs.length - MAX_LOG_BUFFER);
    }
    set({ logs });
  },

  toggleFilter: (agentId) => {
    const filters = { ...get().filters };
    filters[agentId] = !filters[agentId];
    set({ filters });
  },

  setFilter: (agentId, enabled) => {
    const filters = { ...get().filters };
    filters[agentId] = enabled;
    set({ filters });
  },

  getFilteredLogs: () => {
    const { logs, filters } = get();
    return logs.filter((log) => filters[log.agentId]);
  },

  clearLogs: () => set({ logs: [] }),

  setAutoScroll: (enabled) => set({ autoScroll: enabled }),
}));
