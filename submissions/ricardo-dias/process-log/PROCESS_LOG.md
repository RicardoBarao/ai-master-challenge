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
