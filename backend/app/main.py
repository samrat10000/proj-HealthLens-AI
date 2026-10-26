"""FastAPI service exposing the trained diagnostic models.

Run (from backend/):  uvicorn app.main:app --reload --port 8000
"""
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ml import samples
from ml.specs import DISEASES, RISK_BANDS, feature_keys, risk_level

from . import batch
from .engine import display, score

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
FRONTEND_DIST = ROOT.parent / "frontend" / "dist"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

MODELS: dict = {}
META: dict = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    for d in DISEASES:
        path = MODELS_DIR / f"{d}.joblib"
        if not path.exists():
            raise RuntimeError(f"Model {path} missing - run `python -m ml.train` first")
        MODELS[d] = joblib.load(path)
        META[d] = json.loads((MODELS_DIR / f"{d}_meta.json").read_text())
    yield


app = FastAPI(title="AI Health Diagnostic Assistant", version="1.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class PredictRequest(BaseModel):
    values: dict[str, float | None]


def _spec(disease: str) -> dict:
    if disease not in DISEASES:
        raise HTTPException(404, f"Unknown disease '{disease}'. Options: {', '.join(DISEASES)}")
    return DISEASES[disease]


def _validate(disease: str, values: dict) -> dict:
    spec = _spec(disease)
    unknown = set(values) - set(feature_keys(disease))
    if unknown:
        raise HTTPException(422, f"Unknown fields: {', '.join(sorted(unknown))}")
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
        raise HTTPException(422, "; ".join(errors))
    return clean


def _flags(disease: str, row: dict) -> list[dict]:
    flags = []
    for f in DISEASES[disease]["features"]:
        rng, v = f.get("normal"), row[f["key"]]
        if not rng or v is None or np.isnan(v):
            continue
        lo, hi = rng
        status = "low" if lo is not None and v < lo else "high" if hi is not None and v > hi else None
        if status:
            flags.append({"feature": f["key"], "label": f["label"], "status": status,
                          "value": display(f, v), "range": _range_txt(f)})
    return flags


def _range_txt(f: dict) -> str:
    lo, hi = f["normal"]
    unit = f.get("unit", "")
    if lo is None:
        return f"≤ {hi:g} {unit}".strip()
    if hi is None:
        return f"≥ {lo:g} {unit}".strip()
    return f"{lo:g}–{hi:g} {unit}".strip()


def _download(df: pd.DataFrame, name: str, fmt: str) -> Response:
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(400, "format must be csv or xlsx")
    media = "text/csv" if fmt == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(samples.to_bytes(df, fmt), media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"'})


# ---------------------------------------------------------------- routes

@app.get("/api/health")
def health():
    return {"status": "ok", "models_loaded": list(MODELS)}


@app.get("/api/diseases")
def list_diseases():
    return [{"id": d, "name": s["name"], "tagline": s["tagline"], "dataset": s["dataset"],
             "n_features": len(s["features"]), "model": META[d]["best_model"],
             "accuracy": META[d]["holdout"]["accuracy"], "roc_auc": META[d]["holdout"]["roc_auc"],
             "n_patients": META[d]["cleaning"]["rows_clean"]}
            for d, s in DISEASES.items()]


@app.get("/api/diseases/{disease}")
def disease_detail(disease: str):
    spec = _spec(disease)
    return {"id": disease, **spec, "risk_bands": RISK_BANDS[:-1], "meta": META[disease]}


@app.post("/api/predict/{disease}")
def predict(disease: str, req: PredictRequest):
    row = _validate(disease, req.values)
    t0 = time.perf_counter()
    X = pd.DataFrame([row], columns=feature_keys(disease))
    probs, explanations = score(MODELS[disease], disease, X, META[disease]["baseline"])
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
        "flags": _flags(disease, row),
        "imputed": [f["label"] for f in spec["features"] if np.isnan(row[f["key"]])],
        "model": META[disease]["best_model"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


@app.post("/api/batch")
async def predict_file(file: UploadFile = File(...), disease: str | None = Form(None)):
    """Score every patient in an uploaded CSV / Excel file."""
    t0 = time.perf_counter()
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 5 MB.")
    try:
        df = batch.read_table(file.filename or "upload.csv", content)
        detected, match = batch.detect_disease(list(df.columns))
        disease = disease or detected
        _spec(disease)
        parsed = batch.parse(disease, df)
    except HTTPException:
        raise
    except Exception as e:  # unreadable file, unknown columns, ...
        raise HTTPException(422, str(e) or "Could not read the file.")

    spec = DISEASES[disease]
    rows = parsed["rows"]
    ok = [r for r in rows if not r["errors"]]
    if ok:
        X = pd.DataFrame([{k: (np.nan if v is None else v) for k, v in r["values"].items()} for r in ok],
                         columns=feature_keys(disease))
        probs, explanations = score(MODELS[disease], disease, X, META[disease]["baseline"])
        for r, p, expl, (_, xrow) in zip(ok, probs, explanations, X.iterrows()):
            p = float(p)
            r.update({
                "probability": round(p, 4),
                "risk_level": risk_level(p),
                "predicted": int(p >= 0.5),
                "prediction": spec["positive_label"] if p >= 0.5 else spec["negative_label"],
                "top_factors": [e for e in expl if e["impact"] > 0.005][:3],
                "flags": [fl["label"] for fl in _flags(disease, xrow.to_dict())],
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
        "filename": file.filename,
        "summary": summary,
        "columns": parsed["columns"],
        "rows": rows,
        "model": META[disease]["best_model"],
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


@app.get("/api/template/{disease}")
def download_template(disease: str, format: str = "csv"):
    _spec(disease)
    return _download(samples.template(disease), f"{disease}_template", format)


@app.get("/api/sample/{disease}")
def download_sample(disease: str, format: str = "csv"):
    _spec(disease)
    return _download(samples.sample(disease), f"{disease}_patients", format)


# Serve the built React app (production / single-server mode)
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        file = FRONTEND_DIST / path
        return FileResponse(file if path and file.is_file() else FRONTEND_DIST / "index.html")
