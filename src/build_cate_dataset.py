import pandas as pd

INPUT_FILE = "sleep_features.csv"
OUTPUT_FILE = "cate_dataset.csv"

df = pd.read_csv(INPUT_FILE)

# Separate the two conditions
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

    # Observed paired treatment effect
    effect_sleep_efficiency = (
        t["sleep_efficiency_percent"]
        - p["sleep_efficiency_percent"]
    )

    record = {
        "subject": subject,
        "age": p["age"],

        # Encode sex numerically
        "sex": 1 if p["sex"] == "Male" else 0,

        # Baseline / placebo sleep characteristics
        "baseline_sleep_efficiency":
            p["sleep_efficiency_percent"],

        "baseline_total_sleep_time":
            p["total_sleep_time_min"],

        "baseline_sleep_onset_latency":
            p["sleep_onset_latency_min"],

        "baseline_waso":
            p["waso_min"],

        "baseline_n1":
            p["n1_min"],

        "baseline_n2":
            p["n2_min"],

        "baseline_n3":
            p["n3_min"],

        "baseline_rem":
            p["rem_min"],

        # Target
        "treatment_effect_sleep_efficiency":
            effect_sleep_efficiency,
    }

    records.append(record)

cate_df = pd.DataFrame(records)

cate_df.to_csv(
    OUTPUT_FILE,
    index=False,
)

print("\nCreated:", OUTPUT_FILE)
print("Number of subjects:", len(cate_df))

print("\nColumns:")
for column in cate_df.columns:
    print("-", column)

print("\nFirst 10 rows:")
print(cate_df.head(10).to_string(index=False))

print("\nTreatment effect statistics:")
print(
    cate_df["treatment_effect_sleep_efficiency"]
    .describe()
    .round(2)
)