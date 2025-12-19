import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { chatSre, fetchLlmModels, listIncidents, runScenario } from "../api";
import type { IncidentSummary, LlmModelsResponse } from "../types";
import { useSseRevision } from "../sse";

function impactVariant(impact: string) {
  if (impact === "major") return "destructive" as const;
  if (impact === "minor") return "default" as const;
  return "secondary" as const;
}

function signalVariant(state?: string) {
  if (state === "critical") return "destructive" as const;
  if (state === "warning") return "default" as const;
  return "secondary" as const;
}

export function IncidentsPage() {
  const nav = useNavigate();
  const { revision } = useSseRevision();

  const [items, setItems] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [chatOutput, setChatOutput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [chatLlm, setChatLlm] = useState<"auto" | "off" | "openai" | "anthropic">("auto");
  const [chatModel, setChatModel] = useState<string | undefined>(undefined);
  const [llmMeta, setLlmMeta] = useState<LlmModelsResponse | null>(null);

  // Sanitize input on the client side (defense in depth)
  const sanitizeInput = (text: string): string => {
    if (!text) return "";
    
    // Remove HTML/XML tags using regex (doesn't require DOM)
    let sanitized = text.replace(/<[^>]+>/g, "");
    
    // Remove control characters except newline (\n) and tab (\t)
    sanitized = sanitized.replace(/[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]/g, "");
    
    // Limit length (10,000 characters to match backend)
    const MAX_LENGTH = 10000;
    if (sanitized.length > MAX_LENGTH) {
      sanitized = sanitized.substring(0, MAX_LENGTH) + "... [truncated]";
    }
    
    return sanitized.trim();
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listIncidents(100)
      .then((data) => {
        if (cancelled) return;
        setItems(data);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e?.message || e));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [revision]);

  // Fetch available LLM providers + models once on mount.
  useEffect(() => {
    let cancelled = false;
    fetchLlmModels()
      .then((data) => {
        if (!cancelled) setLlmMeta(data);
      })
      .catch(() => {
        // best-effort only; fall back to env-configured defaults
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Keep model selection in sync with provider + metadata.
  useEffect(() => {
    if (!llmMeta) return;
    if (chatLlm === "openai" || chatLlm === "anthropic") {
      const provider = llmMeta.providers.find((p) => p.id === chatLlm);
      if (!provider) return;
      const availableModels = provider.models || [];
      const defaultModel = provider.defaultModel || availableModels[0];
      setChatModel((prev) =>
        prev && availableModels.includes(prev) ? prev : defaultModel
      );
    } else {
      setChatModel(undefined);
    }
  }, [llmMeta, chatLlm]);

  const empty = useMemo(() => !loading && !error && items.length === 0, [items, loading, error]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Ask the SRE agent</CardTitle>
          <CardDescription>
            Paste metrics, logs, or deployment notes and get a concise SRE‑style recommendation.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span className="font-medium">Suggested prompts:</span>
            <button
              type="button"
              className="rounded-md border border-border bg-background/60 px-2 py-1 hover:bg-accent hover:text-accent-foreground"
              onClick={() =>
                setChatInput(
                  "Here are the metrics from my API service:\n- p95 latency: 340ms (baseline: 180ms)\n- Error rate: 1.2%\n- CPU: 85%\n- Memory: 72%\n\nShould I be concerned?"
                )
              }
            >
              API metrics: “Should I be concerned?”
            </button>
            <button
              type="button"
              className="rounded-md border border-border bg-background/60 px-2 py-1 hover:bg-accent hover:text-accent-foreground"
              onClick={() =>
                setChatInput(
                  "Can you review this Prometheus data from the last hour?\n[paste metrics or screenshot]"
                )
              }
            >
              Prometheus data review
            </button>
            <button
              type="button"
              className="rounded-md border border-border bg-background/60 px-2 py-1 hover:bg-accent hover:text-accent-foreground"
              onClick={() =>
                setChatInput(
                  "We deployed v2.3.0 at 14:15 UTC and now we're seeing:\n- 500 errors jumped from 0.1% to 3.5%\n- Started at 14:18 UTC\n- Top error: NullPointerException in UserService\n\nWhat should we do?"
                )
              }
            >
              Post‑deploy regression
            </button>
            <button
              type="button"
              className="rounded-md border border-border bg-background/60 px-2 py-1 hover:bg-accent hover:text-accent-foreground"
              onClick={() =>
                setChatInput(
                  "My Datadog dashboard shows:\n- CPU: 78% (up from 55%)\n- Latency: p95 150ms (SLO: <200ms)\n- Errors: 0.05%\n\nEverything within SLO but CPU is elevated. Thoughts?"
                )
              }
            >
              Elevated CPU, within SLO
            </button>
            <button
              type="button"
              className="rounded-md border border-border bg-background/60 px-2 py-1 hover:bg-accent hover:text-accent-foreground"
              onClick={() =>
                setChatInput(
                  "CloudWatch shows RDS CPU at 92%, and my application logs in Elastic show slow database queries. New Relic APM shows p95 latency at 2.3s.\n\nCan you analyze this?"
                )
              }
            >
              Cross‑tool analysis (RDS / logs / APM)
            </button>
          </div>

          <div className="space-y-2">
            <textarea
              className="min-h-[120px] w-full rounded-md border bg-background/60 p-3 text-sm"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Paste metrics, logs, or deployment notes here…"
            />
            <div className="flex flex-wrap items-center gap-3">
              <div className="text-sm text-muted-foreground">LLM:</div>
              <select
                className="h-9 rounded-md border bg-background/50 px-2 text-sm"
                value={chatLlm}
                onChange={(e) => setChatLlm(e.target.value as any)}
                onFocus={() => fetchLlmModels().then(setLlmMeta).catch(() => {})}
              >
                <option value="auto">auto</option>
                <option value="off">off</option>
                <option value="openai">openai</option>
                <option value="anthropic">anthropic</option>
              </select>

              {(chatLlm === "openai" || chatLlm === "anthropic") && (
                <select
                  className="h-9 rounded-md border bg-background/50 px-2 text-sm"
                  value={chatModel || ""}
                  onChange={(e) => setChatModel(e.target.value || undefined)}
                  disabled={
                    !llmMeta ||
                    !llmMeta.providers.find((p) => p.id === chatLlm && p.available)?.models.length
                  }
                >
                  {(() => {
                    const provider = llmMeta?.providers.find((p) => p.id === chatLlm);
                    const models = provider?.models || [];
                    const labelPrefix = chatLlm === "openai" ? "OpenAI" : "Anthropic";
                    if (!models.length) {
                      return (
                        <option value="">
                          {labelPrefix}: no models detected
                        </option>
                      );
                    }
                    return models.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ));
                  })()}
                </select>
              )}

              <Button
                size="sm"
                disabled={chatBusy || !chatInput.trim()}
                onClick={async () => {
                  setChatBusy(true);
                  setChatError(null);
                  try {
                    // Sanitize input before sending
                    const sanitized = sanitizeInput(chatInput);
                    if (!sanitized) {
                      setChatError("Input is empty after sanitization");
                      setShowErrorModal(true);
                      return;
                    }
                    
                    const providerSpecific = chatLlm === "openai" || chatLlm === "anthropic";
                    const effectiveModel = providerSpecific ? chatModel : undefined;
                    const out = await chatSre(sanitized, chatLlm, effectiveModel);
                    setChatOutput(out);
                  } catch (e: any) {
                    const errorMsg = String(e?.message || e);
                    // Try to extract friendly message from JSON error
                    let friendlyError = errorMsg;
                    try {
                      const match = errorMsg.match(/\{.*"error".*\}/);
                      if (match) {
                        const errorData = JSON.parse(match[0]);
                        if (errorData.error?.message) {
                          friendlyError = errorData.error.message;
                        }
                      }
                    } catch {
                      // Keep original error if parsing fails
                    }
                    setChatError(friendlyError);
                    setShowErrorModal(true);
                  } finally {
                    setChatBusy(false);
                  }
                }}
              >
                {chatBusy ? "Asking…" : "Ask SRE agent"}
              </Button>
            </div>
          </div>

          {chatOutput && (
            <div className="prose prose-sm prose-invert max-w-none max-h-[320px] overflow-auto rounded-md border bg-muted/40 p-4">
              <ReactMarkdown>{chatOutput}</ReactMarkdown>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-primary/5" />
        <CardHeader>
          <CardTitle className="text-balance">
            Correlate alerts into incidents, then generate a situation report
          </CardTitle>
          <CardDescription>
            Demo scenarios let you see the key behavior: <span className="font-medium text-foreground">high saturation alone is not an incident</span> if latency/errors are normal.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={async () => {
              const res = await runScenario("saturation_only");
              if (res.lastIncidentId) nav(`/incidents/${res.lastIncidentId}`);
            }}
          >
            saturation_only (no impact)
          </Button>
          <Button
            variant="destructive"
            onClick={async () => {
              const res = await runScenario("full_outage");
              if (res.lastIncidentId) nav(`/incidents/${res.lastIncidentId}`);
            }}
          >
            full_outage (major)
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Incidents</CardTitle>
          <CardDescription>
            Correlated incidents across providers, grouped by service + env.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading && <div className="text-sm text-muted-foreground">Loading…</div>}
          {error && <div className="text-sm text-destructive">Error: {error}</div>}
          {empty && (
            <div className="text-sm text-muted-foreground">
              No incidents yet. Run a scenario above or POST alerts to `/api/ingest`.
            </div>
          )}

          {!loading && !error && items.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Service</TableHead>
                  <TableHead>Env</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Impact</TableHead>
                  <TableHead>Signals</TableHead>
                  <TableHead>Classification</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((i) => (
                  <TableRow
                    key={i.id}
                    className="cursor-pointer"
                    onClick={() => nav(`/incidents/${i.id}`)}
                  >
                    <TableCell className="font-medium">{i.service}</TableCell>
                    <TableCell>{i.env}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{i.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={impactVariant(i.impact?.impact)}
                        className={i.impact?.impact === "major" ? "impact-glow-major" : ""}
                      >
                        {i.impact?.impact}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant={signalVariant((i.signals as any)?.saturation?.state)}>
                          sat {(i.signals as any)?.saturation?.state || "n/a"}
                        </Badge>
                        <Badge variant={signalVariant((i.signals as any)?.latency?.state)}>
                          lat {(i.signals as any)?.latency?.state || "n/a"}
                        </Badge>
                        <Badge variant={signalVariant((i.signals as any)?.errors?.state)}>
                          err {(i.signals as any)?.errors?.state || "n/a"}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell
                      className={
                        i.impact?.classification === "capacity_warning"
                          ? "text-amber-300"
                          : "text-muted-foreground"
                      }
                    >
                      {i.impact?.classification}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(i.updatedAt).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {showErrorModal && chatError && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setShowErrorModal(false)}
        >
          <div
            className="max-w-lg rounded-lg border bg-card p-6 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-3 text-lg font-semibold text-destructive">Error</h3>
            <p className="mb-4 text-sm text-foreground">{chatError}</p>
            <Button size="sm" onClick={() => setShowErrorModal(false)}>
              Close
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}


