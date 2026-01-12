"""
Data Loader - Load and analyze real submission data from the Forge.

This module loads the submissions.csv file and computes real-world parameters
for calibrating the simulation models.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class RealDataStats:
    """Statistics computed from real submission data."""
    # Basic counts
    total_submissions: int
    unique_students: int
    
    # Time period
    start_date: str
    end_date: str
    duration_hours: float
    
    # Service time statistics (seconds)
    mean_service_time: float
    median_service_time: float
    std_service_time: float
    p95_service_time: float
    min_service_time: float
    max_service_time: float
    
    # Arrival rate
    lambda_per_hour: float
    lambda_per_minute: float
    
    # Service rate
    mu_per_second: float
    mu_per_minute: float
    
    # Peak hours
    peak_hours: dict  # hour -> count
    
    # Estimated rho (with K servers)
    def compute_rho(self, K: int = 4) -> float:
        """Compute traffic intensity for K servers."""
        return self.lambda_per_minute / (K * self.mu_per_minute)


def load_submissions(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load pre-cleaned submissions data from submissions_clean.csv.
    
    The data should be cleaned first using clean_data.py which handles
    the timezone correction (-1h on submission_time).
    
    Expected format: id,student,submission_time,exercise,result_time,service_time
    """
    if csv_path is None:
        # Default: load pre-cleaned data
        base_path = Path(__file__).parents[3]
        csv_path = base_path / "submissions_clean.csv"
        
        if not csv_path.exists():
            raise FileNotFoundError(
                f"Cleaned data not found at {csv_path}. "
                "Please run 'python clean_data.py' first."
            )
    
    df = pd.read_csv(csv_path)
    
    # Parse timestamp for hour analysis
    df['start'] = pd.to_datetime(df['start_time'])
    df['hour'] = df['start'].dt.hour
    
    return df


def compute_stats(df: pd.DataFrame) -> RealDataStats:
    """Compute statistics from loaded data."""
    
    # Time period
    start_date = df['start'].min()
    end_date = df['start'].max()
    duration_hours = (end_date - start_date).total_seconds() / 3600
    
    # Service time stats
    service_times = df['service_time']
    mean_service = service_times.mean()
    
    # Peak hours
    hourly = df.groupby('hour').size().to_dict()
    
    # Arrival rate
    lambda_per_hour = len(df) / duration_hours
    
    # Service rate (μ = 1/mean_service_time)
    mu_per_second = 1 / mean_service
    
    return RealDataStats(
        total_submissions=len(df),
        unique_students=df['student_id'].nunique(),
        start_date=str(start_date),
        end_date=str(end_date),
        duration_hours=duration_hours,
        mean_service_time=mean_service,
        median_service_time=service_times.median(),
        std_service_time=service_times.std(),
        p95_service_time=service_times.quantile(0.95),
        min_service_time=service_times.min(),
        max_service_time=service_times.max(),
        lambda_per_hour=lambda_per_hour,
        lambda_per_minute=lambda_per_hour / 60,
        mu_per_second=mu_per_second,
        mu_per_minute=mu_per_second * 60,
        peak_hours=hourly,
    )


def get_real_parameters(csv_path: Optional[str] = None) -> Tuple[float, float, RealDataStats]:
    """
    Get real λ and μ from data.
    
    Returns:
        Tuple of (lambda_per_minute, mu_per_minute, full_stats)
    """
    df = load_submissions(csv_path)
    stats = compute_stats(df)
    return stats.lambda_per_minute, stats.mu_per_minute, stats


def print_stats(stats: RealDataStats):
    """Pretty print statistics."""
    print("=" * 60)
    print("STATISTIQUES DONNÉES RÉELLES (Forge EPITA)")
    print("=" * 60)
    print(f"Période: {stats.start_date[:10]} → {stats.end_date[:10]}")
    print(f"Durée: {stats.duration_hours:.1f} heures")
    print(f"")
    print(f"Soumissions totales: {stats.total_submissions:,}")
    print(f"Étudiants uniques: {stats.unique_students}")
    print(f"")
    print("--- Temps de service ---")
    print(f"Moyenne: {stats.mean_service_time:.1f}s ({stats.mean_service_time/60:.1f} min)")
    print(f"Médiane: {stats.median_service_time:.1f}s ({stats.median_service_time/60:.1f} min)")
    print(f"Écart-type: {stats.std_service_time:.1f}s")
    print(f"P95: {stats.p95_service_time:.1f}s ({stats.p95_service_time/60:.1f} min)")
    print(f"")
    print("--- Taux ---")
    print(f"λ (arrivées): {stats.lambda_per_minute:.3f}/min ({stats.lambda_per_hour:.1f}/h)")
    print(f"μ (service): {stats.mu_per_minute:.5f}/min")
    print(f"ρ (K=4): {stats.compute_rho(4):.2f}")
    print(f"")
    print("--- Heures de pic ---")
    sorted_hours = sorted(stats.peak_hours.items(), key=lambda x: -x[1])[:5]
    for hour, count in sorted_hours:
        print(f"  {hour:02d}h: {count} soumissions")


if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    df = load_submissions(csv_path)
    stats = compute_stats(df)
    print_stats(stats)
