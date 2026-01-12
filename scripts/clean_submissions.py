#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import timedelta

INPUT_FILE = Path(__file__).parent.parent / "data" / "submissions.csv"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "submissions_cleaned.csv"

COLUMN_NAMES = ["id", "student_id", "start_time", "exercise", "result_time"]


def main():
    print(f"Reading file: {INPUT_FILE}")
    
    df = pd.read_csv(INPUT_FILE, header=None, names=COLUMN_NAMES)
    
    print(f"Number of rows: {len(df)}")
    
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["result_time"] = pd.to_datetime(df["result_time"])
    
    # Count rows where result_time < start_time
    mask = df["result_time"] < df["start_time"]
    count_to_fix = mask.sum()
    print(f"Rows with result_time < start_time: {count_to_fix}")
    
    # Add 1 hour to result_time if result_time < start_time
    df.loc[mask, "result_time"] = df.loc[mask, "result_time"] + timedelta(hours=1)
    
    # Check for remaining anomalies after correction
    mask_after = df["result_time"] < df["start_time"]
    count_remaining = mask_after.sum()
    if count_remaining > 0:
        print(f"Remaining anomalies after correction: {count_remaining}")
    else:
        print("All anomalies have been corrected")
    
    # Calculate service_time (in seconds)
    df["service_time"] = (df["result_time"] - df["start_time"]).dt.total_seconds()
    
    print(f"\nService time statistics (seconds):")
    print(f"  Min: {df['service_time'].min():.2f}")
    print(f"  Max: {df['service_time'].max():.2f}")
    print(f"  Mean: {df['service_time'].mean():.2f}")
    print(f"  Median: {df['service_time'].median():.2f}")
    
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nCleaned file saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
