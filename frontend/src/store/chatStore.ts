import { create } from "zustand";
import type { AgentId } from "./agentStore";

export interface ChatMessage {
  id: string;
  agentId: AgentId;
  role: "user" | "agent" | "system";
  content: string;
  timestamp: string;
}

interface AgentChatState {
  messages: ChatMessage[];
  scrollPosition: number;
}

interface ChatState {
  /** Per-agent chat state keyed by agentId */
  chats: Record<AgentId, AgentChatState>;
  /** Add a message to a specific agent's chat */
  addMessage: (agentId: AgentId, message: ChatMessage) => void;
  /** Set all messages for an agent (e.g., history load) */
  setMessages: (agentId: AgentId, messages: ChatMessage[]) => void;
  /** Save scroll position when switching tabs */
  saveScrollPosition: (agentId: AgentId, position: number) => void;
  /** Get scroll position for an agent */
  getScrollPosition: (agentId: AgentId) => number;
  /** Clear all chats */
  clearAllChats: () => void;
  /** Clear chat for a specific agent */
  clearChat: (agentId: AgentId) => void;
}

const createEmptyChat = (): AgentChatState => ({
  messages: [],
  scrollPosition: 0,
});

const createInitialChats = (): Record<AgentId, AgentChatState> => ({
  pm: createEmptyChat(),
  be: createEmptyChat(),
  fe: createEmptyChat(),
  pl: createEmptyChat(),
  de: createEmptyChat(),
});

export const useChatStore = create<ChatState>((set, get) => ({
  chats: createInitialChats(),

  addMessage: (agentId, message) => {
    const chats = { ...get().chats };
    const agentChat = chats[agentId];
    chats[agentId] = {
      ...agentChat,
      messages: [...agentChat.messages, message],
    };
    set({ chats });
  },

  setMessages: (agentId, messages) => {
    const chats = { ...get().chats };
    chats[agentId] = {
      ...chats[agentId],
      messages,
    };
    set({ chats });
  },

  saveScrollPosition: (agentId, position) => {
    const chats = { ...get().chats };
    chats[agentId] = {
      ...chats[agentId],
      scrollPosition: position,
    };
    set({ chats });
  },

  getScrollPosition: (agentId) => {
    return get().chats[agentId].scrollPosition;
  },

  clearAllChats: () => {
    set({ chats: createInitialChats() });
  },

  clearChat: (agentId) => {
    const chats = { ...get().chats };
    chats[agentId] = createEmptyChat();
    set({ chats });
  },
}));
