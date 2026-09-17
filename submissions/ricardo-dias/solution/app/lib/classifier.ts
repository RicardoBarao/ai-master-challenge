// Inferência do classificador exportado por analysis/03_classifier.py.
// Reproduz o TfidfVectorizer do scikit-learn: tokens [a-z]{2,}, unigramas + bigramas,
// tf sublinear (1 + ln tf), idf suavizado (já calculado), normalização L2.
// Sem dependências de Node: é importado pela rota da API e pelo teste de paridade.

import type { Category, ClassifyResponse, Route } from "./types";

export interface ModelFile {
  version: number;
  classes: Category[];
  threshold: number;
  oodThreshold: number; // fração mínima de palavras conhecidas pelo modelo
  stopWords: string[]; // ignoradas no cálculo de knownShare
  idf: Record<string, number>;
  weights: Record<string, number[]>;
  intercept: number[];
}

export interface Doc {
  id: number;
  text: string;
  label: Category;
}

type SparseVec = Map<string, number>;

export function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function tokenize(text: string): string[] {
  return normalize(text).match(/\b[a-z]{2,}\b/g) ?? [];
}

export function vectorize(text: string, idf: Record<string, number>): SparseVec {
  const tokens = tokenize(text);
  const counts = new Map<string, number>();
  const add = (term: string) => {
    if (idf[term] !== undefined) counts.set(term, (counts.get(term) ?? 0) + 1);
  };
  tokens.forEach((t, i) => {
    add(t);
    if (i + 1 < tokens.length) add(`${t} ${tokens[i + 1]}`);
  });

  const vec: SparseVec = new Map();
  let norm = 0;
  for (const [term, tf] of counts) {
    const v = (1 + Math.log(tf)) * idf[term];
    vec.set(term, v);
    norm += v * v;
  }
  norm = Math.sqrt(norm);
  if (norm > 0) for (const [term, v] of vec) vec.set(term, v / norm);
  return vec;
}

function softmax(z: number[]): number[] {
  const max = Math.max(...z);
  const e = z.map((v) => Math.exp(v - max));
  const sum = e.reduce((a, b) => a + b, 0);
  return e.map((v) => v / sum);
}

// Fração das palavras de conteúdo (sem stopwords) que o modelo conhece.
// Mesma regra de known_share no Python.
const stopWordSets = new WeakMap<string[], Set<string>>();
export function knownShare(text: string, model: Pick<ModelFile, "idf" | "stopWords">): number {
  let stop = stopWordSets.get(model.stopWords);
  if (!stop) stopWordSets.set(model.stopWords, (stop = new Set(model.stopWords)));
  const tokens = tokenize(text).filter((t) => !stop.has(t));
  if (tokens.length === 0) return 0;
  return tokens.filter((t) => model.idf[t] !== undefined).length / tokens.length;
}

export function predict(model: ModelFile, text: string) {
  const vec = vectorize(text, model.idf);
  const z = [...model.intercept];
  for (const [term, x] of vec) {
    const w = model.weights[term];
    if (w) for (let k = 0; k < z.length; k++) z[k] += x * w[k];
  }
  const probs = softmax(z);
  let best = 0;
  for (let k = 1; k < probs.length; k++) if (probs[k] > probs[best]) best = k;

  const topTerms = [...vec]
    .map(([term, x]) => ({ term, weight: x * (model.weights[term]?.[best] ?? 0) }))
    .filter((t) => t.weight > 0)
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 8)
    .map((t) => ({ term: t.term, weight: Math.round(t.weight * 1000) / 1000 }));

  return {
    vec,
    category: model.classes[best],
    confidence: probs[best],
    knownShare: knownShare(text, model),
    probabilities: model.classes
      .map((label, k) => ({ label, p: probs[k] }))
      .sort((a, b) => b.p - a.p),
    topTerms,
  };
}

// ---- Política de roteamento (docs/automacao.md) ----
// Regras explícitas e auditáveis; não são aprendidas.

// Sinais de risco/urgência → humano sênior, independentemente da confiança do modelo.
const ESCALATION_TERMS = [
  "urgent", "urgently", "asap", "immediately", "critical", "outage", "breach", "hacked", "virus",
  "malware", "phishing", "fraud", "legal", "lawsuit", "complaint", "cancel", "cancellation", "refund",
];

// Concessão de privilégio nunca é automática: roteia, mas exige aprovação humana.
const ALWAYS_HUMAN: Partial<Record<Category, string>> = {
  "Administrative rights": "Pedido de privilégio administrativo exige aprovação humana (risco de segurança).",
};

export function decideRoute(
  text: string,
  category: Category,
  confidence: number,
  known: number,
  model: Pick<ModelFile, "threshold" | "oodThreshold">,
): { route: Route; routeReason: string; draftAllowed: boolean } {
  const { threshold, oodThreshold } = model;
  const tokens = new Set(tokenize(text));
  const hits = ESCALATION_TERMS.filter((t) => tokens.has(t));
  if (hits.length > 0) {
    return {
      route: "escalar",
      routeReason: `Sinal de risco/urgência no texto (${hits.join(", ")}): vai direto para atendente sênior.`,
      draftAllowed: false,
    };
  }
  // Medido: fora do domínio o modelo erra com confiança alta. Vocabulário desconhecido → humano.
  if (known < oodThreshold) {
    return {
      route: "revisao_humana",
      routeReason: `Só ${(known * 100).toFixed(0)}% das palavras são conhecidas pelo modelo (mínimo ${(oodThreshold * 100).toFixed(0)}%): texto fora do padrão do treino, triagem humana.`,
      draftAllowed: true,
    };
  }
  if (confidence < threshold) {
    return {
      route: "revisao_humana",
      routeReason: `Confiança ${(confidence * 100).toFixed(0)}% abaixo do limiar de ${(threshold * 100).toFixed(0)}%: triagem humana confirma a categoria.`,
      draftAllowed: true,
    };
  }
  const human = ALWAYS_HUMAN[category];
  if (human) return { route: "revisao_humana", routeReason: human, draftAllowed: true };
  return {
    route: "auto",
    routeReason: `Confiança ${(confidence * 100).toFixed(0)}% ≥ limiar de ${(threshold * 100).toFixed(0)}%: roteado automaticamente para a fila ${category}.`,
    draftAllowed: true,
  };
}

// ---- Tickets similares (cosseno TF-IDF sobre amostra do treino) ----

let neighborCache: { docs: Doc[]; vecs: SparseVec[] } | null = null;

export function similar(model: ModelFile, docs: Doc[], query: SparseVec, k = 3) {
  if (!neighborCache || neighborCache.docs !== docs) {
    neighborCache = { docs, vecs: docs.map((d) => vectorize(d.text, model.idf)) };
  }
  const scored: { text: string; label: Category; score: number }[] = [];
  neighborCache.vecs.forEach((v, i) => {
    let dot = 0;
    const [small, large] = query.size < v.size ? [query, v] : [v, query];
    for (const [term, x] of small) {
      const y = large.get(term);
      if (y) dot += x * y;
    }
    if (dot > 0) scored.push({ text: docs[i].text, label: docs[i].label, score: Math.round(dot * 1000) / 1000 });
  });
  return scored.sort((a, b) => b.score - a.score).slice(0, k);
}

export function classify(model: ModelFile, neighbors: Doc[], text: string): ClassifyResponse {
  const { vec, category, confidence, knownShare: known, probabilities, topTerms } = predict(model, text);
  const { route, routeReason, draftAllowed } = decideRoute(text, category, confidence, known, model);
  return {
    category,
    confidence,
    knownShare: known,
    probabilities,
    topTerms,
    route,
    routeReason,
    draftAllowed,
    similar: similar(model, neighbors, vec),
  };
}
