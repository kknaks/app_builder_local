"use client";

import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  BackgroundVariant,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import { useProjectStore } from "@/stores/useProjectStore";
import {
  useFlowStore,
  DEFAULT_PLANNING_NODES,
  DEFAULT_PLANNING_EDGES,
} from "@/store/flowStore";
import { getProjectFlow } from "@/lib/api";

// ─── Node status → color ──────────────────────────────────
const STATUS_COLORS: Record<string, { bg: string; border: string; glow: string }> = {
  pending: { bg: "bg-gray-700", border: "border-gray-500", glow: "" },
  running: {
    bg: "bg-blue-700",
    border: "border-blue-400",
    glow: "shadow-blue-500/30 shadow-lg",
  },
  completed: { bg: "bg-green-700", border: "border-green-400", glow: "" },
  failed: {
    bg: "bg-red-700",
    border: "border-red-400",
    glow: "shadow-red-500/30 shadow-lg",
  },
};

interface FlowNodeData {
  label: string;
  status: string;
  [key: string]: unknown;
}

// ─── Custom Node ──────────────────────────────────────────
function StageNode({ data }: { data: FlowNodeData }) {
  const colors = STATUS_COLORS[data.status] || STATUS_COLORS.pending;
  const isRunning = data.status === "running";

  return (
    <div
      className={`rounded-lg border-2 ${colors.border} ${colors.bg} ${colors.glow} px-6 py-3 text-center transition-all duration-300`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-gray-400"
      />
      <div className="flex items-center gap-2">
        {isRunning && (
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-300" />
        )}
        <span className="text-sm font-semibold text-white">{data.label}</span>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-gray-400"
      />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  stage: StageNode,
};

// ─── Dagre layout helper ──────────────────────────────────
const NODE_WIDTH = 160;
const NODE_HEIGHT = 50;

function getLayoutedElements(
  nodes: Node<FlowNodeData>[],
  edges: Edge[]
): { nodes: Node<FlowNodeData>[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 60, ranksep: 100 });

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  const layoutedNodes = nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

export default function DashboardPanel() {
  const selectedId = useProjectStore((s) => s.selectedId);
  const project = useProjectStore((s) =>
    s.projects.find((p) => p.id === s.selectedId)
  );
  const flowNodes = useFlowStore((s) => s.nodes);
  const flowEdges = useFlowStore((s) => s.edges);
  const setFlow = useFlowStore((s) => s.setFlow);
  const setLoading = useFlowStore((s) => s.setLoading);

  // Load flow from API when project changes
  useEffect(() => {
    if (!selectedId) {
      setFlow([], []);
      return;
    }

    let cancelled = false;
    setLoading(true);

    getProjectFlow(selectedId)
      .then((data) => {
        if (!cancelled) {
          setFlow(data.nodes, data.edges);
        }
      })
      .catch(() => {
        // Fallback to default planning nodes if API not ready
        if (!cancelled) {
          setFlow(DEFAULT_PLANNING_NODES, DEFAULT_PLANNING_EDGES);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedId, setFlow, setLoading]);

  // Convert flow store data to React Flow nodes/edges
  const layouted = useMemo(() => {
    if (flowNodes.length === 0) {
      return { nodes: [] as Node<FlowNodeData>[], edges: [] as Edge[] };
    }

    const rfNodes: Node<FlowNodeData>[] = flowNodes.map((n) => ({
      id: n.id,
      type: "stage",
      position: { x: 0, y: 0 },
      data: { label: n.label, status: n.status },
    }));

    const rfEdges: Edge[] = flowEdges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      animated: flowNodes.find((n) => n.id === e.target)?.status === "running",
      style: {
        stroke:
          flowNodes.find((n) => n.id === e.target)?.status === "running"
            ? "#60a5fa"
            : "#4b5563",
      },
    }));

    return getLayoutedElements(rfNodes, rfEdges);
  }, [flowNodes, flowEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(layouted.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layouted.edges);

  // Sync layouted elements to React Flow state
  useEffect(() => {
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
  }, [layouted, setNodes, setEdges]);

  const onInit = useCallback(() => {
    // fitView is handled by ReactFlow prop
  }, []);

  if (!selectedId || !project) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-950 text-gray-500">
        <div className="text-center">
          <p className="text-lg font-medium">대시보드</p>
          <p className="mt-1 text-sm">프로젝트를 선택하세요</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-gray-950">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 px-4 py-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-white">{project.name}</h3>
          <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-400">
            {project.status}
          </span>
        </div>
        {/* Legend */}
        <div className="flex items-center gap-3 text-[10px] text-gray-500">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-gray-500" />
            대기
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-blue-400" />
            진행중
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-green-400" />
            완료
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-red-400" />
            에러
          </span>
        </div>
      </div>
      <div className="h-[calc(100%-41px)] w-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onInit={onInit}
          fitView
          proOptions={{ hideAttribution: true }}
          minZoom={0.3}
          maxZoom={1.5}
        >
          <Background
            variant={BackgroundVariant.Dots}
            color="#374151"
            gap={20}
          />
          <Controls
            showInteractive={false}
            className="!bg-gray-800 !border-gray-600 !shadow-xl [&>button]:!bg-gray-700 [&>button]:!border-gray-600 [&>button]:!text-white [&>button:hover]:!bg-gray-600"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
