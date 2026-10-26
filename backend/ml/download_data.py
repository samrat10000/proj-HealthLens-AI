"""Download the raw datasets used to train the diagnostic models.

Sources (same data as the Kaggle mirrors):
  - Heart Disease UCI  -> UCI ML Repository, all 4 clinics (Cleveland, Hungary, Switzerland, VA Long Beach)
  - Pima Indians Diabetes -> UCI / Kaggle "Diabetes Dataset"
  - Indian Liver Patient Dataset (ILPD) -> UCI / Kaggle "Indian Liver Patient Records"
"""
from pathlib import Path
import urllib.request

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

UCI = "https://archive.ics.uci.edu/ml/machine-learning-databases"
SOURCES = {
    "heart_cleveland.data": f"{UCI}/heart-disease/processed.cleveland.data",
    "heart_hungarian.data": f"{UCI}/heart-disease/processed.hungarian.data",
    "heart_switzerland.data": f"{UCI}/heart-disease/processed.switzerland.data",
    "heart_va.data": f"{UCI}/heart-disease/processed.va.data",
    "diabetes.csv": "https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.data.csv",
    "liver.csv": f"{UCI}/00225/Indian%20Liver%20Patient%20Dataset%20(ILPD).csv",
}


def download(force: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        target = RAW_DIR / name
        if target.exists() and not force:
            print(f"[skip] {name} already present")
            continue
        print(f"[get ] {name} <- {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            target.write_bytes(resp.read())
    print("All datasets ready in", RAW_DIR)


if __name__ == "__main__":
    download()
