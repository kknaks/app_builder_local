import { create } from "zustand";
import type { FlowNode, FlowEdge } from "@/lib/api";

export type NodeStatus = "pending" | "running" | "completed" | "failed";

interface FlowState {
  /** Flow nodes for the current project */
  nodes: FlowNode[];
  /** Flow edges for the current project */
  edges: FlowEdge[];
  /** Whether flow data is loading */
  loading: boolean;
  /** Set entire flow */
  setFlow: (nodes: FlowNode[], edges: FlowEdge[]) => void;
  /** Update a single node's status */
  updateNodeStatus: (nodeId: string, status: NodeStatus) => void;
  /** Add a node dynamically */
  addNode: (node: FlowNode) => void;
  /** Add an edge dynamically */
  addEdge: (edge: FlowEdge) => void;
  /** Clear flow state */
  clearFlow: () => void;
  /** Set loading state */
  setLoading: (loading: boolean) => void;
}

// Default planning pipeline stages
export const DEFAULT_PLANNING_NODES: FlowNode[] = [
  { id: "idea", label: "아이디어", status: "completed" },
  { id: "plan-detail", label: "기획 구체화", status: "pending" },
  { id: "plan-review", label: "기획 검토", status: "pending" },
  { id: "plan-approve", label: "승인", status: "pending" },
];

export const DEFAULT_PLANNING_EDGES: FlowEdge[] = [
  { id: "e-idea-plan", source: "idea", target: "plan-detail" },
  { id: "e-plan-review", source: "plan-detail", target: "plan-review" },
  { id: "e-review-approve", source: "plan-review", target: "plan-approve" },
];

export const useFlowStore = create<FlowState>((set, get) => ({
  nodes: [],
  edges: [],
  loading: false,

  setFlow: (nodes, edges) => set({ nodes, edges, loading: false }),

  updateNodeStatus: (nodeId, status) => {
    const nodes = get().nodes.map((n) =>
      n.id === nodeId ? { ...n, status } : n
    );
    set({ nodes });
  },

  addNode: (node) => {
    const existing = get().nodes.find((n) => n.id === node.id);
    if (!existing) {
      set({ nodes: [...get().nodes, node] });
    }
  },

  addEdge: (edge) => {
    const existing = get().edges.find((e) => e.id === edge.id);
    if (!existing) {
      set({ edges: [...get().edges, edge] });
    }
  },

  clearFlow: () => set({ nodes: [], edges: [], loading: false }),

  setLoading: (loading) => set({ loading }),
}));
