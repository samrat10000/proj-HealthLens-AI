"""Single source of truth for every disease model: metadata + input feature schema.

The same spec drives (1) the preprocessing pipeline during training, (2) request
validation in the API and (3) the dynamic input form rendered by the React UI.

Feature fields:
  key        column name used everywhere
  label      human readable name
  input      "number" | "select"      (how the UI renders it)
  kind       "numeric" | "categorical" (how the model preprocesses it)
  log        apply log1p before scaling (heavily skewed lab values)
  optional   may be left blank -> imputed by the pipeline
  normal     [low, high] clinical reference range used for flagging (None = no bound)
  zero_missing  a 0 in an uploaded file means "not measured" (as in the source datasets)
"""

YES_NO = [{"value": 1, "label": "Yes"}, {"value": 0, "label": "No"}]

DISEASES = {
    "heart": {
        "name": "Heart Disease",
        "tagline": "Coronary artery disease risk from cardiac test results",
        "dataset": "Heart Disease UCI (Cleveland, Hungary, Switzerland, VA Long Beach)",
        "positive_label": "Heart disease present",
        "negative_label": "No heart disease",
        "features": [
            {"key": "age", "label": "Age", "input": "number", "kind": "numeric", "unit": "years",
             "min": 18, "max": 100, "step": 1, "default": 54, "group": "Profile"},
            {"key": "sex", "label": "Sex", "input": "select", "kind": "categorical", "default": 1, "group": "Profile",
             "options": [{"value": 1, "label": "Male"}, {"value": 0, "label": "Female"}]},
            {"key": "cp", "label": "Chest pain type", "input": "select", "kind": "categorical", "default": 3,
             "group": "Symptoms",
             "options": [{"value": 1, "label": "Typical angina"}, {"value": 2, "label": "Atypical angina"},
                         {"value": 3, "label": "Non-anginal pain"}, {"value": 4, "label": "Asymptomatic"}],
             "help": "Type of chest pain experienced. Asymptomatic presentation is surprisingly high-risk."},
            {"key": "exang", "label": "Exercise-induced angina", "input": "select", "kind": "categorical",
             "default": 0, "options": YES_NO, "group": "Symptoms"},
            {"key": "trestbps", "zero_missing": True, "label": "Resting blood pressure", "input": "number", "kind": "numeric",
             "unit": "mmHg", "min": 80, "max": 220, "step": 1, "default": 130, "normal": [90, 120], "group": "Vitals"},
            {"key": "chol", "zero_missing": True, "label": "Serum cholesterol", "input": "number", "kind": "numeric", "unit": "mg/dL",
             "min": 100, "max": 600, "step": 1, "default": 230, "normal": [None, 200], "group": "Vitals",
             "optional": True},
            {"key": "fbs", "label": "Fasting blood sugar > 120 mg/dL", "input": "select", "kind": "categorical",
             "default": 0, "options": YES_NO, "group": "Vitals", "optional": True},
            {"key": "thalach", "label": "Max heart rate achieved", "input": "number", "kind": "numeric",
             "unit": "bpm", "min": 60, "max": 220, "step": 1, "default": 150, "group": "Stress test",
             "help": "Peak heart rate during the exercise stress test."},
            {"key": "oldpeak", "label": "ST depression (oldpeak)", "input": "number", "kind": "numeric",
             "unit": "mm", "min": -3, "max": 7, "step": 0.1, "default": 1.0, "normal": [None, 1.0],
             "group": "Stress test", "help": "ST depression induced by exercise relative to rest."},
            {"key": "slope", "label": "ST segment slope", "input": "select", "kind": "categorical", "default": 2,
             "group": "Stress test", "optional": True,
             "options": [{"value": 1, "label": "Upsloping"}, {"value": 2, "label": "Flat"},
                         {"value": 3, "label": "Downsloping"}]},
            {"key": "restecg", "label": "Resting ECG", "input": "select", "kind": "categorical", "default": 0,
             "group": "Stress test", "optional": True,
             "options": [{"value": 0, "label": "Normal"}, {"value": 1, "label": "ST-T wave abnormality"},
                         {"value": 2, "label": "Left ventricular hypertrophy"}]},
            {"key": "ca", "label": "Major vessels (fluoroscopy)", "input": "select", "kind": "numeric",
             "default": 0, "group": "Imaging", "optional": True,
             "options": [{"value": v, "label": str(v)} for v in range(4)],
             "help": "Number of major vessels (0-3) colored by fluoroscopy."},
            {"key": "thal", "label": "Thalassemia (thallium scan)", "input": "select", "kind": "categorical",
             "default": 3, "group": "Imaging", "optional": True,
             "options": [{"value": 3, "label": "Normal"}, {"value": 6, "label": "Fixed defect"},
                         {"value": 7, "label": "Reversible defect"}]},
        ],
        "advice": {
            "low": "Cardiac markers look reassuring. Keep up regular activity, a balanced diet and routine check-ups.",
            "moderate": "Some cardiac risk factors are present. Discuss a lipid panel, ECG and lifestyle changes with a physician.",
            "high": "Pattern strongly resembles patients with diagnosed heart disease. Seek a cardiology evaluation promptly.",
        },
    },
    "diabetes": {
        "name": "Diabetes",
        "tagline": "Type 2 diabetes onset risk from metabolic indicators",
        "dataset": "Pima Indians Diabetes Database (NIDDK)",
        "positive_label": "Diabetic",
        "negative_label": "Non-diabetic",
        "features": [
            {"key": "age", "label": "Age", "input": "number", "kind": "numeric", "unit": "years",
             "min": 21, "max": 90, "step": 1, "default": 33, "group": "Profile"},
            {"key": "pregnancies", "label": "Pregnancies", "input": "number", "kind": "numeric", "unit": "count",
             "min": 0, "max": 17, "step": 1, "default": 2, "group": "Profile",
             "help": "Number of times pregnant (enter 0 if not applicable)."},
            {"key": "pedigree", "label": "Diabetes pedigree function", "input": "number", "kind": "numeric",
             "unit": "score", "min": 0.05, "max": 2.5, "step": 0.01, "default": 0.37, "group": "Profile",
             "help": "Genetic predisposition score based on family history (0.08 - 2.42 in the study)."},
            {"key": "glucose", "zero_missing": True, "label": "Plasma glucose (2h OGTT)", "input": "number", "kind": "numeric",
             "unit": "mg/dL", "min": 40, "max": 250, "step": 1, "default": 117, "normal": [70, 140],
             "group": "Labs"},
            {"key": "insulin", "zero_missing": True, "label": "2-hour serum insulin", "input": "number", "kind": "numeric",
             "unit": "µU/mL", "min": 10, "max": 900, "step": 1, "default": 125, "normal": [16, 166],
             "group": "Labs", "optional": True, "log": True},
            {"key": "bmi", "zero_missing": True, "label": "Body mass index", "input": "number", "kind": "numeric", "unit": "kg/m²",
             "min": 15, "max": 70, "step": 0.1, "default": 32, "normal": [18.5, 24.9], "group": "Body"},
            {"key": "blood_pressure", "zero_missing": True, "label": "Diastolic blood pressure", "input": "number", "kind": "numeric",
             "unit": "mmHg", "min": 30, "max": 130, "step": 1, "default": 72, "normal": [60, 80], "group": "Body"},
            {"key": "skin_thickness", "zero_missing": True, "label": "Triceps skinfold thickness", "input": "number", "kind": "numeric",
             "unit": "mm", "min": 5, "max": 100, "step": 1, "default": 29, "group": "Body", "optional": True},
        ],
        "advice": {
            "low": "Metabolic profile looks healthy. Maintain a healthy weight and get glucose screened every few years.",
            "moderate": "Elevated diabetes risk. Ask about an HbA1c test and consider diet and activity changes.",
            "high": "Profile closely matches diagnosed diabetic patients. Request HbA1c / fasting glucose testing soon.",
        },
    },
    "liver": {
        "name": "Liver Disorder",
        "tagline": "Liver disease likelihood from a liver function panel",
        "dataset": "Indian Liver Patient Dataset (ILPD, UCI)",
        "positive_label": "Liver disease",
        "negative_label": "No liver disease",
        "features": [
            {"key": "age", "label": "Age", "input": "number", "kind": "numeric", "unit": "years",
             "min": 4, "max": 90, "step": 1, "default": 45, "group": "Profile"},
            {"key": "gender", "label": "Sex", "input": "select", "kind": "categorical", "default": 1,
             "group": "Profile", "options": [{"value": 1, "label": "Male"}, {"value": 0, "label": "Female"}]},
            {"key": "total_bilirubin", "label": "Total bilirubin", "input": "number", "kind": "numeric",
             "unit": "mg/dL", "min": 0.1, "max": 75, "step": 0.1, "default": 0.9, "normal": [0.1, 1.2],
             "group": "Bilirubin", "log": True},
            {"key": "direct_bilirubin", "label": "Direct bilirubin", "input": "number", "kind": "numeric",
             "unit": "mg/dL", "min": 0.1, "max": 20, "step": 0.1, "default": 0.2, "normal": [None, 0.3],
             "group": "Bilirubin", "log": True},
            {"key": "alk_phos", "label": "Alkaline phosphatase", "input": "number", "kind": "numeric",
             "unit": "IU/L", "min": 60, "max": 2200, "step": 1, "default": 190, "group": "Enzymes", "log": True},
            {"key": "alt", "label": "ALT (SGPT)", "input": "number", "kind": "numeric", "unit": "IU/L",
             "min": 5, "max": 2000, "step": 1, "default": 28, "normal": [7, 56], "group": "Enzymes", "log": True},
            {"key": "ast", "label": "AST (SGOT)", "input": "number", "kind": "numeric", "unit": "IU/L",
             "min": 5, "max": 5000, "step": 1, "default": 30, "normal": [10, 40], "group": "Enzymes", "log": True},
            {"key": "total_protein", "label": "Total protein", "input": "number", "kind": "numeric",
             "unit": "g/dL", "min": 2.5, "max": 10, "step": 0.1, "default": 6.6, "normal": [6.0, 8.3],
             "group": "Proteins"},
            {"key": "albumin", "label": "Albumin", "input": "number", "kind": "numeric", "unit": "g/dL",
             "min": 0.9, "max": 5.5, "step": 0.1, "default": 3.4, "normal": [3.5, 5.0], "group": "Proteins"},
            {"key": "ag_ratio", "label": "Albumin/Globulin ratio", "input": "number", "kind": "numeric",
             "unit": "ratio", "min": 0.3, "max": 2.8, "step": 0.01, "default": 1.0, "normal": [1.1, 2.5],
             "group": "Proteins", "optional": True},
        ],
        "advice": {
            "low": "Liver panel looks unremarkable. Limit alcohol and keep a healthy weight to keep it that way.",
            "moderate": "Some liver markers are off. A repeat liver function test and physician review is advisable.",
            "high": "Panel resembles patients with liver disease. Consult a hepatologist / gastroenterologist.",
        },
    },
}

RISK_BANDS = [(0.30, "low"), (0.60, "moderate"), (1.01, "high")]


def risk_level(p: float) -> str:
    for cutoff, name in RISK_BANDS:
        if p < cutoff:
            return name
    return "high"


def feature_keys(disease: str) -> list[str]:
    return [f["key"] for f in DISEASES[disease]["features"]]
