"""Etapa 2 — Diagnóstico operacional (Dataset 1) com o que os dados permitem afirmar.

A auditoria (01) mostrou que tempos e CSAT do Dataset 1 não carregam sinal. Aqui:
  1. testamos se segmentos (canal, prioridade, tipo) diferem de verdade antes de chamar algo de gargalo;
  2. medimos o que é confiável: backlog, tickets sem 1ª resposta, pendências com cliente;
  3. estimamos desperdício com premissas explícitas + cobertura MEDIDA do classificador (03).

A fórmula do desperdício é espelhada em app/lib/waste.ts (a calculadora da UI);
scripts/waste-check.ts garante que as duas dão o mesmo resultado.
Saída: app/data/diagnostico.json
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from common import APP_DATA, load_d1, r, write_json

ANNUAL_VOLUME = 30_000
MIN_SEGMENT_N = 300
ALPHA = 0.05


def br_int(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def br_dec(x: float, digits: int = 1) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def br_pct(x: float, digits: int = 1) -> str:
    return f"{br_dec(x * 100, digits)}%"


def status_test(d1: pd.DataFrame, col: str) -> dict:
    ct = pd.crosstab(d1[col], d1["Ticket Status"])
    p = stats.chi2_contingency(ct).pvalue
    return {"variable": col, "test": "qui-quadrado status × " + col, "pValue": r(p), "significant": bool(p < ALPHA)}


def csat_driver(closed: pd.DataFrame, col: str) -> dict:
    groups = {k: g["Customer Satisfaction Rating"].to_numpy() for k, g in closed.groupby(col)}
    h, p = stats.kruskal(*groups.values())
    n = len(closed)
    eps2 = h / (n - 1)  # epsilon² de Kruskal-Wallis: 0,01 pequeno, 0,08 médio, 0,26 grande
    return {
        "variable": col,
        "test": "Kruskal-Wallis",
        "pValue": r(p),
        "effectSize": r(eps2),
        "groups": sorted([{"label": k, "mean": r(v.mean(), 2), "n": int(len(v))} for k, v in groups.items()],
                         key=lambda g: g["mean"]),
    }


def compute_waste(a: dict[str, float]) -> list[dict]:
    """Espelho exato de app/lib/waste.ts. Horas por ano."""
    v = a["annual_volume"]
    human_only = a["human_only_share"]

    triage = v * a["triage_minutes"] / 60
    triage_auto = a["auto_coverage"]

    rework = v * a["misroute_rate"] * a["rework_minutes"] / 60
    residual_error = 1 - a["auto_accuracy"]
    rework_auto = a["auto_coverage"] * max(0.0, 1 - residual_error / a["misroute_rate"]) if a["misroute_rate"] > 0 else 0.0

    followup = v * a["pending_share"] * a["followups_per_pending"] * a["followup_minutes"] / 60
    followup_auto = a["followup_automation"]

    drafting = v * a["draft_minutes"] / 60
    drafting_auto = a["draft_saving"] * (1 - human_only)

    lines = [
        ("Triagem manual (ler, classificar, rotear)", triage, triage_auto,
         "Classificador roteia sozinho os tickets com confiança e vocabulário conhecidos; o resto segue para triagem humana."),
        ("Retrabalho por roteamento errado", rework, rework_auto,
         "Nos tickets roteados automaticamente, o erro cai da taxa manual para o erro medido do modelo."),
        ("Follow-up de tickets aguardando o cliente", followup, followup_auto,
         "Lembretes e fechamento por inatividade automáticos; humano retoma quando o cliente responde."),
        ("Redação de respostas", drafting, drafting_auto,
         "Rascunho sugerido reduz o tempo de escrita; nunca é enviado sem revisão. Não se aplica a casos só-humanos."),
    ]
    return [{"step": s, "hoursPerYear": r(h, 1), "automatableShare": r(share),
             "recoverableHoursPerYear": r(h * share, 1), "rationale": why} for s, h, share, why in lines]


def main() -> None:
    d1 = load_d1()
    n = len(d1)
    metrics = json.loads((APP_DATA / "model_metrics.json").read_text(encoding="utf-8"))
    closed = d1[d1["Ticket Status"] == "Closed"]

    d1["not_closed"] = d1["Ticket Status"] != "Closed"
    d1["pending"] = d1["Ticket Status"] == "Pending Customer Response"
    d1["channel_priority"] = d1["Ticket Channel"] + " × " + d1["Ticket Priority"]

    segments = []
    for (ch, pr), g in d1.groupby(["Ticket Channel", "Ticket Priority"]):
        cg = g[g["Ticket Status"] == "Closed"]["Customer Satisfaction Rating"]
        segments.append({"channel": ch, "priority": pr, "n": int(len(g)), "backlogShare": r(g["not_closed"].mean()),
                         "pendingCustomerShare": r(g["pending"].mean()),
                         "csatMean": r(cg.mean(), 2) if len(cg) else None})
    worst = sorted([s for s in segments if s["n"] >= MIN_SEGMENT_N], key=lambda s: -s["backlogShare"])[:5]

    segment_tests = [status_test(d1, c) for c in ["Ticket Channel", "Ticket Priority", "Ticket Type", "channel_priority"]]
    for t in segment_tests:
        print(f"{t['test']}: p={t['pValue']} significativo={t['significant']}")

    drivers = [csat_driver(closed, c) for c in ["Ticket Channel", "Ticket Priority", "Ticket Type", "Customer Gender"]]
    for d in drivers:
        print(f"CSAT × {d['variable']}: p={d['pValue']} ε²={d['effectSize']}")

    status = d1["Ticket Status"].value_counts(normalize=True)
    open_no_frt = d1.loc[d1["Ticket Status"] == "Open", "First Response Time"].isna().mean()
    human_only = d1["Ticket Type"].isin(["Refund request", "Cancellation request"]).mean()
    auto = metrics["autoRouting"]

    assumptions = [
        {"id": "annual_volume", "label": "Volume anual de tickets", "value": ANNUAL_VOLUME, "unit": "tickets/ano",
         "source": "Enunciado do desafio (o arquivo tem 8.469 tickets).", "editable": True},
        {"id": "hourly_cost", "label": "Custo carregado por hora de agente", "value": 45, "unit": "R$/h",
         "source": "Premissa de trabalho: validar com RH/financeiro.", "editable": True},
        {"id": "triage_minutes", "label": "Tempo de triagem manual por ticket", "value": 3, "unit": "min",
         "source": "Premissa: validar cronometrando 50 triagens.", "editable": True},
        {"id": "misroute_rate", "label": "Taxa de roteamento errado (manual)", "value": 0.15, "unit": "fração",
         "source": "Premissa: medir por reatribuições no helpdesk.", "editable": True},
        {"id": "rework_minutes", "label": "Retrabalho por ticket mal roteado", "value": 15, "unit": "min",
         "source": "Premissa: inclui reler, reatribuir e o atraso ao cliente.", "editable": True},
        {"id": "pending_share", "label": "Tickets aguardando resposta do cliente", "value": r(status["Pending Customer Response"]),
         "unit": "fração", "source": "Medido no Dataset 1 (sintético: mix uniforme).", "editable": True},
        {"id": "followups_per_pending", "label": "Follow-ups manuais por ticket pendente", "value": 2, "unit": "follow-ups",
         "source": "Premissa: validar no histórico do helpdesk.", "editable": True},
        {"id": "followup_minutes", "label": "Tempo por follow-up", "value": 4, "unit": "min",
         "source": "Premissa de trabalho.", "editable": True},
        {"id": "followup_automation", "label": "Follow-ups automatizáveis", "value": 0.8, "unit": "fração",
         "source": "Premissa: lembrete e fechamento por inatividade; 20% exigem contato humano.", "editable": True},
        {"id": "draft_minutes", "label": "Tempo para redigir uma resposta", "value": 6, "unit": "min",
         "source": "Premissa de trabalho.", "editable": True},
        {"id": "draft_saving", "label": "Economia de tempo com rascunho sugerido", "value": 0.3, "unit": "fração",
         "source": "Premissa conservadora: o agente ainda lê, ajusta e aprova.", "editable": True},
        {"id": "human_only_share", "label": "Casos só-humanos (reembolso e cancelamento)", "value": r(human_only),
         "unit": "fração", "source": "Medido no Dataset 1 (sintético: mix uniforme).", "editable": True},
        {"id": "auto_coverage", "label": "Tickets roteados automaticamente", "value": auto["coverage"], "unit": "fração",
         "source": "Medido: holdout de 9.568 tickets (model_metrics.json).", "editable": False},
        {"id": "auto_accuracy", "label": "Acerto nos tickets roteados automaticamente", "value": auto["accuracy"],
         "unit": "fração", "source": "Medido: holdout de 9.568 tickets (model_metrics.json).", "editable": False},
    ]
    a = {x["id"]: x["value"] for x in assumptions}
    waste = compute_waste(a)
    total = sum(w["hoursPerYear"] for w in waste)
    recoverable = sum(w["recoverableHoursPerYear"] for w in waste)
    fte_hours = 1_760  # horas produtivas/ano de um agente em tempo integral
    print(f"desperdício estimado: {total:.0f} h/ano; recuperável: {recoverable:.0f} h/ano "
          f"(R$ {recoverable * a['hourly_cost']:,.0f}; {recoverable / fte_hours:.1f} FTE)")

    any_significant = any(t["significant"] for t in segment_tests)
    headline = [
        {"label": "Tickets não fechados", "value": br_pct(1 - status["Closed"]),
         "detail": f"{br_pct(status['Open'])} abertos e {br_pct(status['Pending Customer Response'])} aguardando o cliente."},
        {"label": "Abertos sem 1ª resposta", "value": f"{open_no_frt * 100:.0f}%",
         "detail": "Nenhum ticket aberto tem registro de primeira resposta. Numa operação real seria fila sem reconhecimento "
                   "ao cliente; neste dataset sintético pode ser só a definição de 'Open'. Primeira métrica a validar com dados reais."},
        {"label": "Gargalo por canal ou prioridade", "value": "Não detectado" if not any_significant else "Detectado",
         "detail": "Status não varia de forma significativa por canal, prioridade ou tipo (qui-quadrado, p > 0,05). "
                   "Com estes dados, apontar um 'pior canal' seria ruído." if not any_significant else "Ver testes por segmento."},
        {"label": "Triagem automatizável hoje", "value": br_pct(auto["coverage"]),
         "detail": f"dos tickets, com {br_pct(auto['accuracy'])} de acerto (medido); o restante vai para triagem humana."},
        {"label": "Horas recuperáveis por ano", "value": f"{br_int(recoverable)} h",
         "detail": f"≈ {br_dec(recoverable / fte_hours)} agentes em tempo integral, ou R$ {br_int(recoverable * a['hourly_cost'])} "
                   "por ano, com as premissas editáveis abaixo."},
    ]

    write_json("diagnostico.json", {
        "nTickets": n,
        "annualVolume": ANNUAL_VOLUME,
        "headline": headline,
        "segments": segments,
        "worstSegments": worst,
        "segmentTests": segment_tests,
        "csatDrivers": drivers,
        "assumptions": assumptions,
        "waste": waste,
    })


if __name__ == "__main__":
    main()
