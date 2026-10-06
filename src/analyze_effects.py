import os

import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import spearmanr, wilcoxon


INPUT_FILE = "sleep_features.csv"
OUTPUT_DIR = "results"

os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(INPUT_FILE)

# --------------------------------------------------
# Separate Placebo and Temazepam
# --------------------------------------------------

placebo = (
    df[df["condition"] == "Placebo"]
    .set_index("subject")
    .sort_index()
)

temazepam = (
    df[df["condition"] == "Temazepam"]
    .set_index("subject")
    .sort_index()
)

# --------------------------------------------------
# Create paired table
# --------------------------------------------------

paired = pd.DataFrame(
    {
        "subject": placebo.index,
        "age": placebo["age"],
        "sex": placebo["sex"],

        "placebo_sleep_efficiency":
            placebo["sleep_efficiency_percent"],

        "temazepam_sleep_efficiency":
            temazepam["sleep_efficiency_percent"],

        "placebo_total_sleep_time":
            placebo["total_sleep_time_min"],

        "temazepam_total_sleep_time":
            temazepam["total_sleep_time_min"],

        "placebo_sleep_onset_latency":
            placebo["sleep_onset_latency_min"],

        "temazepam_sleep_onset_latency":
            temazepam["sleep_onset_latency_min"],

        "placebo_waso":
            placebo["waso_min"],

        "temazepam_waso":
            temazepam["waso_min"],
    }
)

# --------------------------------------------------
# Treatment effects
# --------------------------------------------------

paired["effect_sleep_efficiency"] = (
    paired["temazepam_sleep_efficiency"]
    - paired["placebo_sleep_efficiency"]
)

paired["effect_total_sleep_time"] = (
    paired["temazepam_total_sleep_time"]
    - paired["placebo_total_sleep_time"]
)

paired["effect_sleep_onset_latency"] = (
    paired["temazepam_sleep_onset_latency"]
    - paired["placebo_sleep_onset_latency"]
)

paired["effect_waso"] = (
    paired["temazepam_waso"]
    - paired["placebo_waso"]
)

paired.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "paired_analysis.csv",
    ),
    index=False,
)

# --------------------------------------------------
# Wilcoxon paired tests
# --------------------------------------------------

outcomes = {
    "Sleep Efficiency": (
        paired["placebo_sleep_efficiency"],
        paired["temazepam_sleep_efficiency"],
    ),
    "Total Sleep Time": (
        paired["placebo_total_sleep_time"],
        paired["temazepam_total_sleep_time"],
    ),
    "Sleep Onset Latency": (
        paired["placebo_sleep_onset_latency"],
        paired["temazepam_sleep_onset_latency"],
    ),
    "WASO": (
        paired["placebo_waso"],
        paired["temazepam_waso"],
    ),
}

results = []

for name, (p, t) in outcomes.items():

    statistic, p_value = wilcoxon(
        t,
        p,
        alternative="two-sided",
    )

    effect = t - p

    results.append(
        {
            "outcome": name,
            "placebo_mean": p.mean(),
            "temazepam_mean": t.mean(),
            "mean_effect": effect.mean(),
            "median_effect": effect.median(),
            "wilcoxon_statistic": statistic,
            "p_value": p_value,
        }
    )

stats_df = pd.DataFrame(results)

stats_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "statistical_results.csv",
    ),
    index=False,
)

# --------------------------------------------------
# Age vs treatment effect
# --------------------------------------------------

rho, age_p = spearmanr(
    paired["age"],
    paired["effect_sleep_efficiency"],
)

# --------------------------------------------------
# Positive / negative responders
# --------------------------------------------------

positive = (
    paired["effect_sleep_efficiency"] > 0
).sum()

negative = (
    paired["effect_sleep_efficiency"] < 0
).sum()

# --------------------------------------------------
# Print results
# --------------------------------------------------

print("\n===== Treatment Effect Analysis =====")

print("\nNumber of subjects:")
print(len(paired))

print("\nSleep Efficiency responders:")
print("Positive:", positive)
print("Negative:", negative)

print("\nStatistical results:")
print(
    stats_df.round(3)
    .to_string(index=False)
)

print("\nAge vs Sleep Efficiency effect:")
print(f"Spearman rho = {rho:.3f}")
print(f"p-value      = {age_p:.3f}")

print("\nSex-specific mean effect:")

print(
    paired.groupby("sex")[
        "effect_sleep_efficiency"
    ]
    .agg(["mean", "median", "count"])
    .round(3)
)

# --------------------------------------------------
# Plot 1:
# Paired Sleep Efficiency
# --------------------------------------------------

plt.figure(figsize=(7, 6))

for _, row in paired.iterrows():

    plt.plot(
        ["Placebo", "Temazepam"],
        [
            row["placebo_sleep_efficiency"],
            row["temazepam_sleep_efficiency"],
        ],
        marker="o",
        alpha=0.6,
    )

plt.ylabel("Sleep Efficiency (%)")
plt.title(
    "Sleep Efficiency: "
    "Placebo vs Temazepam"
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "paired_sleep_efficiency.png",
    ),
    dpi=300,
)

plt.close()

# --------------------------------------------------
# Plot 2:
# Treatment Effect Distribution
# --------------------------------------------------

plt.figure(figsize=(7, 5))

plt.hist(
    paired["effect_sleep_efficiency"],
    bins=8,
)

plt.axvline(
    0,
    linestyle="--",
)

plt.xlabel(
    "Treatment Effect "
    "(percentage points)"
)

plt.ylabel("Number of Subjects")

plt.title(
    "Distribution of Individual "
    "Treatment Effects"
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "treatment_effect_distribution.png",
    ),
    dpi=300,
)

plt.close()

# --------------------------------------------------
# Plot 3:
# Age vs Treatment Effect
# --------------------------------------------------

plt.figure(figsize=(7, 5))

plt.scatter(
    paired["age"],
    paired["effect_sleep_efficiency"],
)

plt.axhline(
    0,
    linestyle="--",
)

plt.xlabel("Age")

plt.ylabel(
    "Treatment Effect on "
    "Sleep Efficiency"
)

plt.title(
    "Age vs Treatment Effect"
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        OUTPUT_DIR,
        "age_vs_treatment_effect.png",
    ),
    dpi=300,
)

plt.close()

print("\nCreated results:")
print("- results/paired_analysis.csv")
print("- results/statistical_results.csv")
print("- results/paired_sleep_efficiency.png")
print("- results/treatment_effect_distribution.png")
print("- results/age_vs_treatment_effect.png")