export type ImpactLevel = "none" | "minor" | "major";
export type SignalType = "saturation" | "latency" | "errors" | "other";
export type SignalState = "ok" | "warning" | "critical";
export type Trend = "up" | "down" | "flat" | "unknown";

export interface ImpactAssessment {
  impact: ImpactLevel;
  confidence: number;
  classification: string;
  summary: string;
  reasons?: string[];
}

export interface SignalSnapshot {
  signalType: SignalType;
  state: SignalState;
  trend: Trend;
  observed?: number | null;
  threshold?: number | null;
  unit?: string | null;
  lastUpdatedAt?: string;
  history?: number[];
}

export type ResolutionStatus = "none" | "resolved" | "auto_closed" | "false_alert" | "accepted";

export interface IncidentSummary {
  id: string;
  service: string;
  env: string;
  status: string;
  updatedAt: string;
  impact: ImpactAssessment;
  signals: Record<string, SignalSnapshot>;
  resolutionStatus?: ResolutionStatus;
}

export interface AlertEvent {
  id: string;
  provider: string;
  receivedAt: string;
  service: string;
  env: string;
  severity: string;
  signalType: SignalType;
  metric?: string | null;
  observed?: number | null;
  threshold?: number | null;
  unit?: string | null;
  message?: string | null;
}

export interface Incident {
  id: string;
  service: string;
  env: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  impact: ImpactAssessment;
  signals: Record<string, SignalSnapshot>;
  alerts: AlertEvent[];
  resolutionStatus?: ResolutionStatus;
  resolutionNote?: string | null;
}

export interface LlmProviderInfo {
  id: string; // "openai" | "anthropic" | custom
  weight: number;
  available: boolean;
  defaultModel?: string | null;
  models: string[];
}

export interface LlmModelsResponse {
  providers: LlmProviderInfo[];
  autoOrder: string[];
}

export type LlmWeightsPreset = "balanced" | "prefer_openai" | "prefer_anthropic";


