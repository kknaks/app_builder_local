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

// ─── Token Settings ───────────────────────────────────────
export interface TokenStatus {
  configured: boolean;
}

export function getTokenStatus(): Promise<TokenStatus> {
  return apiFetch<TokenStatus>("/api/settings/token/status");
}

export function saveToken(token: string): Promise<{ ok: boolean }> {
  return apiFetch("/api/settings/token", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
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
  return apiFetch<Project[]>("/api/projects");
}

export function createProject(data: {
  name: string;
  idea: string;
}): Promise<Project> {
  return apiFetch<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(data),
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

export function getProjectCost(projectId: string): Promise<ProjectCost> {
  return apiFetch<ProjectCost>(`/api/projects/${projectId}/cost`);
}

// ─── WebSocket URLs ───────────────────────────────────────
const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:28888";

export function getChatWsUrl(projectId: string): string {
  return `${WS_BASE}/ws/projects/${projectId}/chat`;
}

export function getLogWsUrl(projectId: string): string {
  return `${WS_BASE}/ws/projects/${projectId}/logs`;
}
