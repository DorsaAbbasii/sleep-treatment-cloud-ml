import json
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field


# --------------------------------------------------
# Project paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_FILE = BASE_DIR / "model" / "treatment_effect_model.joblib"
METADATA_FILE = BASE_DIR / "model" / "model_metadata.json"


# --------------------------------------------------
# Load model and metadata
# --------------------------------------------------

model = joblib.load(MODEL_FILE)

with open(METADATA_FILE, "r", encoding="utf-8") as file:
    metadata = json.load(file)


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="Sleep Treatment Effect API",
    description=(
        "Exploratory API for predicting the estimated "
        "effect of Temazepam on Sleep Efficiency."
    ),
    version="1.0.0",
)


# --------------------------------------------------
# Input schema
# --------------------------------------------------

class PatientInput(BaseModel):
    age: int = Field(
        ...,
        ge=18,
        le=100,
        description="Patient age",
    )

    sex: Literal["Male", "Female"]


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Sleep Treatment Effect API is running",
        "model": metadata["model_type"],
        "treatment": metadata["treatment"],
        "control": metadata["control"],
    }


# --------------------------------------------------
# Health endpoint
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# --------------------------------------------------
# Model information endpoint
# --------------------------------------------------

@app.get("/model-info")
def model_info():
    return metadata


# --------------------------------------------------
# Prediction endpoint
# --------------------------------------------------

@app.post("/predict")
def predict(data: PatientInput):

    sex_encoded = 1 if data.sex == "Male" else 0

    input_data = pd.DataFrame(
        [
            {
                "age": data.age,
                "sex": sex_encoded,
            }
        ]
    )

    prediction = model.predict(input_data)[0]

    return {
        "age": data.age,
        "sex": data.sex,
        "treatment": "Temazepam",
        "control": "Placebo",
        "predicted_treatment_effect":
            round(float(prediction), 3),

        "unit":
            "Sleep Efficiency percentage points",

        "interpretation": (
            "Positive values indicate higher predicted "
            "Sleep Efficiency with Temazepam compared "
            "with Placebo. Negative values indicate "
            "lower predicted Sleep Efficiency."
        ),

        "warning": (
            "Exploratory proof-of-concept only. "
            "The model was trained on 22 subjects "
            "and is not intended for clinical decisions."
        ),
    }