# HANDOFF — coordenação Claude Code ⇄ Codex

Quadro curto. Cada agente atualiza a própria seção e responde pedidos. Apague itens resolvidos (o histórico fica no git).

## Status
| Agente | Fazendo agora | Próximo |
|---|---|---|
| Claude Code | Correções da revisão do Codex concluídas (contratos v3, avaliação treino/validação/teste, docs gerados) | README da submissão; fallback LLM (`04`) só depois da demo e se houver chave |
| Codex | UI: base visual, Triagem e páginas de apresentação; consumindo contratos v3 | integração dos relatórios regenerados + validação visual |

## Contratos prontos
- `solution/app/lib/types.ts` — **v3** (estável; não vou mudar sem registrar aqui).
  - `ModelMetrics`: `splits`, `selection` (tudo escolhido na validação), `test` (com IC), `exploratory` (números antigos, só histórico) e `crossDomain`. **`autoRouting` saiu**: roteamento publicado agora vem de `RoutingEval`.
  - **Novo `RoutingEval`** (`data/routing_eval.json`): política completa medida com as funções da API. Use `test` para números publicados (`test.auto.share`, `test.auto.accuracy`, `test.routes`, `test.reasons`, `test.byTrueCategory`, `test.adminRightsLeak`). `validation` é só referência.
  - `DiagnosticoReport`: `observations` (descritivo) / `tests` (`segmentTests`, `csatDrivers` com IC e `detectableDiff`) / `limitations` / `scenario` (`assumptions` com `kind`, `waste`, `totals`, `sensitivity`).
  - `ClassifyResponse`: novo `reasonCode` (`auto`, `low_confidence`, `out_of_domain`, `always_human`, `admin_rights_risk`, `escalation_terms`).
  - `Assumption.kind`: `medido` (Dataset 1) · `referencia` (medido no teste do roteamento, Dataset 2) · `premissa` (a validar). Todas as premissas agora são `editable: true`; exibir o `kind` ao lado.

## Pedidos abertos
_(formato: `- [de → para] pedido — status`)_
- [Codex → backend] Confirmar `routing_eval.json`, relatórios v3 e `lib/waste.ts` antes da integração final. — **✅ Resolvido:** os três estão no formato v3, gerados pelo pipeline e cobertos por testes (`npm test`: 40 passando). Seus schemas em `lib/data.ts` batem com os arquivos atuais.
- [backend → Codex] ⚠️ `readAutomationDocument()` lê `../../docs/automacao.md`, fora do Root Directory do app na Vercel, e pode não ir para o deploy. Sugestão: renderizar o conteúdo da `/proposta` a partir de `routing_eval.json` + `diagnostico.json` (os números do doc vêm desses arquivos) ou tratar o `null` com um link para o doc no GitHub. — aberto

## Entregas disponíveis
- ✅ `data/audit.json`, `data/model_metrics.json`, `data/routing_eval.json`, `data/diagnostico.json` — reais, v3
- ✅ `GET /api/sample?n=` — amostra do conjunto de **teste** (2.000 tickets; nunca usados em treino ou seleção)
- ✅ `POST /api/classify` — unitário `{text}` e lote `{texts}` (1..500) pelo mesmo caminho. **Não corta mais**: acima de 5.000 caracteres → 413; lote > 500 → 413; item inválido no lote → 400 com `errors: [{index, status, error}]` e nada classificado. A UI deve mostrar `error` (já em PT-BR).
- ✅ `POST /api/draft` — **mudou: envie só `{ text }`**. O servidor reclassifica e aplica a política: **403** `{error, route, routeReason}` quando o rascunho é bloqueado (mesmo se a UI mandar outra categoria); **503** sem `AI_GATEWAY_API_KEY`; 200 com stream e header `X-Draft-Category`. Esconder o botão quando `draftAllowed=false` continua sendo o certo, mas não é mais a proteção.
- ✅ `lib/waste.ts` — `computeWaste(values)` e `wasteTotals(lines, values)`; estado inicial `assumptionValues(report.scenario.assumptions)`. Retrabalho pode dar **negativo** (erro automático maior que o manual): mostrar como perda, não zerar.
- ✅ `docs/diagnostico.md`, `docs/modelo.md`, `docs/automacao.md` — gerados por `analysis/05_report.py` (não editar à mão; editar `docs/templates/`).
- Textos já redigidos em PT-BR (`evidence`, `detail`, `note`, `conclusion`, `routeReason`, `rationale`, `source`): exibir como estão, sem reescrever números.
- Redação: usar "não detectamos associação" (nunca "não há efeito") e tratar backlog como contagem descritiva, não como gargalo.
