// Teste de paridade: a inferência TypeScript reproduz as predições do scikit-learn?
// Uso: node scripts/parity.ts   (requer analysis/03_classifier.py rodado antes)
import { readFileSync } from "node:fs";
import { predict, type Doc, type ModelFile } from "../lib/classifier.ts";

const read = <T>(p: string): T => JSON.parse(readFileSync(new URL(p, import.meta.url), "utf-8"));
const model = read<ModelFile>("../data/model.json");
const holdout = read<{ items: Doc[] }>("../data/holdout.json").items;
const expected = new Map(
  read<{ id: number; label: string; confidence: number }[]>("../../analysis/out/parity_expected.json").map((e) => [e.id, e]),
);

let sameLabel = 0, maxDiff = 0, correct = 0;
for (const doc of holdout) {
  const { category, confidence } = predict(model, doc.text);
  const exp = expected.get(doc.id)!;
  if (category === exp.label) sameLabel++;
  if (category === doc.label) correct++;
  maxDiff = Math.max(maxDiff, Math.abs(confidence - exp.confidence));
}
const agreement = sameLabel / holdout.length;
console.log(`paridade de rótulo: ${(agreement * 100).toFixed(2)}% (${sameLabel}/${holdout.length})`);
console.log(`maior diferença de confiança: ${maxDiff.toExponential(2)}`);
console.log(`acurácia TS na amostra holdout: ${((correct / holdout.length) * 100).toFixed(2)}%`);
if (agreement < 0.999 || maxDiff > 1e-3) {
  console.error("FALHOU: TypeScript diverge do Python");
  process.exit(1);
}
console.log("OK");
