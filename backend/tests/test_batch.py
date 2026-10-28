"""File-upload (batch screening) tests.  Run from backend/:  python -m pytest -q"""
import pytest

from app import service
from ml import samples


@pytest.mark.parametrize("disease", ["heart", "diabetes", "liver"])
@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_sample_files_round_trip(disease, fmt):
    content = samples.to_bytes(samples.sample(disease), fmt)
    body = service.predict_file(f"patients.{fmt}", content)
    assert body["disease"] == disease and body["auto_detected"]
    assert body["summary"]["scored"] == body["summary"]["total"] == 40
    assert body["summary"]["labelled"] == 40 and body["summary"]["agreement"] > 0.6
    assert body["columns"]["id_column"] == "Patient ID"
    assert len(service.results_table(body)) == 40


def test_template_downloads():
    assert "Total bilirubin" in samples.to_bytes(samples.template("liver"), "csv").decode("utf-8-sig")


def test_kaggle_column_names_and_codes():
    # fedesoriano / Kaggle "Heart Failure Prediction" style: text codes, different headers
    csv = (
        "Age,Sex,ChestPainType,RestingBP,Cholesterol,FastingBS,RestingECG,MaxHR,ExerciseAngina,Oldpeak,ST_Slope,HeartDisease\n"
        "40,M,ATA,140,289,0,Normal,172,N,0,Up,0\n"
        "65,M,ASY,150,300,1,LVH,105,Y,2.5,Flat,1\n"
    )
    body = service.predict_file("heart.csv", csv.encode())
    assert body["disease"] == "heart" and body["summary"]["scored"] == 2
    lo, hi = body["rows"]
    assert lo["probability"] < hi["probability"]
    assert body["columns"]["target_column"] == "HeartDisease"

    # Original Kaggle Pima column names, semicolon separated
    pima = ("Pregnancies;Glucose;BloodPressure;SkinThickness;Insulin;BMI;DiabetesPedigreeFunction;Age;Outcome\n"
            "6;148;72;35;0;33.6;0.627;50;1\n1;85;66;29;0;26.6;0.351;31;0\n")
    body = service.predict_file("diabetes.csv", pima.encode())
    assert body["disease"] == "diabetes" and body["summary"]["scored"] == 2


def test_bad_rows_reported_not_fatal():
    df = samples.sample("diabetes").head(3).astype(object)
    df.iloc[0, df.columns.get_loc("Plasma glucose (2h OGTT) (mg/dL)")] = 999
    df.iloc[1, df.columns.get_loc("Body mass index (kg/m²)")] = "abc"
    body = service.predict_file("d.csv", df.to_csv(index=False).encode())
    assert body["summary"]["errors"] == 2 and body["summary"]["scored"] == 1
    assert "outside" in body["rows"][0]["errors"][0]
    assert "not a number" in body["rows"][1]["errors"][0]


def test_unrecognised_file():
    with pytest.raises(service.InputError):
        service.predict_file("x.csv", b"foo,bar\n1,2\n")
