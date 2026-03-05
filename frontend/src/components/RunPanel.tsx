"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useProjectStore } from "@/store/projectStore";
import {
  runProject,
  stopProject,
  getRunStatus,
  type RunStatus,
  type RunStatusState,
  type ContainerInfo,
} from "@/lib/api";
import { toastSuccess, toastError, toastInfo } from "@/store/toastStore";
import Spinner from "./Spinner";

const STATUS_CONFIG: Record<
  RunStatusState,
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

/** Map backend status string to our frontend RunStatusState */
function mapBackendStatus(backendStatus: string): RunStatusState {
  switch (backendStatus) {
    case "running":
      return "running";
    case "stopped":
    case "exited":
      return "stopped";
    case "error":
      return "error";
    case "starting":
      return "starting";
    case "no_compose":
    case "unknown":
    default:
      return "idle";
  }
}

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
  const [showContainers, setShowContainers] = useState(false);

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
      const resp = await getRunStatus(selectedId);
      const mappedStatus = mapBackendStatus(resp.status);
      setRunStatus({
        status: mappedStatus,
        urls: resp.urls,
        containers: resp.containers,
        error: resp.error ?? undefined,
      });

      // Stop polling when in terminal state (keep polling if running to detect crashes)
      if (mappedStatus !== "running" && mappedStatus !== "starting") {
        stopPolling();
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
      if (result.status === "running") {
        setRunStatus({
          status: "running",
          urls: result.urls,
          containers: result.containers,
        });
        const firstUrl = Object.values(result.urls)[0];
        toastSuccess(`앱이 실행되었습니다${firstUrl ? `: ${firstUrl}` : ""}`);
        // Start polling to monitor container health
        startPolling();
      } else if (result.status === "error") {
        setRunStatus({
          status: "error",
          error: result.error ?? result.message,
        });
        toastError(`앱 실행 실패: ${result.error ?? result.message}`);
      } else {
        // Other states (might be still starting) — poll for updates
        toastInfo("앱을 시작하고 있습니다...");
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
      const result = await stopProject(selectedId);
      if (result.status === "error") {
        toastError(`앱 중지 실패: ${result.error ?? result.message}`);
        setRunStatus((prev) => ({
          ...prev,
          status: prev.status === "stopping" ? "running" : prev.status,
        }));
      } else {
        setRunStatus({ status: "stopped" });
        toastInfo("앱이 중지되었습니다.");
        stopPolling();
      }
    } catch (e) {
      const errMsg = (e as Error).message;
      toastError(`앱 중지 실패: ${errMsg}`);
      setRunStatus((prev) => ({
        ...prev,
        status: prev.status === "stopping" ? "running" : prev.status,
      }));
    } finally {
      setActionLoading(false);
    }
  }, [selectedId, stopPolling]);

  // Handle Restart
  const handleRestart = useCallback(async () => {
    if (!selectedId) return;
    setActionLoading(true);
    setRunStatus((prev) => ({ ...prev, status: "stopping" }));
    try {
      await stopProject(selectedId);
      setRunStatus({ status: "starting" });
      toastInfo("앱을 재시작합니다...");
      const result = await runProject(selectedId);
      if (result.status === "running") {
        setRunStatus({
          status: "running",
          urls: result.urls,
          containers: result.containers,
        });
        toastSuccess("앱이 재시작되었습니다.");
        startPolling();
      } else {
        startPolling();
      }
    } catch (e) {
      const errMsg = (e as Error).message;
      setRunStatus({ status: "error", error: errMsg });
      toastError(`재시작 실패: ${errMsg}`);
    } finally {
      setActionLoading(false);
    }
  }, [selectedId, startPolling]);

  if (!visible || !selectedId || !project) return null;

  // Only show for completed/testing projects (or any status with existing containers)
  const showRun =
    project.status === "completed" ||
    project.status === "testing" ||
    runStatus.status !== "idle";
  if (!showRun) return null;

  const config = STATUS_CONFIG[runStatus.status];
  const isTransitioning =
    runStatus.status === "starting" || runStatus.status === "stopping";
  const urls = runStatus.urls ?? {};
  const urlEntries = Object.entries(urls);
  const containers = runStatus.containers ?? [];

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
          {runStatus.status === "running" && urlEntries.length > 0 && (
            <div className="flex items-center gap-2">
              {urlEntries.map(([service, url]) => (
                <a
                  key={service}
                  href={url}
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
                  {service}: {url}
                </a>
              ))}
            </div>
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
          {/* Container info toggle */}
          {containers.length > 0 && (
            <button
              onClick={() => setShowContainers(!showContainers)}
              className="rounded-md border border-gray-600 px-2 py-1 text-[10px] text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition"
              title="컨테이너 정보"
            >
              📦 {containers.length}
            </button>
          )}

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
                <Spinner size="sm" />
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
                <Spinner size="sm" />
              ) : (
                <span>⏹</span>
              )}
              중지
            </button>
          )}

          {/* Restart button for running state */}
          {runStatus.status === "running" && (
            <button
              onClick={handleRestart}
              disabled={actionLoading}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
            >
              {actionLoading ? (
                <Spinner size="sm" />
              ) : (
                <span>🔄</span>
              )}
              재시작
            </button>
          )}
        </div>
      </div>

      {/* Container details (collapsible) */}
      {showContainers && containers.length > 0 && (
        <div className="mt-2 rounded-md bg-gray-900/50 border border-gray-700 overflow-hidden">
          <table className="w-full text-xs text-gray-300">
            <thead>
              <tr className="border-b border-gray-700 text-gray-500">
                <th className="px-3 py-1.5 text-left font-medium">서비스</th>
                <th className="px-3 py-1.5 text-left font-medium">상태</th>
                <th className="px-3 py-1.5 text-left font-medium">포트</th>
              </tr>
            </thead>
            <tbody>
              {containers.map((c: ContainerInfo) => (
                <tr key={c.name} className="border-b border-gray-800 last:border-0">
                  <td className="px-3 py-1.5 font-mono">{c.service}</td>
                  <td className="px-3 py-1.5">
                    <span
                      className={`inline-flex items-center gap-1 ${
                        c.state === "running"
                          ? "text-green-400"
                          : c.state === "exited"
                          ? "text-gray-500"
                          : "text-yellow-400"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          c.state === "running"
                            ? "bg-green-400"
                            : c.state === "exited"
                            ? "bg-gray-500"
                            : "bg-yellow-400"
                        }`}
                      />
                      {c.status}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 font-mono text-gray-500">
                    {c.ports || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
