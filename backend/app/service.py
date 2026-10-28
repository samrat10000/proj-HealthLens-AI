"""Prediction service used by the Streamlit UI: model loading, validation, single + file scoring."""
import json
import time
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.specs import DISEASES, feature_keys, risk_level

from . import batch
from .engine import display, score

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class InputError(ValueError):
    """Bad user input (invalid values, unreadable file, ...). The message is shown to the user."""


@lru_cache(maxsize=None)
def model(disease: str):
    _spec(disease)
    path = MODELS_DIR / f"{disease}.joblib"
    if not path.exists():
        raise RuntimeError(f"Model {path} missing - run `python -m ml.train` first")
    return joblib.load(path)


@lru_cache(maxsize=None)
def meta(disease: str) -> dict:
    _spec(disease)
    return json.loads((MODELS_DIR / f"{disease}_meta.json").read_text())


def models_ready() -> bool:
    return all((MODELS_DIR / f"{d}.joblib").exists() for d in DISEASES)


def _spec(disease: str) -> dict:
    if disease not in DISEASES:
        raise InputError(f"Unknown disease '{disease}'. Options: {', '.join(DISEASES)}")
    return DISEASES[disease]


def validate(disease: str, values: dict) -> dict:
    spec = _spec(disease)
    unknown = set(values) - set(feature_keys(disease))
    if unknown:
        raise InputError(f"Unknown fields: {', '.join(sorted(unknown))}")
    errors, clean = [], {}
    for f in spec["features"]:
        v = values.get(f["key"])
        if v is None or (isinstance(v, float) and np.isnan(v)):
            if not f.get("optional"):
                errors.append(f"{f['label']} is required")
            clean[f["key"]] = np.nan
            continue
        if f["input"] == "select":
            allowed = {o["value"] for o in f["options"]}
            if v not in allowed:
                errors.append(f"{f['label']} must be one of {sorted(allowed)}")
        elif not (f["min"] <= v <= f["max"]):
            errors.append(f"{f['label']} must be between {f['min']} and {f['max']} {f.get('unit', '')}".strip())
        clean[f["key"]] = float(v)
    if errors:
        raise InputError("; ".join(errors))
    return clean


def flags(disease: str, row: dict) -> list[dict]:
    out = []
    for f in DISEASES[disease]["features"]:
        rng, v = f.get("normal"), row[f["key"]]
        if not rng or v is None or np.isnan(v):
            continue
        lo, hi = rng
        status = "low" if lo is not None and v < lo else "high" if hi is not None and v > hi else None
        if status:
            out.append({"feature": f["key"], "label": f["label"], "status": status,
                        "value": display(f, v), "range": range_text(f)})
    return out


def range_text(f: dict) -> str:
    lo, hi = f["normal"]
    unit = f.get("unit", "")
    if lo is None:
        return f"≤ {hi:g} {unit}".strip()
    if hi is None:
        return f"≥ {lo:g} {unit}".strip()
    return f"{lo:g}–{hi:g} {unit}".strip()


def disease_summaries() -> list[dict]:
    return [{"id": d, "name": s["name"], "tagline": s["tagline"], "dataset": s["dataset"],
             "n_features": len(s["features"]), "model": meta(d)["best_model"],
             "accuracy": meta(d)["holdout"]["accuracy"], "roc_auc": meta(d)["holdout"]["roc_auc"],
             "n_patients": meta(d)["cleaning"]["rows_clean"]}
            for d, s in DISEASES.items()]


def predict(disease: str, values: dict) -> dict:
    row = validate(disease, values)
    t0 = time.perf_counter()
    X = pd.DataFrame([row], columns=feature_keys(disease))
    probs, explanations = score(model(disease), disease, X, meta(disease)["baseline"])
    p = float(probs[0])
    level = risk_level(p)
    spec = DISEASES[disease]
    return {
        "disease": disease,
        "probability": round(p, 4),
        "risk_level": level,
        "prediction": spec["positive_label"] if p >= 0.5 else spec["negative_label"],
        "advice": spec["advice"][level],
        "contributions": explanations[0],
        "flags": flags(disease, row),
        "imputed": [f["label"] for f in spec["features"] if np.isnan(row[f["key"]])],
        "model": meta(disease)["best_model"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def predict_file(filename: str, content: bytes, disease: str | None = None) -> dict:
    """Score every patient in an uploaded CSV / Excel file."""
    t0 = time.perf_counter()
    if len(content) > MAX_UPLOAD_BYTES:
        raise InputError("File is larger than 5 MB.")
    try:
        df = batch.read_table(filename or "upload.csv", content)
        detected, match = batch.detect_disease(list(df.columns))
        disease = disease or detected
        _spec(disease)
        parsed = batch.parse(disease, df)
    except InputError:
        raise
    except Exception as e:  # unreadable file, unknown columns, ...
        raise InputError(str(e) or "Could not read the file.") from e

    spec = DISEASES[disease]
    rows = parsed["rows"]
    ok = [r for r in rows if not r["errors"]]
    if ok:
        X = pd.DataFrame([{k: (np.nan if v is None else v) for k, v in r["values"].items()} for r in ok],
                         columns=feature_keys(disease))
        probs, explanations = score(model(disease), disease, X, meta(disease)["baseline"])
        for r, p, expl, (_, xrow) in zip(ok, probs, explanations, X.iterrows()):
            p = float(p)
            r.update({
                "probability": round(p, 4),
                "risk_level": risk_level(p),
                "predicted": int(p >= 0.5),
                "prediction": spec["positive_label"] if p >= 0.5 else spec["negative_label"],
                "top_factors": [e for e in expl if e["impact"] > 0.005][:3],
                "flags": [fl["label"] for fl in flags(disease, xrow.to_dict())],
                "imputed": [f["label"] for f in spec["features"] if r["values"][f["key"]] is None],
            })

    levels = [r["risk_level"] for r in ok]
    labelled = [r for r in ok if r["actual"] is not None]
    summary = {
        "total": len(rows),
        "scored": len(ok),
        "errors": len(rows) - len(ok),
        "high": levels.count("high"),
        "moderate": levels.count("moderate"),
        "low": levels.count("low"),
        "predicted_positive": sum(r["predicted"] for r in ok),
        "mean_probability": round(float(np.mean([r["probability"] for r in ok])), 4) if ok else None,
        "labelled": len(labelled),
        "agreement": round(sum(r["predicted"] == r["actual"] for r in labelled) / len(labelled), 4)
        if labelled else None,
    }
    return {
        "disease": disease,
        "disease_name": spec["name"],
        "auto_detected": disease == detected,
        "match_scores": {k: round(v, 2) for k, v in match.items()},
        "filename": filename,
        "summary": summary,
        "columns": parsed["columns"],
        "rows": rows,
        "model": meta(disease)["best_model"],
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def results_table(result: dict) -> pd.DataFrame:
    """Flat, human-readable table of a file screening, for download."""
    out = []
    for r in result["rows"]:
        actual, predicted = r["actual"], r.get("predicted")
        out.append({
            "Patient ID": r["patient_id"],
            "Row": r["row"],
            "Risk %": round(r["probability"] * 100, 1) if "probability" in r else None,
            "Risk level": r.get("risk_level", ""),
            "Prediction": r.get("prediction", ""),
            "Recorded diagnosis": "" if actual is None else "Disease" if actual else "Healthy",
            "Match": "" if actual is None or predicted is None else "Yes" if actual == predicted else "No",
            "Main reasons": "; ".join(f"{f['label']}: {f['display']}" for f in r.get("top_factors", [])),
            "Out-of-range values": "; ".join(r.get("flags", [])),
            "Estimated values": "; ".join(r.get("imputed", [])),
            "Errors": "; ".join(r["errors"]),
        })
    return pd.DataFrame(out)
