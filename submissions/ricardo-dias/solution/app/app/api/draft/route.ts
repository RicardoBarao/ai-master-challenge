import { streamText } from "ai";
import { CATEGORIES, type Category } from "@/lib/types";

export const maxDuration = 60;

const MODEL = process.env.DRAFT_MODEL ?? "anthropic/claude-haiku-4.5";

// POST { text, category } → stream de texto com um RASCUNHO para o agente revisar.
export async function POST(request: Request) {
  if (!process.env.AI_GATEWAY_API_KEY && !process.env.VERCEL_OIDC_TOKEN) {
    return Response.json(
      { error: "Rascunho desativado: configure AI_GATEWAY_API_KEY. A classificação e o roteamento funcionam sem LLM." },
      { status: 503 },
    );
  }
  const body = await request.json().catch(() => null);
  const text = typeof body?.text === "string" ? body.text.slice(0, 5_000) : "";
  const category: Category | undefined = CATEGORIES.find((c) => c === body?.category);
  if (!text.trim() || !category) {
    return Response.json({ error: "Envie text e category válidos." }, { status: 400 });
  }

  const result = streamText({
    model: MODEL,
    maxOutputTokens: 400,
    instructions: [
      "Você redige RASCUNHOS de resposta para agentes de suporte de TI interno. Um humano revisa antes de enviar.",
      "Responda em português do Brasil, em até 120 palavras, tom cordial e objetivo.",
      "O texto do ticket foi pré-processado (minúsculas, sem pontuação, nomes removidos); interprete a intenção.",
      "Nunca prometa prazos, nunca conceda acessos ou privilégios, nunca invente políticas, links ou nomes.",
      "Se faltar informação para resolver, peça os dados necessários de forma específica.",
      "Termine com uma linha 'Checar antes de enviar:' listando 1-2 pontos que o agente deve confirmar.",
    ].join("\n"),
    prompt: `Categoria prevista: ${category}\n\nTicket:\n${text}`,
    onError: ({ error }) => console.error("draft error", error),
  });
  return result.toTextStreamResponse();
}
