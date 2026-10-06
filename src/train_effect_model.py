import numpy as np
import pandas as pd

from sklearn.linear_model import RidgeCV
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

INPUT_FILE = "cate_dataset.csv"
OUTPUT_FILE = "effect_model_predictions.csv"

df = pd.read_csv(INPUT_FILE)

# --------------------------------------------------
# Features and target
# --------------------------------------------------

features = [
    "age",
    "sex",
]

target = "treatment_effect_sleep_efficiency"

X = df[features].values
y = df[target].values

# --------------------------------------------------
# Leave-One-Out Cross-Validation
# --------------------------------------------------

loo = LeaveOneOut()

predictions = np.zeros(len(df))
baseline_predictions = np.zeros(len(df))

selected_alphas = []

for train_index, test_index in loo.split(X):

    X_train = X[train_index]
    X_test = X[test_index]

    y_train = y[train_index]

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "ridge",
                RidgeCV(
                    alphas=[
                        0.01,
                        0.1,
                        1.0,
                        10.0,
                        100.0,
                    ],
                    cv=5,
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)

    predictions[test_index[0]] = model.predict(X_test)[0]

    # Baseline:
    # predict the mean treatment effect
    # of the training subjects
    baseline_predictions[test_index[0]] = y_train.mean()

    selected_alphas.append(
        model.named_steps["ridge"].alpha_
    )

# --------------------------------------------------
# Evaluation
# --------------------------------------------------

mae = mean_absolute_error(
    y,
    predictions,
)

rmse = np.sqrt(
    mean_squared_error(
        y,
        predictions,
    )
)

r2 = r2_score(
    y,
    predictions,
)

baseline_mae = mean_absolute_error(
    y,
    baseline_predictions,
)

baseline_rmse = np.sqrt(
    mean_squared_error(
        y,
        baseline_predictions,
    )
)

baseline_r2 = r2_score(
    y,
    baseline_predictions,
)

# --------------------------------------------------
# Save predictions
# --------------------------------------------------

results = df[
    [
        "subject",
        "age",
        "sex",
        target,
    ]
].copy()

results["predicted_treatment_effect"] = predictions

results["prediction_error"] = (
    predictions
    - y
)

results.to_csv(
    OUTPUT_FILE,
    index=False,
)

# --------------------------------------------------
# Output
# --------------------------------------------------

print("\nCreated:", OUTPUT_FILE)

print("\nFeatures:")
for feature in features:
    print("-", feature)

print("\nRidge + LOOCV results:")

print(
    f"MAE  = {mae:.2f}"
)

print(
    f"RMSE = {rmse:.2f}"
)

print(
    f"R2   = {r2:.2f}"
)

print("\nMean-effect baseline:")

print(
    f"MAE  = {baseline_mae:.2f}"
)

print(
    f"RMSE = {baseline_rmse:.2f}"
)

print(
    f"R2   = {baseline_r2:.2f}"
)

print("\nSelected Ridge alphas:")
print(
    pd.Series(selected_alphas)
    .value_counts()
    .sort_index()
)

print("\nObserved vs predicted effects:")

print(
    results[
        [
            "subject",
            "age",
            "sex",
            target,
            "predicted_treatment_effect",
        ]
    ]
    .round(2)
    .to_string(index=False)
)