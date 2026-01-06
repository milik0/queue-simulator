"""
M/M/1/K Baseline Simulation Model.

This is the foundational model for all comparisons.
A single-server queue with finite capacity K.

Key characteristics:
- Poisson arrivals (rate λ)
- Exponential service times (rate μ)
- 1 server
- Capacity K (jobs are rejected when K jobs in system)
- FIFO discipline

This model has analytical solutions, allowing us to validate
the simulation against theory.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import simpy
import numpy as np

from ..core.job import Job, JobStatus, Population
from ..core.queue import Queue, Server, QueueDiscipline
from ..core.arrivals import PoissonArrivals
from ..core.metrics import MetricsCollector, SimulationResults
from ..analysis.theoretical import mm1k_metrics, print_metrics_comparison
from ..analysis.statistics import validate_against_theory, print_validation_results


@dataclass
class MM1KConfig:
    """Configuration for M/M/1/K simulation."""
    arrival_rate: float      # λ
    service_rate: float      # μ
    capacity: int           # K (total system capacity)
    simulation_time: float   # Duration to simulate
    warmup_time: float = 0.0  # Time to discard (steady-state)
    seed: Optional[int] = None
    
    @property
    def rho(self) -> float:
        """Traffic intensity."""
        return self.arrival_rate / self.service_rate
    
    @property
    def is_stable(self) -> bool:
        """M/M/1/K is always stable (finite capacity)."""
        return True


class MM1KSimulation:
    """
    M/M/1/K Discrete Event Simulation.
    
    This is the baseline model used to:
    1. Validate simulation infrastructure against theory
    2. Serve as comparison baseline for more complex models
    
    Usage:
        sim = MM1KSimulation(lambda_=0.8, mu=1.0, K=10)
        results = sim.run(duration=10000)
        sim.validate()  # Compare to theory
    """
    
    def __init__(
        self,
        arrival_rate: float,
        service_rate: float,
        capacity: int,
        seed: Optional[int] = None
    ):
        self.config = MM1KConfig(
            arrival_rate=arrival_rate,
            service_rate=service_rate,
            capacity=capacity,
            simulation_time=0.0,
            seed=seed
        )
        
        self.rng = np.random.default_rng(seed)
        self.results: Optional[SimulationResults] = None
        self._all_jobs: List[Job] = []
        
    def run(
        self,
        duration: float,
        warmup: float = 0.0,
        verbose: bool = True
    ) -> SimulationResults:
        """
        Run the simulation.
        
        Args:
            duration: Total simulation time
            warmup: Time to discard for steady-state
            verbose: Print progress
        
        Returns:
            SimulationResults with all metrics
        """
        self.config.simulation_time = duration
        self.config.warmup_time = warmup
        
        # Create SimPy environment
        env = simpy.Environment()
        
        # Create queue (capacity = K - 1 since 1 job can be in service)
        queue = Queue(
            env,
            capacity=self.config.capacity - 1,  # Queue capacity (K-1 waiting + 1 in service = K total)
            discipline=QueueDiscipline.FIFO,
            name="main_queue"
        )
        
        # Create server
        server = Server(
            env,
            service_rate=self.config.service_rate,
            name="main_server"
        )
        
        # Metrics collector
        collector = MetricsCollector(
            model_name="M/M/1/K",
            arrival_rate=self.config.arrival_rate,
            service_rate=self.config.service_rate,
            queue_capacity=self.config.capacity
        )
        
        # Storage for jobs
        self._all_jobs = []
        
        # Create arrival generator
        arrivals = PoissonArrivals(
            env,
            arrival_rate=self.config.arrival_rate,
            service_rate=self.config.service_rate,
            rng=self.rng
        )
        
        # Start processes
        env.process(self._arrival_process(env, arrivals, queue, server, collector, warmup))
        env.process(self._server_process(env, queue, server, collector, warmup))
        env.process(self._monitor_process(env, queue, server, collector, warmup))
        
        # Run simulation
        if verbose:
            print(f"Running M/M/1/K simulation...")
            print(f"  λ={self.config.arrival_rate}, μ={self.config.service_rate}, K={self.config.capacity}")
            print(f"  ρ={self.config.rho:.3f}")
            print(f"  Duration={duration}, Warmup={warmup}")
        
        env.run(until=duration)
        
        # Compute results
        collector.set_simulation_time(duration - warmup)
        self.results = collector.compute()
        
        if verbose:
            print(f"  Completed: {self.results.total_completed} jobs")
            print(f"  Rejected: {self.results.total_rejected} jobs")
            print(f"  Rejection rate: {self.results.rejection_rate:.2%}")
        
        return self.results
    
    def _arrival_process(
        self,
        env: simpy.Environment,
        arrivals: PoissonArrivals,
        queue: Queue,
        server: Server,
        collector: MetricsCollector,
        warmup: float
    ):
        """Process that generates arrivals."""
        gen = arrivals.generate()
        
        while True:
            # Wait for next arrival
            yield next(gen)  # This yields the timeout
            job = next(gen)  # This yields the job
            
            # Check if we can accept (system not full)
            # System is full if: queue is full AND server is busy
            system_size = len(queue) + (1 if server.is_busy else 0)
            
            if system_size >= self.config.capacity:
                # Reject
                job.status = JobStatus.REJECTED
                if env.now >= warmup:
                    collector.record_job(job)
            else:
                # Accept - add to queue
                queue.enqueue(job)
                self._all_jobs.append(job)
    
    def _server_process(
        self,
        env: simpy.Environment,
        queue: Queue,
        server: Server,
        collector: MetricsCollector,
        warmup: float
    ):
        """Process that serves jobs."""
        while True:
            if queue.is_empty or server.is_busy:
                # Wait a bit and check again
                yield env.timeout(0.001)
                continue
            
            # Get next job from queue
            job = queue.dequeue()
            if job is None:
                yield env.timeout(0.001)
                continue
            
            # Process the job
            yield from server.process(job)
            
            # Job completed
            job.departure_time = env.now
            
            # Record if past warmup
            if job.arrival_time >= warmup:
                collector.record_job(job)
    
    def _monitor_process(
        self,
        env: simpy.Environment,
        queue: Queue,
        server: Server,
        collector: MetricsCollector,
        warmup: float,
        interval: float = 1.0
    ):
        """Process that records metrics periodically."""
        while True:
            yield env.timeout(interval)
            
            if env.now >= warmup:
                collector.record_queue_length(env.now, len(queue))
                collector.record_utilization(env.now, 1.0 if server.is_busy else 0.0)
    
    def validate(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Validate simulation results against M/M/1/K theory.
        
        Returns:
            Dictionary of validation results
        """
        if self.results is None:
            raise ValueError("Must run simulation before validating")
        
        # Get theoretical values
        theory = mm1k_metrics(
            self.config.arrival_rate,
            self.config.service_rate,
            self.config.capacity
        )
        
        # Extract sojourn and waiting times for CI calculation
        sojourn_times = [
            j.sojourn_time for j in self.results.completed_jobs
            if j.sojourn_time is not None
        ]
        waiting_times = [
            j.waiting_time for j in self.results.completed_jobs
            if j.waiting_time is not None
        ]
        
        # Validate
        validation = validate_against_theory(
            self.results.to_dict(),
            theory,
            sojourn_times=sojourn_times,
            waiting_times=waiting_times
        )
        
        if verbose:
            print_validation_results(validation)
            print(f"\nTheoretical blocking probability: {theory.Pb:.4f}")
        
        return {
            "validation": validation,
            "theoretical": theory.to_dict(),
            "all_acceptable": all(v.acceptable for v in validation.values())
        }
    
    def get_sojourn_times(self) -> List[float]:
        """Get list of sojourn times for completed jobs."""
        return [
            j.sojourn_time for j in self.results.completed_jobs
            if j.sojourn_time is not None
        ]
    
    def get_waiting_times(self) -> List[float]:
        """Get list of waiting times for completed jobs."""
        return [
            j.waiting_time for j in self.results.completed_jobs
            if j.waiting_time is not None
        ]


def run_baseline(
    arrival_rate: float = 0.8,
    service_rate: float = 1.0,
    capacity: int = 10,
    duration: float = 10000,
    warmup: float = 1000,
    seed: Optional[int] = 42
) -> SimulationResults:
    """
    Convenience function to run baseline simulation.
    
    Default parameters are chosen for a moderately loaded system.
    
    Args:
        arrival_rate: λ (default 0.8)
        service_rate: μ (default 1.0)
        capacity: K (default 10)
        duration: Simulation time
        warmup: Warmup period
        seed: Random seed for reproducibility
    
    Returns:
        SimulationResults
    """
    sim = MM1KSimulation(
        arrival_rate=arrival_rate,
        service_rate=service_rate,
        capacity=capacity,
        seed=seed
    )
    
    results = sim.run(duration=duration, warmup=warmup)
    sim.validate()
    
    return results


def parameter_sweep(
    arrival_rates: List[float],
    service_rate: float = 1.0,
    capacity: int = 10,
    duration: float = 5000,
    warmup: float = 500,
    n_runs: int = 5
) -> List[Dict[str, Any]]:
    """
    Run baseline across multiple arrival rates.
    
    Useful for generating curves like "sojourn time vs load".
    
    Returns:
        List of results dictionaries
    """
    all_results = []
    
    for lambda_ in arrival_rates:
        rho = lambda_ / service_rate
        print(f"\n{'='*40}")
        print(f"ρ = {rho:.2f} (λ={lambda_})")
        
        run_results = []
        for run in range(n_runs):
            sim = MM1KSimulation(
                arrival_rate=lambda_,
                service_rate=service_rate,
                capacity=capacity,
                seed=42 + run
            )
            results = sim.run(duration=duration, warmup=warmup, verbose=False)
            run_results.append(results.to_dict())
        
        # Average across runs
        avg_result = {
            "lambda": lambda_,
            "rho": rho,
            "mean_sojourn_time": np.mean([r["mean_sojourn_time"] for r in run_results]),
            "std_sojourn_time": np.std([r["mean_sojourn_time"] for r in run_results]),
            "mean_waiting_time": np.mean([r["mean_waiting_time"] for r in run_results]),
            "rejection_rate": np.mean([r["rejection_rate"] for r in run_results]),
            "server_utilization": np.mean([r["server_utilization"] for r in run_results]),
        }
        
        # Add theoretical
        theory = mm1k_metrics(lambda_, service_rate, capacity)
        avg_result["theoretical_W"] = theory.W
        avg_result["theoretical_Pb"] = theory.Pb
        
        all_results.append(avg_result)
        print(f"  W_sim={avg_result['mean_sojourn_time']:.3f}, W_theory={theory.W:.3f}")
    
    return all_results
