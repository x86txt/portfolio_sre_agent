import type { Incident, IncidentSummary, LlmModelsResponse } from "./types";

const API_BASE = import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000";

async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ""}`);
  }
  return res;
}

export async function listIncidents(limit = 50): Promise<IncidentSummary[]> {
  const res = await apiFetch(`/api/incidents?limit=${limit}`);
  return (await res.json()) as IncidentSummary[];
}

export async function getIncident(id: string): Promise<Incident> {
  const res = await apiFetch(`/api/incidents/${encodeURIComponent(id)}`);
  return (await res.json()) as Incident;
}

export async function runScenario(name: string): Promise<{ lastIncidentId?: string }> {
  const res = await apiFetch(`/api/scenarios/${encodeURIComponent(name)}`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  return (await res.json()) as { lastIncidentId?: string };
}

export async function generateReport(
  incidentId: string,
  format: "markdown" | "text" | "json",
  llm: "auto" | "off" | "openai" | "anthropic",
  model?: string
): Promise<{ contentType: string; body: string }> {
  const params = new URLSearchParams();
  params.set("format", format);
  params.set("llm", llm);
  if (model) params.set("model", model);

  const res = await apiFetch(
    `/api/incidents/${encodeURIComponent(incidentId)}/report?${params.toString()}`,
    { method: "POST" }
  );

  const contentType = res.headers.get("content-type") || "text/plain";
  const body = await res.text();
  return { contentType, body };
}

export async function updateIncidentResolution(
  id: string,
  status: "none" | "resolved" | "auto_closed" | "false_alert" | "accepted",
  note?: string
): Promise<Incident> {
  const res = await apiFetch(`/api/incidents/${encodeURIComponent(id)}/resolution`, {
    method: "POST",
    body: JSON.stringify({ status, note: note ?? null }),
  });
  return (await res.json()) as Incident;
}

export async function fetchLlmModels(): Promise<LlmModelsResponse> {
  const res = await apiFetch("/api/llm/models");
  return (await res.json()) as LlmModelsResponse;
}

export async function updateLlmWeights(weights: Record<string, number>): Promise<LlmModelsResponse> {
  const res = await apiFetch("/api/llm/weights", {
    method: "POST",
    body: JSON.stringify({ weights }),
  });
  return (await res.json()) as LlmModelsResponse;
}

export async function chatSre(
  prompt: string,
  llm: "auto" | "off" | "openai" | "anthropic" = "auto",
  model?: string
): Promise<string> {
  const res = await apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ prompt, llm, model: model || null }),
  });
  return await res.text();
}

export function streamUrl(): string {
  return `${API_BASE}/api/stream`;
}


