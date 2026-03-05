"use client";

import { useState, useCallback } from "react";
import { useProjectStore } from "@/store/projectStore";
import { startSprint, startImplementation, cancelProject } from "@/lib/api";

export type ImplPhase =
  | "idle"
  | "approved"
  | "sprint_planning"
  | "sprint_ready"
  | "implementing"
  | "testing"
  | "completed"
  | "failed";

interface ImplementationActionsProps {
  phase: ImplPhase;
  onPhaseChange?: (phase: ImplPhase) => void;
}

export default function ImplementationActions({
  phase,
  onPhaseChange,
}: ImplementationActionsProps) {
  const selectedId = useProjectStore((s) => s.selectedId);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartSprint = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    try {
      await startSprint(selectedId);
      onPhaseChange?.("sprint_planning");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selectedId, onPhaseChange]);

  const handleStartImplementation = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    try {
      await startImplementation(selectedId);
      onPhaseChange?.("implementing");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selectedId, onPhaseChange]);

  const handleCancel = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    try {
      await cancelProject(selectedId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  if (!selectedId) return null;

  // Only show for implementation-related phases
  if (
    phase !== "approved" &&
    phase !== "sprint_planning" &&
    phase !== "sprint_ready" &&
    phase !== "implementing" &&
    phase !== "testing" &&
    phase !== "completed" &&
    phase !== "failed"
  ) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 border-b border-gray-700 bg-gray-850 px-4 py-2">
      {/* Sprint Plan button */}
      {(phase === "approved" || phase === "sprint_planning") && (
        <button
          onClick={handleStartSprint}
          disabled={loading || phase === "sprint_planning"}
          className="flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50 transition"
        >
          {loading && phase !== "sprint_planning" ? (
            "시작중..."
          ) : phase === "sprint_planning" ? (
            <>
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-violet-300" />
              스프린트 플랜 작성중...
            </>
          ) : (
            "📋 스프린트 플랜"
          )}
        </button>
      )}

      {/* Implementation Start button */}
      {(phase === "sprint_ready" || phase === "implementing") && (
        <button
          onClick={handleStartImplementation}
          disabled={loading || phase === "implementing"}
          className="flex items-center gap-1.5 rounded-md bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-500 disabled:opacity-50 transition"
        >
          {loading && phase !== "implementing" ? (
            "시작중..."
          ) : phase === "implementing" ? (
            <>
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-orange-300" />
              구현 진행중...
            </>
          ) : (
            "🔨 구현 시작"
          )}
        </button>
      )}

      {/* Cancel button (only during active processes) */}
      {(phase === "sprint_planning" || phase === "implementing") && (
        <button
          onClick={handleCancel}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md border border-red-700 bg-red-900/30 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-900/50 disabled:opacity-50 transition"
        >
          ⏹ 중단
        </button>
      )}

      {/* Testing indicator */}
      {phase === "testing" && (
        <div className="flex items-center gap-1.5 text-xs text-cyan-300">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-400" />
          통합 테스트 진행중...
        </div>
      )}

      {/* Completed */}
      {phase === "completed" && (
        <div className="flex items-center gap-1.5 text-xs text-green-400">
          ✅ 구현 완료
        </div>
      )}

      {/* Failed */}
      {phase === "failed" && (
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-red-400">
            ❌ 구현 실패
          </span>
          <button
            onClick={handleStartImplementation}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-md bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-500 disabled:opacity-50 transition"
          >
            🔄 재시도
          </button>
        </div>
      )}

      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}
