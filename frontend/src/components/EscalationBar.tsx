"use client";

import { useState, useCallback } from "react";

export interface Escalation {
  id: string;
  agent_id: string;
  message: string;
  type: "decision" | "error" | "info";
  timestamp: string;
  options?: string[];
}

interface EscalationBarProps {
  escalation: Escalation;
  onApprove?: (id: string, option?: string) => void;
  onReject?: (id: string) => void;
  onDismiss?: (id: string) => void;
}

const AGENT_COLORS: Record<string, string> = {
  pm: "text-purple-400",
  be: "text-green-400",
  fe: "text-blue-400",
  pl: "text-yellow-400",
  de: "text-pink-400",
};

const TYPE_CONFIG: Record<
  Escalation["type"],
  { icon: string; borderColor: string; bgColor: string }
> = {
  decision: {
    icon: "🤔",
    borderColor: "border-yellow-700/50",
    bgColor: "bg-yellow-900/20",
  },
  error: {
    icon: "🚨",
    borderColor: "border-red-700/50",
    bgColor: "bg-red-900/20",
  },
  info: {
    icon: "ℹ️",
    borderColor: "border-blue-700/50",
    bgColor: "bg-blue-900/20",
  },
};

export default function EscalationBar({
  escalation,
  onApprove,
  onReject,
  onDismiss,
}: EscalationBarProps) {
  const [loading, setLoading] = useState(false);
  const config = TYPE_CONFIG[escalation.type];
  const agentColor = AGENT_COLORS[escalation.agent_id] || "text-gray-400";

  const handleApprove = useCallback(
    async (option?: string) => {
      setLoading(true);
      try {
        onApprove?.(escalation.id, option);
      } finally {
        setLoading(false);
      }
    },
    [escalation.id, onApprove]
  );

  const handleReject = useCallback(async () => {
    setLoading(true);
    try {
      onReject?.(escalation.id);
    } finally {
      setLoading(false);
    }
  }, [escalation.id, onReject]);

  return (
    <div
      className={`border-b ${config.borderColor} ${config.bgColor} px-4 py-2.5 animate-in slide-in-from-top`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 min-w-0 flex-1">
          <span className="text-sm flex-shrink-0 mt-0.5">{config.icon}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs font-bold ${agentColor}`}>
                [{escalation.agent_id.toUpperCase()}]
              </span>
              <span className="text-[10px] text-gray-500">
                {new Date(escalation.timestamp).toLocaleTimeString("ko-KR", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>
            <p className="text-sm text-gray-200 leading-relaxed">
              {escalation.message}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {escalation.type === "decision" && (
            <>
              {escalation.options && escalation.options.length > 0 ? (
                escalation.options.map((option) => (
                  <button
                    key={option}
                    onClick={() => handleApprove(option)}
                    disabled={loading}
                    className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
                  >
                    {option}
                  </button>
                ))
              ) : (
                <>
                  <button
                    onClick={handleReject}
                    disabled={loading}
                    className="rounded-md border border-gray-600 bg-gray-700 px-3 py-1.5 text-xs font-medium text-gray-200 hover:bg-gray-600 disabled:opacity-50 transition"
                  >
                    거절
                  </button>
                  <button
                    onClick={() => handleApprove()}
                    disabled={loading}
                    className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50 transition"
                  >
                    승인
                  </button>
                </>
              )}
            </>
          )}

          {escalation.type === "error" && (
            <button
              onClick={() => handleApprove()}
              disabled={loading}
              className="rounded-md bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-500 disabled:opacity-50 transition"
            >
              확인
            </button>
          )}

          {/* Dismiss button */}
          <button
            onClick={() => onDismiss?.(escalation.id)}
            className="rounded p-1 text-gray-500 hover:text-gray-300 transition"
            title="닫기"
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
