// Calculadora de desperdício: espelho exato de compute_waste() em analysis/02_diagnostico.py.
// A UI chama computeWaste() com as premissas editadas pelo usuário.
// scripts/waste-check.ts garante que o resultado bate com data/diagnostico.json.

import type { Assumption, WasteLine } from "./types";

export type AssumptionValues = Record<string, number>;

export const FTE_HOURS_PER_YEAR = 1_760;

export function assumptionValues(assumptions: Assumption[]): AssumptionValues {
  return Object.fromEntries(assumptions.map((a) => [a.id, a.value]));
}

const round = (x: number, digits: number) => Math.round(x * 10 ** digits) / 10 ** digits;

export function computeWaste(a: AssumptionValues): WasteLine[] {
  const v = a.annual_volume;

  const triage = (v * a.triage_minutes) / 60;
  const triageAuto = a.auto_coverage;

  const rework = (v * a.misroute_rate * a.rework_minutes) / 60;
  const residualError = 1 - a.auto_accuracy;
  const reworkAuto = a.misroute_rate > 0 ? a.auto_coverage * Math.max(0, 1 - residualError / a.misroute_rate) : 0;

  const followup = (v * a.pending_share * a.followups_per_pending * a.followup_minutes) / 60;
  const followupAuto = a.followup_automation;

  const drafting = (v * a.draft_minutes) / 60;
  const draftingAuto = a.draft_saving * (1 - a.human_only_share);

  const lines: [string, number, number, string][] = [
    ["Triagem manual (ler, classificar, rotear)", triage, triageAuto,
      "Classificador roteia sozinho os tickets com confiança e vocabulário conhecidos; o resto segue para triagem humana."],
    ["Retrabalho por roteamento errado", rework, reworkAuto,
      "Nos tickets roteados automaticamente, o erro cai da taxa manual para o erro medido do modelo."],
    ["Follow-up de tickets aguardando o cliente", followup, followupAuto,
      "Lembretes e fechamento por inatividade automáticos; humano retoma quando o cliente responde."],
    ["Redação de respostas", drafting, draftingAuto,
      "Rascunho sugerido reduz o tempo de escrita; nunca é enviado sem revisão. Não se aplica a casos só-humanos."],
  ];

  return lines.map(([step, hours, share, rationale]) => ({
    step,
    hoursPerYear: round(hours, 1),
    automatableShare: round(share, 4),
    recoverableHoursPerYear: round(hours * share, 1),
    rationale,
  }));
}

export function wasteTotals(lines: WasteLine[], a: AssumptionValues) {
  const hours = lines.reduce((s, l) => s + l.hoursPerYear, 0);
  const recoverable = lines.reduce((s, l) => s + l.recoverableHoursPerYear, 0);
  return {
    hours,
    recoverable,
    recoverableCost: recoverable * a.hourly_cost,
    fte: recoverable / FTE_HOURS_PER_YEAR,
  };
}
