"""Load + clean each raw dataset into (X, y, report).

Only *deterministic* cleaning happens here (type fixing, impossible values -> NaN,
deduplication, target encoding). Statistical steps such as imputation and scaling
live inside the sklearn Pipeline so they are fit on training folds only (no leakage).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from .specs import feature_keys

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


class Report:
    def __init__(self, raw: pd.DataFrame):
        self.rows_raw = len(raw)
        self.steps: list[dict] = []

    def add(self, action: str, detail: str, affected: int = 0) -> None:
        self.steps.append({"action": action, "detail": detail, "affected": int(affected)})

    def finish(self, X: pd.DataFrame, y: pd.Series) -> dict:
        return {
            "rows_raw": self.rows_raw,
            "rows_clean": len(X),
            "n_features": X.shape[1],
            "positive_rate": round(float(y.mean()), 4),
            "class_counts": {"positive": int(y.sum()), "negative": int((1 - y).sum())},
            "missing_after_cleaning": {k: int(v) for k, v in X.isna().sum().items() if v > 0},
            "steps": self.steps,
        }


def _zero_to_nan(df: pd.DataFrame, cols: list[str], rep: Report, why: str) -> None:
    for c in cols:
        n = int((df[c] == 0).sum())
        if n:
            df.loc[df[c] == 0, c] = np.nan
            rep.add("Impossible zeros -> missing", f"{c}: {n} rows ({why})", n)


def _drop_duplicates(df: pd.DataFrame, rep: Report) -> pd.DataFrame:
    n = int(df.duplicated().sum())
    if n:
        rep.add("Removed duplicate records", f"{n} exact duplicate patients dropped", n)
    return df.drop_duplicates().reset_index(drop=True)


def load_heart():
    cols = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
            "exang", "oldpeak", "slope", "ca", "thal", "num"]
    parts = []
    for site in ["cleveland", "hungarian", "switzerland", "va"]:
        part = pd.read_csv(RAW_DIR / f"heart_{site}.data", header=None, names=cols, na_values="?")
        part["_site"] = site
        parts.append(part)
    df = pd.concat(parts, ignore_index=True)
    rep = Report(df)
    rep.add("Merged clinic sources", "Cleveland, Hungary, Switzerland and VA Long Beach combined", len(df))
    rep.add("Parsed '?' placeholders", "'?' markers converted to proper missing values",
            int(df[cols].isna().sum().sum()))

    df = df.drop(columns="_site")
    _zero_to_nan(df, ["chol", "trestbps"], rep, "physiologically impossible")
    df = _drop_duplicates(df, rep)

    y = (df["num"] > 0).astype(int)
    rep.add("Binarised target", "Severity 0-4 collapsed to 0 = healthy, 1-4 = disease", int(y.sum()))
    X = df[feature_keys("heart")]
    return X, y, rep.finish(X, y)


def load_diabetes():
    cols = ["pregnancies", "glucose", "blood_pressure", "skin_thickness", "insulin",
            "bmi", "pedigree", "age", "outcome"]
    df = pd.read_csv(RAW_DIR / "diabetes.csv", header=None, names=cols)
    rep = Report(df)
    _zero_to_nan(df, ["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"], rep,
                 "0 used as a missing-value code")
    df = _drop_duplicates(df, rep)

    y = df["outcome"].astype(int)
    X = df[feature_keys("diabetes")]
    return X, y, rep.finish(X, y)


def load_liver():
    cols = ["age", "gender", "total_bilirubin", "direct_bilirubin", "alk_phos", "alt", "ast",
            "total_protein", "albumin", "ag_ratio", "selector"]
    df = pd.read_csv(RAW_DIR / "liver.csv", header=None, names=cols)
    rep = Report(df)
    df["gender"] = df["gender"].str.strip().map({"Male": 1, "Female": 0})
    rep.add("Encoded categorical", "gender: Male -> 1, Female -> 0", len(df))
    df = _drop_duplicates(df, rep)

    y = (df["selector"] == 1).astype(int)
    rep.add("Re-coded target", "Selector 1 (liver patient) -> 1, 2 (healthy) -> 0", int(y.sum()))
    skewed = ["total_bilirubin", "direct_bilirubin", "alk_phos", "alt", "ast"]
    rep.add("Skew correction (in pipeline)", "log1p transform on " + ", ".join(skewed), 0)
    X = df[feature_keys("liver")]
    return X, y, rep.finish(X, y)


LOADERS = {"heart": load_heart, "diabetes": load_diabetes, "liver": load_liver}
