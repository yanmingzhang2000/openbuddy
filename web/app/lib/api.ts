/** 控制面 API 客户端封装。所有调用都带 Authorization: Bearer <token>。 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

export type Task = {
  id: string;
  title: string;
  instruction: string;
  status: string;
  max_steps: number;
  timeout_seconds: number;
  token_budget: number;
  cost_budget_usd: number;
  steps_used: number;
  tokens_used: number;
  cost_used_usd: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
};

export type TaskEvent = {
  type: string;
  event_type?: string;
  sequence?: number;
  payload?: Record<string, unknown>;
  status?: string;
  detail?: string;
};

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function signup(
  tenantName: string,
  email: string,
  password: string
): Promise<{ access_token: string }> {
  const res = await fetch(`${API_BASE}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tenant_name: tenantName, email, password }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function login(
  email: string,
  password: string
): Promise<{ access_token: string }> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listTasks(token: string): Promise<Task[]> {
  const res = await fetch(`${API_BASE}/api/tasks`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createTask(
  token: string,
  title: string,
  instruction: string
): Promise<Task> {
  const res = await fetch(`${API_BASE}/api/tasks`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ title, instruction }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getTask(token: string, taskId: string): Promise<Task> {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getTaskEvents(
  token: string,
  taskId: string
): Promise<TaskEvent[]> {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}/events`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function submitApproval(
  token: string,
  taskId: string,
  decision: "approved" | "rejected"
): Promise<Task> {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}/approval`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ decision }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function openTaskEventsSocket(
  token: string,
  taskId: string,
  onEvent: (event: TaskEvent) => void
): WebSocket {
  const ws = new WebSocket(
    `${WS_BASE}/ws/tasks/${taskId}/events?token=${encodeURIComponent(token)}`
  );
  ws.onmessage = (msg) => {
    onEvent(JSON.parse(msg.data) as TaskEvent);
  };
  return ws;
}
