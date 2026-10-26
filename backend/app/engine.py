"""Scoring + explanation shared by the single-patient and file-upload endpoints."""
import numpy as np
import pandas as pd

from ml.specs import DISEASES, feature_keys


def display(f: dict, v: float) -> str:
    if f["input"] == "select":
        return next((o["label"] for o in f["options"] if o["value"] == v), f"{v:g}")
    txt = f"{v:g}"
    return f"{txt} {f['unit']}" if f.get("unit") and f["unit"] not in ("count", "score", "ratio") else txt


def score(model, disease: str, X: pd.DataFrame, baseline: dict) -> tuple[np.ndarray, list[list[dict]]]:
    """Probabilities for every row plus a per-row explanation.

    Explanation = how much the risk drops if one value is replaced by the typical
    healthy patient's value (positive impact = that value raises risk). All variants
    for all rows are scored in a single predict_proba call.
    """
    keys = feature_keys(disease)
    spec = {f["key"]: f for f in DISEASES[disease]["features"]}
    X = X[keys]
    p = model.predict_proba(X)[:, 1]

    variants, owners = [], []
    values = X.to_numpy(dtype=float)
    for i, row in enumerate(values):
        for j, k in enumerate(keys):
            if not np.isnan(row[j]) and row[j] != baseline[k]:
                v = row.copy()
                v[j] = baseline[k]
                variants.append(v)
                owners.append((i, k))

    explanations: list[list[dict]] = [[] for _ in range(len(X))]
    if variants:
        pv = model.predict_proba(pd.DataFrame(variants, columns=keys))[:, 1]
        for (i, k), q in zip(owners, pv):
            f = spec[k]
            explanations[i].append({
                "feature": k, "label": f["label"],
                "display": display(f, values[i][keys.index(k)]),
                "baseline_display": display(f, baseline[k]),
                "impact": round(float(p[i] - q), 4),
            })
    for e in explanations:
        e.sort(key=lambda r: abs(r["impact"]), reverse=True)
    return p, explanations
