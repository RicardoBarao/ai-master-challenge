"""Etapa 5 — Renderiza docs/*.md a partir de docs/templates/*.md.tmpl e dos JSONs gerados.

A prosa é escrita à mão nos templates; todo número vem de um placeholder {{chave}} preenchido aqui.
Placeholder sem valor → erro (nenhum número digitado à mão nos documentos).
"""

from __future__ import annotations

import json
import re

from common import APP_DATA, HERE

DOCS = HERE.parents[1] / "docs"
TEMPLATES = DOCS / "templates"
PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

ROUTE_PT = {"auto": "Automático", "revisao_humana": "Revisão humana", "escalar": "Escalação"}
REASON_PT = {
    "auto": "Roteado automaticamente",
    "low_confidence": "Confiança abaixo do limiar",
    "out_of_domain": "Vocabulário fora do padrão (guarda de domínio)",
    "always_human": "Previsto como privilégio administrativo",
    "admin_rights_risk": "Probabilidade de privilégio acima do limiar",
    "escalation_terms": "Termo de risco/urgência",
}


def load(name: str) -> dict:
    return json.loads((APP_DATA / name).read_text(encoding="utf-8"))


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%".replace(".", ",")


def dec(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def num(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def ci(interval: dict, digits: int = 1) -> str:
    return f"{pct(interval['low'], digits)}–{pct(interval['high'], digits)}"


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def build_context() -> dict[str, str]:
    audit, metrics, routing, diag = load("audit.json"), load("model_metrics.json"), load("routing_eval.json"), load("diagnostico.json")
    t, sel, rt, rv = metrics["test"], metrics["selection"], routing["test"], routing["validation"]
    sc, a = diag["scenario"], {x["id"]: x for x in diag["scenario"]["assumptions"]}
    routes = {x["route"]: x for x in rt["routes"]}
    reasons = {x["reasonCode"]: x for x in rt["reasons"]}
    waste = {w["id"]: w for w in sc["waste"]}
    obs = {o["id"]: o for o in diag["observations"]}
    splits = {s["name"]: s for s in metrics["splits"]}
    findings = {f["id"]: f for f in audit["findings"]}
    exp = metrics["exploratory"]
    cd = metrics["crossDomain"]
    d1_routes = {x["route"]: x["share"] for x in cd["routes"]}
    csat = {c["variable"]: c for c in diag["tests"]["csatDrivers"]}
    seg = {s["variable"]: s for s in diag["tests"]["segmentTests"]}

    ctx: dict[str, str] = {
        # auditoria
        "d1_rows": num(audit["d1"]["rows"]),
        "d2_rows": num(audit["d2"]["rows"]),
        "audit_times": findings["d1-times"]["evidence"],
        "audit_uniform": findings["d1-uniform"]["evidence"],
        "audit_csat": findings["d1-csat"]["evidence"],
        "audit_text": findings["d1-text"]["evidence"],
        # partições e seleção
        "n_train": num(splits["treino"]["n"]), "n_val": num(splits["validacao"]["n"]), "n_test": num(splits["teste"]["n"]),
        "sel_C": str(sel["C"]), "sel_eps": dec(sel["coefEps"], 2),
        "sel_conf": pct(sel["confidenceThreshold"], 0), "sel_ood": pct(sel["oodThreshold"], 0),
        "sel_admin": pct(sel["adminRightsThreshold"], 0) if sel["adminRightsThreshold"] is not None else "não usada",
        "sel_criteria": "\n".join(f"- {c}" for c in sel["criteria"]),
        "table_candidates": table(["Modelo (validação)", "Acurácia", "F1 macro"],
                                  [[c["name"], pct(c["accuracy"]), dec(c["macroF1"], 3)] for c in sel["candidates"]]),
        # teste do modelo
        "test_acc": pct(t["accuracy"]), "test_acc_ci": ci(t["accuracyCI"]),
        "test_f1": dec(t["macroF1"], 3), "test_f1_ci": f"{dec(t['macroF1CI']['low'], 3)}–{dec(t['macroF1CI']['high'], 3)}",
        "test_baseline": pct(t["baselineAccuracy"]),
        "table_per_class": table(["Categoria", "Precisão", "Recall", "F1", "Tickets no teste"],
                                 [[c["label"], pct(c["precision"]), pct(c["recall"]), dec(c["f1"], 3), num(c["support"])] for c in t["perClass"]]),
        "ar_recall": pct(next(c["recall"] for c in t["perClass"] if c["label"] == "Administrative rights")),
        # histórico exploratório
        "exp_acc": pct(exp["accuracy"]), "exp_f1": dec(exp["macroF1"], 3),
        "exp_auto": pct(exp["autoCoverage"]), "exp_auto_acc": pct(exp["autoAccuracy"]),
        # roteamento (teste, política completa)
        "rt_n": num(rt["n"]),
        "rt_auto": pct(routes["auto"]["share"]), "rt_auto_n": num(routes["auto"]["n"]), "rt_auto_ci": ci(rt["auto"]["shareCI"]),
        "rt_auto_acc": pct(rt["auto"]["accuracy"]), "rt_auto_acc_ci": ci(rt["auto"]["accuracyCI"]), "rt_auto_errors": num(rt["auto"]["errors"]),
        "rt_human": pct(routes["revisao_humana"]["share"]), "rt_human_n": num(routes["revisao_humana"]["n"]),
        "rt_escal": pct(routes["escalar"]["share"]), "rt_escal_n": num(routes["escalar"]["n"]),
        "rv_auto": pct(rv["auto"]["share"]), "rv_auto_acc": pct(rv["auto"]["accuracy"]),
        "table_routes": table(["Destino", "Tickets", "Proporção"],
                              [[ROUTE_PT[x["route"]], num(x["n"]), pct(x["share"])] for x in rt["routes"]]),
        "table_reasons": table(["Motivo", "Tickets", "Proporção"],
                               [[REASON_PT[x["reasonCode"]], num(x["n"]), pct(x["share"])] for x in rt["reasons"]]),
        "table_by_category": table(
            ["Categoria real", "Tickets", "Automático", "Revisão humana", "Escalação", "Acerto nos automáticos"],
            [[c["label"], num(c["n"]), num(c["auto"]), num(c["revisao_humana"]), num(c["escalar"]),
              pct(c["autoAccuracy"]) if c["autoAccuracy"] is not None else "—"] for c in rt["byTrueCategory"]]),
        "ar_total": num(rt["adminRightsLeak"]["trueAdminRights"]), "ar_leak_n": num(rt["adminRightsLeak"]["autoRoutedElsewhere"]),
        "ar_leak": pct(rt["adminRightsLeak"]["share"]),
        "ar_leak_queues": ", ".join(f"{q['label']} ({q['n']})" for q in rt["adminRightsLeak"]["toQueues"]) or "nenhuma",
        "ar_leak_val": pct(rv["adminRightsLeak"]["share"]),
        "reason_admin_n": num(reasons["admin_rights_risk"]["n"]), "reason_always_n": num(reasons["always_human"]["n"]),
        "reason_ood": pct(reasons["out_of_domain"]["share"]), "reason_lowconf": pct(reasons["low_confidence"]["share"]),
        "py_agreement": pct(rt["pythonAgreement"]["route"], 0),
        # cruzamento com D1
        "cd_confident": pct(cd["confidentShare"]), "cd_hw": pct(cd["confidentPredictedHardware"], 0),
        "cd_ood": pct(cd["oodFlagged"]), "cd_ood_in": pct(cd["inDomainOodFlagged"]),
        "cd_auto": pct(d1_routes["auto"]), "cd_human": pct(d1_routes["revisao_humana"]), "cd_escal": pct(d1_routes["escalar"]),
        # diagnóstico
        "obs_not_closed": obs["not_closed"]["value"], "obs_not_closed_detail": obs["not_closed"]["detail"],
        "obs_open_no_frt": obs["open_no_frt"]["value"], "obs_pending": obs["pending"]["value"],
        "seg_channel": seg["canal"]["conclusion"], "seg_priority": seg["prioridade"]["conclusion"],
        "seg_type": seg["tipo"]["conclusion"], "seg_combo": seg["canal × prioridade"]["conclusion"],
        "table_csat": table(["Variável", "Teste", "p", "ε²", "Diferença não detectável até"],
                            [[c["variable"], c["test"], dec(c["pValue"], 2), dec(c["effectSize"], 4), f"±{dec(c['detectableDiff'], 2)} ponto"]
                             for c in diag["tests"]["csatDrivers"]]),
        "csat_channel_groups": "; ".join(f"{g['label']} {dec(g['mean'])} (IC {dec(g['ci']['low'])}–{dec(g['ci']['high'])})"
                                         for g in csat["canal"]["groups"]),
        "limitations": "\n".join(f"- {x['text']}" for x in diag["limitations"]),
        # cenário
        "sc_note": sc["note"],
        "sc_total_hours": num(sc["totals"]["hoursPerYear"]), "sc_recoverable": num(sc["totals"]["recoverableHoursPerYear"]),
        "sc_fte": dec(sc["totals"]["fte"], 1), "sc_cost": num(sc["totals"]["recoverableCost"]),
        "table_waste": table(["Etapa", "Horas/ano (hoje)", "Recuperável/ano", "Como foi calculado"],
                             [[w["step"], num(w["hoursPerYear"]), num(w["recoverableHoursPerYear"]), w["rationale"]] for w in sc["waste"]]),
        "table_assumptions": table(["Premissa", "Valor", "Tipo", "Fonte / como validar"],
                                   [[x["label"], f"{dec(x['value'], 4).rstrip('0').rstrip(',')} {x['unit']}", x["kind"], x["source"]]
                                    for x in sc["assumptions"]]),
        "table_sensitivity": table(["Roteamento automático", "Economia líquida com rascunho", "Horas recuperáveis/ano"],
                                   [[pct(s["autoShare"]), pct(s["draftSaving"], 0), num(s["recoverableHoursPerYear"])] for s in sc["sensitivity"]]),
        "w_triage": num(waste["triage"]["recoverableHoursPerYear"]), "w_rework": num(waste["rework"]["recoverableHoursPerYear"]),
        "w_followup": num(waste["followup"]["recoverableHoursPerYear"]), "w_drafting": num(waste["drafting"]["recoverableHoursPerYear"]),
        "sens_low": num(min(s["recoverableHoursPerYear"] for s in sc["sensitivity"])),
        "hourly_cost": num(a["hourly_cost"]["value"]), "annual_volume": num(a["annual_volume"]["value"]),
    }
    return ctx


def render(template: str, ctx: dict[str, str], name: str) -> str:
    missing = sorted({m for m in PLACEHOLDER.findall(template) if m not in ctx})
    if missing:
        raise SystemExit(f"{name}: placeholders sem valor: {missing}")
    header = f"<!-- Gerado por solution/analysis/05_report.py a partir de docs/templates/{name}. Não edite à mão. -->\n\n"
    return header + PLACEHOLDER.sub(lambda m: ctx[m.group(1)], template)


def main() -> None:
    ctx = build_context()
    for tmpl in sorted(TEMPLATES.glob("*.md.tmpl")):
        out = DOCS / tmpl.name.removesuffix(".tmpl")
        out.write_text(render(tmpl.read_text(encoding="utf-8"), ctx, tmpl.name), encoding="utf-8")
        print(f"→ docs/{out.name}")


if __name__ == "__main__":
    main()
