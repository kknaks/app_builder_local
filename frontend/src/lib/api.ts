const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:28888";

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body}`);
  }
  // handle 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ─── Claude CLI Auth Status ──────────────────────────────
export interface TokenStatus {
  configured: boolean;
  valid?: boolean | null;
  message?: string;
}

export function getTokenStatus(): Promise<TokenStatus> {
  return apiFetch<TokenStatus>("/api/settings/token/status");
}

// ─── Projects ─────────────────────────────────────────────
export interface Project {
  id: string;
  name: string;
  idea: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export function getProjects(): Promise<Project[]> {
  return apiFetch<{ projects: Project[]; total: number }>("/api/projects").then(
    (res) => res.projects
  );
}

export function createProject(data: {
  name: string;
  idea: string;
}): Promise<Project> {
  return apiFetch<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify({ name: data.name, idea_text: data.idea }),
  });
}

export function deleteProject(id: string): Promise<void> {
  return apiFetch<void>(`/api/projects/${id}`, { method: "DELETE" });
}

// ─── Cost Tracking ────────────────────────────────────────
export interface AgentCost {
  agent_id: string;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
}

export interface ProjectCost {
  project_id: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number;
  by_agent: AgentCost[];
}

interface RawProjectCost {
  project_id: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: string;
  agent_breakdown: Array<{
    agent_id: string;
    input_tokens: number;
    output_tokens: number;
    total_cost_usd?: string;
  }>;
}

export function getProjectCost(projectId: string): Promise<ProjectCost> {
  return apiFetch<RawProjectCost>(`/api/projects/${projectId}/cost`).then(
    (raw) => ({
      project_id: raw.project_id,
      total_input_tokens: raw.total_input_tokens,
      total_output_tokens: raw.total_output_tokens,
      total_cost: parseFloat(raw.total_cost_usd) || 0,
      by_agent: (raw.agent_breakdown || []).map((a) => ({
        agent_id: a.agent_id,
        input_tokens: a.input_tokens,
        output_tokens: a.output_tokens,
        total_cost: parseFloat(a.total_cost_usd || "0") || 0,
      })),
    })
  );
}

// ─── Planning Flow ────────────────────────────────────────
export function startPlanning(projectId: string): Promise<{ task_id: string }> {
  return apiFetch<{ task_id: string }>(`/api/projects/${projectId}/plan`, {
    method: "POST",
  });
}

export function startReview(projectId: string): Promise<{ task_id: string }> {
  return apiFetch<{ task_id: string }>(`/api/projects/${projectId}/review`, {
    method: "POST",
  });
}

export function approvePlan(projectId: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/projects/${projectId}/approve`, {
    method: "POST",
  });
}

export function submitFeedback(
  projectId: string,
  feedback: string
): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/projects/${projectId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ feedback }),
  });
}

// ─── Implementation Flow ──────────────────────────────────
export function startSprint(projectId: string): Promise<{ task_id: string }> {
  return apiFetch<{ task_id: string }>(`/api/projects/${projectId}/sprint`, {
    method: "POST",
  });
}

export function startImplementation(projectId: string): Promise<{ task_id: string }> {
  return apiFetch<{ task_id: string }>(`/api/projects/${projectId}/implement`, {
    method: "POST",
  });
}

export function cancelProject(projectId: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/projects/${projectId}/cancel`, {
    method: "POST",
  });
}

export function cancelTask(projectId: string, taskId: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/projects/${projectId}/tasks/${taskId}/cancel`, {
    method: "POST",
  });
}

// ─── App Run/Stop ─────────────────────────────────────────
export interface ContainerInfo {
  name: string;
  service: string;
  state: string;
  status: string;
  ports: string;
}

export interface RunResponse {
  status: string;
  urls: Record<string, string>;
  containers: ContainerInfo[];
  message: string;
  error?: string | null;
}

export interface StopResponse {
  status: string;
  message: string;
  error?: string | null;
}

export interface RunStatusResponse {
  status: string;
  urls: Record<string, string>;
  containers: ContainerInfo[];
  error?: string | null;
}

/** Unified frontend run status (derived from API responses) */
export type RunStatusState = "idle" | "starting" | "running" | "stopping" | "stopped" | "error";

export interface RunStatus {
  status: RunStatusState;
  urls?: Record<string, string>;
  containers?: ContainerInfo[];
  error?: string;
}

export function runProject(projectId: string): Promise<RunResponse> {
  return apiFetch<RunResponse>(`/api/projects/${projectId}/run`, {
    method: "POST",
  });
}

export function stopProject(projectId: string): Promise<StopResponse> {
  return apiFetch<StopResponse>(`/api/projects/${projectId}/stop`, {
    method: "POST",
  });
}

export function getRunStatus(projectId: string): Promise<RunStatusResponse> {
  return apiFetch<RunStatusResponse>(`/api/projects/${projectId}/run/status`);
}

// ─── Flow Nodes ───────────────────────────────────────────
export interface FlowNode {
  id: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed";
  type?: string;
  parent_id?: string | null;
  agent?: string;
  retry_count?: number;
  error_message?: string;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
}

export interface ProjectFlow {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

interface RawFlowNode {
  id: number;
  label: string;
  status: string;
  node_type?: string;
  parent_node_id?: number | null;
  agent?: string;
  retry_count?: number;
  error_message?: string;
}

export function getProjectFlow(projectId: string): Promise<ProjectFlow> {
  return apiFetch<{ nodes: RawFlowNode[] }>(`/api/projects/${projectId}/flow`).then(
    (raw) => {
      const nodes: FlowNode[] = raw.nodes.map((n) => ({
        id: String(n.id),
        label: n.label,
        status: n.status as FlowNode["status"],
        type: n.node_type,
        parent_id: n.parent_node_id != null ? String(n.parent_node_id) : null,
        agent: n.agent,
        retry_count: n.retry_count,
        error_message: n.error_message,
      }));
      const edges: FlowEdge[] = raw.nodes
        .filter((n) => n.parent_node_id != null)
        .map((n) => ({
          id: `e${n.parent_node_id}-${n.id}`,
          source: String(n.parent_node_id),
          target: String(n.id),
        }));
      return { nodes, edges };
    }
  );
}

// ─── WebSocket URLs ───────────────────────────────────────
const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:28888";

export function getChatWsUrl(projectId: string): string {
  return `${WS_BASE}/ws/projects/${projectId}/chat`;
}

export function getLogWsUrl(projectId: string): string {
  return `${WS_BASE}/ws/projects/${projectId}/logs`;
}
