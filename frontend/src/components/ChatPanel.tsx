"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useAgentStore, type AgentId } from "@/store/agentStore";
import { useChatStore, type ChatMessage } from "@/store/chatStore";
import { useProjectStore } from "@/store/projectStore";
import { useFlowStore } from "@/store/flowStore";
import { useWebSocket, type WSStatus } from "@/hooks/useWebSocket";
import { getChatWsUrl } from "@/lib/api";
import ReviewCard, { type ReviewResult } from "./ReviewCard";
import ApprovalBar from "./ApprovalBar";
import PlanningActions, { type PlanPhase } from "./PlanningActions";
import ImplementationActions, {
  type ImplPhase,
} from "./ImplementationActions";
import EscalationBar, { type Escalation } from "./EscalationBar";
import ImplementationProgress from "./ImplementationProgress";
import RunPanel from "./RunPanel";

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });
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

export default function ChatPanel() {
  const selectedId = useProjectStore((s) => s.selectedId);
  const project = useProjectStore((s) =>
    s.projects.find((p) => p.id === s.selectedId)
  );
  const activeAgentId = useAgentStore((s) => s.activeAgentId);
  const addMessage = useChatStore((s) => s.addMessage);
  const setMessages = useChatStore((s) => s.setMessages);
  const saveScrollPosition = useChatStore((s) => s.saveScrollPosition);
  const messages = useChatStore((s) => s.chats[activeAgentId].messages);
  const savedScrollPosition = useChatStore(
    (s) => s.chats[activeAgentId].scrollPosition
  );
  const incrementUnread = useAgentStore((s) => s.incrementUnread);
  const setAgentStatus = useAgentStore((s) => s.setAgentStatus);
  const updateNodeStatus = useFlowStore((s) => s.updateNodeStatus);
  const updateNode = useFlowStore((s) => s.updateNode);

  const [input, setInput] = useState("");
  const [planPhase, setPlanPhase] = useState<PlanPhase>("idle");
  const [implPhase, setImplPhase] = useState<ImplPhase>("idle");
  const [reviewResults, setReviewResults] = useState<ReviewResult[]>([]);
  const [showApprovalBar, setShowApprovalBar] = useState(false);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const previousAgentRef = useRef<AgentId>(activeAgentId);
  const isInitialLoadRef = useRef(true);

  // Derive planning/implementation phase from project status
  useEffect(() => {
    if (!project) {
      setPlanPhase("idle");
      setImplPhase("idle");
      setShowApprovalBar(false);
      setReviewResults([]);
      return;
    }
    const status = project.status;

    // Planning phases
    if (status === "planning") setPlanPhase("planning");
    else if (status === "plan_complete") setPlanPhase("plan_complete");
    else if (status === "reviewing") setPlanPhase("reviewing");
    else if (status === "review_complete") {
      setPlanPhase("review_complete");
      setShowApprovalBar(true);
    } else if (status === "approved") {
      setPlanPhase("approved");
      setShowApprovalBar(false);
      setImplPhase("approved");
    } else {
      setPlanPhase("idle");
    }

    // Implementation phases
    if (status === "sprint_planning") {
      setImplPhase("sprint_planning");
      setPlanPhase("approved");
    } else if (status === "sprint_ready" || status === "sprint_complete") {
      setImplPhase("sprint_ready");
      setPlanPhase("approved");
    } else if (status === "implementing") {
      setImplPhase("implementing");
      setPlanPhase("approved");
    } else if (status === "testing") {
      setImplPhase("testing");
      setPlanPhase("approved");
    } else if (status === "completed") {
      setImplPhase("completed");
      setPlanPhase("approved");
    } else if (status === "failed") {
      setImplPhase("failed");
      setPlanPhase("approved");
    }
  }, [project]);

  // WebSocket URL
  const wsUrl = selectedId ? getChatWsUrl(selectedId) : null;

  const handleMessage = useCallback(
    (data: unknown) => {
      const msg = data as {
        type?: string;
        agent_id?: string;
        messages?: ChatMessage[];
        id?: string;
        role?: string;
        content?: string;
        timestamp?: string;
        status?: string;
        phase?: string;
        reviews?: ReviewResult[];
        node_id?: string;
        node_status?: string;
        node_retry_count?: number;
        node_error?: string;
        escalation?: Escalation;
        message?: string;
        escalation_type?: string;
        options?: string[];
      };

      if (msg.type === "history" && msg.messages) {
        const agentId = (msg.agent_id || activeAgentId) as AgentId;
        setMessages(agentId, msg.messages);
      } else if (msg.type === "message" && msg.content) {
        const agentId = (msg.agent_id || activeAgentId) as AgentId;
        const chatMessage: ChatMessage = {
          id: msg.id || crypto.randomUUID(),
          agentId,
          role: (msg.role as ChatMessage["role"]) || "agent",
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
        };
        addMessage(agentId, chatMessage);
        incrementUnread(agentId);
      } else if (msg.type === "agent_status" && msg.agent_id && msg.status) {
        setAgentStatus(
          msg.agent_id as AgentId,
          msg.status as "active" | "idle" | "error"
        );
      } else if (msg.type === "phase_update" && msg.phase) {
        // Phase updates from server (covers both planning and implementation)
        const phase = msg.phase;
        // Planning phases
        if (["planning", "plan_complete", "reviewing", "review_complete", "approved"].includes(phase)) {
          setPlanPhase(phase as PlanPhase);
          if (phase === "review_complete") setShowApprovalBar(true);
          if (phase === "approved") {
            setShowApprovalBar(false);
            setImplPhase("approved");
          }
        }
        // Implementation phases
        if (["sprint_planning", "sprint_ready", "implementing", "testing", "completed", "failed"].includes(phase)) {
          setImplPhase(phase as ImplPhase);
          setPlanPhase("approved");
        }
      } else if (msg.type === "review_results" && msg.reviews) {
        setReviewResults(msg.reviews);
        setShowApprovalBar(true);
        setPlanPhase("review_complete");
      } else if (msg.type === "flow_update" && msg.node_id) {
        // Flow node status update with optional retry/error info
        if (msg.node_status) {
          updateNode(msg.node_id, {
            status: msg.node_status as "pending" | "running" | "completed" | "failed",
            ...(msg.node_retry_count !== undefined && { retry_count: msg.node_retry_count }),
            ...(msg.node_error && { error_message: msg.node_error }),
          });
        }
      } else if (msg.type === "escalation") {
        // Escalation message from PM agent
        const escalation: Escalation = msg.escalation || {
          id: msg.id || crypto.randomUUID(),
          agent_id: msg.agent_id || "pm",
          message: msg.message || msg.content || "",
          type: (msg.escalation_type as Escalation["type"]) || "decision",
          timestamp: msg.timestamp || new Date().toISOString(),
          options: msg.options,
        };
        setEscalations((prev) => [escalation, ...prev]);
      }
    },
    [
      activeAgentId,
      addMessage,
      setMessages,
      incrementUnread,
      setAgentStatus,
      updateNode,
    ]
  );

  const { sendMessage, status } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    onOpen: () => {
      sendMessage({
        type: "switch_agent",
        agent_id: activeAgentId,
      });
    },
    enabled: !!selectedId,
  });

  // Notify server when switching agents
  useEffect(() => {
    if (previousAgentRef.current !== activeAgentId && status === "connected") {
      sendMessage({
        type: "switch_agent",
        agent_id: activeAgentId,
      });
    }
    previousAgentRef.current = activeAgentId;
  }, [activeAgentId, sendMessage, status]);

  // Save scroll position when switching agents
  useEffect(() => {
    const el = scrollContainerRef.current;
    return () => {
      if (el) {
        saveScrollPosition(previousAgentRef.current, el.scrollTop);
      }
    };
  }, [activeAgentId, saveScrollPosition]);

  // Restore scroll position when switching agents
  useEffect(() => {
    if (scrollContainerRef.current && !isInitialLoadRef.current) {
      scrollContainerRef.current.scrollTop = savedScrollPosition;
    }
    isInitialLoadRef.current = false;
  }, [activeAgentId, savedScrollPosition]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || status !== "connected") return;

    const message: ChatMessage = {
      id: crypto.randomUUID(),
      agentId: activeAgentId,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    addMessage(activeAgentId, message);
    sendMessage({
      type: "message",
      agent_id: activeAgentId,
      content: text,
    });
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleApprove = () => {
    setShowApprovalBar(false);
    setPlanPhase("approved");
    setImplPhase("approved");
    updateNodeStatus("plan-approve", "completed");
    setReviewResults([]);
  };

  const handleFeedback = () => {
    setShowApprovalBar(false);
    setPlanPhase("planning");
    updateNodeStatus("plan-review", "pending");
    updateNodeStatus("plan-detail", "running");
  };

  const handleEscalationApprove = useCallback(
    (id: string, option?: string) => {
      // Send approval response to server
      sendMessage({
        type: "escalation_response",
        escalation_id: id,
        action: "approve",
        option,
      });
      setEscalations((prev) => prev.filter((e) => e.id !== id));
    },
    [sendMessage]
  );

  const handleEscalationReject = useCallback(
    (id: string) => {
      sendMessage({
        type: "escalation_response",
        escalation_id: id,
        action: "reject",
      });
      setEscalations((prev) => prev.filter((e) => e.id !== id));
    },
    [sendMessage]
  );

  const handleEscalationDismiss = useCallback((id: string) => {
    setEscalations((prev) => prev.filter((e) => e.id !== id));
  }, []);

  if (!selectedId) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-gray-600">프로젝트를 선택하세요</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      {/* Planning action bar (only during planning phases) */}
      {planPhase !== "approved" && (
        <PlanningActions phase={planPhase} onPhaseChange={setPlanPhase} />
      )}

      {/* Implementation action bar (after planning approved) */}
      <ImplementationActions phase={implPhase} onPhaseChange={setImplPhase} />

      {/* Run panel (after implementation completed) */}
      <RunPanel visible={implPhase === "completed" || implPhase === "testing"} />

      {/* Approval bar (pinned at top when review is complete) */}
      {showApprovalBar && (
        <ApprovalBar onApprove={handleApprove} onFeedback={handleFeedback} />
      )}

      {/* Escalation bars (pinned at top) */}
      {escalations.map((esc) => (
        <EscalationBar
          key={esc.id}
          escalation={esc}
          onApprove={handleEscalationApprove}
          onReject={handleEscalationReject}
          onDismiss={handleEscalationDismiss}
        />
      ))}

      {/* Connection status */}
      <div className="flex items-center justify-end px-3 py-1">
        <ConnectionBadge status={status} />
      </div>

      {/* Messages area */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto px-4 py-2 space-y-3"
      >
        {/* Review results cards */}
        {reviewResults.length > 0 && (
          <div className="space-y-2 pb-3">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wide">
              📋 검토 결과
            </h4>
            {reviewResults.map((review) => (
              <ReviewCard key={review.agent_id} review={review} />
            ))}
          </div>
        )}

        {messages.length === 0 && reviewResults.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-600">
            {activeAgentId.toUpperCase()} 에이전트와 대화를 시작하세요
          </p>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : msg.role === "system"
                    ? "bg-gray-700 text-gray-300 italic"
                    : "bg-gray-800 text-gray-200"
                }`}
              >
                {msg.role === "agent" && (
                  <span className="mb-1 block text-xs font-bold text-blue-400">
                    [{msg.agentId.toUpperCase()}]
                  </span>
                )}
                <p className="whitespace-pre-wrap break-words">
                  {msg.content}
                </p>
                <span className="mt-1 block text-right text-[10px] opacity-50">
                  {formatTime(msg.timestamp)}
                </span>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Implementation progress (during implementing phase) */}
      {(implPhase === "implementing" || implPhase === "testing") && (
        <ImplementationProgress />
      )}

      {/* Input area */}
      <div className="border-t border-gray-700 p-3">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder={
              status === "connected"
                ? activeAgentId === "pm" && implPhase === "implementing"
                  ? '"현재 상황?" 으로 진행 상황 확인...'
                  : "메시지를 입력하세요..."
                : "연결 대기 중..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={status !== "connected"}
            className="flex-1 rounded-lg border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || status !== "connected"}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition"
          >
            전송
          </button>
        </div>
      </div>
    </div>
  );
}
