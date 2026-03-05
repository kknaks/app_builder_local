import { create } from "zustand";

export type AgentId = "pm" | "be" | "fe" | "pl" | "de";
export type AgentStatus = "active" | "idle" | "waiting" | "inactive" | "error";

export interface AgentInfo {
  id: AgentId;
  label: string;
  status: AgentStatus;
  unreadCount: number;
}

const INITIAL_AGENTS: AgentInfo[] = [
  { id: "pm", label: "PM", status: "inactive", unreadCount: 0 },
  { id: "be", label: "BE", status: "inactive", unreadCount: 0 },
  { id: "fe", label: "FE", status: "inactive", unreadCount: 0 },
  { id: "pl", label: "PL", status: "inactive", unreadCount: 0 },
  { id: "de", label: "DE", status: "inactive", unreadCount: 0 },
];

interface AgentState {
  agents: AgentInfo[];
  activeAgentId: AgentId;
  setActiveAgent: (id: AgentId) => void;
  setAgentStatus: (id: AgentId, status: AgentStatus) => void;
  incrementUnread: (id: AgentId) => void;
  clearUnread: (id: AgentId) => void;
  getAgent: (id: AgentId) => AgentInfo | undefined;
  resetAgents: () => void;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: INITIAL_AGENTS.map((a) => ({ ...a })),
  activeAgentId: "pm",

  setActiveAgent: (id) => {
    set({ activeAgentId: id });
    // Clear unread when switching to this agent
    const agents = get().agents.map((a) =>
      a.id === id ? { ...a, unreadCount: 0 } : a
    );
    set({ agents });
  },

  setAgentStatus: (id, status) => {
    const agents = get().agents.map((a) =>
      a.id === id ? { ...a, status } : a
    );
    set({ agents });
  },

  incrementUnread: (id) => {
    const { activeAgentId } = get();
    // Don't increment if this agent is currently active
    if (id === activeAgentId) return;
    const agents = get().agents.map((a) =>
      a.id === id ? { ...a, unreadCount: a.unreadCount + 1 } : a
    );
    set({ agents });
  },

  clearUnread: (id) => {
    const agents = get().agents.map((a) =>
      a.id === id ? { ...a, unreadCount: 0 } : a
    );
    set({ agents });
  },

  getAgent: (id) => get().agents.find((a) => a.id === id),

  resetAgents: () => {
    set({ agents: INITIAL_AGENTS.map((a) => ({ ...a })) });
  },
}));
