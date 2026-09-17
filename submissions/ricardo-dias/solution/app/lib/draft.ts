// Rascunho de resposta com a política aplicada NO SERVIDOR.
// O cliente envia só o texto; categoria e permissão são recalculadas aqui, antes de qualquer
// chamada ao provedor de LLM. A categoria enviada pelo cliente é ignorada.

import { classifyTicket } from "./classifier";
import type { Model, PolicyRules } from "./model-schema";
import type { Category } from "./types";
import { readJsonObject, validateText } from "./validation";

export interface DraftDeps {
  getModel: () => Model;
  getRules: () => PolicyRules;
  hasProvider: () => boolean;
  generate: (input: { text: string; category: Category }) => Response | Promise<Response>;
}

export function createDraftHandler(deps: DraftDeps) {
  return async function POST(request: Request): Promise<Response> {
    const parsed = await readJsonObject(request);
    if (!parsed.ok) return Response.json({ error: parsed.error }, { status: parsed.status });
    const input = validateText(parsed.body.text);
    if (!input.ok) return Response.json({ error: input.error }, { status: input.status });

    const result = classifyTicket(deps.getModel(), deps.getRules(), input.text, null);
    if (!result.draftAllowed) {
      return Response.json(
        {
          error: "Rascunho bloqueado pela política: este ticket é respondido por um atendente sênior.",
          route: result.route,
          routeReason: result.routeReason,
        },
        { status: 403 },
      );
    }
    if (!deps.hasProvider()) {
      return Response.json(
        { error: "Rascunho desativado: configure AI_GATEWAY_API_KEY. A classificação e o roteamento funcionam sem LLM." },
        { status: 503 },
      );
    }
    const response = await deps.generate({ text: input.text, category: result.category });
    response.headers.set("X-Draft-Category", result.category);
    return response;
  };
}
