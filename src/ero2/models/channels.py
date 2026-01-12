"""
Channels and Dams Model - Heterogeneous Populations.

This models the moulinette with two distinct user populations:
- STANDARD: Frequent arrivals, short jobs
- COMPLEX: Rare arrivals, long jobs

Key features:
- Different arrival rates and service times per population
- Blocking mechanism (Dam) to regulate STANDARD access
- SJF and dedicated lanes optimization
- Fairness analysis between populations
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import simpy
import numpy as np

from ..core.job import Job, JobStatus, Population
from ..core.queue import Queue, Server, ServerPool, QueueDiscipline
from ..core.arrivals import PoissonArrivals
from ..core.metrics import MetricsCollector, SimulationResults


class RegulationPolicy(Enum):
    """Regulation policy for managing populations."""
    NONE = "none"              # No regulation, everyone equal
    DAM = "dam"                # Block STANDARD periodically
    SJF = "sjf"                # Shortest Job First
    DEDICATED = "dedicated"    # Dedicated servers per population


@dataclass
class PopulationConfig:
    """Configuration for a population type."""
    name: str
    arrival_rate: float      # λ
    service_rate: float      # μ (1/mean_service_time)
    population: Population


@dataclass
class ChannelsConfig:
    """Configuration for Channels simulation."""
    # Population configs
    standard_arrival_rate: float = 2.0      # λ_STANDARD: high frequency
    standard_service_rate: float = 1.0      # μ_STANDARD: short jobs
    complex_arrival_rate: float = 0.5    # λ_COMPLEX: low frequency  
    complex_service_rate: float = 0.2    # μ_COMPLEX: long jobs
    
    # Server config
    num_servers: int = 4
    queue_capacity: int = 20
    
    # Regulation
    regulation: RegulationPolicy = RegulationPolicy.NONE
    
    # Dam-specific config
    dam_block_time: float = 10.0       # t_b: STANDARD blocked for t_b
    dam_open_time: float = 5.0         # STANDARD open for t_b/2
    
    # Dedicated-specific config
    standard_dedicated_servers: int = 1     # Servers reserved for STANDARD
    
    # Simulation
    simulation_time: float = 10000
    warmup_time: float = 1000
    seed: Optional[int] = None


@dataclass 
class ChannelsResults:
    """Results specific to Channels model."""
    base_results: SimulationResults
    
    # Per-population metrics
    standard_count: int = 0
    complex_count: int = 0
    standard_mean_sojourn: float = 0.0
    complex_mean_sojourn: float = 0.0
    standard_p95_sojourn: float = 0.0
    complex_p95_sojourn: float = 0.0
    
    # Fairness metrics
    sojourn_ratio: float = 0.0  # STANDARD/COMPLEX sojourn time ratio
    
    # Dam-specific
    standard_blocked_arrivals: int = 0


class ChannelsSimulation:
    """
    Channels and Dams simulation with heterogeneous populations.
    
    Models STANDARD (frequent, short) vs COMPLEX (rare, long) student populations.
    """
    
    def __init__(self, config: ChannelsConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.results: Optional[ChannelsResults] = None
        
        # Tracking
        self._standard_jobs: List[Job] = []
        self._complex_jobs: List[Job] = []
        self._blocked_arrivals: int = 0
        self._dam_is_open: bool = True
    
    def run(self, verbose: bool = True) -> ChannelsResults:
        """Run the Channels simulation."""
        
        env = simpy.Environment()
        
        # Create queue based on regulation policy
        if self.config.regulation == RegulationPolicy.SJF:
            discipline = QueueDiscipline.SJF
        else:
            discipline = QueueDiscipline.FIFO
        
        queue = Queue(
            env,
            capacity=self.config.queue_capacity,
            discipline=discipline,
            name="main_queue"
        )
        
        # Create servers
        if self.config.regulation == RegulationPolicy.DEDICATED:
            standard_pool = ServerPool(
                env, 
                self.config.standard_dedicated_servers,
                (self.config.standard_service_rate + self.config.complex_service_rate) / 2,
                "standard_servers"
            )
            shared_pool = ServerPool(
                env,
                self.config.num_servers - self.config.standard_dedicated_servers,
                (self.config.standard_service_rate + self.config.complex_service_rate) / 2,
                "shared_servers"
            )
        else:
            standard_pool = None
            shared_pool = ServerPool(
                env,
                self.config.num_servers,
                (self.config.standard_service_rate + self.config.complex_service_rate) / 2,
                "servers"
            )
        
        # Metrics
        collector = MetricsCollector(
            model_name=f"Channels ({self.config.regulation.value})",
            arrival_rate=self.config.standard_arrival_rate + self.config.complex_arrival_rate,
            service_rate=self.config.standard_service_rate  # Approximate
        )
        
        # Reset tracking
        self._standard_jobs = []
        self._complex_jobs = []
        self._blocked_arrivals = 0
        self._dam_is_open = True
        
        # Create STANDARD arrivals
        standard_arrivals = PoissonArrivals(
            env,
            self.config.standard_arrival_rate,
            self.config.standard_service_rate,
            population=Population.STANDARD,
            rng=np.random.default_rng(self.config.seed)
        )
        
        # Create COMPLEX arrivals
        complex_arrivals = PoissonArrivals(
            env,
            self.config.complex_arrival_rate,
            self.config.complex_service_rate,
            population=Population.COMPLEX,
            rng=np.random.default_rng((self.config.seed or 0) + 1000)
        )
        
        # Start processes
        env.process(self._arrival_process(env, standard_arrivals, queue, Population.STANDARD))
        env.process(self._arrival_process(env, complex_arrivals, queue, Population.COMPLEX))
        
        if self.config.regulation == RegulationPolicy.DAM:
            env.process(self._dam_controller(env))
        
        if self.config.regulation == RegulationPolicy.DEDICATED:
            env.process(self._dedicated_server_process(env, queue, standard_pool, shared_pool, collector))
        else:
            env.process(self._server_process(env, queue, shared_pool, collector))
        
        env.process(self._monitor(env, queue, collector))
        
        if verbose:
            print(f"Running Channels simulation ({self.config.regulation.value})...")
            print(f"  STANDARD: λ={self.config.standard_arrival_rate}, μ={self.config.standard_service_rate}")
            print(f"  COMPLEX: λ={self.config.complex_arrival_rate}, μ={self.config.complex_service_rate}")
            print(f"  Servers: {self.config.num_servers}")
        
        # Run
        env.run(until=self.config.simulation_time)
        
        # Compile results
        collector.set_simulation_time(self.config.simulation_time - self.config.warmup_time)
        base = collector.compute()
        
        # Per-population analysis
        standard_sojourns = [j.sojourn_time for j in self._standard_jobs if j.sojourn_time]
        complex_sojourns = [j.sojourn_time for j in self._complex_jobs if j.sojourn_time]
        
        self.results = ChannelsResults(
            base_results=base,
            standard_count=len(self._standard_jobs),
            complex_count=len(self._complex_jobs),
            standard_mean_sojourn=np.mean(standard_sojourns) if standard_sojourns else 0,
            complex_mean_sojourn=np.mean(complex_sojourns) if complex_sojourns else 0,
            standard_p95_sojourn=np.percentile(standard_sojourns, 95) if standard_sojourns else 0,
            complex_p95_sojourn=np.percentile(complex_sojourns, 95) if complex_sojourns else 0,
            standard_blocked_arrivals=self._blocked_arrivals
        )
        
        if self.results.complex_mean_sojourn > 0:
            self.results.sojourn_ratio = self.results.standard_mean_sojourn / self.results.complex_mean_sojourn
        
        if verbose:
            print(f"\n  STANDARD: n={self.results.standard_count}, W={self.results.standard_mean_sojourn:.2f}")
            print(f"  COMPLEX: n={self.results.complex_count}, W={self.results.complex_mean_sojourn:.2f}")
            print(f"  Ratio (STANDARD/COMPLEX): {self.results.sojourn_ratio:.2f}")
            if self.config.regulation == RegulationPolicy.DAM:
                print(f"  STANDARD blocked arrivals: {self._blocked_arrivals}")
        
        return self.results
    
    def _arrival_process(self, env, arrivals, queue, population):
        """Handle arrivals for a population."""
        gen = arrivals.generate()
        
        while True:
            yield next(gen)
            job = next(gen)
            
            # Check if blocked by Dam (STANDARD only)
            if population == Population.STANDARD and self.config.regulation == RegulationPolicy.DAM:
                if not self._dam_is_open:
                    if env.now >= self.config.warmup_time:
                        self._blocked_arrivals += 1
                    continue  # Skip this arrival
            
            if queue.enqueue(job):
                pass  # Successfully queued
            else:
                job.status = JobStatus.REJECTED
    
    def _dam_controller(self, env):
        """Control Dam opening/closing for STANDARD regulation."""
        while True:
            # Open period
            self._dam_is_open = True
            yield env.timeout(self.config.dam_open_time)
            
            # Closed period
            self._dam_is_open = False
            yield env.timeout(self.config.dam_block_time)
    
    def _server_process(self, env, queue, server_pool, collector):
        """Generic server process."""
        while True:
            if queue.is_empty or server_pool.num_idle == 0:
                yield env.timeout(0.01)
                continue
            
            job = queue.dequeue()
            if job is None:
                yield env.timeout(0.01)
                continue
            
            server = server_pool.get_idle_server()
            if server is None:
                queue.enqueue(job)
                yield env.timeout(0.01)
                continue
            
            # Process
            yield from server.process(job)
            job.departure_time = env.now
            job.status = JobStatus.COMPLETED
            
            if job.arrival_time >= self.config.warmup_time:
                collector.record_job(job)
                if job.population == Population.STANDARD:
                    self._standard_jobs.append(job)
                else:
                    self._complex_jobs.append(job)
    
    def _dedicated_server_process(self, env, queue, standard_pool, shared_pool, collector):
        """Process with dedicated servers for STANDARD."""
        while True:
            if queue.is_empty:
                yield env.timeout(0.01)
                continue
            
            job = queue.peek()
            if job is None:
                yield env.timeout(0.01)
                continue
            
            # STANDARD can use dedicated or shared servers
            if job.population == Population.STANDARD:
                server = standard_pool.get_idle_server()
                if server is None:
                    server = shared_pool.get_idle_server()
            else:
                # COMPLEX can only use shared servers
                server = shared_pool.get_idle_server()
            
            if server is None:
                yield env.timeout(0.01)
                continue
            
            job = queue.dequeue()
            yield from server.process(job)
            job.departure_time = env.now
            job.status = JobStatus.COMPLETED
            
            if job.arrival_time >= self.config.warmup_time:
                collector.record_job(job)
                if job.population == Population.STANDARD:
                    self._standard_jobs.append(job)
                else:
                    self._complex_jobs.append(job)
    
    def _monitor(self, env, queue, collector, interval=1.0):
        """Monitor queue length."""
        while True:
            yield env.timeout(interval)
            if env.now >= self.config.warmup_time:
                collector.record_queue_length(env.now, len(queue))


def run_channels(
    regulation: str = "none",
    duration: float = 10000,
    seed: int = 42
) -> ChannelsResults:
    """
    Convenience function to run Channels simulation.
    
    Args:
        regulation: "none", "dam", "sjf", or "dedicated"
        duration: Simulation time
        seed: Random seed
    """
    policy = RegulationPolicy(regulation)
    
    config = ChannelsConfig(
        regulation=policy,
        simulation_time=duration,
        warmup_time=duration * 0.1,
        seed=seed
    )
    
    sim = ChannelsSimulation(config)
    return sim.run()


def compare_regulations(
    n_runs: int = 5,
    duration: float = 5000
) -> Dict[str, Dict[str, float]]:
    """
    Compare all regulation policies.
    
    Returns metrics for each policy.
    """
    policies = [
        RegulationPolicy.NONE,
        RegulationPolicy.DAM,
        RegulationPolicy.SJF,
        RegulationPolicy.DEDICATED
    ]
    
    results = {}
    
    for policy in policies:
        print(f"\n{'='*40}")
        print(f"Testing {policy.value}...")
        
        run_metrics = []
        for i in range(n_runs):
            config = ChannelsConfig(
                regulation=policy,
                simulation_time=duration,
                warmup_time=duration * 0.1,
                seed=42 + i
            )
            sim = ChannelsSimulation(config)
            r = sim.run(verbose=False)
            run_metrics.append({
                "standard_sojourn": r.standard_mean_sojourn,
                "complex_sojourn": r.complex_mean_sojourn,
                "total_sojourn": r.base_results.mean_sojourn_time,
                "ratio": r.sojourn_ratio in [float('inf'), float('nan')] and r.sojourn_ratio or r.sojourn_ratio
            })
        
        results[policy.value] = {
            "standard_mean": np.mean([m["standard_sojourn"] for m in run_metrics]),
            "complex_mean": np.mean([m["complex_sojourn"] for m in run_metrics]),
            "total_mean": np.mean([m["total_sojourn"] for m in run_metrics]),
            "ratio_mean": np.mean([m["ratio"] for m in run_metrics if m["ratio"] not in [float('inf'), float('nan')]])
        }
        
        print(f"  STANDARD: {results[policy.value]['standard_mean']:.2f}")
        print(f"  COMPLEX: {results[policy.value]['complex_mean']:.2f}")
        print(f"  Ratio: {results[policy.value]['ratio_mean']:.2f}")
    
    return results
