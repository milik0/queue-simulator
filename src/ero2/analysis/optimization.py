import itertools
from typing import List, Dict, Any, Optional
import pandas as pd
from rich.table import Table
from rich.console import Console
from rich.panel import Panel

from ..models.waterfall import WaterfallSimulation, WaterfallConfig
from ..core.metrics import SimulationResults

console = Console()

def run_hyperparameter_grid_search(
    arrival_rate: float = 0.8,
    exec_service_rate: float = 0.25,
    return_service_rate: float = 2.0,
    server_cost_weight: float = 10.0,
    queue_cost_weight: float = 1.0,
    target_rejection: float = 0.01
) -> None:
    """
    Run a grid search to optimize Waterfall architecture.
    
    Justifies the choice of K (servers), ks (exec queue), kf (return queue).
    
    Args:
        arrival_rate: Load to optimize for (lambda).
        exec_service_rate: Service rate per execution server (mu1).
        return_service_rate: Service rate for return server (mu2).
        server_cost_weight: Penalty for adding a server.
        queue_cost_weight: Penalty for increasing queue size.
        target_rejection: Maximum acceptable rejection rate (1%).
    """
    
    # 1. Define Hyperspace
    # We test unstable (k=3) to proven stable (k=5)
    k_options = [3, 4, 5, 6]
    # We test tight queues (5) to "infinite" (50)
    ks_options = [5, 10, 20, 50] 
    kf_options = [2, 5, 10, 20]
    
    results = []
    
    total_sims = len(k_options) * len(ks_options) * len(kf_options)
    console.print(f"[bold]Running {total_sims} simulations for Grid Search...[/bold]")
    console.print(f"Parameters: λ={arrival_rate}, μ₁={exec_service_rate}, μ₂={return_service_rate}")
    
    # 2. Iterate
    with console.status("[bold green]Simulating configurations...") as status:
        for K, ks, kf in itertools.product(k_options, ks_options, kf_options):
            
            # Label for display
            cfg_label = f"K={K}, ks={ks}, kf={kf}"
            
            # Configure
            config = WaterfallConfig(
                arrival_rate=arrival_rate,
                num_exec_servers=K,
                exec_service_rate=exec_service_rate,
                exec_queue_capacity=ks,
                return_service_rate=return_service_rate,
                return_queue_capacity=kf,
                enable_backup=False, # Optimizing basic structure first
                simulation_time=3000, # Shorter for speed, sufficient for steady state check
                seed=42
            )
            
            # Run
            sim = WaterfallSimulation(config)
            res = sim.run(verbose=False)
            
            # Collect metrics
            # Note: base_results.rejection_rate might be inaccurate if collector doesn't see rejected jobs
            # So we sum the specific rates
            total_rejection = res.exec_rejection_rate + res.page_blanche_rate

            metrics = {
                "K": K,
                "ks": ks,
                "kf": kf,
                "exec_reject": res.exec_rejection_rate,
                "return_reject": res.page_blanche_rate,
                "total_reject": total_rejection,
                "mean_sojourn": res.base_results.mean_sojourn_time,
                "score": 0.0,
                "status": ""
            }
            
            # 3. Score (Cost functions)
            # Cost = (K * 10) + (Capacity) + Penalty for Rejection
            resource_cost = (K * server_cost_weight) + ((ks + kf) * queue_cost_weight)
            
            # Constraint check
            if metrics["total_reject"] > target_rejection:
                metrics["status"] = "REJECTED (Quality)"
                metrics["score"] = float('inf') # Invalid
            # Relax mean sojourn constraint if needed, or make it dynamic
            elif res.base_results.mean_sojourn_time > 100.0:
                 metrics["status"] = "REJECTED (Slow)"
                 metrics["score"] = float('inf')
            else:
                metrics["status"] = "VALID"
                metrics["score"] = resource_cost
            
            # DEBUG: Print everything if none found
            # console.print(f"{cfg_label} -> R={metrics['total_reject']:.2%} W={metrics['mean_sojourn']:.2f}")

            results.append(metrics)

    # 4. Analysis
    df = pd.DataFrame(results)
    
    # Sort for easier debugging of "why no valid found"
    df = df.sort_values("total_reject")
    
    # Find Best
    valid_configs = df[df["score"] != float('inf')]
    
    if valid_configs.empty:
        console.print("[red]No valid configuration found! Showing closest attempts:[/red]")
        console.print(df.head(5))
        return

    best_config = valid_configs.loc[valid_configs["score"].idxmin()]
    
    # 5. Reporting
    _print_optimization_report(df, best_config, target_rejection)

def _print_optimization_report(df, best, target_rejection):
    """Print detailed justification report."""
    
    console.print(Panel.fit(
        f"[bold]Optimal Configuration Found[/bold]\n"
        f"K = {int(best['K'])}\n"
        f"ks = {int(best['ks'])}\n"
        f"kf = {int(best['kf'])}",
        title="🏆 Optimization Results"
    ))
    
    # Justification 1: Why K? (Fix best ks, kf, vary K)
    console.print("\n[bold cyan]1. Justification du nombre de serveurs (K)[/bold cyan]")
    df_k = df[(df["ks"] == best["ks"]) & (df["kf"] == best["kf"])].sort_values("K")
    
    table_k = Table(show_header=True, header_style="bold magenta")
    table_k.add_column("K (Serveurs)")
    table_k.add_column("Rejet Global")
    table_k.add_column("Temps Séjour")
    table_k.add_column("Status")
    
    for _, row in df_k.iterrows():
        status_style = "green" if row["status"] == "VALID" else "red"
        reject_fmt = f"{row['total_reject']:.1%}"
        if row['total_reject'] > target_rejection:
            reject_fmt = f"[red]{reject_fmt}[/red]"
        
        table_k.add_row(
            str(int(row["K"])),
            reject_fmt,
            f"{row['mean_sojourn']:.2f}s",
            f"[{status_style}]{row['status']}[/{status_style}]"
        )
    console.print(table_k)
    console.print(f"[italic]Analyis: K={int(best['K'])} est le minimum nécessaire pour passer sous {target_rejection:.0%} de rejet.[/italic]")

    # Justification 2: Why Exec Capacity? (Fix best K, kf, vary ks)
    console.print("\n[bold cyan]2. Justification de la file d'exécution (ks)[/bold cyan]")
    df_ks = df[(df["K"] == best["K"]) & (df["kf"] == best["kf"])].sort_values("ks")
    
    table_ks = Table(show_header=True, header_style="bold magenta")
    table_ks.add_column("ks (Capacité)")
    table_ks.add_column("Rejet Exec")
    table_ks.add_column("Rejet Global")
    table_ks.add_column("Temps Séjour")
    
    for _, row in df_ks.iterrows():
        is_best = (row["ks"] == best["ks"])
        style = "bold green" if is_best else ""
        table_ks.add_row(
            str(int(row["ks"])),
            f"{row['exec_reject']:.1%}",
            f"{row['total_reject']:.1%}",
            f"{row['mean_sojourn']:.2f}s",
            style=style
        )
    console.print(table_ks)
    console.print(f"[italic]Analyis: ks={int(best['ks'])} offre le meilleur compromis taille/rejet.[/italic]")
    
    # Justification 3: Why Return Capacity? (Fix best K, best ks, vary kf)
    console.print("\n[bold cyan]3. Justification de la file de renvoi (kf)[/bold cyan]")
    df_kf = df[(df["K"] == best["K"]) & (df["ks"] == best["ks"])].sort_values("kf")
    
    table_kf = Table(show_header=True, header_style="bold magenta")
    table_kf.add_column("kf (Capacité)")
    table_kf.add_column("Page Blanche")
    table_kf.add_column("Rejet Global")
    
    for _, row in df_kf.iterrows():
        is_best = (row["kf"] == best["kf"])
        style = "bold green" if is_best else ""
        table_kf.add_row(
            str(int(row["kf"])),
            f"{row['return_reject']:.1%}",
            f"{row['total_reject']:.1%}",
            style=style
        )
    console.print(table_kf)
    console.print(f"[italic]Analyis: kf={int(best['kf'])} suffit pour minimiser les pages blanches sans sur-dimensionner.[/italic]")
