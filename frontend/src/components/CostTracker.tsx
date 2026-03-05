"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useProjectStore } from "@/store/projectStore";
import { getProjectCost, type ProjectCost, type AgentCost } from "@/lib/api";

const AGENT_COLORS: Record<string, string> = {
  pm: "text-purple-400",
  be: "text-green-400",
  fe: "text-blue-400",
  pl: "text-yellow-400",
  de: "text-pink-400",
};

function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return tokens.toString();
}

export default function CostTracker() {
  const selectedId = useProjectStore((s) => s.selectedId);
  const [cost, setCost] = useState<ProjectCost | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);
  const [error, setError] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchCost = useCallback(async () => {
    if (!selectedId) {
      setCost(null);
      return;
    }
    try {
      const data = await getProjectCost(selectedId);
      setCost(data);
      setError(false);
    } catch {
      setError(true);
    }
  }, [selectedId]);

  // Poll every 10 seconds
  useEffect(() => {
    fetchCost();

    intervalRef.current = setInterval(fetchCost, 10_000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchCost]);

  if (!selectedId) return null;

  return (
    <div
      className="relative"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Main cost display */}
      <div className="flex cursor-default items-center gap-2 rounded-md bg-gray-800 px-3 py-1.5 text-xs">
        <svg
          className="h-3.5 w-3.5 text-green-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        {error ? (
          <span className="text-gray-500">--</span>
        ) : cost ? (
          <>
            <span className="font-mono text-white">
              {formatCost(cost.total_cost)}
            </span>
            <span className="text-gray-500">
              ({formatTokens(cost.total_input_tokens + cost.total_output_tokens)} tokens)
            </span>
          </>
        ) : (
          <span className="text-gray-500">로딩중...</span>
        )}
      </div>

      {/* Tooltip with per-agent breakdown */}
      {showTooltip && cost && cost.by_agent.length > 0 && (
        <div className="absolute right-0 top-full z-50 mt-2 w-64 rounded-lg bg-gray-800 p-3 shadow-xl border border-gray-700">
          <h4 className="mb-2 text-xs font-bold text-gray-300">
            에이전트별 비용
          </h4>
          <div className="space-y-1.5">
            {cost.by_agent.map((agent: AgentCost) => (
              <div
                key={agent.agent_id}
                className="flex items-center justify-between text-xs"
              >
                <span
                  className={`font-bold ${
                    AGENT_COLORS[agent.agent_id] || "text-gray-400"
                  }`}
                >
                  [{agent.agent_id.toUpperCase()}]
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-gray-500">
                    {formatTokens(agent.input_tokens + agent.output_tokens)}
                  </span>
                  <span className="font-mono text-white">
                    {formatCost(agent.total_cost)}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-2 border-t border-gray-700 pt-2 flex justify-between text-xs">
            <span className="font-bold text-gray-300">합계</span>
            <span className="font-mono text-white">
              {formatCost(cost.total_cost)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
