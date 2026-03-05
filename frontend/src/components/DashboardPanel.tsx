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

// ─── Node status → color ──────────────────────────────────
const STATUS_COLORS: Record<string, { bg: string; border: string }> = {
  pending: { bg: "bg-gray-700", border: "border-gray-500" },
  running: { bg: "bg-blue-700", border: "border-blue-400" },
  completed: { bg: "bg-green-700", border: "border-green-400" },
  failed: { bg: "bg-red-700", border: "border-red-400" },
};

interface FlowNodeData {
  label: string;
  status: string;
  [key: string]: unknown;
}

// ─── Custom Node ──────────────────────────────────────────
function StageNode({ data }: { data: FlowNodeData }) {
  const colors = STATUS_COLORS[data.status] || STATUS_COLORS.pending;
  return (
    <div
      className={`rounded-lg border-2 ${colors.border} ${colors.bg} px-6 py-3 text-center shadow-lg`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-gray-400"
      />
      <span className="text-sm font-semibold text-white">{data.label}</span>
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
const NODE_WIDTH = 140;
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

// ─── Default pipeline stages ──────────────────────────────
const DEFAULT_STAGES = [
  { id: "idea", label: "아이디어", status: "pending" },
  { id: "planning", label: "기획", status: "pending" },
  { id: "implementation", label: "구현", status: "pending" },
  { id: "deploy", label: "배포", status: "pending" },
];

const DEFAULT_EDGES: Edge[] = [
  { id: "e-idea-planning", source: "idea", target: "planning" },
  {
    id: "e-planning-impl",
    source: "planning",
    target: "implementation",
  },
  { id: "e-impl-deploy", source: "implementation", target: "deploy" },
];

export default function DashboardPanel() {
  const selectedId = useProjectStore((s) => s.selectedId);
  const project = useProjectStore((s) =>
    s.projects.find((p) => p.id === s.selectedId)
  );

  const initialElements = useMemo(() => {
    const rawNodes: Node<FlowNodeData>[] = DEFAULT_STAGES.map((stage) => ({
      id: stage.id,
      type: "stage",
      position: { x: 0, y: 0 },
      data: { label: stage.label, status: stage.status },
    }));
    return getLayoutedElements(rawNodes, DEFAULT_EDGES);
  }, []);

  const [nodes, setNodes, onNodesChange] = useNodesState(
    initialElements.nodes
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialElements.edges
  );

  // Re-layout when project changes
  useEffect(() => {
    const rawNodes: Node<FlowNodeData>[] = DEFAULT_STAGES.map((stage) => ({
      id: stage.id,
      type: "stage",
      position: { x: 0, y: 0 },
      data: { label: stage.label, status: stage.status },
    }));
    const laid = getLayoutedElements(rawNodes, DEFAULT_EDGES);
    setNodes(laid.nodes);
    setEdges(laid.edges);
  }, [selectedId, setNodes, setEdges]);

  const onInit = useCallback(() => {
    // no-op; fitView is handled by ReactFlow prop
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
      <div className="flex items-center border-b border-gray-700 px-4 py-2">
        <h3 className="text-sm font-bold text-white">{project.name}</h3>
        <span className="ml-2 text-xs text-gray-500">
          {project.status}
        </span>
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
          <Background variant={BackgroundVariant.Dots} color="#374151" gap={20} />
          <Controls
            showInteractive={false}
            className="!bg-gray-800 !border-gray-600 !shadow-xl [&>button]:!bg-gray-700 [&>button]:!border-gray-600 [&>button]:!text-white [&>button:hover]:!bg-gray-600"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
