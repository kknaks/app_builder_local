"use client";

import { useState, useCallback } from "react";
import { useProjectStore } from "@/store/projectStore";
import { useFlowStore } from "@/store/flowStore";
import { startPlanning, startReview } from "@/lib/api";

type PlanPhase = "idle" | "planning" | "plan_complete" | "reviewing" | "review_complete" | "approved";

interface PlanningActionsProps {
  phase: PlanPhase;
  onPhaseChange?: (phase: PlanPhase) => void;
}

export default function PlanningActions({
  phase,
  onPhaseChange,
}: PlanningActionsProps) {
  const selectedId = useProjectStore((s) => s.selectedId);
  const updateNodeStatus = useFlowStore((s) => s.updateNodeStatus);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartPlanning = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    try {
      await startPlanning(selectedId);
      updateNodeStatus("plan-detail", "running");
      onPhaseChange?.("planning");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selectedId, updateNodeStatus, onPhaseChange]);

  const handleStartReview = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    try {
      await startReview(selectedId);
      updateNodeStatus("plan-review", "running");
      onPhaseChange?.("reviewing");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selectedId, updateNodeStatus, onPhaseChange]);

  if (!selectedId) return null;

  return (
    <div className="flex items-center gap-2 border-b border-gray-700 bg-gray-850 px-4 py-2">
      {(phase === "idle" || phase === "planning") && (
        <button
          onClick={handleStartPlanning}
          disabled={loading || phase === "planning"}
          className="flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50 transition"
        >
          {loading && phase !== "planning" ? (
            "시작중..."
          ) : phase === "planning" ? (
            <>
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-indigo-300" />
              기획 진행중...
            </>
          ) : (
            "📝 기획 시작"
          )}
        </button>
      )}

      {phase === "plan_complete" && (
        <button
          onClick={handleStartReview}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-500 disabled:opacity-50 transition"
        >
          {loading ? "시작중..." : "🔍 검토 시작"}
        </button>
      )}

      {phase === "reviewing" && (
        <div className="flex items-center gap-1.5 text-xs text-amber-300">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-400" />
          검토 진행중...
        </div>
      )}

      {phase === "approved" && (
        <div className="flex items-center gap-1.5 text-xs text-green-400">
          ✅ 기획 승인 완료
        </div>
      )}

      {error && (
        <span className="text-xs text-red-400">{error}</span>
      )}
    </div>
  );
}

export type { PlanPhase };
