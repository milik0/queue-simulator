from dataclasses import dataclass
from typing import Dict, Any
import numpy as np
from math import factorial


@dataclass
class TheoreticalMetrics:
    """Container for theoretical queueing metrics."""
    rho: float  # Traffic intensity (utilization)
    L: float    # Average number in system
    Lq: float   # Average number in queue
    W: float    # Average time in system (sojourn time)
    Wq: float   # Average time in queue (waiting time)
    P0: float   # Probability of empty system
    Pb: float = 0.0  # Probability of blocking (for finite queues)
    lambda_eff: float = 0.0  # Effective arrival rate (after blocking)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "rho": self.rho,
            "L": self.L,
            "Lq": self.Lq,
            "W": self.W,
            "Wq": self.Wq,
            "P0": self.P0,
            "Pb": self.Pb,
            "lambda_eff": self.lambda_eff,
        }


def mm1_metrics(lambda_: float, mu: float) -> TheoreticalMetrics:
    rho = lambda_ / mu
    
    if rho >= 1:
        # Unstable system - return infinity for queue metrics
        return TheoreticalMetrics(
            rho=rho,
            L=float('inf'),
            Lq=float('inf'),
            W=float('inf'),
            Wq=float('inf'),
            P0=0.0,
            lambda_eff=lambda_
        )
    
    L = rho / (1 - rho)
    Lq = (rho ** 2) / (1 - rho)
    W = 1 / (mu - lambda_)
    Wq = rho / (mu - lambda_)
    P0 = 1 - rho
    
    return TheoreticalMetrics(
        rho=rho,
        L=L,
        Lq=Lq,
        W=W,
        Wq=Wq,
        P0=P0,
        lambda_eff=lambda_
    )


def mm1k_metrics(lambda_: float, mu: float, K: int) -> TheoreticalMetrics:
    rho = lambda_ / mu
    
    if abs(rho - 1.0) < 1e-10:
        # Special case: ρ = 1
        P0 = 1 / (K + 1)
        Pb = P0  # P_K = P_0 when ρ = 1
        L = K / 2
    else:
        # Standard case: ρ ≠ 1
        rho_K1 = rho ** (K + 1)
        P0 = (1 - rho) / (1 - rho_K1)
        Pb = P0 * (rho ** K)  # P_K
        
        # Average number in system
        numerator = rho * (1 - (K + 1) * (rho ** K) + K * rho_K1)
        denominator = (1 - rho) * (1 - rho_K1)
        L = numerator / denominator
    
    # Effective arrival rate (accounting for blocking)
    lambda_eff = lambda_ * (1 - Pb)
    
    # Little's law for effective values
    if lambda_eff > 0:
        W = L / lambda_eff
    else:
        W = 0.0
    
    # Queue length and waiting time
    Lq = L - (1 - P0)  # L - (probability server is busy)
    Wq = W - (1 / mu)   # W - average service time
    
    return TheoreticalMetrics(
        rho=rho,
        L=L,
        Lq=max(0, Lq),
        W=W,
        Wq=max(0, Wq),
        P0=P0,
        Pb=Pb,
        lambda_eff=lambda_eff
    )


def erlang_c(lambda_: float, mu: float, k: int) -> float:
    rho = lambda_ / (k * mu)
    
    if rho >= 1:
        return 1.0  # System is overloaded
    
    # Calculate sum term
    sum_term = sum(
        ((k * rho) ** n) / factorial(n)
        for n in range(k)
    )
    
    # Final term
    final_term = ((k * rho) ** k) / (factorial(k) * (1 - rho))
    
    # Erlang-C
    C = final_term / (sum_term + final_term)
    
    return C


def mmk_metrics(lambda_: float, mu: float, k: int) -> TheoreticalMetrics:
    rho = lambda_ / (k * mu)  # Per-server utilization
    
    if rho >= 1:
        return TheoreticalMetrics(
            rho=rho,
            L=float('inf'),
            Lq=float('inf'),
            W=float('inf'),
            Wq=float('inf'),
            P0=0.0,
            lambda_eff=lambda_
        )
    
    # Erlang-C probability
    C = erlang_c(lambda_, mu, k)
    
    # Average number in queue
    Lq = (C * rho) / (1 - rho)
    
    # Average waiting time in queue
    Wq = Lq / lambda_
    
    # Average time in system
    W = Wq + (1 / mu)
    
    # Average number in system
    L = lambda_ * W
    
    # Probability of empty system
    sum_term = sum(((k * rho) ** n) / factorial(n) for n in range(k))
    P0 = 1 / (sum_term + ((k * rho) ** k) / (factorial(k) * (1 - rho)))
    
    return TheoreticalMetrics(
        rho=rho,
        L=L,
        Lq=Lq,
        W=W,
        Wq=Wq,
        P0=P0,
        lambda_eff=lambda_
    )


def tandem_metrics(
    lambda_: float,
    mu1: float,
    mu2: float,
    k1: int = 1,
    k2: int = 1
) -> Dict[str, TheoreticalMetrics]:
    stage1 = mmk_metrics(lambda_, mu1, k1) if k1 > 1 else mm1_metrics(lambda_, mu1)
    stage2 = mmk_metrics(lambda_, mu2, k2) if k2 > 1 else mm1_metrics(lambda_, mu2)
    
    return {
        "stage1": stage1,
        "stage2": stage2,
        "total_W": stage1.W + stage2.W,
        "total_L": stage1.L + stage2.L,
    }


def print_metrics_comparison(
    name: str,
    simulated: Dict[str, float],
    theoretical: TheoreticalMetrics
):
    """Print a formatted comparison of simulated vs theoretical results."""
    print(f"\n{'='*50}")
    print(f" {name} - Validation Results")
    print(f"{'='*50}")
    
    theory = theoretical.to_dict()
    
    metrics_to_compare = [
        ("Utilization (ρ)", "rho", "server_utilization"),
        ("Mean Time in System (W)", "W", "mean_sojourn_time"),
        ("Mean Queue Length (Lq)", "Lq", "mean_queue_length"),
        ("Mean Wait Time (Wq)", "Wq", "mean_waiting_time"),
    ]
    
    if theoretical.Pb > 0:
        metrics_to_compare.append(("Blocking Prob (Pb)", "Pb", "rejection_rate"))
    
    print(f"{'Metric':<30} {'Theory':>12} {'Simulated':>12} {'Error %':>10}")
    print("-" * 66)
    
    for label, theory_key, sim_key in metrics_to_compare:
        t_val = theory.get(theory_key, 0)
        s_val = simulated.get(sim_key, 0)
        
        if t_val != 0:
            error = abs(s_val - t_val) / t_val * 100
        else:
            error = 0 if s_val == 0 else float('inf')
        
        print(f"{label:<30} {t_val:>12.4f} {s_val:>12.4f} {error:>9.2f}%")
    
    print("=" * 66)
