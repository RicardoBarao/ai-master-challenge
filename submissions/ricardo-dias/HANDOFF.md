# HANDOFF — coordenação Claude Code ⇄ Codex

Quadro curto. Cada agente atualiza a própria seção e responde pedidos. Apague itens resolvidos (o histórico fica no git).

## Status
| Agente | Fazendo agora | Próximo |
|---|---|---|
| Claude Code | `docs/` (diagnóstico, modelo, automação) | fallback LLM (`04`, precisa da chave) |
| Codex | — (aguardando início) | Backlog item 1 (layout e navegação) |

## Contratos prontos
- `solution/app/lib/types.ts` — **v2**. Mudanças desde a v1:
  - `ClassifyResponse`: novos `knownShare` (guarda de domínio) e `draftAllowed` (esconder o botão de rascunho quando `false`)
  - `ModelMetrics`: novo `autoRouting {coverage, accuracy}`; `crossDomain` ganhou `confidentShare`, `confidentPredictedHardware` e `oodGuard`
  - `DiagnosticoReport`: novo `segmentTests` (se `significant=false`, não destacar o "pior segmento" como se fosse real)
  - `POST /api/classify` aceita lote: `{ texts: string[] }` (até 500) → `{ results }`. Use isso no "Testar em 200 tickets", não 200 chamadas

## Pedidos abertos
_(formato: `- [de → para] pedido — status`)_

## Entregas disponíveis
- ✅ `data/audit.json` — real
- ✅ `data/model_metrics.json` — real
- ✅ `GET /api/sample?n=` — real (holdout de 2.000 tickets)
- ✅ `POST /api/classify` — real (unitário e lote)
- ✅ `POST /api/draft` — pronto; sem `AI_GATEWAY_API_KEY` responde **503** com `{error}` → a UI mostra a mensagem e mantém o resto funcionando
- ✅ `data/diagnostico.json` — real
- ✅ `lib/waste.ts` — `computeWaste(values)` + `wasteTotals(lines, values)` para a calculadora. Use `assumptionValues(report.assumptions)` como estado inicial e recalcule no cliente ao editar. Premissas com `editable: false` são medidas: mostrar sem input.
- Os achados da auditoria e do diagnóstico já vêm redigidos em PT-BR (`evidence`, `detail`, `note`): exibir como estão, sem reescrever números
- Dica de UX: exibir `routeReason` literalmente, porque ele já vem em PT-BR para o usuário final
