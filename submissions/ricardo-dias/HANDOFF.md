# HANDOFF — coordenação Claude Code ⇄ Codex

Quadro curto. Cada agente atualiza a própria seção e responde pedidos. Apague itens resolvidos (o histórico fica no git).

## Status
| Agente | Fazendo agora | Próximo |
|---|---|---|
| Claude Code | `01_audit.py` → `data/audit.json`; depois `02_diagnostico.py` | classificador + `/api/classify` |
| Codex | — (aguardando início) | Backlog item 1 (layout e navegação) |

## Contratos prontos
- `solution/app/lib/types.ts` — v1 (audit, diagnostico, model_metrics, classify, sample, draft)

## Pedidos abertos
_(formato: `- [de → para] pedido — status`)_

## Entregas disponíveis
_(JSONs reais e rotas de API que já podem substituir fixtures)_
