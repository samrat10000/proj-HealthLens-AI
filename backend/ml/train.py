"""Train, compare and export a classifier for every disease.

PyCaret-style workflow implemented with scikit-learn:
  clean -> stratified train/test split -> compare_models (5-fold CV)
  -> soft-voting blend of the top 3 -> pick best by ROC-AUC
  -> evaluate on hold-out -> refit on all data -> export pipeline + metadata

Run:  python -m ml.train            (from the backend/ folder)
"""
import json
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (ExtraTreesClassifier, GradientBoostingClassifier,
                              RandomForestClassifier, VotingClassifier)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.svm import SVC

from .cleaning import LOADERS
from .specs import DISEASES

warnings.filterwarnings("ignore")
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
SEED = 42
SCORING = ["accuracy", "roc_auc", "f1", "precision", "recall"]


def build_preprocessor(disease: str) -> ColumnTransformer:
    feats = DISEASES[disease]["features"]
    plain = [f["key"] for f in feats if f["kind"] == "numeric" and not f.get("log")]
    logged = [f["key"] for f in feats if f["kind"] == "numeric" and f.get("log")]
    cats = [f["key"] for f in feats if f["kind"] == "categorical"]
    blocks = []
    if plain:
        blocks.append(("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                                        ("scale", StandardScaler())]), plain))
    if logged:
        blocks.append(("log", Pipeline([("impute", SimpleImputer(strategy="median")),
                                        ("log1p", FunctionTransformer(np.log1p)),
                                        ("scale", StandardScaler())]), logged))
    if cats:
        blocks.append(("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                                        ("onehot", OneHotEncoder(handle_unknown="ignore"))]), cats))
    return ColumnTransformer(blocks)


def candidate_models() -> dict:
    return {
        "Logistic Regression": LogisticRegression(max_iter=3000, C=0.5),
        "Random Forest": RandomForestClassifier(n_estimators=400, min_samples_leaf=3, random_state=SEED, n_jobs=-1),
        "Extra Trees": ExtraTreesClassifier(n_estimators=400, min_samples_leaf=3, random_state=SEED, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=3,
                                                        subsample=0.8, random_state=SEED),
        "SVM (RBF)": SVC(C=1.0, probability=True, random_state=SEED),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=15, weights="distance"),
        "Naive Bayes": GaussianNB(),
    }


def make_pipeline(disease: str, clf) -> Pipeline:
    return Pipeline([("prep", build_preprocessor(disease)), ("model", clf)])


def cv_scores(pipe, X, y, cv) -> dict:
    t0 = time.perf_counter()
    res = cross_validate(pipe, X, y, cv=cv, scoring=SCORING, n_jobs=-1)
    out = {m: round(float(res[f"test_{m}"].mean()), 4) for m in SCORING}
    out["roc_auc_std"] = round(float(res["test_roc_auc"].std()), 4)
    out["train_time_s"] = round(time.perf_counter() - t0, 2)
    return out


def healthy_baseline(disease: str, X: pd.DataFrame, y: pd.Series) -> dict:
    """Reference 'healthy' patient: median / mode of the negative class. Used for explanations."""
    neg = X[y == 0]
    base = {}
    for f in DISEASES[disease]["features"]:
        col = neg[f["key"]].dropna()
        if f["kind"] == "categorical" or f["input"] == "select":
            base[f["key"]] = float(col.mode().iloc[0])
        else:
            base[f["key"]] = round(float(col.median()), 3)
    return base


def pick_samples(model, X_test, y_test) -> list[dict]:
    """Choose real, complete hold-out patients the model is confident about as demo profiles."""
    complete = X_test.dropna()
    proba = model.predict_proba(complete)[:, 1]
    yt = y_test.loc[complete.index].values
    samples = []
    for label, target, picker in [("Healthy profile", 0, np.argmin), ("High-risk profile", 1, np.argmax)]:
        idx = np.where(yt == target)[0]
        if len(idx) == 0:
            continue
        # pick a fairly typical (not extreme) confident case: ~10th / 90th percentile
        order = idx[np.argsort(proba[idx])]
        pos = int(len(order) * (0.15 if target == 0 else 0.85))
        row = complete.iloc[order[min(pos, len(order) - 1)]]
        samples.append({"label": label, "values": {k: (None if pd.isna(v) else float(v)) for k, v in row.items()}})
    # borderline case for the demo
    mid = int(np.argmin(np.abs(proba - 0.5)))
    samples.insert(1, {"label": "Borderline profile",
                       "values": {k: float(v) for k, v in complete.iloc[mid].items()}})
    return samples


def train_disease(disease: str) -> dict:
    spec = DISEASES[disease]
    print(f"\n=== {spec['name']} ===")
    X, y, report = LOADERS[disease]()
    report["steps"].append({"action": "Imputation + scaling (in pipeline)",
                            "detail": "Median / most-frequent imputation, standard scaling and one-hot encoding "
                                      "fitted inside each CV fold to prevent data leakage", "affected": 0})
    print(f"rows {report['rows_raw']} -> {report['rows_clean']}, positive rate {report['positive_rate']:.1%}")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    leaderboard = []
    for name, clf in candidate_models().items():
        scores = cv_scores(make_pipeline(disease, clf), X_tr, y_tr, cv)
        leaderboard.append({"model": name, **scores})
        print(f"  {name:<22} AUC {scores['roc_auc']:.3f}  ACC {scores['accuracy']:.3f}  F1 {scores['f1']:.3f}")

    leaderboard.sort(key=lambda r: r["roc_auc"], reverse=True)
    top3 = [r["model"] for r in leaderboard[:3]]
    models = candidate_models()
    blend = VotingClassifier([(n, models[n]) for n in top3], voting="soft")
    blend_name = "Soft-Voting Ensemble"
    scores = cv_scores(make_pipeline(disease, blend), X_tr, y_tr, cv)
    leaderboard.append({"model": blend_name, "members": top3, **scores})
    print(f"  {blend_name:<22} AUC {scores['roc_auc']:.3f}  ACC {scores['accuracy']:.3f}  ({' + '.join(top3)})")
    leaderboard.sort(key=lambda r: r["roc_auc"], reverse=True)

    best_name = leaderboard[0]["model"]
    best_clf = blend if best_name == blend_name else candidate_models()[best_name]
    print(f"  -> selected: {best_name}")

    # ---- hold-out evaluation ----
    pipe = make_pipeline(disease, best_clf).fit(X_tr, y_tr)
    proba = pipe.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    fpr, tpr, _ = roc_curve(y_te, proba)
    keep = np.unique(np.linspace(0, len(fpr) - 1, min(60, len(fpr))).astype(int))
    holdout = {
        "accuracy": round(accuracy_score(y_te, pred), 4),
        "roc_auc": round(roc_auc_score(y_te, proba), 4),
        "f1": round(f1_score(y_te, pred), 4),
        "precision": round(precision_score(y_te, pred), 4),
        "recall": round(recall_score(y_te, pred), 4),
        "confusion_matrix": confusion_matrix(y_te, pred).tolist(),
        "roc_curve": [{"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)} for i in keep],
        "n_test": int(len(y_te)),
    }
    print(f"  hold-out AUC {holdout['roc_auc']:.3f}  ACC {holdout['accuracy']:.3f}")

    imp = permutation_importance(pipe, X_te, y_te, scoring="roc_auc", n_repeats=15, random_state=SEED, n_jobs=-1)
    labels = {f["key"]: f["label"] for f in spec["features"]}
    importance = sorted(
        [{"feature": k, "label": labels[k], "importance": round(float(m), 4)}
         for k, m in zip(X.columns, imp.importances_mean)],
        key=lambda r: r["importance"], reverse=True)

    samples = pick_samples(pipe, X_te, y_te)

    # ---- final model on all data ----
    final = make_pipeline(disease, best_clf).fit(X, y)
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(final, MODELS_DIR / f"{disease}.joblib")

    meta = {
        "disease": disease,
        "best_model": best_name,
        "best_members": leaderboard[0].get("members"),
        "trained_at": time.strftime("%Y-%m-%d %H:%M"),
        "cv_folds": 5,
        "leaderboard": leaderboard,
        "holdout": holdout,
        "feature_importance": importance,
        "cleaning": report,
        "baseline": healthy_baseline(disease, X, y),
        "samples": samples,
    }
    (MODELS_DIR / f"{disease}_meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def main():
    summary = {}
    for disease in DISEASES:
        m = train_disease(disease)
        summary[disease] = {"model": m["best_model"], "auc": m["holdout"]["roc_auc"], "acc": m["holdout"]["accuracy"]}
    print("\nSummary:", json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
