from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import simpy
import numpy as np

from ..core.job import Job, JobStatus, Population
from ..core.queue import Queue, Server, ServerPool, QueueDiscipline
from ..core.arrivals import PoissonArrivals
from ..core.metrics import MetricsCollector, SimulationResults


@dataclass
class ScenarioConfig:
    """Configuration for a simulation scenario."""
    name: str
    arrival_rate: float      # λ (jobs per time unit)
    service_rate: float      # μ (1/mean_service_time)
    num_students: int        # For reference
    description: str


# Pre-defined ING1 scenarios
ATELIER_CONFIG = ScenarioConfig(
    name="ATELIER",
    arrival_rate=2.0,        # Many submissions per time unit
    service_rate=1.0,        # Short jobs (quick tests)
    num_students=800,
    description="TP avec beaucoup d'exercices, 800 étudiants, soumissions fréquentes"
)

PROJET_CONFIG = ScenarioConfig(
    name="PROJET", 
    arrival_rate=0.3,        # ~1 submission per week per group
    service_rate=0.2,        # Long testsuites (5x longer than Atelier)
    num_students=200,        # ~200 groups (4 students per group)
    description="Projet en groupe, soumissions rares mais lourdes, pic samedi soir"
)


@dataclass
class ScenariosConfig:
    """Configuration for ING1 scenarios simulation."""
    # Scenario parameters  
    atelier_arrival_rate: float = 2.0      # λ_ATELIER: high frequency
    atelier_service_rate: float = 1.0      # μ_ATELIER: short jobs
    projet_arrival_rate: float = 0.3       # λ_PROJET: low frequency
    projet_service_rate: float = 0.2       # μ_PROJET: long testsuites
    
    # Server config
    num_servers: int = 4
    queue_capacity: int = 20
    
    # Simulation
    simulation_time: float = 10000
    warmup_time: float = 1000
    seed: Optional[int] = None
    
    # Which scenario to simulate (None = both)
    scenario: Optional[str] = None  # "atelier", "projet", or None for both


@dataclass 
class ScenariosResults:
    """Results for ING1 scenarios simulation."""
    base_results: SimulationResults
    
    # Per-scenario metrics
    atelier_count: int = 0
    projet_count: int = 0
    atelier_mean_sojourn: float = 0.0
    projet_mean_sojourn: float = 0.0
    atelier_p95_sojourn: float = 0.0
    projet_p95_sojourn: float = 0.0
    
    # Page blanche (result lost when return queue full)
    page_blanche_count: int = 0
    page_blanche_rate: float = 0.0


class ScenariosSimulation:
    """
    ING1 Scenarios Simulation.
    
    Models two types of ING1 usage:
    - ATELIER: TP period, 800 students, many small submissions daily
    - PROJET: Project period, groups, 1 heavy submission per week
    
    The simulation helps identify optimal configuration for each scenario.
    """
    
    def __init__(self, config: ScenariosConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.results: Optional[ScenariosResults] = None
        
        # Tracking
        self._atelier_jobs: List[Job] = []
        self._projet_jobs: List[Job] = []
    
    def run(self, verbose: bool = True) -> ScenariosResults:
        """Run the scenarios simulation."""
        
        env = simpy.Environment()
        
        queue = Queue(
            env,
            capacity=self.config.queue_capacity,
            discipline=QueueDiscipline.FIFO,
            name="main_queue"
        )
        
        server_pool = ServerPool(
            env,
            self.config.num_servers,
            (self.config.atelier_service_rate + self.config.projet_service_rate) / 2,
            "servers"
        )
        
        # Metrics
        collector = MetricsCollector(
            model_name="ING1 Scenarios",
            arrival_rate=self.config.atelier_arrival_rate + self.config.projet_arrival_rate,
            service_rate=self.config.atelier_service_rate
        )
        
        # Reset tracking
        self._atelier_jobs = []
        self._projet_jobs = []
        
        # Create arrivals based on scenario config
        if self.config.scenario is None or self.config.scenario == "atelier":
            atelier_arrivals = PoissonArrivals(
                env,
                self.config.atelier_arrival_rate,
                self.config.atelier_service_rate,
                population=Population.ATELIER,
                rng=np.random.default_rng(self.config.seed)
            )
            env.process(self._arrival_process(env, atelier_arrivals, queue, Population.ATELIER))
        
        if self.config.scenario is None or self.config.scenario == "projet":
            projet_arrivals = PoissonArrivals(
                env,
                self.config.projet_arrival_rate,
                self.config.projet_service_rate,
                population=Population.PROJET,
                rng=np.random.default_rng((self.config.seed or 0) + 1000)
            )
            env.process(self._arrival_process(env, projet_arrivals, queue, Population.PROJET))
        
        env.process(self._server_process(env, queue, server_pool, collector))
        env.process(self._monitor(env, queue, collector))
        
        if verbose:
            print(f"Running ING1 Scenarios simulation...")
            if self.config.scenario is None or self.config.scenario == "atelier":
                print(f"  ATELIER: λ={self.config.atelier_arrival_rate}, μ={self.config.atelier_service_rate}")
            if self.config.scenario is None or self.config.scenario == "projet":
                print(f"  PROJET: λ={self.config.projet_arrival_rate}, μ={self.config.projet_service_rate}")
            print(f"  Servers: {self.config.num_servers}")
        
        # Run
        env.run(until=self.config.simulation_time)
        
        # Compile results
        collector.set_simulation_time(self.config.simulation_time - self.config.warmup_time)
        base = collector.compute()
        
        # Per-scenario analysis
        atelier_sojourns = [j.sojourn_time for j in self._atelier_jobs if j.sojourn_time]
        projet_sojourns = [j.sojourn_time for j in self._projet_jobs if j.sojourn_time]
        
        self.results = ScenariosResults(
            base_results=base,
            atelier_count=len(self._atelier_jobs),
            projet_count=len(self._projet_jobs),
            atelier_mean_sojourn=np.mean(atelier_sojourns) if atelier_sojourns else 0,
            projet_mean_sojourn=np.mean(projet_sojourns) if projet_sojourns else 0,
            atelier_p95_sojourn=np.percentile(atelier_sojourns, 95) if atelier_sojourns else 0,
            projet_p95_sojourn=np.percentile(projet_sojourns, 95) if projet_sojourns else 0,
        )
        
        if verbose:
            print(f"\n  ATELIER: n={self.results.atelier_count}, W={self.results.atelier_mean_sojourn:.2f}")
            print(f"  PROJET: n={self.results.projet_count}, W={self.results.projet_mean_sojourn:.2f}")
        
        return self.results
    
    def _arrival_process(self, env, arrivals, queue, population):
        """Handle arrivals for a scenario."""
        gen = arrivals.generate()
        
        while True:
            yield next(gen)
            job = next(gen)
            
            if queue.enqueue(job):
                pass  # Successfully queued
            else:
                job.status = JobStatus.REJECTED
    
    def _server_process(self, env, queue, server_pool, collector):
        """Process jobs through servers."""
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
                if job.population == Population.ATELIER:
                    self._atelier_jobs.append(job)
                else:
                    self._projet_jobs.append(job)
    
    def _monitor(self, env, queue, collector, interval=1.0):
        """Monitor queue length."""
        while True:
            yield env.timeout(interval)
            if env.now >= self.config.warmup_time:
                collector.record_queue_length(env.now, len(queue))


def run_atelier(
    arrival_rate: float = 2.0,
    service_rate: float = 1.0,
    num_servers: int = 4,
    duration: float = 10000,
    seed: int = 42
) -> ScenariosResults:
    """
    Run ATELIER scenario simulation.
    
    Simulates TP period: 800 students, many frequent small submissions.
    """
    config = ScenariosConfig(
        atelier_arrival_rate=arrival_rate,
        atelier_service_rate=service_rate,
        num_servers=num_servers,
        simulation_time=duration,
        warmup_time=duration * 0.1,
        scenario="atelier",
        seed=seed
    )
    
    sim = ScenariosSimulation(config)
    return sim.run()


def run_projet(
    arrival_rate: float = 0.3,
    service_rate: float = 0.2,
    num_servers: int = 4,
    duration: float = 10000,
    seed: int = 42
) -> ScenariosResults:
    """
    Run PROJET scenario simulation.
    
    Simulates project period: groups, 1 submission/week, heavy testsuites.
    """
    config = ScenariosConfig(
        projet_arrival_rate=arrival_rate,
        projet_service_rate=service_rate,
        num_servers=num_servers,
        simulation_time=duration,
        warmup_time=duration * 0.1,
        scenario="projet",
        seed=seed
    )
    
    sim = ScenariosSimulation(config)
    return sim.run()


def compare_scenarios(
    n_runs: int = 5,
    duration: float = 5000
) -> Dict[str, Dict[str, float]]:
    """
    Compare ATELIER vs PROJET scenarios.
    
    Returns metrics for each scenario.
    """
    results = {}
    
    for scenario_name, arr_rate, svc_rate in [
        ("atelier", 2.0, 1.0),
        ("projet", 0.3, 0.2)
    ]:
        print(f"\n{'='*40}")
        print(f"Testing {scenario_name.upper()}...")
        
        run_metrics = []
        for i in range(n_runs):
            if scenario_name == "atelier":
                r = run_atelier(
                    arrival_rate=arr_rate,
                    service_rate=svc_rate,
                    duration=duration,
                    seed=42 + i
                )
                sojourn = r.atelier_mean_sojourn
            else:
                r = run_projet(
                    arrival_rate=arr_rate,
                    service_rate=svc_rate,
                    duration=duration,
                    seed=42 + i
                )
                sojourn = r.projet_mean_sojourn
            
            run_metrics.append({
                "sojourn": sojourn,
                "total_sojourn": r.base_results.mean_sojourn_time,
            })
        
        results[scenario_name] = {
            "mean_sojourn": np.mean([m["sojourn"] for m in run_metrics]),
            "total_mean": np.mean([m["total_sojourn"] for m in run_metrics]),
        }
        
        print(f"  Mean sojourn: {results[scenario_name]['mean_sojourn']:.2f}")
    
    return results


# =============================================================================
# CHANNELS & DAMS MODEL
# =============================================================================
# Modélise les populations hétérogènes (ING vs PREPA) avec régulation
# par blocage temporaire de la file ING.

@dataclass
class ChannelsDamsConfig:
    """Configuration pour le modèle Channels & Dams."""
    # ING population (arrivées fréquentes, jobs courts)
    ing_arrival_rate: float = 2.0
    ing_service_rate: float = 1.0
    
    # PREPA population (arrivées rares, jobs longs) 
    prepa_arrival_rate: float = 0.1
    prepa_service_rate: float = 0.1
    
    # Serveurs partagés
    num_servers: int = 4
    queue_capacity: int = 20
    
    # Régulation par blocage (t_b)
    regulation_enabled: bool = False
    block_duration: float = 10.0      # t_b: durée de blocage ING
    unblock_duration: float = 5.0     # t_b/2: durée d'ouverture
    
    # Simulation
    simulation_time: float = 10000
    warmup_time: float = 1000
    seed: Optional[int] = None


@dataclass
class ChannelsDamsResults:
    """Résultats du modèle Channels & Dams."""
    base_results: SimulationResults
    
    # Métriques par population
    ing_count: int = 0
    prepa_count: int = 0
    ing_mean_sojourn: float = 0.0
    prepa_mean_sojourn: float = 0.0
    ing_p95_sojourn: float = 0.0
    prepa_p95_sojourn: float = 0.0
    
    # Variance empirique (demandée dans le sujet)
    ing_var_sojourn: float = 0.0
    prepa_var_sojourn: float = 0.0
    
    # Rejets par population
    ing_rejection_rate: float = 0.0
    prepa_rejection_rate: float = 0.0
    
    # Disparité (ratio temps ING / temps PREPA)
    disparity_ratio: float = 0.0


class ChannelsDamsSimulation:
    """
    Simulation Channels & Dams.
    
    Modélise les populations hétérogènes avec :
    - ING: arrivées fréquentes, jobs courts
    - PREPA: arrivées rares mais jobs longs
    
    Avec option de régulation par blocage temporaire.
    """
    
    def __init__(self, config: ChannelsDamsConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self._ing_jobs: List[Job] = []
        self._prepa_jobs: List[Job] = []
        self._ing_rejected: List[Job] = []
        self._prepa_rejected: List[Job] = []
        self._ing_blocked = False
        
    def run(self, verbose: bool = True) -> ChannelsDamsResults:
        """Exécute la simulation Channels & Dams."""
        
        env = simpy.Environment()
        
        queue = Queue(
            env,
            capacity=self.config.queue_capacity,
            discipline=QueueDiscipline.FIFO,
            name="shared_queue"
        )
        
        # Service rate moyen pondéré
        avg_service_rate = (self.config.ing_service_rate + self.config.prepa_service_rate) / 2
        server_pool = ServerPool(
            env,
            self.config.num_servers,
            avg_service_rate,
            "servers"
        )
        
        collector = MetricsCollector(
            model_name="Channels & Dams",
            arrival_rate=self.config.ing_arrival_rate + self.config.prepa_arrival_rate,
            service_rate=avg_service_rate
        )
        
        # Reset
        self._ing_jobs = []
        self._prepa_jobs = []
        self._ing_rejected = []
        self._prepa_rejected = []
        self._ing_blocked = False
        
        # Arrivées ING
        ing_arrivals = PoissonArrivals(
            env,
            self.config.ing_arrival_rate,
            self.config.ing_service_rate,
            population=Population.ING,
            rng=np.random.default_rng(self.config.seed)
        )
        
        # Arrivées PREPA
        prepa_arrivals = PoissonArrivals(
            env,
            self.config.prepa_arrival_rate,
            self.config.prepa_service_rate,
            population=Population.PREPA,
            rng=np.random.default_rng((self.config.seed or 0) + 1000)
        )
        
        # Processus
        env.process(self._ing_arrival_process(env, ing_arrivals, queue))
        env.process(self._prepa_arrival_process(env, prepa_arrivals, queue))
        env.process(self._server_process(env, queue, server_pool, collector))
        
        if self.config.regulation_enabled:
            env.process(self._regulation_process(env))
        
        if verbose:
            print(f"Running Channels & Dams simulation...")
            print(f"  ING: λ={self.config.ing_arrival_rate}, μ={self.config.ing_service_rate}")
            print(f"  PREPA: λ={self.config.prepa_arrival_rate}, μ={self.config.prepa_service_rate}")
            print(f"  Regulation: {'enabled (t_b=' + str(self.config.block_duration) + ')' if self.config.regulation_enabled else 'disabled'}")
        
        env.run(until=self.config.simulation_time)
        
        # Calcul des résultats
        collector.set_simulation_time(self.config.simulation_time - self.config.warmup_time)
        base = collector.compute()
        
        ing_sojourns = [j.sojourn_time for j in self._ing_jobs if j.sojourn_time]
        prepa_sojourns = [j.sojourn_time for j in self._prepa_jobs if j.sojourn_time]
        
        ing_mean = np.mean(ing_sojourns) if ing_sojourns else 0
        prepa_mean = np.mean(prepa_sojourns) if prepa_sojourns else 0
        
        total_ing = len(self._ing_jobs) + len(self._ing_rejected)
        total_prepa = len(self._prepa_jobs) + len(self._prepa_rejected)
        
        results = ChannelsDamsResults(
            base_results=base,
            ing_count=len(self._ing_jobs),
            prepa_count=len(self._prepa_jobs),
            ing_mean_sojourn=ing_mean,
            prepa_mean_sojourn=prepa_mean,
            ing_p95_sojourn=np.percentile(ing_sojourns, 95) if ing_sojourns else 0,
            prepa_p95_sojourn=np.percentile(prepa_sojourns, 95) if prepa_sojourns else 0,
            ing_var_sojourn=np.var(ing_sojourns) if ing_sojourns else 0,
            prepa_var_sojourn=np.var(prepa_sojourns) if prepa_sojourns else 0,
            ing_rejection_rate=len(self._ing_rejected) / total_ing if total_ing > 0 else 0,
            prepa_rejection_rate=len(self._prepa_rejected) / total_prepa if total_prepa > 0 else 0,
            disparity_ratio=prepa_mean / ing_mean if ing_mean > 0 else 0,
        )
        
        if verbose:
            print(f"\n  ING: n={results.ing_count}, W={results.ing_mean_sojourn:.2f}s, Var={results.ing_var_sojourn:.2f}")
            print(f"  PREPA: n={results.prepa_count}, W={results.prepa_mean_sojourn:.2f}s, Var={results.prepa_var_sojourn:.2f}")
            print(f"  Disparity ratio (PREPA/ING): {results.disparity_ratio:.2f}x")
        
        return results
    
    def _ing_arrival_process(self, env, arrivals, queue):
        """Gère les arrivées ING avec possible blocage."""
        gen = arrivals.generate()
        
        while True:
            yield next(gen)
            job = next(gen)
            
            if self._ing_blocked:
                job.status = JobStatus.REJECTED
                if env.now >= self.config.warmup_time:
                    self._ing_rejected.append(job)
                continue
            
            if not queue.enqueue(job):
                job.status = JobStatus.REJECTED
                if env.now >= self.config.warmup_time:
                    self._ing_rejected.append(job)
    
    def _prepa_arrival_process(self, env, arrivals, queue):
        """Gère les arrivées PREPA (jamais bloquées)."""
        gen = arrivals.generate()
        
        while True:
            yield next(gen)
            job = next(gen)
            
            if not queue.enqueue(job):
                job.status = JobStatus.REJECTED
                if env.now >= self.config.warmup_time:
                    self._prepa_rejected.append(job)
    
    def _server_process(self, env, queue, server_pool, collector):
        """Traite les jobs."""
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
            
            yield from server.process(job)
            job.departure_time = env.now
            job.status = JobStatus.COMPLETED
            
            if job.arrival_time >= self.config.warmup_time:
                collector.record_job(job)
                if job.population == Population.ING:
                    self._ing_jobs.append(job)
                else:
                    self._prepa_jobs.append(job)
    
    def _regulation_process(self, env):
        """Régulation par blocage alterné de la file ING."""
        while True:
            # Phase de blocage
            self._ing_blocked = True
            yield env.timeout(self.config.block_duration)
            
            # Phase d'ouverture
            self._ing_blocked = False
            yield env.timeout(self.config.unblock_duration)


def run_channels_dams(
    ing_arrival_rate: float = 2.0,
    prepa_arrival_rate: float = 0.1,
    regulation: str = "none",
    block_duration: float = 10.0,
    duration: float = 10000,
    seed: int = 42
) -> ChannelsDamsResults:
    """
    Fonction de commodité pour lancer la simulation Channels & Dams.
    
    Args:
        regulation: "none", "blocking", ou "custom"
    """
    config = ChannelsDamsConfig(
        ing_arrival_rate=ing_arrival_rate,
        prepa_arrival_rate=prepa_arrival_rate,
        regulation_enabled=(regulation != "none"),
        block_duration=block_duration,
        unblock_duration=block_duration / 2,
        simulation_time=duration,
        warmup_time=duration * 0.1,
        seed=seed
    )
    
    sim = ChannelsDamsSimulation(config)
    return sim.run()


def compare_regulation_policies(
    n_runs: int = 5,
    duration: float = 5000
) -> Dict[str, Dict[str, float]]:
    """
    Compare les différentes politiques de régulation.
    
    Retourne les métriques pour :
    - Sans régulation (baseline)
    - Avec blocage t_b=10
    - Avec blocage t_b=5 (plus agressif)
    """
    policies = [
        ("no_regulation", False, 0),
        ("blocking_t10", True, 10.0),
        ("blocking_t5", True, 5.0),
    ]
    
    results = {}
    
    for name, enabled, tb in policies:
        print(f"\n{'='*40}")
        print(f"Testing {name}...")
        
        run_metrics = []
        for i in range(n_runs):
            config = ChannelsDamsConfig(
                regulation_enabled=enabled,
                block_duration=tb,
                unblock_duration=tb / 2 if tb > 0 else 0,
                simulation_time=duration,
                warmup_time=duration * 0.1,
                seed=42 + i
            )
            sim = ChannelsDamsSimulation(config)
            r = sim.run(verbose=False)
            
            run_metrics.append({
                "ing_sojourn": r.ing_mean_sojourn,
                "prepa_sojourn": r.prepa_mean_sojourn,
                "disparity": r.disparity_ratio,
            })
        
        results[name] = {
            "ing_mean": np.mean([m["ing_sojourn"] for m in run_metrics]),
            "prepa_mean": np.mean([m["prepa_sojourn"] for m in run_metrics]),
            "disparity": np.mean([m["disparity"] for m in run_metrics]),
        }
        
        print(f"  ING: {results[name]['ing_mean']:.2f}s")
        print(f"  PREPA: {results[name]['prepa_mean']:.2f}s")
        print(f"  Disparity: {results[name]['disparity']:.2f}x")
    
    return results
