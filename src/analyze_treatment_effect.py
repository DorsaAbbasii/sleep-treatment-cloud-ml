import pandas as pd

INPUT_FILE = "sleep_features.csv"
OUTPUT_FILE = "paired_treatment_effects.csv"

df = pd.read_csv(INPUT_FILE)

outcomes = [
    "sleep_efficiency_percent",
    "total_sleep_time_min",
    "sleep_onset_latency_min",
    "waso_min",
    "n1_min",
    "n2_min",
    "n3_min",
    "rem_min",
]

# Separate placebo and treatment nights
placebo = (
    df[df["condition"] == "Placebo"]
    .set_index("subject")
)

temazepam = (
    df[df["condition"] == "Temazepam"]
    .set_index("subject")
)

records = []

for subject in sorted(df["subject"].unique()):

    p = placebo.loc[subject]
    t = temazepam.loc[subject]

    record = {
        "subject": subject,
        "age": p["age"],
        "sex": p["sex"],
    }

    for outcome in outcomes:
        placebo_value = p[outcome]
        temazepam_value = t[outcome]

        effect = temazepam_value - placebo_value

        record[f"placebo_{outcome}"] = placebo_value
        record[f"temazepam_{outcome}"] = temazepam_value
        record[f"effect_{outcome}"] = effect

    records.append(record)

effects = pd.DataFrame(records)

effects.to_csv(
    OUTPUT_FILE,
    index=False,
)

print("\nCreated:", OUTPUT_FILE)
print("Number of subjects:", len(effects))

print("\nMean treatment effects:")

for outcome in outcomes:
    column = f"effect_{outcome}"

    mean_effect = effects[column].mean()
    median_effect = effects[column].median()

    print(
        f"{outcome}: "
        f"mean={mean_effect:.2f}, "
        f"median={median_effect:.2f}"
    )

print("\nSleep Efficiency effect by subject:")

print(
    effects[
        [
            "subject",
            "age",
            "sex",
            "placebo_sleep_efficiency_percent",
            "temazepam_sleep_efficiency_percent",
            "effect_sleep_efficiency_percent",
        ]
    ].to_string(index=False)
)