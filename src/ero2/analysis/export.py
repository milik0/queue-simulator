"""
Data export utilities for simulation results.

Exports results to CSV and JSON for external analysis.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.metrics import SimulationResults


def ensure_dir(path: str) -> Path:
    """Ensure directory exists."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def export_results_json(
    results: SimulationResults,
    filepath: str,
    include_jobs: bool = False
) -> str:
    """
    Export simulation results to JSON.
    
    Args:
        results: SimulationResults to export
        filepath: Output file path
        include_jobs: Include raw job data (can be large)
    
    Returns:
        Path to created file
    """
    data = {
        "metadata": {
            "model": results.model_name,
            "exported_at": datetime.now().isoformat(),
            "simulation_time": results.simulation_time,
        },
        "parameters": {
            "lambda": results.arrival_rate,
            "mu": results.service_rate,
            "num_servers": results.num_servers,
            "queue_capacity": results.queue_capacity,
        },
        "metrics": {
            "utilization": results.server_utilization,
            "mean_sojourn_time": results.mean_sojourn_time,
            "std_sojourn_time": results.std_sojourn_time,
            "median_sojourn_time": results.median_sojourn_time,
            "p95_sojourn_time": results.p95_sojourn_time,
            "p99_sojourn_time": results.p99_sojourn_time,
            "mean_waiting_time": results.mean_waiting_time,
            "mean_queue_length": results.mean_queue_length,
            "max_queue_length": results.max_queue_length,
            "rejection_rate": results.rejection_rate,
            "total_arrivals": results.total_arrivals,
            "total_completed": results.total_completed,
            "total_rejected": results.total_rejected,
        },
        "population_metrics": results.metrics_by_population,
        "theoretical": results.theoretical_values,
    }
    
    if include_jobs:
        data["jobs"] = [
            {
                "id": j.id,
                "arrival_time": j.arrival_time,
                "service_time": j.service_time,
                "sojourn_time": j.sojourn_time,
                "waiting_time": j.waiting_time,
                "population": j.population.value,
                "status": j.status.value,
            }
            for j in results.completed_jobs
        ]
    
    # Ensure directory exists
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"Exported JSON: {filepath}")
    return str(filepath)


def export_results_csv(
    results: SimulationResults,
    filepath: str
) -> str:
    """
    Export simulation metrics to CSV.
    
    Single row with all key metrics.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    row = {
        "model": results.model_name,
        "lambda": results.arrival_rate,
        "mu": results.service_rate,
        "num_servers": results.num_servers,
        "queue_capacity": results.queue_capacity,
        "simulation_time": results.simulation_time,
        "utilization": results.server_utilization,
        "mean_sojourn_time": results.mean_sojourn_time,
        "std_sojourn_time": results.std_sojourn_time,
        "p95_sojourn_time": results.p95_sojourn_time,
        "mean_waiting_time": results.mean_waiting_time,
        "mean_queue_length": results.mean_queue_length,
        "max_queue_length": results.max_queue_length,
        "rejection_rate": results.rejection_rate,
        "total_completed": results.total_completed,
        "total_rejected": results.total_rejected,
    }
    
    file_exists = path.exists()
    
    with open(filepath, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    
    print(f"Exported CSV: {filepath}")
    return str(filepath)


def export_jobs_csv(
    results: SimulationResults,
    filepath: str
) -> str:
    """
    Export individual job data to CSV.
    
    Useful for detailed statistical analysis.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        "id", "arrival_time", "service_time", "queue_entry_time",
        "service_start_time", "departure_time", "sojourn_time",
        "waiting_time", "population", "status"
    ]
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for job in results.completed_jobs:
            writer.writerow({
                "id": job.id,
                "arrival_time": job.arrival_time,
                "service_time": job.service_time,
                "queue_entry_time": job.queue_entry_time,
                "service_start_time": job.service_start_time,
                "departure_time": job.departure_time,
                "sojourn_time": job.sojourn_time,
                "waiting_time": job.waiting_time,
                "population": job.population.value,
                "status": job.status.value,
            })
    
    print(f"Exported {len(results.completed_jobs)} jobs to: {filepath}")
    return str(filepath)


def export_time_series_csv(
    results: SimulationResults,
    filepath: str
) -> str:
    """Export queue length and utilization time series."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["time", "queue_length"])
        
        for time, length in results.queue_length_history:
            writer.writerow([time, length])
    
    print(f"Exported time series: {filepath}")
    return str(filepath)


def export_comparison_csv(
    results_list: List[Dict[str, Any]],
    filepath: str,
    labels: Optional[List[str]] = None
) -> str:
    """
    Export comparison of multiple simulation runs.
    
    Args:
        results_list: List of result dictionaries
        filepath: Output path
        labels: Optional labels for each result
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if not results_list:
        print("No results to export")
        return ""
    
    # Get all keys from first result
    fieldnames = ["label"] + list(results_list[0].keys())
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(results_list):
            row = {"label": labels[i] if labels else f"run_{i}"}
            row.update(result)
            writer.writerow(row)
    
    print(f"Exported comparison: {filepath}")
    return str(filepath)


def generate_report(
    results: SimulationResults,
    output_dir: str = "results",
    include_jobs: bool = False
) -> Dict[str, str]:
    """
    Generate complete report with all exports.
    
    Returns:
        Dictionary of generated file paths
    """
    output_path = ensure_dir(output_dir)
    data_path = ensure_dir(f"{output_dir}/data")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_safe = results.model_name.replace("/", "_").replace(" ", "_")
    
    files = {}
    
    # JSON export
    files["json"] = export_results_json(
        results,
        str(data_path / f"{model_safe}_{timestamp}.json"),
        include_jobs=include_jobs
    )
    
    # CSV summary
    files["csv_summary"] = export_results_csv(
        results,
        str(data_path / "simulation_results.csv")
    )
    
    # Time series
    if results.queue_length_history:
        files["csv_timeseries"] = export_time_series_csv(
            results,
            str(data_path / f"{model_safe}_{timestamp}_timeseries.csv")
        )
    
    # Jobs (if requested)
    if include_jobs:
        files["csv_jobs"] = export_jobs_csv(
            results,
            str(data_path / f"{model_safe}_{timestamp}_jobs.csv")
        )
    
    print(f"\n✅ Report generated in {output_dir}/data/")
    return files
