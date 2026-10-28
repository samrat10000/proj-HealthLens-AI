"""Smoke tests for the prediction service.  Run from backend/:  python -m pytest -q"""
import pytest

from app import service


def _sample(disease: str, label: str) -> dict:
    return dict(next(s["values"] for s in service.meta(disease)["samples"] if s["label"] == label))


def test_list_and_detail():
    ds = service.disease_summaries()
    assert {d["id"] for d in ds} == {"heart", "diabetes", "liver"}
    assert service.meta("heart")["leaderboard"]


def test_samples_rank_correctly():
    for d in ["heart", "diabetes", "liver"]:
        lo = service.predict(d, _sample(d, "Healthy profile"))
        hi = service.predict(d, _sample(d, "High-risk profile"))
        assert lo["probability"] < hi["probability"], d
        assert hi["contributions"], d


def test_optional_fields_are_imputed():
    vals = _sample("heart", "High-risk profile")
    vals.update(ca=None, thal=None, slope=None)
    assert len(service.predict("heart", vals)["imputed"]) == 3


def test_validation_errors():
    vals = _sample("diabetes", "Healthy profile")
    for bad in ({**vals, "glucose": 999}, {**vals, "glucose": None}, {**vals, "bogus": 1}):
        with pytest.raises(service.InputError):
            service.predict("diabetes", bad)
    with pytest.raises(service.InputError):
        service.predict("kidney", {})
