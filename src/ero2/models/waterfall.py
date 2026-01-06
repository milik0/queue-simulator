"""
Waterfall Model - Tandem Queue Simulation.

This models the moulinette's two-stage processing:
1. Execution stage: K servers process the submitted code
2. Return stage: 1 server sends results back to students

Key features:
- Tandem (series) queues
- Finite capacity at each stage
- Backup system before return stage
- Analysis of "page blanche" (empty result) phenomenon
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import simpy
import numpy as np

from ..core.job import Job, JobStatus, Population
from ..core.queue import Queue, Server, ServerPool, QueueDiscipline
from ..core.arrivals import PoissonArrivals
from ..core.metrics import MetricsCollector, SimulationResults


class RejectionType(Enum):
    """Type of rejection in Waterfall model."""
    EXECUTION_QUEUE_FULL = "execution_full"  # Error message to student
    RETURN_QUEUE_FULL = "return_full"         # "Page blanche" if no backup
    NONE = "none"


@dataclass
class WaterfallConfig:
    """Configuration for Waterfall simulation."""
    # Arrival parameters
    arrival_rate: float        # λ
    
    # Execution stage
    num_exec_servers: int      # K (nombre de serveurs d'exécution)
    exec_service_rate: float   # μ₁ (taux de service exécution)
    exec_queue_capacity: int   # k_s (capacité file exécution)
    
    # Return stage
    return_service_rate: float  # μ₂ (taux de service renvoi)
    return_queue_capacity: int  # k_f (capacité file renvoi)
    
    # Backup options
    enable_backup: bool = False
    backup_probability: float = 1.0  # 1.0 = systematic, <1.0 = random
    
    # Simulation
    simulation_time: float = 10000
    warmup_time: float = 1000
    seed: Optional[int] = None


@dataclass
class WaterfallResults:
    """Results specific to Waterfall model."""
    base_results: SimulationResults
    
    # Stage-specific metrics
    exec_rejections: int = 0
    return_rejections: int = 0  # "Pages blanches" without backup
    backed_up_jobs: int = 0
    backup_recoveries: int = 0
    
    # Rates
    exec_rejection_rate: float = 0.0
    page_blanche_rate: float = 0.0
    
    # Times
    mean_exec_time: float = 0.0
    mean_return_time: float = 0.0
    mean_total_time: float = 0.0


class WaterfallSimulation:
    """
    Waterfall (Tandem) Queue Simulation.
    
    Models the two-stage moulinette:
    
        [Push Tag] → [Exec Queue (k_s)] → [K Servers] → 
                     [Return Queue (k_f)] → [1 Server] → [Result]
    
    With optional backup between execution and return.
    """
    
    def __init__(self, config: WaterfallConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.results: Optional[WaterfallResults] = None
        
        # Tracking
        self._exec_rejections: List[Job] = []
        self._return_rejections: List[Job] = []
        self._backed_up: List[Job] = []
        self._completed: List[Job] = []
    
    def run(self, verbose: bool = True) -> WaterfallResults:
        """Run the Waterfall simulation."""
        
        env = simpy.Environment()
        
        # Create execution stage
        exec_queue = Queue(
            env,
            capacity=self.config.exec_queue_capacity,
            name="exec_queue"
        )
        exec_pool = ServerPool(
            env,
            num_servers=self.config.num_exec_servers,
            service_rate=self.config.exec_service_rate,
            name="exec_servers"
        )
        
        # Create return stage
        return_queue = Queue(
            env,
            capacity=self.config.return_queue_capacity,
            name="return_queue"
        )
        return_server = Server(
            env,
            service_rate=self.config.return_service_rate,
            name="return_server"
        )
        
        # Metrics
        collector = MetricsCollector(
            model_name="Waterfall",
            arrival_rate=self.config.arrival_rate,
            service_rate=self.config.exec_service_rate
        )
        
        # Reset tracking
        self._exec_rejections = []
        self._return_rejections = []
        self._backed_up = []
        self._completed = []
        
        # Create arrivals
        arrivals = PoissonArrivals(
            env,
            self.config.arrival_rate,
            self.config.exec_service_rate,
            rng=self.rng
        )
        
        # Start processes
        env.process(self._arrival_process(env, arrivals, exec_queue))
        env.process(self._exec_process(env, exec_queue, exec_pool, return_queue))
        env.process(self._return_process(env, return_queue, return_server, collector))
        env.process(self._monitor(env, exec_queue, return_queue, collector))
        
        if verbose:
            print("Running Waterfall simulation...")
            print(f"  λ={self.config.arrival_rate}")
            print(f"  Exec: K={self.config.num_exec_servers}, μ₁={self.config.exec_service_rate}, k_s={self.config.exec_queue_capacity}")
            print(f"  Return: μ₂={self.config.return_service_rate}, k_f={self.config.return_queue_capacity}")
            print(f"  Backup: {'enabled' if self.config.enable_backup else 'disabled'}")
        
        # Run
        env.run(until=self.config.simulation_time)
        
        # Compile results
        collector.set_simulation_time(self.config.simulation_time - self.config.warmup_time)
        base = collector.compute()
        
        total_arrivals = len(self._completed) + len(self._exec_rejections) + len(self._return_rejections)
        
        self.results = WaterfallResults(
            base_results=base,
            exec_rejections=len(self._exec_rejections),
            return_rejections=len(self._return_rejections),
            backed_up_jobs=len(self._backed_up),
            exec_rejection_rate=len(self._exec_rejections) / total_arrivals if total_arrivals > 0 else 0,
            page_blanche_rate=len(self._return_rejections) / total_arrivals if total_arrivals > 0 else 0,
        )
        
        if verbose:
            print(f"\n  Total arrivals: {total_arrivals}")
            print(f"  Completed: {len(self._completed)}")
            print(f"  Exec rejections: {len(self._exec_rejections)} ({self.results.exec_rejection_rate:.2%})")
            print(f"  Pages blanches: {len(self._return_rejections)} ({self.results.page_blanche_rate:.2%})")
            if self.config.enable_backup:
                print(f"  Backed up: {len(self._backed_up)}")
        
        return self.results
    
    def _arrival_process(self, env, arrivals, exec_queue):
        """Handle arrivals to execution queue."""
        gen = arrivals.generate()
        
        while True:
            yield next(gen)
            job = next(gen)
            job.stage = 1
            
            if not exec_queue.enqueue(job):
                # Rejected at execution stage - student gets error message
                job.status = JobStatus.REJECTED
                if env.now >= self.config.warmup_time:
                    self._exec_rejections.append(job)
    
    def _exec_process(self, env, exec_queue, exec_pool, return_queue):
        """Process jobs through execution servers."""
        while True:
            if exec_queue.is_empty or exec_pool.num_idle == 0:
                yield env.timeout(0.01)
                continue
            
            job = exec_queue.dequeue()
            if job is None:
                yield env.timeout(0.01)
                continue
            
            server = exec_pool.get_idle_server()
            if server is None:
                # Put back in queue
                exec_queue.enqueue(job)
                yield env.timeout(0.01)
                continue
            
            # Process
            yield from server.process(job)
            job.stage = 2
            
            # Try to send to return queue
            if self.config.enable_backup:
                # Backup before attempting return queue
                job.backed_up = True
                if env.now >= self.config.warmup_time:
                    if self.rng.random() < self.config.backup_probability:
                        self._backed_up.append(job)
            
            if not return_queue.enqueue(job):
                # Return queue full - potential "page blanche"
                if not job.backed_up:
                    job.status = JobStatus.REJECTED
                    if env.now >= self.config.warmup_time:
                        self._return_rejections.append(job)
                # If backed up, job can be retried (simplified: just drop from return)
    
    def _return_process(self, env, return_queue, return_server, collector):
        """Process jobs through return server."""
        while True:
            if return_queue.is_empty or return_server.is_busy:
                yield env.timeout(0.01)
                continue
            
            job = return_queue.dequeue()
            if job is None:
                yield env.timeout(0.01)
                continue
            
            # Generate return service time
            return_time = self.rng.exponential(1.0 / self.config.return_service_rate)
            job.service_time = return_time  # Override for return stage
            
            yield from return_server.process(job)
            job.departure_time = env.now
            job.status = JobStatus.COMPLETED
            
            if job.arrival_time >= self.config.warmup_time:
                collector.record_job(job)
                self._completed.append(job)
    
    def _monitor(self, env, exec_queue, return_queue, collector, interval=1.0):
        """Monitor queue lengths."""
        while True:
            yield env.timeout(interval)
            
            if env.now >= self.config.warmup_time:
                # Record total queue length
                total_length = len(exec_queue) + len(return_queue)
                collector.record_queue_length(env.now, total_length)


def run_waterfall(
    arrival_rate: float = 0.8,
    num_exec_servers: int = 4,
    exec_service_rate: float = 0.3,  # μ₁ so K*μ₁ > λ
    exec_queue_capacity: int = 10,
    return_service_rate: float = 1.0,  # μ₂
    return_queue_capacity: int = 5,
    enable_backup: bool = True,
    duration: float = 10000,
    seed: int = 42
) -> WaterfallResults:
    """
    Convenience function to run Waterfall simulation.
    
    Default parameters model:
    - 4 execution servers
    - Moderate queue sizes
    - Backup enabled
    """
    config = WaterfallConfig(
        arrival_rate=arrival_rate,
        num_exec_servers=num_exec_servers,
        exec_service_rate=exec_service_rate,
        exec_queue_capacity=exec_queue_capacity,
        return_service_rate=return_service_rate,
        return_queue_capacity=return_queue_capacity,
        enable_backup=enable_backup,
        simulation_time=duration,
        warmup_time=duration * 0.1,
        seed=seed
    )
    
    sim = WaterfallSimulation(config)
    return sim.run()


def analyze_backup_impact(
    base_config: WaterfallConfig,
    n_runs: int = 5
) -> Dict[str, Any]:
    """
    Compare systematic vs random vs no backup.
    
    Returns comparison metrics for each strategy.
    """
    strategies = [
        ("no_backup", False, 0.0),
        ("random_50%", True, 0.5),
        ("systematic", True, 1.0),
    ]
    
    results = {}
    
    for name, enabled, prob in strategies:
        config = WaterfallConfig(
            arrival_rate=base_config.arrival_rate,
            num_exec_servers=base_config.num_exec_servers,
            exec_service_rate=base_config.exec_service_rate,
            exec_queue_capacity=base_config.exec_queue_capacity,
            return_service_rate=base_config.return_service_rate,
            return_queue_capacity=base_config.return_queue_capacity,
            enable_backup=enabled,
            backup_probability=prob,
            simulation_time=base_config.simulation_time,
            warmup_time=base_config.warmup_time
        )
        
        run_results = []
        for i in range(n_runs):
            config.seed = 42 + i
            sim = WaterfallSimulation(config)
            r = sim.run(verbose=False)
            run_results.append({
                "page_blanche_rate": r.page_blanche_rate,
                "exec_rejection_rate": r.exec_rejection_rate,
                "mean_sojourn_time": r.base_results.mean_sojourn_time
            })
        
        results[name] = {
            "page_blanche_rate": np.mean([r["page_blanche_rate"] for r in run_results]),
            "page_blanche_std": np.std([r["page_blanche_rate"] for r in run_results]),
            "mean_sojourn_time": np.mean([r["mean_sojourn_time"] for r in run_results]),
        }
        
        print(f"{name}: Page blanche = {results[name]['page_blanche_rate']:.2%}, "
              f"W = {results[name]['mean_sojourn_time']:.2f}")
    
    return results
