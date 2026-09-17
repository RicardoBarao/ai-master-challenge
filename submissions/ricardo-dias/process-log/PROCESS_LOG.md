# Process Log — Challenge 002 (Redesign de Suporte)

Registro cronológico de como usei IA. Ferramenta principal: **Claude Code (Claude Opus 5)** no terminal, com o transcript da sessão exportado em `process-log/`.

## 2026-09-16 — Entendimento do problema e plano

1. Pedi ao Claude Code que lesse o repositório: README, submission-guide, CONTRIBUTING, template e os 4 challenges.
2. Escolhi o **002 — Redesign de Suporte**. O Claude recomendou o 003 (Lead Scorer). Preferi o 002 porque ele junta diagnóstico, processo e build, que é o perfil de AI Master que a vaga descreve.
3. Decisões tomadas antes de escrever código:
   - **Entrega:** Next.js publicado na Vercel, para o diretor abrir um link e ver algo rodando.
   - **Arquitetura híbrida:** um classificador leve, treinado nos 48 mil tickets, responde com custo zero e acurácia medida. O LLM entra só quando a confiança é baixa e para rascunhar respostas. Descartei "LLM em tudo" porque sai caro, é lento e fica difícil medir a acurácia nos 48 mil tickets.
   - **Verificar antes de concluir:** o README fala em ~30 mil tickets, mas a versão do dataset no Kaggle pode ser diferente e possivelmente sintética. Por isso a primeira etapa é auditar os dados, e não sair gerando gráficos.
4. Plano em 7 etapas: setup, auditoria, diagnóstico, classificador com avaliação, proposta de automação, app, docs/PR.

### [claude] 2026-09-16 — Setup do ambiente
- Clone do repo, branch `submission/ricardo-dias`, estrutura de pastas.
- O instalador do `uv` via PowerShell travou sem mostrar erro. Interrompi e baixei o binário direto do GitHub Releases. Ficou instalado Python 3.12 isolado, sem mexer no Python 3.8 do sistema.

### [claude] 2026-09-16 — Auditoria dos dados (antes de qualquer gráfico)
Hipótese do planejamento: o Dataset 1 pode ser sintético. Testei em vez de assumir.
- **Tamanho:** 8.469 tickets, não os ~30 mil do enunciado.
- **Uniformidade:** tipo, prioridade, canal, status e CSAT uniformes (qui-quadrado, todos com p > 0,1). Operação real nunca é uniforme.
- **Tempos inválidos:** `First Response Time` e `Time to Resolution` são timestamps concentrados em ~27h (31/05 a 02/06/2023). Não há horário de abertura. Em **49%** dos fechados (1.365 de 2.769), a resolução acontece *antes* da primeira resposta.
- **CSAT sem driver:** Kruskal-Wallis por tipo, prioridade, canal, gênero e produto, e Spearman com duração e idade: todos com p > 0,25.
- **Texto sem sinal:** `{product_purchased}` literal em 100% das descrições, resolução em lorem ipsum (Faker). Um TF-IDF + LogReg treinado no texto prevê o tipo com 18,8% de acerto, contra 20,7% chutando a classe majoritária.
- **Dataset 2 é bom:** 47.837 tickets, 8 classes desbalanceadas (Hardware 28%, Administrative rights 3,7%), 0 duplicatas, 0 rótulos conflitantes. Texto pré-processado (minúsculas, sem dígitos).

**Decisão (julgamento humano + IA):** não vou fabricar "gargalos" nem "drivers de CSAT" a partir de ruído, que é exatamente o erro de "a IA disse, o candidato acreditou". O diagnóstico vai (1) mostrar a auditoria como primeiro achado, (2) usar só o que é confiável (volume, mix, backlog, pendências com cliente), (3) quantificar desperdício com premissas explícitas e editáveis e (4) entregar a metodologia pronta para rodar em dados reais. O peso da prova de valor passa para o classificador treinado no Dataset 2, que tem sinal real e acurácia mensurável.

### [claude] 2026-09-16 — Preparando trabalho em paralelo com Codex
- A pedido do Ricardo, criei `AGENTS.md` (lido pelo Codex) e `CLAUDE.md` (importa o mesmo arquivo), com fatos verificados, regras, lanes por caminho, backlog do Codex e regras de git para dois agentes na mesma branch.
- Defini os contratos de dados em `solution/app/lib/types.ts` *antes* de construir. Assim a UI (Codex) e a análise (Claude) avançam juntas sem se bloquear.
- `HANDOFF.md` funciona como quadro de coordenação.

### [claude] 2026-09-16 — `01_audit.py` → `app/data/audit.json`
- Transformei a auditoria exploratória em script reprodutível. Cada achado sai com evidência numérica, implicação e severidade, para a UI citar sem reinterpretar.
- **Erros da IA pegos na revisão da saída:**
  1. Um `.replace(",", ".")` para formatar milhares trocou também as vírgulas das frases ("8.469 tickets no arquivo. contra..."). Corrigi com um formatador só para números.
  2. Na auditoria inicial, a IA escreveu que o Dataset 2 vinha "sem stopwords". Olhando as amostras ("connection **with** icon", "coming next **his** name"), desconfiei e medi: **21,6% dos tokens são stopwords**. A afirmação estava errada e foi corrigida no JSON e no AGENTS.md, onde o Codex leria o fato errado.
- Lição registrada: fatos passados a outro agente precisam estar medidos, porque o erro se propaga.

### [claude] 2026-09-16 — Classificador (Dataset 2), export para TypeScript e rotas da API
**Resultado** (holdout estratificado de 9.568 tickets, seed 42):

| Modelo | Acurácia | F1 macro |
|---|---|---|
| Baseline (sempre "Hardware") | 28,5% | 0,055 |
| TF-IDF + Complement NB | 81,8% | 0,808 |
| TF-IDF + Linear SVM | 86,7% | 0,866 |
| TF-IDF + Regressão Logística, **exportada** (40k termos, coeficientes podados) | **86,4%** | **0,865** |

- **Escolhi a regressão logística e não o SVM** (0,3 ponto abaixo) porque ela dá probabilidade calibrada. Sem isso não existe limiar de confiança nem fila humana.
- **Poda medida, não assumida:** zerei coeficientes com |coef| < ε para ε de 0,02 a 0,3. A acurácia não mudou, e o arquivo caiu de 7,1 MB para 2,85 MB. Usei ε = 0,2.
- **Rota automática:** confiança ≥ 80% **e** vocabulário conhecido. Cobre **69,7%** dos tickets com **95,7%** de acerto; o resto vai para triagem humana.

**Erros encontrados e corrigidos nesta etapa:**
1. **O teste de paridade Python × TS falhou (99,35%).** A causa foi minha: o holdout foi exportado com o texto cortado em 800 caracteres e 134 tickets longos ficaram diferentes. Exportando o texto completo, a paridade foi a **100% (2.000 de 2.000)**, com diferença máxima de confiança de 2e-6. Sem esse teste, o app mostraria uma acurácia que não é a do modelo.
2. **Um patch automatizado gravou `\b` como caractere de backspace** no regex do Python, e o limiar do guarda saiu 0,0 (não barrava nada). Pegamos porque o número era absurdo. O mesmo tipo de problema trocou o escape `\u0300` do TypeScript por caracteres literais. Corrigi e conferi byte a byte com `od`.
3. **Premissa errada sobre o cruzamento de datasets.** Antes de rodar, eu tinha escrito que o modelo "teria pouca confiança" no Dataset 1. Medido, foi o contrário: **53,9% dos tickets de e-commerce passam do limiar de confiança, e 92% desses viram "Hardware"**, inclusive "Payment issue". **Confiança alta não protege contra texto de outro domínio.** Isso virou uma feature: um **guarda de domínio** (fração das palavras de conteúdo conhecidas pelo modelo) que barra 98,6% do Dataset 1 e só 4,3% do próprio domínio.
4. **O guarda era rígido demais para texto digitado.** "Hi, my laptop screen is broken..." caía na revisão humana por causa de "my", pronome que o pré-processamento do Dataset 2 removeu. Passei a ignorar stopwords no cálculo, com a mesma lista em Python e TS, exportada no `model.json`.

**Achado que só apareceu por causa da explicabilidade:** o termo que mais pesa para "HR Support" num ticket de novo funcionário é **"belgrade"**, nome de escritório. O modelo aprendeu localização como sinal de categoria (correlação espúria). Vai para limitações e para a recomendação de re-treino com dados da operação.

**Teste de ponta a ponta das rotas (dev server):** lote de 200 tickets aleatórios do holdout teve 88% de acerto geral e 99,2% nos roteados automaticamente. A escalação ("urgent/hacked/phishing") funciona e a rota de rascunho sem chave responde 503 com uma mensagem clara.

### [claude] 2026-09-16 — Diagnóstico operacional (`02_diagnostico.py` → `diagnostico.json`)
- **Testei antes de chamar algo de gargalo.** Status × canal (p = 0,77), × prioridade (p = 0,23), × tipo (p = 0,34) e × canal+prioridade (p = 0,50): nenhum é significativo. O "pior segmento" (Phone × Low, 72% não fechados) é indistinguível do acaso, e a UI é instruída pelo contrato (`segmentTests.significant`) a não destacá-lo.
- **Drivers de CSAT:** Kruskal-Wallis com tamanho de efeito ε² ≤ 0,0014 em todas as variáveis, efeito praticamente nulo.
- **Desperdício:** ~6.990 h/ano estimadas, das quais **~3.230 h/ano são recuperáveis** (≈ 1,8 agente em tempo integral; ≈ R$ 145 mil/ano a R$ 45/h), para 30 mil tickets/ano. Separei explicitamente:
  - o que é **medido**: cobertura de 69,7% e acerto de 95,7% do roteamento automático, pendências de 34% e casos só-humanos de 40,7% (os dois últimos com a ressalva de que o mix é sintético);
  - o que é **premissa editável**: minutos de triagem, taxa de roteamento errado, follow-ups, custo/hora. Cada premissa diz como validar ("cronometrar 50 triagens", "medir reatribuições no helpdesk").
- A maior fatia recuperável **não é a IA generativa**: são follow-up automático (1.089 h) e triagem (1.045 h). Rascunho de resposta com LLM fica em 534 h, porque assumi economia conservadora de 30% e excluí os casos só-humanos. Isso orienta a priorização: começar pelo que é barato e mensurável.
- **Erros pegos:**
  1. A formatação brasileira de números quebrou a pontuação da frase pela segunda vez ("integral. ou R$ 145.282 por ano. com"). Troquei os `.replace` encadeados por formatadores dedicados (`br_int`, `br_pct`).
  2. A primeira versão afirmava "fila sem reconhecimento ao cliente" para os abertos sem 1ª resposta. Isso é interpretação: no dataset sintético pode ser só a definição de "Open". Reescrevi com a ressalva.
- **Calculadora da UI:** a fórmula existe em Python e em `lib/waste.ts`. `scripts/waste-check.ts` garante que as duas dão o mesmo resultado, para a calculadora nunca contradizer o relatório.

### [claude] 2026-09-16 — Revisão cruzada pelo Codex e correções
**Contexto:** o Ricardo pediu ao Codex uma revisão do backend em modo leitura, antes de ampliar funcionalidades. O Codex apontou 6 problemas. Verifiquei cada um no código antes de agir:

| # | Apontamento do Codex | Verificação | O que mudou |
|---|---|---|---|
| 1 | O mesmo conjunto servia para escolher parâmetros e para reportar o teste | **Procedia.** O `te` (20%) escolhia modelo, poda, limiar de confiança e guarda, e depois era publicado como teste | Treino 70% / validação 15% / teste 15%. Tudo escolhido na validação e congelado (`selection`) antes do teste. IC 95% por bootstrap. Números antigos marcados como **exploratórios** |
| 2 | `autoRouting` ignorava parte da política | **Procedia.** Escalação e "Administrative rights → humano" ficavam de fora, e o vazamento de privilégio nunca tinha sido medido | `scripts/evaluate-routing.ts` mede com **as funções da API**. `policy.py` replica a política só para selecionar, e um teste exige 100% de concordância. Vazamento medido deu **>2% na validação sem regra**, então entrou a regra "probabilidade de privilégio ≥ τ → humano", com τ escolhido na validação |
| 3 | `/api/draft` confiava na categoria enviada pelo cliente | **Procedia** | A rota recebe só `{text}`, reclassifica no servidor e bloqueia com 403 **antes** de chamar o LLM. Teste com espião prova 0 chamadas, inclusive com categoria forjada |
| 4 | `model.json` sem `stopWords` quebrava a inferência | **Parcial.** O arquivo commitado já tinha o campo; o Codex leu um estado intermediário da minha alteração. Mas a lacuna era real: o formato mudou, a `version` continuou 1 e não havia validação | `model.json` v2 validado com zod ao carregar, com erro claro ("versão X incompatível… rode 03_classifier.py") e testes para versão errada e campo ausente |
| 5 | Diagnóstico incompleto e redação forte demais; vazamento no CV da auditoria | **Procedia** | Auditoria com `Pipeline` dentro de cada fold (18,8% → 18,7%, conclusão mantida). Redação "não detectamos associação" com diferença detectável (±0,13–0,17 ponto). Backlog tratado como descritivo. Diagnóstico em observado / testes / limitações / cenário. Economia desconta conferência, revisão e erro residual e usa a cobertura **final**. Docs gerados de templates, sem número digitado à mão |
| 6 | Validação da API inconsistente, com cortes silenciosos | **Procedia** | `lib/validation.ts` único: 400/413 explícitos, lote recusado inteiro com índices dos erros, e o lote usa o mesmo caminho do unitário. Testes de limites (5.000/5.001, 500/501), tipos e equivalência lote × unitário |

**Números antigos × finais:**

| Métrica | Exploratório (1ª versão) | Final (teste, IC 95%) |
|---|---|---|
| Acurácia | 86,4% | **86,0%** (85,2–86,7%) |
| F1 macro | 0,865 | **0,856** (0,846–0,864) |
| Roteamento automático | 69,7% (só confiança + guarda) | **65,3%** (política completa da API) |
| Acerto nos automáticos | 95,7% | **94,9%** (94,3–95,6%) |
| Horas recuperáveis/ano (cenário) | ~3.230 | **~2.514** (desconta resíduos) |

**Leitura honesta:**
- Os números caíram um pouco, como era de se esperar quando a avaliação deixa de "ver" as escolhas.
- O acerto nos automáticos ficou **abaixo da meta de 95%** usada na validação. Isso está reportado assim, com a recomendação de começar em modo sombra.
- As decisões de desenho (usar regressão logística, criar o guarda, ignorar stopwords) foram tomadas vendo o conjunto antigo, então o novo teste não é "virgem" em sentido estrito. Isso está documentado em `docs/modelo.md`.

**Outros erros pegos nesta rodada:**
- `getPolicyRules` tentava ler do disco um arquivo que vem de import (3 testes falharam e corrigi).
- A flag de regex `/s` não compila no target ES2017 do projeto.
- O `vitest` 5 exigia `@types/node` ≥ 22, e o scaffold veio com a v20: alinhei com o Node 24 em uso.
- A nota do cruzamento saiu com ponto decimal. Rodei o pipeline de novo para confirmar que a única diferença entre execuções vinha dessa correção.

**Verificação:**
- `bash solution/pipeline.sh` roda do zero: 40 testes, `tsc` e lint ok, e `next build` ok.
- Os JSONs lidos via `fs` entram no bundle de deploy (conferido no `.nft.json`).
- Os leitores de UI do Codex (`lib/data.ts`) aceitam os quatro relatórios v3 (teste temporário).

**Sobre trabalhar com dois agentes:** a revisão do Codex pegou problemas metodológicos que eu não tinha visto, porque eu estava perto demais do código. O valor esteve em *verificar* cada apontamento, e não em aceitar todos: um deles era parcialmente um artefato de timing entre os agentes.

### [claude] 2026-09-16 — README da submissão e export do transcript
- **README** (`README.md`) segue o template do G4. É gerado por `05_report.py` a partir de `docs/templates/README.md.tmpl`, então todo número vem dos JSONs e não diverge dos docs. Campos que dependem do Ricardo ficam marcados para preencher: nome completo, LinkedIn, link do deploy, screenshots e data de envio. A seção "O que eu adicionei" está rascunhada a partir do que aconteceu na sessão, para o Ricardo revisar.
- **Transcript** (`process-log/chat-exports/claude-code-sessao-principal.md`) é gerado por `process-log/export_transcript.py` a partir do `.jsonl` da sessão. Traz mensagens (inclusive as enviadas no meio de um turno), respostas, chamadas de ferramenta com saída resumida e planos aprovados. Omite contexto de sistema e conteúdo integral de arquivos, que está no git.
- **Sanitização verificada com grep:** e-mails, caminho e nome do usuário do Windows e nome da conta de trabalho do GitHub foram trocados por marcadores. As únicas ocorrências restantes dos termos buscados são os próprios comandos de verificação registrados no transcript.
- **Pedido do Codex atendido:** `05_report.py` também gera `solution/app/public/docs/automacao.md` (cópia servida pela UI, porque `docs/` fica fora do Root Directory no deploy). Conferi que é idêntica ao doc e à cópia manual que o Codex tinha feito.
- **Erros pegos na revisão do README gerado:**
  1. O resumo dizia "nenhuma associação detectável", fora da redação combinada; trocado por "não detectamos associação".
  2. As contagens da auditoria saíam sem separador de milhar.
  3. O total recuperável é 2.514 h (arredondamento de 2.514,5), mas o log dizia ~2.515.
  4. Uma frase atribuía ao Ricardo um motivo para ter interrompido um comando, e esse motivo nunca foi dito. Removida: não inventar intenção de pessoa.

### [claude] 2026-09-16 — Registro das ferramentas
- O Ricardo esclareceu a configuração do segundo agente: **Codex com o modelo gpt-6-astra em raciocínio xhigh**, usado em dois papéis: auditor de qualidade do backend (revisão cruzada em modo leitura) e construção da interface. Tabela de ferramentas do README atualizada.

### [codex] 2026-09-16 23:01 — Interface de diagnóstico, triagem, modelo e proposta
- **Pedido:** construir a interface usando o G4 OS como referência visual e integrar o trabalho de análise do Claude. Foram consultados a página pública e screenshots oficiais do produto. A skill `ui-ux-pro-max` orientou a revisão de hierarquia, contraste, foco e adaptação de layout. Seus scripts auxiliares não estavam disponíveis no caminho indicado; não foram usados como evidência de validação.
- **Entrega:** navegação entre quatro páginas, paleta azul-marinho/dourado, tipografia Inter/Manrope, layouts adaptáveis e estados de carregamento, indisponibilidade e erro. Diagnóstico apresenta auditoria, observações, segmentos, testes de associação, limitações e calculadora. Triagem usa amostras reais e APIs individuais/em lote, mostra motivos do encaminhamento, termos, similares e rascunho em streaming. Modelo mostra avaliação no teste, seleção na validação, F1, matriz de confusão, intervalos, motivos e destinos por categoria. Proposta mostra o fluxo das verificações e o documento gerado.
- **Integração:** leitura e validação dos contratos v3 com zod; relatório ausente/incompatível produz estado de indisponibilidade. Não foi necessário inventar fixtures. A calculadora reutiliza `lib/waste.ts`, distingue premissa/observado/referência, mantém perdas negativas e permite restaurar o cenário. `/api/draft` recebe somente o texto. Edição do ticket cancela a solicitação anterior para impedir que um resultado antigo apareça no novo texto.
- **Coordenação:** a documentação originalmente ficava fora da raiz de deploy. O Claude passou a gerar a cópia pública de `automacao.md`; a UI lê essa cópia, e um teste exige igualdade com o documento de origem. O `include` do Vitest foi ampliado a pedido do Claude para incluir os 13 testes novos de interface no `npm test`.
- **Erros e correções:** o primeiro build acusou um seletor CSS inválido gerado pela detecção ampla do Tailwind. A detecção foi restringida aos arquivos da interface e a compilação seguinte passou dessa etapa. O arredondamento de números foi alinhado ao modo half-even dos relatórios Python, evitando divergências de uma unidade na apresentação das projeções. Uma verificação temporária via stdin perdeu acentos por causa da codificação do PowerShell; foram usados seletores ASCII na repetição, sem alterar o texto em português da interface.
- **Validação aprovada:** `tsc --noEmit` e `npm run lint`. Verificação adicional em processo único, com transformação TypeScript em memória, React e Testing Library/jsdom: renderização das quatro páginas, validação dos quatro relatórios reais, sincronização do documento, recálculo/restauração/inputs inválidos/perdas negativas; classificação com rascunho indisponível, envio de texto apenas, descarte de resposta atrasada, lote de 200 e suas contagens/filtro, bloqueio em escalação, streaming completo, recusa de lote incompleto e erro de validação da API. APIs de rascunho foram simuladas; não houve chamada paga ao provedor.
- **Limite da validação:** `npm test` não iniciou os testes porque a sandbox bloqueia o subprocesso `net use` usado pelo Vite (`spawn EPERM`). `npm run build` compilou CSS/JS, mas foi bloqueado ao criar o worker de TypeScript. O navegador automatizado também foi bloqueado. Portanto, a suíte Vitest completa, o build de produção completo e a conferência visual desktop/mobile ainda precisam rodar no ambiente do Claude. Pedido registrado no HANDOFF; não foram produzidas screenshots da interface nem feitos push/deploy.
- **Git:** a tentativa de stage pelo script obrigatório `scripts/git-add.sh` foi impedida na inicialização do Git Bash (`CreateFileMapping`, erro 5). Nenhum arquivo foi stageado e nenhum commit foi criado nesta sessão. O HANDOFF lista o escopo para versionamento; os arquivos novos permanecem sujeitos ao ignore `submissions/` da raiz.

### [claude] 2026-09-16 — Revisão cruzada da interface do Codex
- **Pedido do Ricardo:** revisar a UI que o Codex terminou. Fiz a revisão em modo leitura, no sentido inverso da revisão que o Codex fez do backend.
- **O que o Codex não conseguiu validar e eu rodei:** o sandbox dele bloqueou subprocessos. No meu ambiente: `npm test` 53/53, `tsc`, lint e `next build` ok. Com `next start`, as 4 páginas responderam 200 e o texto visível não tem `undefined`, `null` ou `NaN`; os números da home batem com os JSONs.
- **Erro meu durante a verificação:** a primeira rodada deu 500 em todas as páginas. Antes de culpar a UI, olhei o log: `EADDRINUSE`. A porta estava presa por um `next dev` meu, que ficou órfão quando parei a tarefa antes (parar o `npx` não mata o `node` filho). Encerrei o processo depois de confirmar a linha de comando, rodei de novo e passei a checar a porta ao final. Também vi que as 24–36 ocorrências de "undefined" estavam no payload de hidratação dentro de `<script>`, não no texto visível. Um alarme falso evitado por verificar em vez de reportar.
- **Achados:** nenhum grave. O mais importante é **meu**: a `/proposta` exibe a nota "Rascunho para revisão do Ricardo" que vem do template do `automacao.md`. Os demais ficam para o Codex e o Ricardo: similaridade exibida como porcentagem, ICs pouco visíveis, rótulos em minúsculas por chave de mapeamento divergente, casas decimais inconsistentes, nome "Ricardo Dias" × "Ricardo Barão". Lista completa no HANDOFF.
- **Commit do trabalho do Codex:** a pedido dele, commitei a UI exatamente como entregue (`df02646`, prefixo `[codex]`), com o escopo conferido.
- **Pendente:** conferência visual desktop/mobile, que nenhum dos agentes executou.
