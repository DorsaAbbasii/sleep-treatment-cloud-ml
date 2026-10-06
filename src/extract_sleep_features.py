import pandas as pd
import mne

METADATA_FILE = "telemetry_metadata.csv"
OUTPUT_FILE = "sleep_features.csv"

metadata = pd.read_csv(METADATA_FILE)

SLEEP_STAGES = {
    "Sleep stage 1",
    "Sleep stage 2",
    "Sleep stage 3",
    "Sleep stage 4",
    "Sleep stage R",
}

WAKE_STAGE = "Sleep stage W"

records = []

for _, row in metadata.iterrows():

    annotations = mne.read_annotations(row["hypnogram_file"])

    stages = []

    for onset, duration, description in zip(
        annotations.onset,
        annotations.duration,
        annotations.description,
    ):
        stages.append(
            {
                "onset": float(onset),
                "duration": float(duration),
                "stage": description,
            }
        )

    # --------------------------------------------------
    # Total recording / annotated time
    # --------------------------------------------------

    total_recording_time = sum(
        item["duration"]
        for item in stages
    )

    # --------------------------------------------------
    # Sleep-stage durations
    # --------------------------------------------------

    n1 = sum(
        item["duration"]
        for item in stages
        if item["stage"] == "Sleep stage 1"
    )

    n2 = sum(
        item["duration"]
        for item in stages
        if item["stage"] == "Sleep stage 2"
    )

    n3 = sum(
        item["duration"]
        for item in stages
        if item["stage"] in {
            "Sleep stage 3",
            "Sleep stage 4",
        }
    )

    rem = sum(
        item["duration"]
        for item in stages
        if item["stage"] == "Sleep stage R"
    )

    wake = sum(
        item["duration"]
        for item in stages
        if item["stage"] == WAKE_STAGE
    )

    total_sleep_time = n1 + n2 + n3 + rem

    # --------------------------------------------------
    # Sleep Onset Latency
    # --------------------------------------------------

    first_sleep = next(
        (
            item
            for item in stages
            if item["stage"] in SLEEP_STAGES
        ),
        None,
    )

    if first_sleep is not None:
        sleep_onset_latency = first_sleep["onset"]
        sleep_onset = first_sleep["onset"]
    else:
        sleep_onset_latency = None
        sleep_onset = None

    # --------------------------------------------------
    # Wake After Sleep Onset (WASO)
    # --------------------------------------------------

    if sleep_onset is not None:
        waso = sum(
            item["duration"]
            for item in stages
            if (
                item["stage"] == WAKE_STAGE
                and item["onset"] >= sleep_onset
            )
        )
    else:
        waso = None

    # --------------------------------------------------
    # Sleep Efficiency
    # --------------------------------------------------

    if total_recording_time > 0:
        sleep_efficiency = (
            total_sleep_time
            / total_recording_time
        ) * 100
    else:
        sleep_efficiency = None

    records.append(
        {
            "subject": row["subject"],
            "age": row["age"],
            "sex": row["sex"],
            "night": row["night"],
            "condition": row["condition"],
            "treatment": row["treatment"],

            "total_recording_time_min":
                total_recording_time / 60,

            "total_sleep_time_min":
                total_sleep_time / 60,

            "sleep_efficiency_percent":
                sleep_efficiency,

            "sleep_onset_latency_min":
                (
                    sleep_onset_latency / 60
                    if sleep_onset_latency is not None
                    else None
                ),

            "waso_min":
                (
                    waso / 60
                    if waso is not None
                    else None
                ),

            "wake_min":
                wake / 60,

            "n1_min":
                n1 / 60,

            "n2_min":
                n2 / 60,

            "n3_min":
                n3 / 60,

            "rem_min":
                rem / 60,

            "psg_file":
                row["psg_file"],

            "hypnogram_file":
                row["hypnogram_file"],
        }
    )

features = pd.DataFrame(records)

features.to_csv(
    OUTPUT_FILE,
    index=False,
)

print("\nCreated:", OUTPUT_FILE)

print(
    "Number of records:",
    len(features),
)

print(
    "Number of subjects:",
    features["subject"].nunique(),
)

print("\nCondition counts:")
print(
    features["condition"]
    .value_counts()
)

print("\nAverage outcomes by condition:")

summary = features.groupby(
    "condition"
)[
    [
        "total_sleep_time_min",
        "sleep_efficiency_percent",
        "sleep_onset_latency_min",
        "waso_min",
        "n1_min",
        "n2_min",
        "n3_min",
        "rem_min",
    ]
].mean()

print(
    summary.round(2)
)

print("\nFirst 10 records:")

print(
    features.head(10)
    .to_string(index=False)
)