"""Human-friendly patient files: blank templates and real-patient samples (CSV / Excel).

Run `python -m ml.samples` to write them to ../sample_data/ for sharing.
"""
import io
from pathlib import Path

import numpy as np
import pandas as pd

from .cleaning import LOADERS
from .specs import DISEASES

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"


def header(f: dict) -> str:
    unit = f.get("unit")
    return f"{f['label']} ({unit})" if f["input"] == "number" and unit not in (None, "count", "score", "ratio") \
        else f["label"]


def readable(disease: str, X: pd.DataFrame, ids: list[str], y: pd.Series | None = None) -> pd.DataFrame:
    spec = DISEASES[disease]
    out = pd.DataFrame({"Patient ID": ids})
    for f in spec["features"]:
        col = X[f["key"]].to_numpy()
        if f["input"] == "select":
            labels = {o["value"]: o["label"] for o in f["options"]}
            out[header(f)] = [labels.get(v, "") if not pd.isna(v) else "" for v in col]
        else:
            out[header(f)] = [v if not pd.isna(v) else None for v in col]
    if y is not None:
        out["Actual diagnosis"] = [spec["positive_label"] if v else spec["negative_label"] for v in y]
    return out


def template(disease: str) -> pd.DataFrame:
    feats = DISEASES[disease]["features"]
    X = pd.DataFrame([{f["key"]: f["default"] for f in feats}])
    return readable(disease, X, ["P-001"])


def sample(disease: str, n: int = 40, seed: int = 7) -> pd.DataFrame:
    X, y, _ = LOADERS[disease]()
    required = [f["key"] for f in DISEASES[disease]["features"] if not f.get("optional")]
    usable = X[required].notna().all(axis=1).to_numpy()
    X, y = X[usable], y[usable]
    rng = np.random.default_rng(seed)
    pos = rng.choice(np.where(y == 1)[0], n // 2, replace=False)
    neg = rng.choice(np.where(y == 0)[0], n - n // 2, replace=False)
    idx = rng.permutation(np.concatenate([pos, neg]))
    prefix = {"heart": "H", "diabetes": "D", "liver": "L"}[disease]
    return readable(disease, X.iloc[idx], [f"{prefix}-{i + 1:03d}" for i in range(n)], y.iloc[idx])


def to_bytes(df: pd.DataFrame, fmt: str) -> bytes:
    if fmt == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xl:
            df.to_excel(xl, index=False, sheet_name="Patients")
            ws = xl.sheets["Patients"]
            for i, col in enumerate(df.columns):
                width = max(len(str(col)), *(len(str(v)) for v in df[col].head(50))) + 2
                ws.column_dimensions[ws.cell(1, i + 1).column_letter].width = min(width, 34)
            ws.freeze_panes = "B2"
        return buf.getvalue()
    return df.to_csv(index=False).encode("utf-8-sig")  # BOM so Excel shows µ, ² correctly


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    for d in DISEASES:
        for fmt in ("csv", "xlsx"):
            (OUT_DIR / f"{d}_patients.{fmt}").write_bytes(to_bytes(sample(d), fmt))
            (OUT_DIR / f"{d}_template.{fmt}").write_bytes(to_bytes(template(d), fmt))
    print("Wrote sample files to", OUT_DIR)
