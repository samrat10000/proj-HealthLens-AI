"""Parse an uploaded CSV / Excel file of patients into model-ready rows.

Tolerant by design: column names are matched by feature key, by the UI label,
or by common aliases (including the original Kaggle column names), and category
values may be codes or words ("Male", "M", "1"; "asymptomatic", "ASY", "4").
Rows that can't be used are reported individually instead of failing the upload.
"""
import io
import re

import numpy as np
import pandas as pd

from ml.specs import DISEASES

MAX_ROWS = 5000


def norm(s) -> str:
    s = re.sub(r"\(.*?\)|\[.*?\]", "", str(s).lower())
    return re.sub(r"[^a-z0-9]", "", s)


# ---------------------------------------------------------------- aliases

COLUMN_ALIASES = {
    "heart": {
        "cp": ["chestpaintype", "chestpain"],
        "trestbps": ["restingbp", "restingbloodpressure"],
        "chol": ["cholesterol", "serumcholesterol"],
        "fbs": ["fastingbs", "fastingbloodsugar"],
        "restecg": ["restingecg", "ecg"],
        "thalach": ["thalch", "maxhr", "maxheartrate"],
        "exang": ["exerciseangina", "exerciseinducedangina"],
        "oldpeak": ["stdepression"],
        "slope": ["stslope"],
        "ca": ["vessels", "majorvessels", "numvessels"],
        "thal": ["thalassemia", "thallium"],
    },
    "diabetes": {
        "blood_pressure": ["bloodpressure", "diastolicbp", "diastolicbloodpressure", "bp"],
        "skin_thickness": ["skinthickness", "tricepsskinfold"],
        "pedigree": ["diabetespedigreefunction", "pedigreefunction", "dpf"],
        "glucose": ["plasmaglucose"],
        "insulin": ["seruminsulin"],
        "bmi": ["bodymassindex"],
    },
    "liver": {
        "gender": ["sex"],
        "total_bilirubin": ["totalbilirubin", "tb"],
        "direct_bilirubin": ["directbilirubin", "db"],
        "alk_phos": ["alkalinephosphotase", "alkalinephosphatase", "alkphos", "alp"],
        "alt": ["alamineaminotransferase", "alanineaminotransferase", "sgpt"],
        "ast": ["aspartateaminotransferase", "sgot"],
        "total_protein": ["totalprotiens", "totalproteins", "tp"],
        "albumin": ["alb"],
        "ag_ratio": ["albuminandglobulinratio", "albuminglobulinratio", "agratio", "ag"],
    },
}

YES = ["yes", "y", "true", "t", "positive", "present"]
NO = ["no", "n", "false", "f", "negative", "absent"]
SEX = {1: ["male", "m", "man"], 0: ["female", "f", "woman"]}

VALUE_ALIASES = {
    ("heart", "sex"): SEX,
    ("liver", "gender"): SEX,
    ("heart", "fbs"): {1: YES, 0: NO},
    ("heart", "exang"): {1: YES, 0: NO},
    ("heart", "cp"): {1: ["typical", "ta"], 2: ["atypical", "ata"], 3: ["nonanginal", "nap"],
                      4: ["asymptomatic", "asy"]},
    ("heart", "restecg"): {0: ["normal"], 1: ["st", "stt", "sttabnormality", "stabnormality"],
                           2: ["lvh", "lvhypertrophy", "hypertrophy"]},
    ("heart", "slope"): {1: ["up", "upsloping"], 2: ["flat"], 3: ["down", "downsloping"]},
    ("heart", "thal"): {3: ["normal"], 6: ["fixed", "fixeddefect"],
                        7: ["reversible", "reversable", "reversabledefect", "reversibledefect"]},
}

ID_COLUMNS = {"id", "patientid", "patient", "patientname", "name", "mrn", "patientno", "no"}
TARGET_COLUMNS = {
    "heart": {"target", "num", "heartdisease", "diagnosis", "actualdiagnosis", "actual", "outcome", "label"},
    "diabetes": {"outcome", "target", "diabetes", "diagnosis", "actualdiagnosis", "actual", "label", "class"},
    "liver": {"dataset", "selector", "target", "liverdisease", "diagnosis", "actualdiagnosis", "actual", "label"},
}
MISSING = {"", "na", "nan", "null", "none", "?", "-", "unknown", "notmeasured", "nr"}


def _column_lookup(disease: str) -> dict:
    lookup = {}
    for f in DISEASES[disease]["features"]:
        for name in [f["key"], f["label"], *COLUMN_ALIASES[disease].get(f["key"], [])]:
            lookup.setdefault(norm(name), f["key"])
    return lookup


def _option_lookup(disease: str, f: dict) -> dict:
    lookup = {norm(o["label"]): o["value"] for o in f["options"]}
    for value, names in VALUE_ALIASES.get((disease, f["key"]), {}).items():
        for n in names:
            lookup[norm(n)] = value
    return lookup


# ---------------------------------------------------------------- reading

def read_table(filename: str, content: bytes) -> pd.DataFrame:
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        df = pd.read_excel(io.BytesIO(content))
    else:
        text = None
        for enc in ("utf-8-sig", "latin-1"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str, skip_blank_lines=True)
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    if df.empty:
        raise ValueError("The file has no patient rows.")
    if len(df) > MAX_ROWS:
        raise ValueError(f"File has {len(df)} rows; the limit is {MAX_ROWS}.")
    return df


def detect_disease(columns: list[str]) -> tuple[str, dict]:
    scores = {}
    for d in DISEASES:
        lookup = _column_lookup(d)
        hits = {lookup[norm(c)] for c in columns if norm(c) in lookup}
        required = [f["key"] for f in DISEASES[d]["features"] if not f.get("optional")]
        scores[d] = sum(k in hits for k in required) / len(required)
    best = max(scores, key=scores.get)
    if scores[best] < 0.5:
        raise ValueError("Couldn't recognise the columns. Download a template to see the expected format.")
    return best, scores


# ---------------------------------------------------------------- parsing

def _parse_value(disease: str, f: dict, raw, options: dict | None):
    if raw is None or (isinstance(raw, float) and np.isnan(raw)) or norm(raw) in MISSING:
        return None, None
    try:
        v = float(raw) if isinstance(raw, (int, float, np.number)) else float(str(raw).strip().replace(",", "."))
    except ValueError:
        v = None
    if f["input"] == "select":
        allowed = {o["value"] for o in f["options"]}
        if v is not None and v in allowed:
            return v, None
        if v is None and norm(raw) in options:
            return float(options[norm(raw)]), None
        choices = "/".join(o["label"] for o in f["options"])
        return None, f"{f['label']}: '{raw}' not recognised (expected {choices})"
    if v is None:
        return None, f"{f['label']}: '{raw}' is not a number"
    if v == 0 and f.get("zero_missing"):  # datasets use 0 as a "not measured" code
        return None, None
    if not (f["min"] <= v <= f["max"]):
        return None, f"{f['label']}: {v:g} is outside {f['min']}–{f['max']}"
    return v, None


def _parse_target(disease: str, col: str, raw) -> int | None:
    if raw is None or (isinstance(raw, float) and np.isnan(raw)) or norm(raw) in MISSING:
        return None
    spec = DISEASES[disease]
    n = norm(raw)
    if n == norm(spec["positive_label"]) or n in YES or n in {"diabetic", "disease", "sick"}:
        return 1
    if n == norm(spec["negative_label"]) or n in NO or n in {"nondiabetic", "healthy", "normal"}:
        return 0
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if disease == "liver" and norm(col) in {"dataset", "selector"}:
        return {1.0: 1, 2.0: 0}.get(v)
    if disease == "heart" and norm(col) == "num":
        return int(v > 0)
    return {1.0: 1, 0.0: 0}.get(v)


def parse(disease: str, df: pd.DataFrame) -> dict:
    spec = DISEASES[disease]
    lookup = _column_lookup(disease)
    mapping, id_col, target_col, ignored = {}, None, None, []
    for c in df.columns:
        n = norm(c)
        if n in lookup and lookup[n] not in mapping.values():
            mapping[c] = lookup[n]
        elif id_col is None and n in ID_COLUMNS:
            id_col = c
        elif target_col is None and n in TARGET_COLUMNS[disease]:
            target_col = c
        else:
            ignored.append(c)
    by_key = {v: k for k, v in mapping.items()}
    missing_cols = [f for f in spec["features"] if f["key"] not in by_key]
    missing_required = [f["label"] for f in missing_cols if not f.get("optional")]
    if missing_required:
        raise ValueError("Missing required column(s): " + ", ".join(missing_required))

    options = {f["key"]: _option_lookup(disease, f) for f in spec["features"] if f["input"] == "select"}
    rows = []
    for i, (_, r) in enumerate(df.iterrows()):
        values, errors = {}, []
        for f in spec["features"]:
            col = by_key.get(f["key"])
            raw = r[col] if col is not None else None
            v, err = _parse_value(disease, f, raw, options.get(f["key"]))
            if err:
                errors.append(err)
            elif v is None and not f.get("optional"):
                errors.append(f"{f['label']} is missing")
            values[f["key"]] = v
        pid = r[id_col] if id_col is not None else None
        rows.append({
            "row": i + 2,  # spreadsheet row number (header is row 1)
            "patient_id": str(pid).strip() if pid is not None and not pd.isna(pid) else f"Row {i + 2}",
            "values": values,
            "actual": _parse_target(disease, target_col, r[target_col]) if target_col else None,
            "errors": errors,
        })
    return {
        "rows": rows,
        "columns": {
            "recognised": [{"column": c, "feature": spec_label(disease, k)} for c, k in mapping.items()],
            "id_column": id_col,
            "target_column": target_col,
            "ignored": ignored,
            "not_provided": [f["label"] for f in missing_cols],
        },
    }


def spec_label(disease: str, key: str) -> str:
    return next(f["label"] for f in DISEASES[disease]["features"] if f["key"] == key)
