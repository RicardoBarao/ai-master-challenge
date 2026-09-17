"""Etapa 3 — Classificador de tickets (Dataset 2) + avaliação honesta + export para TypeScript.

Saídas:
  app/data/model_metrics.json   métricas, matriz de confusão, curva cobertura × acurácia
  app/data/model.json           vocabulário + idf + coeficientes (inferência em lib/classifier.ts)
  app/data/holdout.json         amostra do teste (nunca vista no treino) para /api/sample
  app/data/neighbors.json       amostra do treino para "tickets similares"
  analysis/out/parity_expected.json  predições do Python para o teste de paridade TS
"""

from __future__ import annotations

import json
import re
import time
import unicodedata

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.svm import LinearSVC

from common import HERE, SEED, load_d1, load_d2, r, write_json

MAX_FEATURES = 40_000
COEF_EPS = 0.2  # |coef| menor que isso vira zero no export: 2,85 MB e a mesma acurácia (medido de 0,02 a 0,3)
OOD_QUANTILE = 0.05  # guarda de domínio: aceita-se mandar ~5% dos tickets do próprio domínio para humano
HOLDOUT_EXPORT = 2_000
NEIGHBORS_EXPORT = 4_000


def normalize(text: str) -> str:
    """Mesma normalização de lib/classifier.ts: minúsculas, sem acento, só letras a-z."""
    text = unicodedata.normalize("NFKD", str(text).lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z]+", " ", text)).strip()


def make_vectorizer(**kw) -> TfidfVectorizer:
    # token_pattern restrito a [a-z]{2,} para ser reproduzível byte a byte em JS
    return TfidfVectorizer(preprocessor=normalize, token_pattern=r"\b[a-z]{2,}\b",
                           ngram_range=(1, 2), min_df=2, sublinear_tf=True, **kw)


def known_share(texts, vocab: set[str]) -> np.ndarray:
    """Fração dos tokens de conteúdo (sem stopwords) que o modelo conhece. Mesma regra de lib/classifier.ts.

    Stopwords ficam de fora porque o pré-processamento do Dataset 2 removeu parte delas (ex.: "my"),
    e um texto digitado normalmente não pode ser barrado só por conter pronomes.
    """
    out = []
    for t in texts:
        toks = [w for w in re.findall(r"\b[a-z]{2,}\b", normalize(t)) if w not in ENGLISH_STOP_WORDS]
        out.append(sum(tok in vocab for tok in toks) / len(toks) if toks else 0.0)
    return np.array(out)


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def evaluate(name, y_true, y_pred, extra=None):
    out = {"name": name, "accuracy": r(accuracy_score(y_true, y_pred)),
           "macroF1": r(f1_score(y_true, y_pred, average="macro"))}
    print(f"{name:<45} acc={out['accuracy']:.4f} macroF1={out['macroF1']:.4f} {extra or ''}")
    return out


def main() -> None:
    d2 = load_d2()
    X_text, y = d2["Document"].to_numpy(), d2["Topic_group"].to_numpy()
    idx = np.arange(len(d2))
    tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=SEED)
    print(f"treino={len(tr)} teste={len(te)}")

    candidates = []
    dummy = DummyClassifier(strategy="most_frequent").fit(X_text[tr], y[tr])
    candidates.append(evaluate("Baseline: sempre a classe mais comum", y[te], dummy.predict(X_text[te])))

    vec_full = make_vectorizer()
    Xtr_full = vec_full.fit_transform(X_text[tr]); Xte_full = vec_full.transform(X_text[te])
    nb = ComplementNB(alpha=0.3).fit(Xtr_full, y[tr])
    candidates.append(evaluate("TF-IDF + Complement Naive Bayes", y[te], nb.predict(Xte_full)))
    svc = LinearSVC(C=0.5).fit(Xtr_full, y[tr])
    candidates.append(evaluate("TF-IDF + Linear SVM", y[te], svc.predict(Xte_full),
                               f"(vocab={len(vec_full.vocabulary_)})"))

    t0 = time.time()
    lr_full = LogisticRegression(C=10, max_iter=3000).fit(Xtr_full, y[tr])
    candidates.append(evaluate("TF-IDF + Regressão Logística (vocab completo)", y[te], lr_full.predict(Xte_full),
                               f"({time.time() - t0:.0f}s)"))

    # Modelo exportável: vocabulário limitado + coeficientes esparsos
    vec = make_vectorizer(max_features=MAX_FEATURES)
    Xtr = vec.fit_transform(X_text[tr]); Xte = vec.transform(X_text[te])
    lr = LogisticRegression(C=10, max_iter=3000).fit(Xtr, y[tr])
    candidates.append(evaluate(f"TF-IDF + Regressão Logística ({MAX_FEATURES // 1000}k termos)", y[te], lr.predict(Xte)))

    coef = np.where(np.abs(lr.coef_) < COEF_EPS, 0.0, lr.coef_).round(3)
    intercept = lr.intercept_.round(4)
    proba = softmax(Xte @ coef.T + intercept)
    classes = lr.classes_
    y_pred = classes[proba.argmax(1)]
    chosen = f"TF-IDF + Regressão Logística ({MAX_FEATURES // 1000}k termos, exportado)"
    candidates.append(evaluate(chosen, y[te], y_pred,
                               f"(nnz coef={np.count_nonzero(coef)}/{coef.size})"))

    conf = proba.max(1)
    correct = y_pred == y[te]
    coverage = []
    for t in np.round(np.arange(0.30, 0.96, 0.05), 2):
        m = conf >= t
        coverage.append({"threshold": float(t), "coverage": r(m.mean()),
                         "accuracy": r(correct[m].mean() if m.any() else 1.0)})
    # limiar recomendado: maior cobertura com acurácia ≥ 95% nos tickets roteados automaticamente
    ok = [c for c in coverage if c["accuracy"] >= 0.95]
    recommended = max(ok, key=lambda c: c["coverage"])["threshold"] if ok else 0.9
    rec = next(c for c in coverage if c["threshold"] == recommended)
    print(f"limiar recomendado={recommended} cobertura={rec['coverage']} acurácia={rec['accuracy']}")

    p, rc, f, s = precision_recall_fscore_support(y[te], y_pred, labels=classes)
    order = pd.Series(s, index=classes).sort_values(ascending=False).index.tolist()
    per_class = [{"label": c, "precision": r(p[i]), "recall": r(rc[i]), "f1": r(f[i]), "support": int(s[i])}
                 for c in order for i in [list(classes).index(c)]]
    cm = confusion_matrix(y[te], y_pred, labels=order)

    # Cruzamento: o modelo treinado no D2 aplicado aos textos do D1 (outro domínio)
    d1 = load_d1()
    d1_text = (d1["Ticket Subject"] + " " + d1.apply(
        lambda row: row["Ticket Description"].replace("{product_purchased}", row["Product Purchased"]), axis=1))
    d1_conf = softmax(vec.transform(d1_text) @ coef.T + intercept).max(1)
    # Guarda de domínio: confiança alta NÃO protege contra texto de outro domínio (medido abaixo),
    # então checamos se o vocabulário do ticket é conhecido pelo modelo.
    vocab_set = set(vec.vocabulary_)
    te_known = known_share(X_text[te], vocab_set)
    d1_known = known_share(d1_text, vocab_set)
    ood_threshold = float(np.floor(np.quantile(te_known, OOD_QUANTILE) * 100) / 100)
    d1_pred = classes[softmax(vec.transform(d1_text) @ coef.T + intercept).argmax(1)]
    d1_confident = d1_conf >= recommended
    hardware_share = float((d1_pred[d1_confident] == "Hardware").mean())
    in_flag = float((te_known < ood_threshold).mean()); out_flag = float((d1_known < ood_threshold).mean())
    auto_te = (conf >= recommended) & (te_known >= ood_threshold)
    print(f"guarda de domínio: limiar={ood_threshold} D2 barrado={in_flag:.3f} D1 barrado={out_flag:.3f}")
    print(f"D2 teste roteado auto com guarda: cobertura={auto_te.mean():.4f} acurácia={correct[auto_te].mean():.4f}")
    edges = [0, 0.3, 0.5, 0.7, recommended, 1.0001]
    labels = ["< 30%", "30–50%", "50–70%", f"70–{int(recommended * 100)}%", f"≥ {int(recommended * 100)}%"]
    hist = pd.Series(pd.cut(d1_conf, edges, labels=labels, right=False)).value_counts(normalize=True).reindex(labels, fill_value=0)
    te_auto = rec["coverage"]
    d1_auto = float((d1_conf >= recommended).mean())
    print(f"D1 com confiança ≥ limiar: {d1_auto:.3f} (no D2 teste: {te_auto})")

    write_json("model_metrics.json", {
        "split": {"train": int(len(tr)), "test": int(len(te)), "seed": SEED},
        "candidates": candidates,
        "chosen": chosen,
        "perClass": per_class,
        "confusion": {"labels": order, "matrix": cm.tolist()},
        "coverage": coverage,
        "recommendedThreshold": recommended,
        "autoRouting": {"coverage": r(auto_te.mean()), "accuracy": r(correct[auto_te].mean())},
        "crossDomain": {
            "note": (f"Aplicado aos {len(d1)} tickets do Dataset 1 (e-commerce de eletrônicos), o modelo treinado em TI "
                     f"interna passa do limiar de confiança em {d1_auto * 100:.1f}% dos casos, e {hardware_share * 100:.0f}% "
                     f"deles viram 'Hardware', inclusive pedidos de pagamento e reembolso. Confiança alta não protege "
                     f"contra texto de outro domínio. Por isso a rota automática também exige que o vocabulário do "
                     f"ticket seja conhecido pelo modelo. Esse guarda barra {out_flag * 100:.1f}% dos tickets do Dataset 1 "
                     f"e só {in_flag * 100:.1f}% dos tickets do próprio domínio. Em produção, re-treinar com o histórico "
                     f"rotulado da operação."),
            "confidenceHistogram": [{"bucket": b, "share": r(v)} for b, v in hist.items()],
            "confidentShare": r(d1_auto),
            "confidentPredictedHardware": r(hardware_share),
            "oodGuard": {"threshold": ood_threshold, "inDomainFlagged": r(in_flag), "outDomainFlagged": r(out_flag)},
        },
    })

    # ---- export do modelo para TypeScript ----
    vocab = sorted(vec.vocabulary_.items(), key=lambda kv: kv[1])
    terms = [t for t, _ in vocab]
    weights = {}
    for j, t in enumerate(terms):
        col = coef[:, j]
        if np.any(col):
            weights[t] = [float(v) for v in col]
    model = {
        "version": 1,
        "classes": list(classes),
        "threshold": recommended,
        "oodThreshold": ood_threshold,
        "stopWords": sorted(ENGLISH_STOP_WORDS),
        "sublinearTf": True,
        "ngramRange": [1, 2],
        "tokenPattern": "[a-z]{2,}",
        "idf": {t: round(float(vec.idf_[j]), 5) for j, t in enumerate(terms)},
        "weights": weights,
        "intercept": [float(v) for v in intercept],
    }
    model_path = write_json("model.json", model, generated=False, compact=True)
    print(f"model.json: {model_path.stat().st_size / 1e6:.2f} MB, {len(terms)} termos, {len(weights)} com peso")

    rng = np.random.default_rng(SEED)
    hold = rng.choice(te, size=HOLDOUT_EXPORT, replace=False)
    write_json("holdout.json", {"note": "Amostra aleatória do conjunto de teste (nunca vista no treino).",
                                "items": [{"id": int(i), "text": X_text[i], "label": y[i]} for i in hold]})
    neigh = rng.choice(tr, size=NEIGHBORS_EXPORT, replace=False)
    write_json("neighbors.json", {"note": "Amostra do treino usada para mostrar tickets similares.",
                                  "items": [{"id": int(i), "text": X_text[i], "label": y[i]} for i in neigh]})

    # predições de referência para o teste de paridade Python × TypeScript
    hold_pos = {i: k for k, i in enumerate(te)}
    rows = [hold_pos[i] for i in hold]
    out_dir = HERE / "out"; out_dir.mkdir(exist_ok=True)
    (out_dir / "parity_expected.json").write_text(json.dumps([
        {"id": int(i), "label": y_pred[k], "confidence": round(float(conf[k]), 6)}
        for i, k in zip(hold, rows)]), encoding="utf-8")
    print(f"acurácia na amostra holdout exportada ({HOLDOUT_EXPORT}): {correct[rows].mean():.4f}")


if __name__ == "__main__":
    main()
