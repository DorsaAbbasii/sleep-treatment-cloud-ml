import glob
import pandas as pd

METADATA_FILE = "ST-subjects.xls"
OUTPUT_FILE = "telemetry_metadata.csv"

# Read Excel file
df = pd.read_excel(METADATA_FILE, header=[0, 1])

records = []

for _, row in df.iterrows():
    subject_value = row.iloc[0]

    if pd.isna(subject_value):
        continue

    subject = int(subject_value)
    age = int(row.iloc[1])

    sex_code = int(row.iloc[2])
    sex = {
        1: "Male",
        2: "Female"
    }.get(sex_code, "Unknown")

    placebo_night = int(row.iloc[3])
    placebo_lights_off = row.iloc[4]

    temazepam_night = int(row.iloc[5])
    temazepam_lights_off = row.iloc[6]

    conditions = [
        {
            "condition": "Placebo",
            "treatment": 0,
            "night": placebo_night,
            "lights_off": placebo_lights_off,
        },
        {
            "condition": "Temazepam",
            "treatment": 1,
            "night": temazepam_night,
            "lights_off": temazepam_lights_off,
        },
    ]

    for condition in conditions:
        night = condition["night"]

        prefix = f"ST7{subject:02d}{night}"

        psg_matches = glob.glob(f"{prefix}*-PSG.edf")
        hypnogram_matches = glob.glob(f"{prefix}*-Hypnogram.edf")

        psg_file = psg_matches[0] if len(psg_matches) == 1 else None
        hypnogram_file = (
            hypnogram_matches[0]
            if len(hypnogram_matches) == 1
            else None
        )

        records.append(
            {
                "subject": subject,
                "age": age,
                "sex": sex,
                "night": night,
                "condition": condition["condition"],
                "treatment": condition["treatment"],
                "lights_off": condition["lights_off"],
                "psg_file": psg_file,
                "hypnogram_file": hypnogram_file,
            }
        )

metadata = pd.DataFrame(records)

metadata.to_csv(OUTPUT_FILE, index=False)

print("\nCreated:", OUTPUT_FILE)
print("Number of records:", len(metadata))
print("Number of subjects:", metadata["subject"].nunique())

print("\nTreatment counts:")
print(metadata["condition"].value_counts())

print("\nMissing PSG files:", metadata["psg_file"].isna().sum())
print(
    "Missing Hypnogram files:",
    metadata["hypnogram_file"].isna().sum()
)

print("\nFirst 10 records:")
print(metadata.head(10).to_string(index=False))