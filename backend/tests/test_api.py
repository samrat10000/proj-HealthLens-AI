"""Smoke tests for the API.  Run from backend/:  python -m pytest -q"""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def _sample(disease: str, label: str) -> dict:
    meta = json.loads((MODELS_DIR / f"{disease}_meta.json").read_text())
    return next(s["values"] for s in meta["samples"] if s["label"] == label)


def test_list_and_detail():
    with TestClient(app) as c:
        ds = c.get("/api/diseases").json()
        assert {d["id"] for d in ds} == {"heart", "diabetes", "liver"}
        detail = c.get("/api/diseases/heart").json()
        assert detail["features"] and detail["meta"]["leaderboard"]


def test_samples_rank_correctly():
    with TestClient(app) as c:
        for d in ["heart", "diabetes", "liver"]:
            lo = c.post(f"/api/predict/{d}", json={"values": _sample(d, "Healthy profile")}).json()
            hi = c.post(f"/api/predict/{d}", json={"values": _sample(d, "High-risk profile")}).json()
            assert lo["probability"] < hi["probability"], d
            assert hi["contributions"], d


def test_optional_fields_are_imputed():
    with TestClient(app) as c:
        vals = _sample("heart", "High-risk profile")
        vals.update(ca=None, thal=None, slope=None)
        r = c.post("/api/predict/heart", json={"values": vals})
        assert r.status_code == 200
        assert len(r.json()["imputed"]) == 3


def test_validation_errors():
    with TestClient(app) as c:
        vals = _sample("diabetes", "Healthy profile")
        assert c.post("/api/predict/diabetes", json={"values": {**vals, "glucose": 999}}).status_code == 422
        assert c.post("/api/predict/diabetes", json={"values": {**vals, "glucose": None}}).status_code == 422
        assert c.post("/api/predict/diabetes", json={"values": {**vals, "bogus": 1}}).status_code == 422
        assert c.post("/api/predict/kidney", json={"values": {}}).status_code == 404
