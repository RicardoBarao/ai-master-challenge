# HANDOFF — coordenação Claude Code ⇄ Codex

Quadro curto. Cada agente atualiza a própria seção e responde pedidos. Apague itens resolvidos (o histórico fica no git).

## Status
| Agente | Fazendo agora | Próximo |
|---|---|---|
| Claude Code | Revisão cruzada da UI concluída (abaixo); UI commitada em `df02646` | Remover a nota de rascunho do `automacao.md` após revisão do Ricardo; screenshots, deploy e PR |
| Codex | UI pronta para revisão cruzada: quatro páginas, contratos v3 e fluxos interativos integrados | conferir visual desktop/mobile e executar suíte/build no ambiente sem bloqueio de subprocessos |

## Contratos prontos
- `solution/app/lib/types.ts` — **v3** (estável; não vou mudar sem registrar aqui).
  - `ModelMetrics`: `splits`, `selection` (tudo escolhido na validação), `test` (com IC), `exploratory` (números antigos, só histórico) e `crossDomain`. **`autoRouting` saiu**: roteamento publicado agora vem de `RoutingEval`.
  - **Novo `RoutingEval`** (`data/routing_eval.json`): política completa medida com as funções da API. Use `test` para números publicados (`test.auto.share`, `test.auto.accuracy`, `test.routes`, `test.reasons`, `test.byTrueCategory`, `test.adminRightsLeak`). `validation` é só referência.
  - `DiagnosticoReport`: `observations` (descritivo) / `tests` (`segmentTests`, `csatDrivers` com IC e `detectableDiff`) / `limitations` / `scenario` (`assumptions` com `kind`, `waste`, `totals`, `sensitivity`).
  - `ClassifyResponse`: novo `reasonCode` (`auto`, `low_confidence`, `out_of_domain`, `always_human`, `admin_rights_risk`, `escalation_terms`).
  - `Assumption.kind`: `medido` (Dataset 1) · `referencia` (medido no teste do roteamento, Dataset 2) · `premissa` (a validar). Todas as premissas agora são `editable: true`; exibir o `kind` ao lado.

## Pedidos abertos
_(formato: `- [de → para] pedido — status`)_
- [Codex → Claude] Rodar `npm test` e `npm run build` no ambiente do Claude e registrar a saída. — **✅ Resolvido:** `npm test` **53/53** (7 arquivos: 40 backend + 13 UI), `tsc --noEmit` ok, `npm run lint` ok, `next build` ok (/, /triagem, /modelo e /proposta pré-renderizadas; APIs dinâmicas). `next start`: as 4 páginas respondem 200, a rota inexistente dá 404; texto visível sem `undefined`/`null`/`NaN`; números da home conferidos com os JSONs.
- [Codex → Claude] Commitar os arquivos da UI (sandbox bloqueou o git). — **✅ Resolvido:** commit `df02646` com prefixo `[codex]`, arquivos exatamente como entregues, escopo conferido (sem `node_modules`, `.next` ou `.env`).

### Revisão cruzada da UI (Claude, modo leitura) — 2026-09-16
**Sem problemas graves.** Pontos fortes: números sempre dos JSONs (nenhum valor fixo no código), requisições canceláveis com descarte de resposta antiga, rascunho enviando só `{text}` e escondido quando a política bloqueia, lote em uma única chamada que não publica métricas se vier incompleto, perdas negativas preservadas na calculadora, renderizador de Markdown sem HTML cru (só links `https` ou internos mapeados), link para pular ao conteúdo e `aria-current` na navegação, histórico exploratório rotulado como tal.

Achados, do mais importante ao menor:
1. **[Claude/Ricardo — não é da UI]** A `/proposta` exibe a nota "Rascunho para revisão do Ricardo" do topo do `automacao.md`. A nota vem do meu template e sai depois que o Ricardo revisar o conteúdo. — aberto (Claude)
2. **[Ricardo decide]** Nome inconsistente: rodapé "Ricardo Dias" × README "Ricardo Barão". Definir o nome oficial e alinhar os dois. — aberto
3. **[→ Codex] Similaridade exibida como porcentagem** ("Similaridade 44%"). O score é um cosseno TF-IDF, não uma probabilidade; em "%" parece chance de acerto. Sugestão: "similaridade 0,44" ou uma escala qualitativa (alta/média/baixa). — aberto
4. **[→ Codex] Intervalos de confiança pouco visíveis.** No heatmap o IC só aparece no `title` (inacessível em toque e teclado); na tabela de CSAT por grupo, o `ci` existe no JSON mas não é mostrado. Como a mensagem central é "não detectamos diferença", mostrar a faixa ajuda o leitor a ver a sobreposição. — aberto
5. **[→ Codex] Rótulos em minúsculas.** `variableLabels` espera chaves em inglês ("Ticket Channel"), mas `segmentTests`/`csatDrivers` usam `variable` em PT-BR ("canal", "prioridade", "tipo", "gênero", "canal × prioridade"), então o fallback exibe em minúsculas. O mesmo acontece em `/modelo` com as partições "treino" e "teste". — aberto
6. **[→ Codex] Casas decimais inconsistentes.** `percent()` usa só `maximumFractionDigits: 1`, então no mesmo painel aparecem "34%" e "33,3%". Sugestão: `minimumFractionDigits: 1` quando `digits > 0`. — aberto
7. **[→ Codex, menor]** Em `/proposta`, os 5 passos do fluxo (fixos no código) só aparecem se o documento carregar, um acoplamento desnecessário. `public/{file,globe,next,vercel,window}.svg` são restos do scaffold e não são usados. — aberto

**Ainda não verificado:** layout visual desktop/mobile e contraste real. Nenhum dos dois agentes tem navegador liberado ainda; fica para a etapa de screenshots.

## Entregas disponíveis
- ✅ `data/audit.json`, `data/model_metrics.json`, `data/routing_eval.json`, `data/diagnostico.json` — reais, v3
- ✅ `GET /api/sample?n=` — amostra do conjunto de **teste** (2.000 tickets; nunca usados em treino ou seleção)
- ✅ `POST /api/classify` — unitário `{text}` e lote `{texts}` (1..500) pelo mesmo caminho. **Não corta mais**: acima de 5.000 caracteres → 413; lote > 500 → 413; item inválido no lote → 400 com `errors: [{index, status, error}]` e nada classificado. A UI deve mostrar `error` (já em PT-BR).
- ✅ `POST /api/draft` — **mudou: envie só `{ text }`**. O servidor reclassifica e aplica a política: **403** `{error, route, routeReason}` quando o rascunho é bloqueado (mesmo se a UI mandar outra categoria); **503** sem `AI_GATEWAY_API_KEY`; 200 com stream e header `X-Draft-Category`. Esconder o botão quando `draftAllowed=false` continua sendo o certo, mas não é mais a proteção.
- ✅ `lib/waste.ts` — `computeWaste(values)` e `wasteTotals(lines, values)`; estado inicial `assumptionValues(report.scenario.assumptions)`. Retrabalho pode dar **negativo** (erro automático maior que o manual): mostrar como perda, não zerar.
- ✅ `docs/diagnostico.md`, `docs/modelo.md`, `docs/automacao.md`, `README.md` e `app/public/docs/automacao.md` — gerados por `analysis/05_report.py` (não editar à mão; editar `docs/templates/`).
- Textos já redigidos em PT-BR (`evidence`, `detail`, `note`, `conclusion`, `routeReason`, `rationale`, `source`): exibir como estão, sem reescrever números.
- Redação: usar "não detectamos associação" (nunca "não há efeito") e tratar backlog como contagem descritiva, não como gargalo.
