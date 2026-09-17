import { classify, predict, decideRoute } from "@/lib/classifier";
import { getModel, getNeighbors } from "@/lib/server-data";

const MAX_CHARS = 5_000;
const MAX_BATCH = 500;

// POST { text } → ClassifyResponse
// POST { texts: string[] } → { results: ClassifyResponse[] } (sem "similar", para lote rápido)
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const model = getModel();

  if (body && Array.isArray(body.texts)) {
    const texts: unknown[] = body.texts.slice(0, MAX_BATCH);
    const results = texts.map((t) => {
      const text = String(t).slice(0, MAX_CHARS);
      const { category, confidence, knownShare, probabilities, topTerms } = predict(model, text);
      const route = decideRoute(text, category, confidence, knownShare, model);
      return { category, confidence, knownShare, probabilities, topTerms, ...route, similar: [] };
    });
    return Response.json({ results });
  }

  const text = typeof body?.text === "string" ? body.text.slice(0, MAX_CHARS) : "";
  if (text.trim().split(/\s+/).length < 2) {
    return Response.json({ error: "Envie o texto do ticket (pelo menos 2 palavras)." }, { status: 400 });
  }
  return Response.json(classify(model, getNeighbors(), text));
}
