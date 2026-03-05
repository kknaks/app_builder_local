"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useProjectStore } from "@/store/projectStore";
import { runProject, stopProject, getRunStatus, type RunStatus } from "@/lib/api";
import { toastSuccess, toastError, toastInfo } from "@/store/toastStore";

/** Spinner SVG */
function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin-fast ${className}`}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

const STATUS_CONFIG: Record<
  RunStatus["status"],
  { label: string; icon: string; color: string; bgColor: string }
> = {
  idle: {
    label: "대기",
    icon: "⏸",
    color: "text-gray-400",
    bgColor: "bg-gray-800",
  },
  starting: {
    label: "시작 중...",
    icon: "🔄",
    color: "text-blue-400",
    bgColor: "bg-blue-900/30",
  },
  running: {
    label: "실행 중",
    icon: "🟢",
    color: "text-green-400",
    bgColor: "bg-green-900/20",
  },
  stopping: {
    label: "중지 중...",
    icon: "🔄",
    color: "text-yellow-400",
    bgColor: "bg-yellow-900/20",
  },
  stopped: {
    label: "중지됨",
    icon: "⏹",
    color: "text-gray-400",
    bgColor: "bg-gray-800",
  },
  error: {
    label: "오류",
    icon: "❌",
    color: "text-red-400",
    bgColor: "bg-red-900/20",
  },
};

interface RunPanelProps {
  /** Only show when project is in completed status */
  visible?: boolean;
}

export default function RunPanel({ visible = true }: RunPanelProps) {
  const selectedId = useProjectStore((s) => s.selectedId);
  const project = useProjectStore((s) =>
    s.projects.find((p) => p.id === s.selectedId)
  );

  const [runStatus, setRunStatus] = useState<RunStatus>({ status: "idle" });
  const [actionLoading, setActionLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Fetch run status
  const fetchStatus = useCallback(async () => {
    if (!selectedId) return;
    try {
      const status = await getRunStatus(selectedId);
      setRunStatus(status);

      // Stop polling when in terminal state
      if (status.status === "running" || status.status === "stopped" || status.status === "error" || status.status === "idle") {
        // Keep polling if running (to detect crashes), stop for terminal states
        if (status.status !== "running") {
          stopPolling();
        }
      }
    } catch {
      // API might not be ready, that's ok
    }
  }, [selectedId, stopPolling]);

  // Start polling for status
  const startPolling = useCallback(() => {
    stopPolling();
    fetchStatus();
    pollRef.current = setInterval(fetchStatus, 3000);
  }, [fetchStatus, stopPolling]);

  // Fetch initial status when project changes
  useEffect(() => {
    if (selectedId && visible) {
      fetchStatus();
    }
    return stopPolling;
  }, [selectedId, visible, fetchStatus, stopPolling]);

  // Handle Run
  const handleRun = useCallback(async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setRunStatus({ status: "starting" });
    try {
      const result = await runProject(selectedId);
      toastInfo("앱을 시작하고 있습니다...");
      if (result.url) {
        setRunStatus({ status: "running", url: result.url });
        toastSuccess(`앱이 실행되었습니다: ${result.url}`);
      } else {
        startPolling();
      }
    } catch (e) {
      const errMsg = (e as Error).message;
      setRunStatus({ status: "error", error: errMsg });
      toastError(`앱 실행 실패: ${errMsg}`);
    } finally {
      setActionLoading(false);
    }
  }, [selectedId, startPolling]);

  // Handle Stop
  const handleStop = useCallback(async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setRunStatus((prev) => ({ ...prev, status: "stopping" }));
    try {
      await stopProject(selectedId);
      setRunStatus({ status: "stopped" });
      toastInfo("앱이 중지되었습니다.");
      stopPolling();
    } catch (e) {
      const errMsg = (e as Error).message;
      toastError(`앱 중지 실패: ${errMsg}`);
      setRunStatus((prev) => ({ ...prev, status: prev.status === "stopping" ? "running" : prev.status }));
    } finally {
      setActionLoading(false);
    }
  }, [selectedId, stopPolling]);

  if (!visible || !selectedId || !project) return null;

  // Only show for completed/testing projects (or any status with existing containers)
  const showRun = project.status === "completed" || project.status === "testing" || runStatus.status !== "idle";
  if (!showRun) return null;

  const config = STATUS_CONFIG[runStatus.status];
  const isTransitioning = runStatus.status === "starting" || runStatus.status === "stopping";

  return (
    <div
      className={`border-b border-gray-700 ${config.bgColor} px-4 py-3 transition-colors`}
    >
      <div className="flex items-center justify-between">
        {/* Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {isTransitioning ? (
              <Spinner className="h-4 w-4 text-blue-400" />
            ) : (
              <span className="text-sm">{config.icon}</span>
            )}
            <span className={`text-sm font-medium ${config.color}`}>
              {config.label}
            </span>
          </div>

          {/* URL display when running */}
          {runStatus.status === "running" && runStatus.url && (
            <a
              href={runStatus.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 rounded-md bg-green-800/40 px-3 py-1 text-xs font-mono text-green-300 hover:bg-green-800/60 transition"
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
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
              {runStatus.url}
            </a>
          )}

          {/* Error message */}
          {runStatus.status === "error" && runStatus.error && (
            <span className="text-xs text-red-400 max-w-xs truncate">
              {runStatus.error}
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {/* Run button */}
          {(runStatus.status === "idle" ||
            runStatus.status === "stopped" ||
            runStatus.status === "error") && (
            <button
              onClick={handleRun}
              disabled={actionLoading}
              className="flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50 transition"
            >
              {actionLoading ? (
                <Spinner className="h-3.5 w-3.5" />
              ) : (
                <span>🚀</span>
              )}
              앱 실행
            </button>
          )}

          {/* Stop button */}
          {(runStatus.status === "running" ||
            runStatus.status === "starting") && (
            <button
              onClick={handleStop}
              disabled={actionLoading}
              className="flex items-center gap-1.5 rounded-md border border-red-700 bg-red-900/30 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-900/50 disabled:opacity-50 transition"
            >
              {actionLoading ? (
                <Spinner className="h-3.5 w-3.5" />
              ) : (
                <span>⏹</span>
              )}
              중지
            </button>
          )}

          {/* Re-run button for running state */}
          {runStatus.status === "running" && (
            <button
              onClick={async () => {
                await handleStop();
                // Small delay then re-run
                setTimeout(handleRun, 1000);
              }}
              disabled={actionLoading}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
            >
              🔄 재시작
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
