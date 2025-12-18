import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { fetchLlmModels, generateReport, getIncident, updateIncidentResolution, updateLlmWeights } from "../api";
import type { Incident, LlmModelsResponse, LlmWeightsPreset, ResolutionStatus } from "../types";
import { useSseRevision } from "../sse";

function impactVariant(impact: string) {
  if (impact === "major") return "destructive" as const;
  if (impact === "minor") return "default" as const;
  return "secondary" as const;
}

function stateVariant(state?: string) {
  if (state === "critical") return "destructive" as const;
  if (state === "warning") return "default" as const;
  return "secondary" as const;
}

type ReportFormat = "markdown" | "text" | "json";

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { revision } = useSseRevision();

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [format, setFormat] = useState<ReportFormat>("markdown");
  const [llm, setLlm] = useState<"auto" | "off" | "openai" | "anthropic">("auto");
  const [reportByFormat, setReportByFormat] = useState<Record<ReportFormat, string>>({
    markdown: "",
    text: "",
    json: "",
  });
  const [reportError, setReportError] = useState<string | null>(null);
  const [reportBusyFormat, setReportBusyFormat] = useState<ReportFormat | null>(null);
  const reportReqIdRef = useRef(0);
  const [resolutionBusy, setResolutionBusy] = useState(false);
  const [resolutionError, setResolutionError] = useState<string | null>(null);
  const [llmMeta, setLlmMeta] = useState<LlmModelsResponse | null>(null);
  const [model, setModel] = useState<string | undefined>(undefined);
  const [llmWeightsPreset, setLlmWeightsPreset] = useState<LlmWeightsPreset>("balanced");
  const [llmWeightsBusy, setLlmWeightsBusy] = useState(false);
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getIncident(id)
      .then((data) => {
        if (cancelled) return;
        setIncident(data);
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
  }, [id, revision]);

  // Reset report cache when switching to a different incident.
  useEffect(() => {
    setReportByFormat({ markdown: "", text: "", json: "" });
    setReportError(null);
    setReportBusyFormat(null);
    reportReqIdRef.current += 1; // invalidate any in-flight request
  }, [incident?.id]);

  // Fetch available LLM providers + models once.
  useEffect(() => {
    let cancelled = false;
    fetchLlmModels()
      .then((data) => {
        if (!cancelled) {
          setLlmMeta(data);
          // Infer initial preset from weights if both providers are present.
          const openai = data.providers.find((p) => p.id === "openai");
          const anthropic = data.providers.find((p) => p.id === "anthropic");
          if (openai && anthropic) {
            if (Math.abs(openai.weight - anthropic.weight) < 1e-6) {
              setLlmWeightsPreset("balanced");
            } else if (openai.weight > anthropic.weight) {
              setLlmWeightsPreset("prefer_openai");
            } else {
              setLlmWeightsPreset("prefer_anthropic");
            }
          }
        }
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
    if (llm === "openai" || llm === "anthropic") {
      const provider = llmMeta.providers.find((p) => p.id === llm);
      if (!provider) return;
      const availableModels = provider.models || [];
      const defaultModel = provider.defaultModel || availableModels[0];
      setModel((prev) =>
        prev && availableModels.includes(prev) ? prev : defaultModel
      );
    } else {
      setModel(undefined);
    }
  }, [llmMeta, llm]);

  const signals = useMemo(() => {
    const s = incident?.signals || {};
    return Object.entries(s).map(([k, v]) => ({ key: k, ...v }));
  }, [incident]);

  if (!id) {
    return (
      <div className="text-sm text-destructive">
        Missing incident id.
      </div>
    );
  }

  const reportOut = reportByFormat[format];
  const reportBusy = reportBusyFormat === format;

  const generateForFormat = async (targetFormat: ReportFormat) => {
    if (!incident) return;
    const reqId = ++reportReqIdRef.current;
    setReportError(null);
    setReportBusyFormat(targetFormat);
    try {
      // Only send an explicit model when a specific provider is selected.
      const providerSpecific = llm === "openai" || llm === "anthropic";
      const effectiveModel = providerSpecific ? model : undefined;
      const res = await generateReport(incident.id, targetFormat, llm, effectiveModel);
      // only apply if still the latest request
      if (reqId !== reportReqIdRef.current) return;
      setReportByFormat((prev) => ({ ...prev, [targetFormat]: res.body }));
    } catch (e: any) {
      if (reqId !== reportReqIdRef.current) return;
      setReportError(String(e?.message || e));
    } finally {
      if (reqId === reportReqIdRef.current) setReportBusyFormat(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/" className="text-sm text-muted-foreground hover:underline">
          ← Back to incidents
        </Link>
      </div>

      {loading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-destructive">Error: {error}</div>}

      {incident && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-3">
                <span>
                  {incident.service} <span className="text-muted-foreground">({incident.env})</span>
                </span>
                <Badge variant="outline">{incident.status}</Badge>
                <Badge
                  variant={impactVariant(incident.impact?.impact)}
                  className={incident.impact?.impact === "major" ? "impact-glow-major" : ""}
                >
                  {incident.impact?.impact}
                </Badge>
                <Badge variant="outline">{incident.impact?.classification}</Badge>
                <span className="text-xs text-muted-foreground">
                  confidence {incident.impact?.confidence}
                </span>
              </CardTitle>
              <CardDescription>
                <div className="text-xs text-muted-foreground">
                  Incident ID: <code>{incident.id}</code>
                </div>
                <div className="mt-2">
                  {incident.impact?.classification === "capacity_warning" ? (
                    <div className="rounded-md border border-amber-400/60 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                      <span className="font-semibold text-amber-300">Capacity warning:</span>{" "}
                      <span>{incident.impact?.summary || "Saturation is high, but no evidence of user impact yet."}</span>
                    </div>
                  ) : (
                    incident.impact?.summary || "—"
                  )}
                </div>
                <div className="mt-3">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 px-2 text-xs"
                    onClick={() => setSummaryModalOpen(true)}
                  >
                    View incident summary
                  </Button>
                </div>
                {incident.impact?.reasons?.length ? (
                  <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                    {incident.impact.reasons.slice(0, 6).map((r, idx) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>
                ) : null}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-3">
              {signals.map((s) => (
                <div key={s.key} className="rounded-lg border p-4">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium">{s.signalType || s.key}</div>
                    <Badge
                      variant={stateVariant(s.state)}
                      className={s.state === "critical" ? "impact-glow-critical" : ""}
                    >
                      {s.state}
                    </Badge>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    trend: {s.trend}
                  </div>
                  <div className="mt-2 text-xs">
                    observed: <span className="font-mono">{s.observed ?? "n/a"}{s.unit || ""}</span>
                  </div>
                  <div className="text-xs">
                    threshold: <span className="font-mono">{s.threshold ?? "n/a"}{s.unit || ""}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Generate situation report</CardTitle>
              <CardDescription>
                Output can be <code>text</code>, <code>markdown</code>, or <code>json</code>. LLM is optional (auto/off/OpenAI/Anthropic).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="text-sm text-muted-foreground">LLM:</div>
                <select
                  className="h-10 rounded-md border bg-background/50 px-3 text-sm"
                  value={llm}
                  onFocus={() => {
                    // Refresh models on focus for a "live" view of providers.
                    fetchLlmModels()
                      .then((data) => {
                        setLlmMeta(data);
                      })
                      .catch(() => {});
                  }}
                  onChange={(e) => setLlm(e.target.value as any)}
                >
                  <option value="auto">auto</option>
                  <option value="off">off</option>
                  <option value="openai">openai</option>
                  <option value="anthropic">anthropic</option>
                </select>

                {(llm === "openai" || llm === "anthropic") && (
                  <select
                    className="h-10 rounded-md border bg-background/50 px-3 text-sm"
                    value={model || ""}
                    onChange={(e) => setModel(e.target.value || undefined)}
                    disabled={
                      !llmMeta ||
                      !llmMeta.providers.find((p) => p.id === llm && p.available)?.models.length
                    }
                  >
                    {(() => {
                      const provider = llmMeta?.providers.find((p) => p.id === llm);
                      const models = provider?.models || [];
                      const labelPrefix = llm === "openai" ? "OpenAI" : "Anthropic";
                      if (!models.length) {
                        return (
                          <option value="">
                            {labelPrefix}: no models detected
                          </option>
                        );
                      }
                      return models.map((m) => (
                        <option key={m} value={m}>
                          {labelPrefix}: {m}
                        </option>
                      ));
                    })()}
                  </select>
                )}

                <Button
                  disabled={reportBusy}
                  onClick={async () => {
                    await generateForFormat(format);
                  }}
                >
                  {reportBusy ? "Generating…" : "Generate"}
                </Button>
              </div>

              {reportError && (
                <div className="text-sm text-destructive">Report error: {reportError}</div>
              )}

              {llmMeta && (
                <div className="space-y-2 rounded-md border bg-background/40 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-xs font-medium text-muted-foreground">
                      Auto mode weighting (when both providers are available)
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {llmMeta.providers.map((p) => (
                        <span key={p.id}>
                          {p.id}: {p.weight.toFixed(1)}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3 text-xs">
                    {[
                      { id: "balanced" as LlmWeightsPreset, label: "Balanced (1:1)" },
                      { id: "prefer_openai" as LlmWeightsPreset, label: "Prefer OpenAI (3:1)" },
                      { id: "prefer_anthropic" as LlmWeightsPreset, label: "Prefer Anthropic (1:3)" },
                    ].map((opt) => (
                      <button
                        key={opt.id}
                        type="button"
                        className={
                          "inline-flex items-center rounded-md border px-2 py-1 " +
                          (llmWeightsPreset === opt.id
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border bg-background/40 text-muted-foreground")
                        }
                        disabled={llmWeightsBusy}
                        onClick={async () => {
                          setLlmWeightsPreset(opt.id);
                          setLlmWeightsBusy(true);
                          try {
                            let weights: Record<string, number>;
                            if (opt.id === "balanced") {
                              weights = { openai: 1, anthropic: 1 };
                            } else if (opt.id === "prefer_openai") {
                              weights = { openai: 3, anthropic: 1 };
                            } else {
                              weights = { openai: 1, anthropic: 3 };
                            }
                            const updated = await updateLlmWeights(weights);
                            setLlmMeta(updated);
                          } catch {
                            // best-effort only
                          } finally {
                            setLlmWeightsBusy(false);
                          }
                        }}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <Tabs
                value={format}
                onValueChange={(v) => {
                  const next = v as ReportFormat;
                  setFormat(next);
                  // Auto-update report output when user clicks a different format tab.
                  void generateForFormat(next);
                }}
              >
                <TabsList>
                  <TabsTrigger value="markdown">markdown</TabsTrigger>
                  <TabsTrigger value="text">text</TabsTrigger>
                  <TabsTrigger value="json">json</TabsTrigger>
                </TabsList>
                <TabsContent value={format}>
                  <pre className="max-h-[420px] overflow-auto rounded-lg border bg-muted/40 p-4 text-xs leading-relaxed">
                    {reportOut || (reportBusy ? "Updating…" : "Click Generate to create a report…")}
                  </pre>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Resolution</CardTitle>
              <CardDescription>
                Mark how this incident was ultimately handled (resolved / auto-closed / false alert / accepted).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {resolutionError && (
                <div className="text-sm text-destructive">Resolution error: {resolutionError}</div>
              )}
              <div className="flex flex-wrap gap-2">
                {[
                  { id: "resolved", label: "Resolved" },
                  { id: "auto_closed", label: "Auto-closed" },
                  { id: "false_alert", label: "False alert" },
                  { id: "accepted", label: "Accepted / won't fix" },
                ].map((opt) => (
                  <Button
                    key={opt.id}
                    size="sm"
                    variant={incident.resolutionStatus === (opt.id as ResolutionStatus) ? "default" : "outline"}
                    disabled={resolutionBusy}
                    onClick={async () => {
                      setResolutionBusy(true);
                      setResolutionError(null);
                      try {
                        const updated = await updateIncidentResolution(
                          incident.id,
                          opt.id as ResolutionStatus,
                          incident.resolutionNote ?? undefined
                        );
                        setIncident(updated);
                      } catch (e: any) {
                        setResolutionError(String(e?.message || e));
                      } finally {
                        setResolutionBusy(false);
                      }
                    }}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Resolution note (optional)</div>
                <textarea
                  className="min-h-[80px] w-full rounded-md border bg-background/50 p-2 text-xs"
                  value={incident.resolutionNote ?? ""}
                  onChange={(e) => {
                    const value = e.target.value;
                    setIncident((prev) =>
                      prev ? { ...prev, resolutionNote: value.length ? value : null } : prev
                    );
                  }}
                  onBlur={async () => {
                    if (!incident.resolutionStatus || incident.resolutionStatus === "none") return;
                    setResolutionBusy(true);
                    setResolutionError(null);
                    try {
                      const updated = await updateIncidentResolution(
                        incident.id,
                        (incident.resolutionStatus as ResolutionStatus) || "resolved",
                        incident.resolutionNote ?? undefined
                      );
                      setIncident(updated);
                    } catch (e: any) {
                      setResolutionError(String(e?.message || e));
                    } finally {
                      setResolutionBusy(false);
                    }
                  }}
                  placeholder="Add context (e.g. root cause, why it was accepted / won't fix)…"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent alerts</CardTitle>
              <CardDescription>Last {incident.alerts.length} normalized alert events attached to this incident.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Signal</TableHead>
                    <TableHead>Observed</TableHead>
                    <TableHead>Threshold</TableHead>
                    <TableHead>Resolution</TableHead>
                    <TableHead>Message</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {incident.alerts.slice(-25).reverse().map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="text-muted-foreground">{new Date(a.receivedAt).toLocaleString()}</TableCell>
                      <TableCell>{a.provider}</TableCell>
                      <TableCell>
                        <Badge
                          variant={stateVariant(a.severity)}
                          className={a.severity === "critical" ? "impact-glow-critical" : ""}
                        >
                          {a.severity}
                        </Badge>
                      </TableCell>
                      <TableCell>{a.signalType}</TableCell>
                      <TableCell className="font-mono">
                        {a.observed ?? "n/a"}{a.unit || ""}
                      </TableCell>
                      <TableCell className="font-mono">
                        {a.threshold ?? "n/a"}{a.unit || ""}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {incident.resolutionStatus && incident.resolutionStatus !== "none"
                          ? incident.resolutionStatus.replace("_", " ")
                          : "—"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{a.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {summaryModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
              <div className="max-h-[80vh] w-full max-w-xl overflow-auto rounded-lg border bg-background p-5 shadow-xl">
                <div className="mb-3 flex items-center justify-between gap-4">
                  <h2 className="text-base font-semibold">
                    Incident summary — {incident.service} ({incident.env})
                  </h2>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 px-2 text-xs"
                    onClick={() => setSummaryModalOpen(false)}
                  >
                    Close
                  </Button>
                </div>
                <div className="space-y-3 text-sm">
                  <div>
                    <span className="font-medium">Impact:</span>{" "}
                    <span>{incident.impact?.impact} ({incident.impact?.classification})</span>
                  </div>
                  <div>
                    <span className="font-medium">Summary:</span>
                    <p className="mt-1 text-muted-foreground">
                      {incident.impact?.summary || "—"}
                    </p>
                  </div>
                  {incident.impact?.reasons?.length ? (
                    <div>
                      <span className="font-medium">Why we classified it this way:</span>
                      <ul className="mt-1 list-disc space-y-1 pl-5 text-muted-foreground">
                        {incident.impact.reasons.map((r, idx) => (
                          <li key={idx}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}


