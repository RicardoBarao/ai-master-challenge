// Contratos entre a análise (Python → app/data/*.json) e a UI.
// Dono: Claude Code. Para mudar, registrar o pedido em ../../../HANDOFF.md.

export const CATEGORIES = [
  "Hardware",
  "HR Support",
  "Access",
  "Miscellaneous",
  "Storage",
  "Purchase",
  "Internal Project",
  "Administrative rights",
] as const;
export type Category = (typeof CATEGORIES)[number];

export type Severity = "bloqueante" | "alerta" | "info";

// data/audit.json
export interface AuditFinding {
  id: string;
  dataset: "D1" | "D2";
  title: string;
  evidence: string; // frase curta com o número que prova o achado
  metric?: number | string;
  implication: string; // o que isso muda na análise
  severity: Severity;
}
export interface AuditReport {
  generatedAt: string;
  d1: { rows: number; columns: number; statusMix: { status: string; n: number; share: number }[] };
  d2: { rows: number; classes: { label: Category; n: number; share: number }[] };
  findings: AuditFinding[];
}

// data/diagnostico.json
export interface Assumption {
  id: string;
  label: string;
  value: number;
  unit: string;
  source: string; // de onde veio a premissa (benchmark, dado, julgamento)
  editable: boolean; // a UI pode expor como input
}
export interface SegmentCell {
  channel: string;
  priority: string;
  n: number;
  backlogShare: number; // Open + Pending / total
  pendingCustomerShare: number;
  csatMean: number | null;
}
export interface CsatDriver {
  variable: string;
  test: string;
  pValue: number;
  effectSize: number;
  groups: { label: string; mean: number; n: number }[];
}
export interface WasteLine {
  step: string; // ex.: "Triagem manual"
  hoursPerYear: number;
  automatableShare: number; // 0..1
  recoverableHoursPerYear: number;
  rationale: string;
}
export interface DiagnosticoReport {
  generatedAt: string;
  nTickets: number;
  annualVolume: number; // volume de referência do enunciado (30k)
  headline: { label: string; value: string; detail: string }[];
  segments: SegmentCell[];
  worstSegments: SegmentCell[];
  csatDrivers: CsatDriver[];
  assumptions: Assumption[];
  waste: WasteLine[];
}

// data/model_metrics.json
export interface ModelMetrics {
  generatedAt: string;
  split: { train: number; test: number; seed: number };
  candidates: { name: string; accuracy: number; macroF1: number }[];
  chosen: string;
  perClass: { label: Category; precision: number; recall: number; f1: number; support: number }[];
  confusion: { labels: Category[]; matrix: number[][] };
  coverage: { threshold: number; coverage: number; accuracy: number }[];
  recommendedThreshold: number;
  llmFallback?: {
    model: string;
    n: number;
    accuracyLocal: number;
    accuracyLlm: number;
    costUsd: number;
    p50LatencyMs: number;
  };
  crossDomain?: {
    note: string;
    confidenceHistogram: { bucket: string; share: number }[];
  };
}

// POST /api/classify  { text: string }
export type Route = "auto" | "revisao_humana" | "escalar";
export interface ClassifyResponse {
  category: Category;
  confidence: number;
  probabilities: { label: Category; p: number }[];
  topTerms: { term: string; weight: number }[]; // explicação: contribuição por termo
  route: Route;
  routeReason: string;
  similar: { text: string; label: Category; score: number }[];
}

// GET /api/sample?n=200  → tickets do holdout (nunca vistos no treino)
export interface SampleResponse {
  items: { id: number; text: string; label: Category }[];
}

// POST /api/draft { text, category } → stream de texto (rascunho para o agente aprovar)
