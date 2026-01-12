from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np

from ..core.arrivals import daily_pattern, deadline_peak
from ..models.baseline import MM1KSimulation, MM1KConfig
from ..models.waterfall import WaterfallSimulation, WaterfallConfig
from ..models.channels import ChannelsSimulation, ChannelsConfig, RegulationPolicy
from ..analysis.metrics import mm1k_metrics


class Scenario(Enum):
    """Pre-defined test scenarios."""
    NORMAL = "normal"           # Standard day, moderate load
    DEADLINE = "deadline"       # Peak before deadline (40 pushes/min)
    EXAM = "exam"               # High priority, many students
    FAILURE = "failure"         # Server goes down mid-simulation


@dataclass
class ScenarioConfig:
    """Configuration for a test scenario."""
    name: str
    description: str
    arrival_rate: float         # Base λ
    service_rate: float         # μ
    num_servers: int
    queue_capacity: int
    duration: float
    
    # Special conditions
    peak_multiplier: float = 1.0    # For deadline scenario
    failure_time: Optional[float] = None   # When server fails
    failure_duration: float = 0.0   # How long failure lasts


# Pre-defined scenarios based on real observations
SCENARIOS = {
    Scenario.NORMAL: ScenarioConfig(
        name="Normal Day",
        description="Standard activity: 10-15 pushes/min, stable load",
        arrival_rate=0.5,
        service_rate=1.0,
        num_servers=4,
        queue_capacity=20,
        duration=10000,
    ),
    Scenario.DEADLINE: ScenarioConfig(
        name="Deadline Rush",
        description="Peak activity before deadline: 40 pushes/min spike",
        arrival_rate=0.8,
        service_rate=1.0,
        num_servers=4,
        queue_capacity=20,
        duration=10000,
        peak_multiplier=4.0,  # 4x normal rate
    ),
    Scenario.EXAM: ScenarioConfig(
        name="Exam Period",
        description="High stakes, all students active: sustained high load",
        arrival_rate=0.95,
        service_rate=1.0,
        num_servers=6,  # More servers allocated
        queue_capacity=50,
        duration=10000,
    ),
    Scenario.FAILURE: ScenarioConfig(
        name="Server Failure",
        description="One server fails mid-operation for 500 time units",
        arrival_rate=0.6,
        service_rate=1.0,
        num_servers=4,
        queue_capacity=20,
        duration=10000,
        failure_time=5000.0,
        failure_duration=500.0,
    ),
}


def run_scenario(
    scenario: Scenario,
    model: str = "baseline",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run a pre-defined scenario.
    
    Args:
        scenario: Scenario enum value
        model: "baseline", "waterfall", or "channels"
        verbose: Print progress
    
    Returns:
        Dictionary with scenario results
    """
    config = SCENARIOS[scenario]
    
    if verbose:
        print(f"\n{'='*50}")
        print(f"SCENARIO: {config.name}")
        print(f"{'='*50}")
        print(f"Description: {config.description}")
        print(f"λ={config.arrival_rate}, μ={config.service_rate}")
        print(f"Servers={config.num_servers}, K={config.queue_capacity}")
    
    results = {
        "scenario": scenario.value,
        "config": config,
    }
    
    if model == "baseline":
        sim = MM1KSimulation(
            arrival_rate=config.arrival_rate,
            service_rate=config.service_rate,
            capacity=config.queue_capacity,
            seed=42
        )
        sim_results = sim.run(
            duration=config.duration,
            warmup=config.duration * 0.1,
            verbose=verbose
        )
        
        # Get theoretical for comparison
        theory = mm1k_metrics(
            config.arrival_rate,
            config.service_rate,
            config.queue_capacity
        )
        
        results["simulated"] = sim_results.to_dict()
        results["theoretical"] = theory.to_dict()
        results["validation"] = sim.validate(verbose=verbose)
        
    elif model == "waterfall":
        wf_config = WaterfallConfig(
            arrival_rate=config.arrival_rate,
            num_exec_servers=config.num_servers,
            exec_service_rate=config.service_rate / config.num_servers,
            exec_queue_capacity=config.queue_capacity,
            return_service_rate=config.service_rate * 2,
            return_queue_capacity=config.queue_capacity // 2,
            enable_backup=True,
            simulation_time=config.duration,
            warmup_time=config.duration * 0.1,
            seed=42
        )
        sim = WaterfallSimulation(wf_config)
        sim_results = sim.run(verbose=verbose)
        
        results["simulated"] = sim_results.base_results.to_dict()
        results["page_blanche_rate"] = sim_results.page_blanche_rate
        results["exec_rejection_rate"] = sim_results.exec_rejection_rate

    elif model == "channels":
        # Heuristic mapping: Split arrival rate, vary service rates
        c_config = ChannelsConfig(
            standard_arrival_rate=config.arrival_rate * 0.8,
            standard_service_rate=config.service_rate, # Fast
            complex_arrival_rate=config.arrival_rate * 0.2,
            complex_service_rate=config.service_rate * 0.2, # Slow (5x slower)
            num_servers=config.num_servers,
            queue_capacity=config.queue_capacity,
            regulation=RegulationPolicy.NONE,
            simulation_time=config.duration,
            warmup_time=config.duration * 0.1,
            seed=42
        )
        sim = ChannelsSimulation(c_config)
        sim_results = sim.run(verbose=verbose)
        
        results["simulated"] = sim_results.base_results.to_dict()
        results["details"] = {
            "standard_mean": sim_results.standard_mean_sojourn,
            "complex_mean": sim_results.complex_mean_sojourn,
            "ratio": sim_results.sojourn_ratio
        }
    
    return results


def run_all_scenarios(model: str = "baseline") -> Dict[str, Dict]:
    """Run all pre-defined scenarios and compare."""
    all_results = {}
    
    for scenario in Scenario:
        results = run_scenario(scenario, model=model, verbose=True)
        all_results[scenario.value] = results
    
    return all_results


def compare_scenarios(results: Dict[str, Dict]) -> None:
    """Print comparison table of scenario results."""
    print("\n" + "="*70)
    print(" SCENARIO COMPARISON")
    print("="*70)
    print(f"{'Scenario':<15} {'W (sojourn)':<12} {'Wq (wait)':<12} {'Reject %':<10} {'ρ':<8}")
    print("-"*70)
    
    for name, data in results.items():
        sim = data.get("simulated", {})
        W = sim.get("mean_sojourn_time", 0)
        Wq = sim.get("mean_waiting_time", 0)
        reject = sim.get("rejection_rate", 0) * 100
        rho = sim.get("server_utilization", 0)
        
        print(f"{name:<15} {W:<12.2f} {Wq:<12.2f} {reject:<10.2f} {rho:<8.2f}")
    
    print("="*70)


def stress_test(
    max_rho: float = 1.5,
    steps: int = 10,
    duration: float = 5000
) -> List[Dict]:
    """
    Stress test: push system beyond stability.
    
    Useful for Alex (tech) to find breaking points.
    """
    import numpy as np
    
    results = []
    rhos = np.linspace(0.5, max_rho, steps)
    
    print("\nSTRESS TEST - Finding Breaking Points")
    print("="*50)
    
    for rho in rhos:
        sim = MM1KSimulation(
            arrival_rate=rho,
            service_rate=1.0,
            capacity=20,
            seed=42
        )
        r = sim.run(duration=duration, warmup=500, verbose=False)
        
        status = "✓ OK" if r.rejection_rate < 0.05 else "⚠ WARNING" if r.rejection_rate < 0.1 else "✗ CRITICAL"
        
        print(f"ρ={rho:.2f}: Reject={r.rejection_rate:.1%}, W={r.mean_sojourn_time:.2f} {status}")
        
        results.append({
            "rho": rho,
            "rejection_rate": r.rejection_rate,
            "mean_sojourn_time": r.mean_sojourn_time,
            "max_queue_length": r.max_queue_length,
        })
    
    # Find breaking point
    breaking_point = None
    for r in results:
        if r["rejection_rate"] > 0.05:
            breaking_point = r["rho"]
            break
    
    if breaking_point:
        print(f"\n⚠ System becomes unstable (>5% rejection) at ρ ≈ {breaking_point:.2f}")
    
    return results
