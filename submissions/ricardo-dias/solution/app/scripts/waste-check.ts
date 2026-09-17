// A calculadora TS (lib/waste.ts) reproduz o diagnóstico do Python?
// Uso: node scripts/waste-check.ts   (requer analysis/02_diagnostico.py rodado antes)
import { readFileSync } from "node:fs";
import { assumptionValues, computeWaste } from "../lib/waste.ts";
import type { DiagnosticoReport } from "../lib/types.ts";

const report: DiagnosticoReport = JSON.parse(readFileSync(new URL("../data/diagnostico.json", import.meta.url), "utf-8"));
const values = assumptionValues(report.assumptions);
const ts = computeWaste(values);

let ok = true;
report.waste.forEach((py, i) => {
  const t = ts[i];
  const diff = Math.abs(py.recoverableHoursPerYear - t.recoverableHoursPerYear) + Math.abs(py.hoursPerYear - t.hoursPerYear);
  const same = py.step === t.step && diff < 0.2;
  ok &&= same;
  console.log(`${same ? "ok  " : "FAIL"} ${py.step}: py=${py.recoverableHoursPerYear} ts=${t.recoverableHoursPerYear}`);
});

// Sensibilidade: dobrar o custo/hora não pode mudar horas; zerar a cobertura zera a triagem recuperável.
const zero = computeWaste({ ...values, auto_coverage: 0 });
ok &&= zero[0].recoverableHoursPerYear === 0 && zero[1].recoverableHoursPerYear === 0;
if (!ok) {
  console.error("FALHOU: lib/waste.ts diverge de 02_diagnostico.py");
  process.exit(1);
}
console.log("OK");
