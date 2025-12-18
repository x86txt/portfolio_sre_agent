import React, { useEffect, useMemo, useState } from "react";
import { Box, Text, render, useApp, useInput } from "ink";

type IncidentSummary = {
  id: string;
  service: string;
  env: string;
  status: string;
  updatedAt: string;
  impact: { impact: "none" | "minor" | "major"; confidence: number; classification: string; summary: string };
};

type Incident = IncidentSummary & {
  alerts: Array<{
    id: string;
    provider: string;
    receivedAt: string;
    severity: string;
    signalType: string;
    observed?: number | null;
    threshold?: number | null;
    unit?: string | null;
    message?: string | null;
  }>;
  signals: Record<string, any>;
};

function impactColor(impact: string) {
  if (impact === "major") return "red";
  if (impact === "minor") return "yellow";
  return "green";
}

function apiBase(): string {
  return process.env.AITRIAGE_API_BASE_URL || "http://localhost:8000";
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: any = {}): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as any as T;
}

type View = { kind: "list" } | { kind: "detail"; id: string } | { kind: "report"; id: string; text: string };

function TuiApp() {
  const { exit } = useApp();

  const [view, setView] = useState<View>({ kind: "list" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [selected, setSelected] = useState(0);

  const [incident, setIncident] = useState<Incident | null>(null);

  const refreshList = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson<IncidentSummary[]>(`/api/incidents?limit=100`);
      setIncidents(data);
      setSelected((s) => Math.min(s, Math.max(0, data.length - 1)));
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  };

  const refreshDetail = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson<Incident>(`/api/incidents/${encodeURIComponent(id)}`);
      setIncident(data);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshList();
  }, []);

  useEffect(() => {
    if (view.kind === "detail") refreshDetail(view.id);
  }, [view]);

  const selectedIncident = useMemo(() => incidents[selected], [incidents, selected]);

  useInput((input, key) => {
    if (key.ctrl && input === "c") exit();

    if (view.kind === "list") {
      if (input === "q") exit();
      if (input === "r") refreshList();
      if (key.upArrow) setSelected((s) => Math.max(0, s - 1));
      if (key.downArrow) setSelected((s) => Math.min(incidents.length - 1, s + 1));
      if (key.return && selectedIncident) setView({ kind: "detail", id: selectedIncident.id });
      if (input === "1") postJson(`/api/scenarios/saturation_only`).then(() => refreshList());
      if (input === "2") postJson(`/api/scenarios/full_outage`).then(() => refreshList());
      return;
    }

    if (view.kind === "detail") {
      if (input === "q") exit();
      if (input === "b") setView({ kind: "list" });
      if (input === "r") refreshDetail(view.id);
      if (input === "g") {
        postJson<string>(`/api/incidents/${encodeURIComponent(view.id)}/report?format=markdown&llm=auto`)
          .then((text) => setView({ kind: "report", id: view.id, text }))
          .catch((e: any) => setError(String(e?.message || e)));
      }
      return;
    }

    if (view.kind === "report") {
      if (input === "q") exit();
      if (input === "b") setView({ kind: "detail", id: view.id });
    }
  });

  return (
    <Box flexDirection="column" padding={1}>
      <Box justifyContent="space-between">
        <Text bold>aiTriage</Text>
        <Text dimColor>{apiBase()}</Text>
      </Box>

      <Box marginTop={1}>
        <Text dimColor>
          {view.kind === "list" && "List: ↑/↓ select, Enter details, r refresh, 1/2 demo, q quit"}
          {view.kind === "detail" && "Detail: b back, g report, r refresh, q quit"}
          {view.kind === "report" && "Report: b back, q quit"}
        </Text>
      </Box>

      {error && (
        <Box marginTop={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
      )}

      {loading && (
        <Box marginTop={1}>
          <Text dimColor>Loading…</Text>
        </Box>
      )}

      {!loading && view.kind === "list" && (
        <Box flexDirection="column" marginTop={1}>
          {incidents.length === 0 ? (
            <Text dimColor>No incidents yet. Press 1 or 2 to run demos.</Text>
          ) : (
            incidents.map((i, idx) => {
              const active = idx === selected;
              return (
                <Box key={i.id}>
                  <Text color={active ? "cyan" : undefined}>
                    {active ? "› " : "  "}
                    {i.service}/{i.env}{" "}
                    <Text color={impactColor(i.impact?.impact)}>{i.impact?.impact}</Text>{" "}
                    <Text dimColor>{i.status}</Text>{" "}
                    <Text dimColor>({i.impact?.classification})</Text>
                  </Text>
                </Box>
              );
            })
          )}
        </Box>
      )}

      {!loading && view.kind === "detail" && incident && (
        <Box flexDirection="column" marginTop={1}>
          <Text>
            <Text bold>
              {incident.service}/{incident.env}
            </Text>{" "}
            <Text color={impactColor(incident.impact?.impact)}>{incident.impact?.impact}</Text>{" "}
            <Text dimColor>{incident.status}</Text>
          </Text>
          <Text dimColor>{incident.impact?.summary}</Text>
          <Box marginTop={1} flexDirection="column">
            <Text bold>Signals</Text>
            {Object.entries(incident.signals || {}).map(([k, v]: any) => (
              <Text key={k} dimColor>
                - {k}: {v.state} (trend {v.trend})
              </Text>
            ))}
          </Box>
          <Box marginTop={1} flexDirection="column">
            <Text bold>Recent alerts</Text>
            {incident.alerts.slice(-6).reverse().map((a) => (
              <Text key={a.id} dimColor>
                - {a.provider} {a.severity} {a.signalType}: {a.message}
              </Text>
            ))}
          </Box>
        </Box>
      )}

      {!loading && view.kind === "report" && (
        <Box flexDirection="column" marginTop={1}>
          <Text bold>Report</Text>
          <Box marginTop={1} flexDirection="column">
            {view.text.split("\n").slice(0, 60).map((line, idx) => (
              <Text key={idx} dimColor>
                {line}
              </Text>
            ))}
            {view.text.split("\n").length > 60 && (
              <Text dimColor>… (truncated)</Text>
            )}
          </Box>
        </Box>
      )}
    </Box>
  );
}

export async function runTui() {
  render(<TuiApp />);
}


