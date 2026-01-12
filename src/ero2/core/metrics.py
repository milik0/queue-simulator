from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np
from scipy import stats

from .job import Job, JobStatus, Population


@dataclass
class SimulationResults:
    """
    Aggregated results from a simulation run.
    
    Contains all metrics needed for analysis and reporting.
    """
    # Configuration
    model_name: str = ""
    arrival_rate: float = 0.0  # λ
    service_rate: float = 0.0  # μ
    num_servers: int = 1
    queue_capacity: int = 0
    simulation_time: float = 0.0
    
    # Job-level data
    completed_jobs: List[Job] = field(default_factory=list)
    rejected_jobs: List[Job] = field(default_factory=list)
    
    # Computed metrics (set by MetricsCollector.compute())
    # Time metrics
    mean_sojourn_time: float = 0.0
    std_sojourn_time: float = 0.0
    median_sojourn_time: float = 0.0
    p95_sojourn_time: float = 0.0
    p99_sojourn_time: float = 0.0
    
    mean_waiting_time: float = 0.0
    std_waiting_time: float = 0.0
    median_waiting_time: float = 0.0
    p95_waiting_time: float = 0.0
    
    mean_service_time: float = 0.0
    
    # Utilization metrics
    server_utilization: float = 0.0  # ρ
    
    # Queue metrics
    mean_queue_length: float = 0.0
    max_queue_length: int = 0
    
    # Rejection metrics
    rejection_rate: float = 0.0
    total_arrivals: int = 0
    total_completed: int = 0
    total_rejected: int = 0
    
    # Per-population metrics (for heterogeneous models)
    metrics_by_population: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Time series data
    queue_length_history: List[tuple[float, int]] = field(default_factory=list)
    utilization_history: List[tuple[float, float]] = field(default_factory=list)
    
    # Theoretical comparison
    theoretical_values: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "model_name": self.model_name,
            "lambda": self.arrival_rate,
            "mu": self.service_rate,
            "num_servers": self.num_servers,
            "queue_capacity": self.queue_capacity,
            "simulation_time": self.simulation_time,
            "mean_sojourn_time": self.mean_sojourn_time,
            "std_sojourn_time": self.std_sojourn_time,
            "p95_sojourn_time": self.p95_sojourn_time,
            "mean_waiting_time": self.mean_waiting_time,
            "server_utilization": self.server_utilization,
            "mean_queue_length": self.mean_queue_length,
            "max_queue_length": self.max_queue_length,
            "rejection_rate": self.rejection_rate,
            "total_arrivals": self.total_arrivals,
            "total_completed": self.total_completed,
            "total_rejected": self.total_rejected,
        }


class MetricsCollector:
    """
    Collects and computes metrics during and after simulation.
    
    Usage:
        collector = MetricsCollector("M/M/1/K", lambda_=0.8, mu=1.0)
        # During simulation:
        collector.record_job(job)
        collector.record_queue_length(time, length)
        # After simulation:
        results = collector.compute()
    """
    
    def __init__(
        self,
        model_name: str,
        arrival_rate: float,
        service_rate: float,
        num_servers: int = 1,
        queue_capacity: int = float('inf')
    ):
        self.model_name = model_name
        self.arrival_rate = arrival_rate
        self.service_rate = service_rate
        self.num_servers = num_servers
        self.queue_capacity = queue_capacity
        
        # Storage
        self._jobs: List[Job] = []
        self._queue_lengths: List[tuple[float, int]] = []
        self._utilization_samples: List[tuple[float, float]] = []
        
        self._simulation_time = 0.0
    
    def record_job(self, job: Job):
        """Record a job that has been processed or rejected."""
        self._jobs.append(job)
    
    def record_queue_length(self, time: float, length: int):
        """Record queue length at a point in time."""
        self._queue_lengths.append((time, length))
    
    def record_utilization(self, time: float, utilization: float):
        """Record server utilization at a point in time."""
        self._utilization_samples.append((time, utilization))
    
    def set_simulation_time(self, time: float):
        """Set the total simulation time."""
        self._simulation_time = time
    
    def compute(self) -> SimulationResults:
        """
        Compute all metrics from collected data.
        
        Returns:
            SimulationResults with all computed metrics
        """
        results = SimulationResults(
            model_name=self.model_name,
            arrival_rate=self.arrival_rate,
            service_rate=self.service_rate,
            num_servers=self.num_servers,
            queue_capacity=self.queue_capacity,
            simulation_time=self._simulation_time
        )
        
        # Separate completed and rejected jobs
        completed = [j for j in self._jobs if j.status == JobStatus.COMPLETED]
        rejected = [j for j in self._jobs if j.status == JobStatus.REJECTED]
        
        results.completed_jobs = completed
        results.rejected_jobs = rejected
        results.total_completed = len(completed)
        results.total_rejected = len(rejected)
        results.total_arrivals = len(self._jobs)
        
        # Rejection rate
        if results.total_arrivals > 0:
            results.rejection_rate = results.total_rejected / results.total_arrivals
        
        # Time metrics (from completed jobs)
        if completed:
            sojourn_times = [j.sojourn_time for j in completed if j.sojourn_time is not None]
            waiting_times = [j.waiting_time for j in completed if j.waiting_time is not None]
            service_times = [j.service_time for j in completed]
            
            if sojourn_times:
                results.mean_sojourn_time = np.mean(sojourn_times)
                results.std_sojourn_time = np.std(sojourn_times)
                results.median_sojourn_time = np.median(sojourn_times)
                results.p95_sojourn_time = np.percentile(sojourn_times, 95)
                results.p99_sojourn_time = np.percentile(sojourn_times, 99)
            
            if waiting_times:
                results.mean_waiting_time = np.mean(waiting_times)
                results.std_waiting_time = np.std(waiting_times)
                results.median_waiting_time = np.median(waiting_times)
                results.p95_waiting_time = np.percentile(waiting_times, 95)
            
            if service_times:
                results.mean_service_time = np.mean(service_times)
        
        # Queue length statistics
        if self._queue_lengths:
            lengths = [l for _, l in self._queue_lengths]
            results.mean_queue_length = np.mean(lengths)
            results.max_queue_length = max(lengths)
            results.queue_length_history = self._queue_lengths.copy()
        
        # Utilization (time-weighted average)
        if self._utilization_samples:
            results.utilization_history = self._utilization_samples.copy()
            # Simple average for now
            utils = [u for _, u in self._utilization_samples]
            results.server_utilization = np.mean(utils)
        else:
            # Estimate from throughput
            if self._simulation_time > 0 and completed:
                throughput = len(completed) / self._simulation_time
                results.server_utilization = throughput / (self.num_servers * self.service_rate)
        
        # Per-population metrics
        results.metrics_by_population = self._compute_population_metrics(completed)
        
        return results
    
    def _compute_population_metrics(self, completed: List[Job]) -> Dict[str, Dict[str, float]]:
        """Compute metrics broken down by population."""
        metrics = {}
        
        for pop in Population:
            pop_jobs = [j for j in completed if j.population == pop]
            if not pop_jobs:
                continue
            
            sojourn_times = [j.sojourn_time for j in pop_jobs if j.sojourn_time is not None]
            waiting_times = [j.waiting_time for j in pop_jobs if j.waiting_time is not None]
            
            if sojourn_times:
                metrics[pop.value] = {
                    "count": len(pop_jobs),
                    "mean_sojourn_time": np.mean(sojourn_times),
                    "std_sojourn_time": np.std(sojourn_times),
                    "p95_sojourn_time": np.percentile(sojourn_times, 95),
                    "mean_waiting_time": np.mean(waiting_times) if waiting_times else 0.0,
                }
        
        return metrics


def confidence_interval(data: List[float], confidence: float = 0.95) -> tuple[float, float]:
    """
    Calculate confidence interval for the mean.
    
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if len(data) < 2:
        mean = data[0] if data else 0.0
        return (mean, mean)
    
    mean = np.mean(data)
    se = stats.sem(data)
    h = se * stats.t.ppf((1 + confidence) / 2, len(data) - 1)
    
    return (mean - h, mean + h)


def compare_means(
    data1: List[float],
    data2: List[float],
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Compare two distributions using Mann-Whitney U test.
    
    Returns:
        Dictionary with test results
    """
    if len(data1) < 3 or len(data2) < 3:
        return {"error": "Insufficient data for comparison"}
    
    statistic, pvalue = stats.mannwhitneyu(data1, data2, alternative='two-sided')
    
    return {
        "statistic": statistic,
        "p_value": pvalue,
        "significant": pvalue < alpha,
        "mean1": np.mean(data1),
        "mean2": np.mean(data2),
        "median1": np.median(data1),
        "median2": np.median(data2),
    }
