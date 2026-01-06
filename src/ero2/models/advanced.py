"""
Advanced simulation models.

Features:
- Non-homogeneous Poisson process λ(t)
- Batch arrivals
- Daily patterns based on real data
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
import simpy
import numpy as np

from ..core.job import Job, JobStatus, Population
from ..core.queue import Queue, Server, QueueDiscipline
from ..core.arrivals import NonHomogeneousArrivals, BatchArrivals, daily_pattern, deadline_peak
from ..core.metrics import MetricsCollector, SimulationResults


@dataclass
class AdvancedConfig:
    """Configuration for advanced simulation."""
    # Base parameters
    base_arrival_rate: float = 10.0  # λ₀ (pushes per minute baseline)
    service_rate: float = 1.0        # μ
    num_servers: int = 4
    queue_capacity: int = 50
    
    # Time pattern
    pattern: str = "daily"  # "constant", "daily", "deadline"
    peak_rate: float = 40.0  # Peak λ (from real data: 40 pushes/min at 20:00-21:00)
    peak_hour: float = 20.5  # 20:30
    
    # Simulation
    simulation_hours: float = 24.0  # Simulate one full day
    warmup_hours: float = 1.0
    seed: Optional[int] = None


class AdvancedSimulation:
    """
    Advanced simulation with time-varying arrival rates.
    
    Based on real observations:
    - Baseline: 10-15 pushes/min during day
    - Peak: 40 pushes/min around 20:00-21:00
    - Low: minimal activity at night
    """
    
    def __init__(self, config: AdvancedConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.results: Optional[SimulationResults] = None
        self._arrival_rate_log: List[tuple[float, float]] = []
    
    def _get_rate_function(self) -> tuple[Callable[[float], float], float]:
        """Get rate function and max rate based on pattern."""
        if self.config.pattern == "constant":
            rate_func = lambda t: self.config.base_arrival_rate
            max_rate = self.config.base_arrival_rate
        
        elif self.config.pattern == "daily":
            rate_func = daily_pattern(
                base_rate=self.config.base_arrival_rate,
                peak_rate=self.config.peak_rate,
                peak_hour=self.config.peak_hour
            )
            max_rate = self.config.peak_rate
        
        elif self.config.pattern == "deadline":
            # Exponentially increasing towards deadline
            deadline_time = self.config.simulation_hours * 60  # End of simulation
            rate_func = deadline_peak(
                base_rate=self.config.base_arrival_rate,
                peak_rate=self.config.peak_rate,
                peak_time=deadline_time * 0.9,  # Peak at 90% of time
                width=deadline_time * 0.1
            )
            max_rate = self.config.peak_rate
        
        else:
            rate_func = lambda t: self.config.base_arrival_rate
            max_rate = self.config.base_arrival_rate
        
        return rate_func, max_rate
    
    def run(self, verbose: bool = True) -> SimulationResults:
        """Run the advanced simulation."""
        env = simpy.Environment()
        
        # Convert hours to simulation time units (minutes)
        duration = self.config.simulation_hours * 60
        warmup = self.config.warmup_hours * 60
        
        # Create queue
        queue = Queue(
            env,
            capacity=self.config.queue_capacity,
            discipline=QueueDiscipline.FIFO,
            name="main_queue"
        )
        
        # Create servers
        servers = [
            Server(env, self.config.service_rate, f"server_{i}")
            for i in range(self.config.num_servers)
        ]
        
        # Metrics
        collector = MetricsCollector(
            model_name=f"Advanced ({self.config.pattern})",
            arrival_rate=self.config.base_arrival_rate,
            service_rate=self.config.service_rate,
            num_servers=self.config.num_servers,
            queue_capacity=self.config.queue_capacity
        )
        
        # Get rate function
        rate_func, max_rate = self._get_rate_function()
        
        # Create non-homogeneous arrivals
        arrivals = NonHomogeneousArrivals(
            env,
            rate_function=rate_func,
            max_rate=max_rate,
            service_rate=self.config.service_rate,
            rng=self.rng
        )
        
        self._arrival_rate_log = []
        
        if verbose:
            print(f"Running Advanced simulation ({self.config.pattern})...")
            print(f"  Duration: {self.config.simulation_hours:.1f} hours")
            print(f"  Base λ={self.config.base_arrival_rate}, Peak λ={self.config.peak_rate}")
            print(f"  Servers: {self.config.num_servers}, K={self.config.queue_capacity}")
        
        # Start processes
        env.process(self._arrival_process(env, arrivals, queue, rate_func, warmup))
        env.process(self._server_process(env, queue, servers, collector, warmup))
        env.process(self._monitor(env, queue, collector, rate_func, warmup))
        
        # Run
        env.run(until=duration)
        
        # Compile results
        collector.set_simulation_time(duration - warmup)
        self.results = collector.compute()
        
        if verbose:
            print(f"\n  Completed: {self.results.total_completed} jobs")
            print(f"  Rejected: {self.results.total_rejected} jobs")
            print(f"  Rejection rate: {self.results.rejection_rate:.2%}")
            print(f"  Mean sojourn: {self.results.mean_sojourn_time:.2f}")
        
        return self.results
    
    def _arrival_process(self, env, arrivals, queue, rate_func, warmup):
        """Non-homogeneous arrival process."""
        gen = arrivals.generate()
        
        while True:
            try:
                result = next(gen)
                if isinstance(result, simpy.Event):
                    yield result
                    continue
                
                job = result
                
                # Log current rate
                if env.now >= warmup:
                    current_rate = rate_func(env.now)
                    self._arrival_rate_log.append((env.now, current_rate))
                
                # Try to enqueue
                if not queue.enqueue(job):
                    job.status = JobStatus.REJECTED
                    
            except StopIteration:
                break
    
    def _server_process(self, env, queue, servers, collector, warmup):
        """Multi-server process."""
        while True:
            if queue.is_empty:
                yield env.timeout(0.01)
                continue
            
            # Find idle server
            idle_server = None
            for server in servers:
                if not server.is_busy:
                    idle_server = server
                    break
            
            if idle_server is None:
                yield env.timeout(0.01)
                continue
            
            job = queue.dequeue()
            if job is None:
                yield env.timeout(0.01)
                continue
            
            # Process
            yield from idle_server.process(job)
            job.departure_time = env.now
            
            if job.arrival_time >= warmup:
                collector.record_job(job)
    
    def _monitor(self, env, queue, collector, rate_func, warmup, interval=1.0):
        """Monitor queue and rate."""
        while True:
            yield env.timeout(interval)
            
            if env.now >= warmup:
                collector.record_queue_length(env.now, len(queue))
    
    def get_rate_log(self) -> List[tuple[float, float]]:
        """Get logged arrival rates over time."""
        return self._arrival_rate_log.copy()


def run_daily_simulation(
    duration_hours: float = 24.0,
    seed: int = 42
) -> SimulationResults:
    """Run a full day simulation with realistic arrival pattern."""
    config = AdvancedConfig(
        pattern="daily",
        simulation_hours=duration_hours,
        warmup_hours=1.0,
        seed=seed
    )
    
    sim = AdvancedSimulation(config)
    return sim.run()


def analyze_peak_behavior(
    peak_rates: List[float] = [20, 30, 40, 50, 60],
    n_runs: int = 3
) -> Dict[str, Any]:
    """
    Analyze system behavior under different peak loads.
    
    Useful for capacity planning around deadlines.
    """
    results = []
    
    print("\nPEAK BEHAVIOR ANALYSIS")
    print("=" * 50)
    
    for peak in peak_rates:
        run_results = []
        
        for run in range(n_runs):
            config = AdvancedConfig(
                pattern="daily",
                peak_rate=peak,
                simulation_hours=24.0,
                seed=42 + run
            )
            sim = AdvancedSimulation(config)
            r = sim.run(verbose=False)
            run_results.append({
                "rejection_rate": r.rejection_rate,
                "mean_sojourn": r.mean_sojourn_time,
                "p95_sojourn": r.p95_sojourn_time,
            })
        
        avg = {
            "peak_rate": peak,
            "rejection_rate": np.mean([r["rejection_rate"] for r in run_results]),
            "mean_sojourn": np.mean([r["mean_sojourn"] for r in run_results]),
            "p95_sojourn": np.mean([r["p95_sojourn"] for r in run_results]),
        }
        results.append(avg)
        
        status = "✓" if avg["rejection_rate"] < 0.05 else "⚠" if avg["rejection_rate"] < 0.1 else "✗"
        print(f"Peak λ={peak:>3}: Reject={avg['rejection_rate']:.1%}, "
              f"W={avg['mean_sojourn']:.1f}, P95={avg['p95_sojourn']:.1f} {status}")
    
    return {"peak_analysis": results}
