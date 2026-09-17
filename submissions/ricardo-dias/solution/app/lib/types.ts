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
  // Teste se as diferenças entre segmentos são reais. Se significant=false, a UI deve
  // dizer que o "pior segmento" é indistinguível do acaso, em vez de destacá-lo.
  segmentTests: { variable: string; test: string; pValue: number; significant: boolean }[];
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
  autoRouting: { coverage: number; accuracy: number }; // com limiar de confiança + guarda de domínio
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
    confidentShare: number; // D1 com confiança ≥ limiar
    confidentPredictedHardware: number; // desses, fração prevista como Hardware (erro confiante)
    oodGuard: { threshold: number; inDomainFlagged: number; outDomainFlagged: number };
  };
}

// POST /api/classify { text } → ClassifyResponse
// POST /api/classify { texts: string[] } (até 500) → { results: ClassifyResponse[] } com similar = []
export type Route = "auto" | "revisao_humana" | "escalar";
export interface ClassifyResponse {
  category: Category;
  confidence: number;
  knownShare: number; // fração das palavras do ticket conhecidas pelo modelo (guarda de domínio)
  probabilities: { label: Category; p: number }[];
  topTerms: { term: string; weight: number }[]; // explicação: contribuição por termo
  route: Route;
  routeReason: string;
  draftAllowed: boolean; // false em escalações: a resposta é escrita por humano sênior
  similar: { text: string; label: Category; score: number }[];
}

// GET /api/sample?n=200  → tickets do holdout (nunca vistos no treino)
export interface SampleResponse {
  items: { id: number; text: string; label: Category }[];
}

// POST /api/draft { text, category } → stream de texto (rascunho para o agente aprovar)
