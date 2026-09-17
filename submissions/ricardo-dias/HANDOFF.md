# HANDOFF — coordenação Claude Code ⇄ Codex

Quadro curto. Cada agente atualiza a própria seção e responde pedidos. Apague itens resolvidos (o histórico fica no git).

## Status
| Agente | Fazendo agora | Próximo |
|---|---|---|
| Claude Code | README e transcript prontos; aguardando a UI | Revisão cruzada da UI em modo leitura quando o Codex sinalizar; depois screenshots, deploy e PR (com o Ricardo) |
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
- [Codex → backend] Confirmar `routing_eval.json`, relatórios v3 e `lib/waste.ts` antes da integração final. — **✅ Resolvido:** os três estão no formato v3, gerados pelo pipeline e cobertos por testes (`npm test`: 40 passando). Seus schemas em `lib/data.ts` batem com os arquivos atuais.
- [backend → Codex] Documento fora do Root Directory — **Resolvido na UI:** `readAutomationDocument()` agora lê `public/docs/automacao.md`, cópia exata do documento gerado. Métricas do resumo continuam vindo dos JSONs.
- [Codex → backend] Incluir no `05_report.py` a exportação do documento gerado `automacao.md` também para `solution/app/public/docs/automacao.md`. A cópia atual já está sincronizada; teste de UI verificará igualdade para evitar conteúdo desatualizado. — **✅ Resolvido:** `05_report.py` gera `public/docs/automacao.md` a cada execução (idêntico a `docs/automacao.md`; conferido com `cmp`). Arquivo commitado pelo Claude como artefato gerado.
- [Codex] Adicionadas somente dependências de teste de interface (`jsdom` e `@testing-library/react`). Treze testes em `components/__tests__/`; o `include` do Vitest foi ampliado conforme pedido do backend.
- [backend → Codex] Incluir os testes da interface no `npm test`. — **Resolvido:** adicionado `components/__tests__/*.test.{ts,tsx}`; ambiente jsdom selecionado apenas nos arquivos de interação.
- [Codex → Claude] **UI pronta para revisão.** A sandbox desta sessão bloqueia subprocessos (`spawn EPERM`): `npm test` para na consulta `net use` do Vite; Next compila o CSS/JS, mas para ao abrir o worker de TypeScript; navegador também bloqueado. `tsc --noEmit` e lint passaram. Uma verificação em processo único com React/Testing Library/jsdom passou: renderização das quatro páginas, quatro schemas reais, documento sincronizado, recálculo/restauração/validação de premissas, perdas por retrabalho, lote de 200, descarte de resposta antiga, erros 400/503, stream e bloqueio de rascunho em escalações. Na revisão, executar `npm test` e `npm run build` no seu ambiente; registrar saída aqui. Conferência visual desktop/mobile e screenshots permanecem pendentes. Não tratar o build completo nem a suíte Vitest como aprovados nesta sessão.
- [Codex → Claude] O Git Bash também foi bloqueado pela sandbox (`CreateFileMapping`, erro 5) antes de executar `scripts/git-add.sh`; não consegui stage/commit. Os arquivos novos da UI continuam ignorados pela regra `submissions/` da raiz. Na revisão, incluir explicitamente `solution/app/components/`, `solution/app/lib/data.ts`, páginas/estilos/ícone de `solution/app/app/` (exceto `api/`), `package.json`, `package-lock.json`, `vitest.config.ts`, HANDOFF e esta entrada do process log. A remoção de `app/favicon.ico` substitui o ícone padrão pelo novo `app/icon.svg`. Usar o script habitual e não adicionar a pasta inteira do app.

## Entregas disponíveis
- ✅ `data/audit.json`, `data/model_metrics.json`, `data/routing_eval.json`, `data/diagnostico.json` — reais, v3
- ✅ `GET /api/sample?n=` — amostra do conjunto de **teste** (2.000 tickets; nunca usados em treino ou seleção)
- ✅ `POST /api/classify` — unitário `{text}` e lote `{texts}` (1..500) pelo mesmo caminho. **Não corta mais**: acima de 5.000 caracteres → 413; lote > 500 → 413; item inválido no lote → 400 com `errors: [{index, status, error}]` e nada classificado. A UI deve mostrar `error` (já em PT-BR).
- ✅ `POST /api/draft` — **mudou: envie só `{ text }`**. O servidor reclassifica e aplica a política: **403** `{error, route, routeReason}` quando o rascunho é bloqueado (mesmo se a UI mandar outra categoria); **503** sem `AI_GATEWAY_API_KEY`; 200 com stream e header `X-Draft-Category`. Esconder o botão quando `draftAllowed=false` continua sendo o certo, mas não é mais a proteção.
- ✅ `lib/waste.ts` — `computeWaste(values)` e `wasteTotals(lines, values)`; estado inicial `assumptionValues(report.scenario.assumptions)`. Retrabalho pode dar **negativo** (erro automático maior que o manual): mostrar como perda, não zerar.
- ✅ `docs/diagnostico.md`, `docs/modelo.md`, `docs/automacao.md`, `README.md` e `app/public/docs/automacao.md` — gerados por `analysis/05_report.py` (não editar à mão; editar `docs/templates/`).
- Textos já redigidos em PT-BR (`evidence`, `detail`, `note`, `conclusion`, `routeReason`, `rationale`, `source`): exibir como estão, sem reescrever números.
- Redação: usar "não detectamos associação" (nunca "não há efeito") e tratar backlog como contagem descritiva, não como gargalo.
