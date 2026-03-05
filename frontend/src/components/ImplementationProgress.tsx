"use client";

import { useMemo } from "react";
import { useFlowStore } from "@/store/flowStore";
import type { FlowNode } from "@/lib/api";

const STATUS_ICONS: Record<string, { icon: string; color: string }> = {
  pending: { icon: "○", color: "text-gray-500" },
  running: { icon: "●", color: "text-blue-400" },
  completed: { icon: "✅", color: "text-green-400" },
  failed: { icon: "❌", color: "text-red-400" },
};

interface FeatureGroup {
  featureId: string;
  featureLabel: string;
  nodes: FlowNode[];
}

export default function ImplementationProgress() {
  const nodes = useFlowStore((s) => s.nodes);

  // Group nodes by feature (nodes with type containing "impl-" prefix)
  const { featureGroups, stats } = useMemo(() => {
    // Find implementation nodes (nodes with agent field or impl type)
    const implNodes = nodes.filter(
      (n) =>
        n.agent ||
        n.type?.startsWith("impl") ||
        n.id.includes("impl") ||
        n.id.includes("sprint")
    );

    if (implNodes.length === 0) {
      return { featureGroups: [], stats: { total: 0, completed: 0, running: 0, failed: 0 } };
    }

    // Group by feature prefix
    const groups = new Map<string, FlowNode[]>();
    for (const node of implNodes) {
      // Try to extract feature group from node ID (e.g., "impl-auth-be" → "auth")
      const parts = node.id.split("-");
      let featureKey = node.id;
      if (parts.length >= 3 && parts[0] === "impl") {
        featureKey = parts.slice(1, -1).join("-");
      } else if (parts.length >= 2 && parts[0] === "sprint") {
        featureKey = parts.slice(1).join("-");
      }

      if (!groups.has(featureKey)) {
        groups.set(featureKey, []);
      }
      groups.get(featureKey)!.push(node);
    }

    const featureGroups: FeatureGroup[] = Array.from(groups.entries()).map(
      ([key, groupNodes]) => ({
        featureId: key,
        featureLabel: groupNodes[0]?.label?.replace(/\s*(BE|FE|테스트|Design)$/, "") || key,
        nodes: groupNodes,
      })
    );

    const stats = {
      total: implNodes.length,
      completed: implNodes.filter((n) => n.status === "completed").length,
      running: implNodes.filter((n) => n.status === "running").length,
      failed: implNodes.filter((n) => n.status === "failed").length,
    };

    return { featureGroups, stats };
  }, [nodes]);

  if (featureGroups.length === 0) return null;

  const progressPercent =
    stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <div className="border-t border-gray-700 bg-gray-900/50 px-4 py-3">
      {/* Progress overview */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-bold text-gray-300">구현 진행률</span>
          <span className="text-xs text-gray-400">
            {stats.completed}/{stats.total} ({progressPercent}%)
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-gray-700 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              stats.failed > 0 ? "bg-red-500" : "bg-green-500"
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="mt-1 flex items-center gap-3 text-[10px] text-gray-500">
          {stats.running > 0 && (
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
              진행 {stats.running}
            </span>
          )}
          {stats.completed > 0 && (
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
              완료 {stats.completed}
            </span>
          )}
          {stats.failed > 0 && (
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
              에러 {stats.failed}
            </span>
          )}
        </div>
      </div>

      {/* Feature groups */}
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {featureGroups.map((group) => (
          <FeatureRow key={group.featureId} group={group} />
        ))}
      </div>
    </div>
  );
}

function FeatureRow({ group }: { group: FeatureGroup }) {
  return (
    <div className="rounded-md bg-gray-800/50 px-3 py-2">
      <div className="text-xs font-medium text-gray-300 mb-1.5">
        {group.featureLabel}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {group.nodes.map((node) => (
          <NodeChip key={node.id} node={node} />
        ))}
      </div>
    </div>
  );
}

function NodeChip({ node }: { node: FlowNode }) {
  const statusCfg = STATUS_ICONS[node.status] || STATUS_ICONS.pending;
  const isRunning = node.status === "running";
  const isFailed = node.status === "failed";

  // Determine chip label from agent or node label
  const chipLabel = node.agent?.toUpperCase() || node.label;

  return (
    <div
      className={`flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] transition-all ${
        isRunning
          ? "border-blue-500/50 bg-blue-900/30 text-blue-300"
          : isFailed
          ? "border-red-500/50 bg-red-900/30 text-red-300"
          : node.status === "completed"
          ? "border-green-700/30 bg-green-900/20 text-green-400"
          : "border-gray-700 bg-gray-800 text-gray-500"
      }`}
      title={node.error_message || node.label}
    >
      {isRunning && (
        <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
      )}
      <span className={statusCfg.color}>{statusCfg.icon}</span>
      <span>{chipLabel}</span>
      {isFailed && node.retry_count !== undefined && node.retry_count > 0 && (
        <span className="text-red-400 font-bold">
          ×{node.retry_count}
        </span>
      )}
    </div>
  );
}
