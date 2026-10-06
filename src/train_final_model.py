import json
import joblib
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


INPUT_FILE = "cate_dataset.csv"

MODEL_FILE = "treatment_effect_model.joblib"
METADATA_FILE = "model_metadata.json"


df = pd.read_csv(INPUT_FILE)


features = [
    "age",
    "sex",
]

target = "treatment_effect_sleep_efficiency"


X = df[features]
y = df[target]


model = Pipeline(
    [
        (
            "scaler",
            StandardScaler(),
        ),
        (
            "ridge",
            Ridge(
                alpha=10.0,
            ),
        ),
    ]
)


model.fit(X, y)


joblib.dump(
    model,
    MODEL_FILE,
)


metadata = {
    "model_type": "Ridge Regression",
    "purpose": (
        "Exploratory prediction of individual "
        "Temazepam treatment effect on Sleep Efficiency"
    ),
    "features": features,
    "target": target,
    "number_of_subjects": len(df),
    "treatment": "Temazepam",
    "control": "Placebo",
    "mean_observed_treatment_effect": float(
        y.mean()
    ),
    "limitations": [
        "Only 22 subjects",
        "Exploratory proof-of-concept",
        "Age and sex have weak predictive power",
        "Not intended for clinical decision making",
    ],
}


with open(
    METADATA_FILE,
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        metadata,
        file,
        indent=4,
    )


print("\nModel trained successfully.")

print(
    "Saved model:",
    MODEL_FILE,
)

print(
    "Saved metadata:",
    METADATA_FILE,
)

print(
    "\nMean observed treatment effect:",
    round(y.mean(), 2),
)