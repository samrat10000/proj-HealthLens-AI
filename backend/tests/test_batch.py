"""File-upload (batch screening) tests.  Run from backend/:  python -m pytest -q"""
import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from ml import samples


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _upload(client, name: str, content: bytes, disease: str | None = None):
    data = {"disease": disease} if disease else {}
    return client.post("/api/batch", files={"file": (name, content)}, data=data)


@pytest.mark.parametrize("disease", ["heart", "diabetes", "liver"])
@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_sample_files_round_trip(client, disease, fmt):
    file = client.get(f"/api/sample/{disease}?format={fmt}")
    assert file.status_code == 200
    r = _upload(client, f"patients.{fmt}", file.content)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["disease"] == disease and body["auto_detected"]
    assert body["summary"]["scored"] == body["summary"]["total"] == 40
    assert body["summary"]["labelled"] == 40 and body["summary"]["agreement"] > 0.6
    assert body["columns"]["id_column"] == "Patient ID"


def test_template_downloads(client):
    r = client.get("/api/template/liver?format=csv")
    assert r.status_code == 200 and "Total bilirubin" in r.content.decode("utf-8-sig")


def test_kaggle_column_names_and_codes(client):
    # fedesoriano / Kaggle "Heart Failure Prediction" style: text codes, different headers
    csv = (
        "Age,Sex,ChestPainType,RestingBP,Cholesterol,FastingBS,RestingECG,MaxHR,ExerciseAngina,Oldpeak,ST_Slope,HeartDisease\n"
        "40,M,ATA,140,289,0,Normal,172,N,0,Up,0\n"
        "65,M,ASY,150,300,1,LVH,105,Y,2.5,Flat,1\n"
    )
    body = _upload(client, "heart.csv", csv.encode()).json()
    assert body["disease"] == "heart" and body["summary"]["scored"] == 2
    lo, hi = body["rows"]
    assert lo["probability"] < hi["probability"]
    assert body["columns"]["target_column"] == "HeartDisease"

    # Original Kaggle Pima column names, semicolon separated
    pima = ("Pregnancies;Glucose;BloodPressure;SkinThickness;Insulin;BMI;DiabetesPedigreeFunction;Age;Outcome\n"
            "6;148;72;35;0;33.6;0.627;50;1\n1;85;66;29;0;26.6;0.351;31;0\n")
    body = _upload(client, "diabetes.csv", pima.encode()).json()
    assert body["disease"] == "diabetes" and body["summary"]["scored"] == 2


def test_bad_rows_reported_not_fatal(client):
    df = samples.sample("diabetes").head(3).astype(object)
    df.iloc[0, df.columns.get_loc("Plasma glucose (2h OGTT) (mg/dL)")] = 999
    df.iloc[1, df.columns.get_loc("Body mass index (kg/m²)")] = "abc"
    body = _upload(client, "d.csv", df.to_csv(index=False).encode()).json()
    assert body["summary"]["errors"] == 2 and body["summary"]["scored"] == 1
    assert "outside" in body["rows"][0]["errors"][0]
    assert "not a number" in body["rows"][1]["errors"][0]


def test_unrecognised_file(client):
    r = _upload(client, "x.csv", b"foo,bar\n1,2\n")
    assert r.status_code == 422
