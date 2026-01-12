#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import json

# Chemins
INPUT_FILE = Path(__file__).parent.parent / "data" / "submissions.csv"
OUTPUT_FILE = Path(__file__).parent.parent / "results" / "section_1_1_stats.json"

# Number of execution servers
K = 4


def main():
    print(f"Reading file: {INPUT_FILE}")
    
    df = pd.read_csv(INPUT_FILE)
    
    print(f"Number of submissions: {len(df)}")
    
    df["start_time"] = pd.to_datetime(df["start_time"], format="ISO8601")
    df["result_time"] = pd.to_datetime(df["result_time"], format="ISO8601")
    
    # 1. Analyzed period
    start_date = df["start_time"].min()
    end_date = df["start_time"].max()
    period_hours = (end_date - start_date).total_seconds() / 3600
    
    print(f"\n=== Analyzed Period ===")
    print(f"Start: {start_date}")
    print(f"End: {end_date}")
    print(f"Total duration: {period_hours:.0f}h")
    
    # 2. Number of submissions and students
    n_submissions = len(df)
    n_students = df["student_id"].nunique()
    
    print(f"\n=== Volumes ===")
    print(f"Valid submissions: {n_submissions}")
    print(f"Unique students: {n_students}")
    
    # 3. Arrival rate (lambda)
    arrivals_per_minute = n_submissions / (period_hours * 60)
    arrivals_per_hour = arrivals_per_minute * 60
    
    print(f"\n=== Arrival Rate ===")
    print(f"Lambda (submissions/min): {arrivals_per_minute:.2f}")
    print(f"Lambda (submissions/h): {arrivals_per_hour:.1f}")
    
    # 4. Service time
    service_mean = df["service_time"].mean()
    service_median = df["service_time"].median()
    service_mean_min = service_mean / 60
    service_median_min = service_median / 60
    
    print(f"\n=== Service Time ===")
    print(f"Mean: {service_mean:.1f}s ({service_mean_min:.1f} min)")
    print(f"Median: {service_median:.1f}s ({service_median_min:.1f} min)")
    
    # 5. Service rate (mu)
    mu = 1.0 / service_mean_min
    
    print(f"Service rate (mu): {mu:.2f}/min")
    
    # 6. Traffic intensity (rho)
    rho = arrivals_per_minute / (K * mu)
    
    print(f"\n=== Intensity ===")
    print(f"rho (K={K} servers): {rho:.2f}")
    print(f"System stable: {'Yes' if rho < 1 else 'No'}")
    
    # 7. Peak activity (by hour of the day)
    df["hour"] = df["start_time"].dt.hour
    hourly_counts = df.groupby("hour").size()
    peak_hour = hourly_counts.idxmax()
    peak_count = hourly_counts.max()
    
    print(f"\n=== Peak Activity ===")
    print(f"Peak hour: {peak_hour}h")
    print(f"Submissions at peak hour: {peak_count}")
    
    # Top 3 activity hours
    top_hours = hourly_counts.nlargest(3)
    print(f"Top 3 hours: {list(top_hours.index)}h with {list(top_hours.values)} submissions")
    
    # Summary for report
    print("\n" + "=" * 60)
    print("SUMMARY FOR REPORT (Section 1.1)")
    print("=" * 60)
    print(f"Period: {start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')} ({period_hours:.0f}h)")
    print(f"Valid submissions: {n_submissions}")
    print(f"Students: {n_students}")
    print(f"Lambda (arrival rate): {arrivals_per_minute:.2f}/min ({arrivals_per_hour:.1f}/h)")
    print(f"Mean service time: {service_mean_min:.1f} min (median: {service_median_min:.1f} min)")
    print(f"Mu (service rate): {mu:.2f}/min")
    print(f"Rho (intensity, K={K}): {rho:.2f}")
    print(f"Peak activity: {peak_hour}h ({peak_count} submissions)")
    
    # Save results
    results = {
        "period_start": start_date.strftime("%d %b %Y"),
        "period_end": end_date.strftime("%d %b %Y"),
        "period_hours": round(period_hours),
        "n_submissions": n_submissions,
        "n_students": n_students,
        "lambda_per_min": round(arrivals_per_minute, 2),
        "lambda_per_hour": round(arrivals_per_hour, 1),
        "service_mean_sec": round(service_mean, 1),
        "service_mean_min": round(service_mean_min, 1),
        "service_median_min": round(service_median_min, 1),
        "mu_per_min": round(mu, 2),
        "K_servers": K,
        "rho": round(rho, 2),
        "peak_hour": int(peak_hour),
        "peak_count": int(peak_count)
    }
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {OUTPUT_FILE}")
    
    return results


if __name__ == "__main__":
    main()
