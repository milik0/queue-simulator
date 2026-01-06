"""
Channels and Dams Model - Heterogeneous Populations.

This models the moulinette with two distinct user populations:
- ING: Frequent arrivals, short jobs
- PREPA: Rare arrivals, long jobs

Key features:
- Different arrival rates and service times per population
- Blocking mechanism (Dam) to regulate ING access
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
    DAM = "dam"                # Block ING periodically
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
    ing_arrival_rate: float = 2.0      # λ_ING: high frequency
    ing_service_rate: float = 1.0      # μ_ING: short jobs
    prepa_arrival_rate: float = 0.5    # λ_PREPA: low frequency  
    prepa_service_rate: float = 0.2    # μ_PREPA: long jobs
    
    # Server config
    num_servers: int = 4
    queue_capacity: int = 20
    
    # Regulation
    regulation: RegulationPolicy = RegulationPolicy.NONE
    
    # Dam-specific config
    dam_block_time: float = 10.0       # t_b: ING blocked for t_b
    dam_open_time: float = 5.0         # ING open for t_b/2
    
    # Dedicated-specific config
    ing_dedicated_servers: int = 1     # Servers reserved for ING
    
    # Simulation
    simulation_time: float = 10000
    warmup_time: float = 1000
    seed: Optional[int] = None


@dataclass 
class ChannelsResults:
    """Results specific to Channels model."""
    base_results: SimulationResults
    
    # Per-population metrics
    ing_count: int = 0
    prepa_count: int = 0
    ing_mean_sojourn: float = 0.0
    prepa_mean_sojourn: float = 0.0
    ing_p95_sojourn: float = 0.0
    prepa_p95_sojourn: float = 0.0
    
    # Fairness metrics
    sojourn_ratio: float = 0.0  # ING/PREPA sojourn time ratio
    
    # Dam-specific
    ing_blocked_arrivals: int = 0


class ChannelsSimulation:
    """
    Channels and Dams simulation with heterogeneous populations.
    
    Models ING (frequent, short) vs PREPA (rare, long) student populations.
    """
    
    def __init__(self, config: ChannelsConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.results: Optional[ChannelsResults] = None
        
        # Tracking
        self._ing_jobs: List[Job] = []
        self._prepa_jobs: List[Job] = []
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
            ing_pool = ServerPool(
                env, 
                self.config.ing_dedicated_servers,
                (self.config.ing_service_rate + self.config.prepa_service_rate) / 2,
                "ing_servers"
            )
            shared_pool = ServerPool(
                env,
                self.config.num_servers - self.config.ing_dedicated_servers,
                (self.config.ing_service_rate + self.config.prepa_service_rate) / 2,
                "shared_servers"
            )
        else:
            ing_pool = None
            shared_pool = ServerPool(
                env,
                self.config.num_servers,
                (self.config.ing_service_rate + self.config.prepa_service_rate) / 2,
                "servers"
            )
        
        # Metrics
        collector = MetricsCollector(
            model_name=f"Channels ({self.config.regulation.value})",
            arrival_rate=self.config.ing_arrival_rate + self.config.prepa_arrival_rate,
            service_rate=self.config.ing_service_rate  # Approximate
        )
        
        # Reset tracking
        self._ing_jobs = []
        self._prepa_jobs = []
        self._blocked_arrivals = 0
        self._dam_is_open = True
        
        # Create ING arrivals
        ing_arrivals = PoissonArrivals(
            env,
            self.config.ing_arrival_rate,
            self.config.ing_service_rate,
            population=Population.ING,
            rng=np.random.default_rng(self.config.seed)
        )
        
        # Create PREPA arrivals
        prepa_arrivals = PoissonArrivals(
            env,
            self.config.prepa_arrival_rate,
            self.config.prepa_service_rate,
            population=Population.PREPA,
            rng=np.random.default_rng((self.config.seed or 0) + 1000)
        )
        
        # Start processes
        env.process(self._arrival_process(env, ing_arrivals, queue, Population.ING))
        env.process(self._arrival_process(env, prepa_arrivals, queue, Population.PREPA))
        
        if self.config.regulation == RegulationPolicy.DAM:
            env.process(self._dam_controller(env))
        
        if self.config.regulation == RegulationPolicy.DEDICATED:
            env.process(self._dedicated_server_process(env, queue, ing_pool, shared_pool, collector))
        else:
            env.process(self._server_process(env, queue, shared_pool, collector))
        
        env.process(self._monitor(env, queue, collector))
        
        if verbose:
            print(f"Running Channels simulation ({self.config.regulation.value})...")
            print(f"  ING: λ={self.config.ing_arrival_rate}, μ={self.config.ing_service_rate}")
            print(f"  PREPA: λ={self.config.prepa_arrival_rate}, μ={self.config.prepa_service_rate}")
            print(f"  Servers: {self.config.num_servers}")
        
        # Run
        env.run(until=self.config.simulation_time)
        
        # Compile results
        collector.set_simulation_time(self.config.simulation_time - self.config.warmup_time)
        base = collector.compute()
        
        # Per-population analysis
        ing_sojourns = [j.sojourn_time for j in self._ing_jobs if j.sojourn_time]
        prepa_sojourns = [j.sojourn_time for j in self._prepa_jobs if j.sojourn_time]
        
        self.results = ChannelsResults(
            base_results=base,
            ing_count=len(self._ing_jobs),
            prepa_count=len(self._prepa_jobs),
            ing_mean_sojourn=np.mean(ing_sojourns) if ing_sojourns else 0,
            prepa_mean_sojourn=np.mean(prepa_sojourns) if prepa_sojourns else 0,
            ing_p95_sojourn=np.percentile(ing_sojourns, 95) if ing_sojourns else 0,
            prepa_p95_sojourn=np.percentile(prepa_sojourns, 95) if prepa_sojourns else 0,
            ing_blocked_arrivals=self._blocked_arrivals
        )
        
        if self.results.prepa_mean_sojourn > 0:
            self.results.sojourn_ratio = self.results.ing_mean_sojourn / self.results.prepa_mean_sojourn
        
        if verbose:
            print(f"\n  ING: n={self.results.ing_count}, W={self.results.ing_mean_sojourn:.2f}")
            print(f"  PREPA: n={self.results.prepa_count}, W={self.results.prepa_mean_sojourn:.2f}")
            print(f"  Ratio (ING/PREPA): {self.results.sojourn_ratio:.2f}")
            if self.config.regulation == RegulationPolicy.DAM:
                print(f"  ING blocked arrivals: {self._blocked_arrivals}")
        
        return self.results
    
    def _arrival_process(self, env, arrivals, queue, population):
        """Handle arrivals for a population."""
        gen = arrivals.generate()
        
        while True:
            yield next(gen)
            job = next(gen)
            
            # Check if blocked by Dam (ING only)
            if population == Population.ING and self.config.regulation == RegulationPolicy.DAM:
                if not self._dam_is_open:
                    if env.now >= self.config.warmup_time:
                        self._blocked_arrivals += 1
                    continue  # Skip this arrival
            
            if queue.enqueue(job):
                pass  # Successfully queued
            else:
                job.status = JobStatus.REJECTED
    
    def _dam_controller(self, env):
        """Control Dam opening/closing for ING regulation."""
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
                if job.population == Population.ING:
                    self._ing_jobs.append(job)
                else:
                    self._prepa_jobs.append(job)
    
    def _dedicated_server_process(self, env, queue, ing_pool, shared_pool, collector):
        """Process with dedicated servers for ING."""
        while True:
            if queue.is_empty:
                yield env.timeout(0.01)
                continue
            
            job = queue.peek()
            if job is None:
                yield env.timeout(0.01)
                continue
            
            # ING can use dedicated or shared servers
            if job.population == Population.ING:
                server = ing_pool.get_idle_server()
                if server is None:
                    server = shared_pool.get_idle_server()
            else:
                # PREPA can only use shared servers
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
                if job.population == Population.ING:
                    self._ing_jobs.append(job)
                else:
                    self._prepa_jobs.append(job)
    
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
                "ing_sojourn": r.ing_mean_sojourn,
                "prepa_sojourn": r.prepa_mean_sojourn,
                "total_sojourn": r.base_results.mean_sojourn_time,
                "ratio": r.sojourn_ratio in [float('inf'), float('nan')] and r.sojourn_ratio or r.sojourn_ratio
            })
        
        results[policy.value] = {
            "ing_mean": np.mean([m["ing_sojourn"] for m in run_metrics]),
            "prepa_mean": np.mean([m["prepa_sojourn"] for m in run_metrics]),
            "total_mean": np.mean([m["total_sojourn"] for m in run_metrics]),
            "ratio_mean": np.mean([m["ratio"] for m in run_metrics if m["ratio"] not in [float('inf'), float('nan')]])
        }
        
        print(f"  ING: {results[policy.value]['ing_mean']:.2f}")
        print(f"  PREPA: {results[policy.value]['prepa_mean']:.2f}")
        print(f"  Ratio: {results[policy.value]['ratio_mean']:.2f}")
    
    return results
