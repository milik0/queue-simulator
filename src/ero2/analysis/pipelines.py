from typing import List, Dict, Any, Optional, Union
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from rich.progress import track
from rich import print as rprint
import dataclasses

from ..core.metrics import SimulationResults
from ..models.baseline import MM1KSimulation
from ..models.waterfall import WaterfallSimulation, WaterfallConfig
from ..models.channels import ChannelsSimulation, ChannelsConfig, RegulationPolicy
from ..visualization.static import ensure_output_dir, set_theme, FIGURE_SIZES, COLORS
from .scenarios import Scenario, run_scenario

def run_parameter_comparison_pipeline(
    model: str,
    param_name: str,
    param_range: List[float],
    fixed_params: Dict[str, Any],
    output_dir: str = "results/figures/params"
) -> None:
    """
    Compare a single architecture's performance across varying parameter values.
    
    Args:
        model: "baseline", "waterfall", or "channels"
        param_name: Name of parameter to vary (e.g., "arrival_rate", "num_servers")
        param_range: List of values to test
        fixed_params: Dictionary of constant parameters
        output_dir: Output directory
    """
    path = ensure_output_dir(output_dir)
    results_list = []
    
    print(f"Running parameter sweep for {model}: {param_name} = {param_range}")
    
    for val in track(param_range, description="Simulating..."):
        current_params = fixed_params.copy()
        current_params[param_name] = val
        current_params["seed"] = 42
        
        sim_res = None
        
        try:
            if model == "baseline":
                # MM1KSimulation signature: arrival_rate, service_rate, capacity, seed
                # Duration is passed to run(), not init
                sim_config = {
                    "arrival_rate": current_params.get("arrival_rate", 0.8),
                    "service_rate": current_params.get("service_rate", 1.0),
                    "capacity": current_params.get("capacity", 10),
                    "seed": current_params.get("seed", 42)
                }
                sim = MM1KSimulation(**sim_config)
                sim_res = sim.run(duration=current_params.get("duration", 5000), 
                                warmup=current_params.get("warmup", 500))
                population_metrics = {}
                
            elif model == "waterfall":
                # Need to adapt params to Config object
                full_config = current_params.copy()
                cfg = WaterfallConfig(
                    arrival_rate=full_config.get("arrival_rate", 0.5),
                    num_exec_servers=full_config.get("num_servers", 4), # Mapping check
                    exec_service_rate=full_config.get("service_rate", 1.0) / 4,
                    simulation_time=full_config.get("duration", 5000),
                    # Defaults or passed params for others
                    exec_queue_capacity=full_config.get("capacity", 20),
                    return_service_rate=full_config.get("service_rate", 1.0) * 2,
                    return_queue_capacity=full_config.get("capacity", 20)//2,
                    enable_backup=True
                )
                sim = WaterfallSimulation(cfg)
                sim_res = sim.run().base_results
                population_metrics = {}
                
            elif model == "channels":
                # Simplified mapping 
                cfg = ChannelsConfig(
                    standard_arrival_rate=current_params.get("arrival_rate", 0.5) * 0.8,
                    standard_service_rate=current_params.get("service_rate", 1.0),
                    complex_arrival_rate=current_params.get("arrival_rate", 0.5) * 0.2,
                    complex_service_rate=current_params.get("service_rate", 1.0) * 0.5,
                    num_servers=current_params.get("num_servers", 4),
                    queue_capacity=current_params.get("capacity", 20),
                    simulation_time=current_params.get("duration", 5000)
                )
                sim = ChannelsSimulation(cfg)
                full_res = sim.run()
                sim_res = full_res.base_results
                
                # Store population specific metrics
                population_metrics = {
                    "standard_mean": full_res.standard_mean_sojourn,
                    "complex_mean": full_res.complex_mean_sojourn
                }
            
            elif model == "advanced":
                # Advanced Simulation Config
                from ..models.advanced import AdvancedConfig, AdvancedSimulation
                cfg = AdvancedConfig(
                    simulation_hours=current_params.get("duration", 5000),
                    peak_rate=current_params.get("arrival_rate", 40.0), # Assuming this is peak
                    seed=current_params.get("seed", 42)
                )
                sim = AdvancedSimulation(cfg)
                sim_res = sim.run()
                population_metrics = {}

            else:
                 population_metrics = {}

            if sim_res:
                data_point = {
                    "param_val": val,
                    "mean_sojourn": sim_res.mean_sojourn_time,
                    "p95_sojourn": sim_res.p95_sojourn_time,
                    "rejection_rate": sim_res.rejection_rate,
                    "throughput": sim_res.total_completed / sim_res.simulation_time
                }
                # Merge population metrics if they exist
                data_point.update(population_metrics)
                results_list.append(data_point)
                
        except Exception as e:
            print(f"Error at {param_name}={val}: {e}")

    # Visualization
    if not results_list:
        print("No results to plot.")
        return

    _plot_parameter_sweep(results_list, model, param_name, path)

def _plot_parameter_sweep(data: List[Dict], model: str, param_name: str, path: Path):
    """Generate plots for parameter sweep."""
    set_theme()
    
    x = [d["param_val"] for d in data]
    means = [d["mean_sojourn"] for d in data]
    p95s = [d["p95_sojourn"] for d in data]
    rejects = [d["rejection_rate"] * 100 for d in data]
    
    # 1. Sojourn Time
    fig, ax1 = plt.subplots(figsize=FIGURE_SIZES["medium"])
    
    # Check if we have population specific data
    if "standard_mean" in data[0]:
        std_means = [d.get("standard_mean", 0) for d in data]
        cplx_means = [d.get("complex_mean", 0) for d in data]
        
        ax1.plot(x, std_means, '^-', label="Standard (Short/Freq)", color=COLORS["success"])
        ax1.plot(x, cplx_means, 'v-', label="Complex (Long/Rare)", color=COLORS["error"])
        ax1.plot(x, means, '--', label="Global Average", color="gray", alpha=0.5)
    else:
        ax1.plot(x, means, 'o-', label="Mean Sojourn Time", color=COLORS["primary"])
        ax1.plot(x, p95s, 's--', label="P95 Sojourn Time", color=COLORS["secondary"])
    
    ax1.set_xlabel(param_name)
    ax1.set_ylabel("Time Units")
    ax1.set_title(f"Performance vs {param_name} ({model})")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    fig.savefig(path / f"{model}_vs_{param_name}_time.png")
    plt.close(fig)
    
    # 2. Rejection Rate
    fig, ax2 = plt.subplots(figsize=FIGURE_SIZES["medium"])
    ax2.plot(x, rejects, 'o-', color=COLORS["error"])
    ax2.set_xlabel(param_name)
    ax2.set_ylabel("Rejection Rate (%)")
    ax2.set_title(f"Stability vs {param_name} ({model})")
    ax2.grid(True, alpha=0.3)
    
    fig.savefig(path / f"{model}_vs_{param_name}_rejection.png")
    plt.close(fig)
    
    rprint(f"[green]Generated plots in {path}[/green]")


def run_architecture_comparison_pipeline(
    scenario_name: str,
    output_dir: str = "results/figures/archis"
) -> None:
    """Compare baseline, waterfall, and channels on a specific scenario."""
    from .scenarios import SCENARIOS
    
    path = ensure_output_dir(output_dir)
    print(f"Comparing architectures for scenario: {scenario_name}")
    
    models = ["baseline", "waterfall", "channels"]
    results_map = {}
    
    try:
        scenario = Scenario(scenario_name)
    except ValueError:
        print(f"Invalid scenario. Choices: {[s.value for s in Scenario]}")
        return

    for m in models:
        try:
            res_dict = run_scenario(scenario, model=m, verbose=False)
            
            # Extract basic metrics
            sim_data = res_dict.get("simulated", {})
            # Need to normalize keys if they differ, but to_dict() should be consistent enough
            results_map[m] = {
                "mean_sojourn": sim_data.get("mean_sojourn_time", 0),
                "p95_sojourn": sim_data.get("p95_sojourn_time", 0),
                "rejection_rate": sim_data.get("rejection_rate", 0),
                "utilization": sim_data.get("server_utilization", 0)
            }
        except Exception as e:
            print(f"Failed to run {m}: {e}")

    # Plot Comparison
    _plot_archi_comparison(results_map, scenario_name, path)


def _plot_archi_comparison(results: Dict[str, Dict], scenario: str, path: Path):
    set_theme()
    
    models = list(results.keys())
    means = [results[m]["mean_sojourn"] for m in models]
    p95s = [results[m]["p95_sojourn"] for m in models]
    rejects = [results[m]["rejection_rate"] * 100 for m in models]
    
    x = np.arange(len(models))
    width = 0.35
    
    # Time Plot
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["medium"])
    rects1 = ax.bar(x - width/2, means, width, label='Mean W', color=COLORS["primary"])
    rects2 = ax.bar(x + width/2, p95s, width, label='P95 W', color=COLORS["secondary"])
    
    ax.set_ylabel('Time Units')
    ax.set_title(f'Architecture Comparison - {scenario}')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend()
    
    ax.bar_label(rects1, padding=3, fmt='%.1f')
    ax.bar_label(rects2, padding=3, fmt='%.1f')
    
    fig.tight_layout()
    fig.savefig(path / f"compare_{scenario}_times.png")
    plt.close(fig)
    
    # Rejection Plot
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["medium"])
    rects = ax.bar(models, rejects, color=COLORS["error"])
    ax.set_ylabel('Rejection Rate (%)')
    ax.set_title(f'Rejection Comparison - {scenario}')
    ax.bar_label(rects, fmt='%.1f%%')
    
    fig.tight_layout()
    fig.savefig(path / f"compare_{scenario}_rejection.png")
    plt.close(fig)
    
    rprint(f"[green]Comparison charts saved to {path}[/green]")


def run_load_scenarios_pipeline(
    model: str = "baseline",
    loads: List[str] = ["low", "normal", "high", "overload"],
    output_dir: str = "results/figures/loads"
) -> None:
    """Run a model against a set of predefined load levels."""
    path = ensure_output_dir(output_dir)
    print(f"Running load scenarios for {model}...")
    
    # Define load levels (multipliers of base capacity)
    # Assuming baseline capacity K=20, mu=1.0, 4 servers -> capacity ~4.0
    load_map = {
        "low": {"lambda": 1.0, "desc": "Low Traffic (ρ≈0.25)"},
        "normal": {"lambda": 2.5, "desc": "Normal Traffic (ρ≈0.6)"},
        "high": {"lambda": 3.8, "desc": "High Traffic (ρ≈0.95)"},
        "overload": {"lambda": 5.0, "desc": "Overload (ρ>1.0)"}
    }
    
    results = {}
    
    for load_name in loads:
        if load_name not in load_map:
            continue
            
        params = load_map[load_name]
        lam = params["lambda"]
        
        # Base config for comparison
        # Using 4 servers, capacity 20 as standard
        fixed_conf = {
            "arrival_rate": lam,
            "service_rate": 1.0,
            "num_servers": 4,
            "capacity": 20,
            "duration": 5000,
            "seed": 42
        }
        
        # Create a temp wrapper to reuse param pipeline logic or direct call
        # Let's call direct simulation to get result
        try:
            if model == "baseline":
                sim = MM1KSimulation(arrival_rate=lam, service_rate=1.0, capacity=20) 
                pass
        except:
            pass
    
    summary = []
    
    for load_name in loads:
        if load_name == "low": lam = 0.3
        elif load_name == "normal": lam = 0.7
        elif load_name == "high": lam = 0.95
        elif load_name == "overload": lam = 1.5
        else: lam = 0.5
        
        rprint(f"  > Simulating {load_name} (λ={lam})...")
        
        # We use a generic runner helper
        res = _run_generic(model, lam)
        if res:
            summary.append({
                "load": load_name,
                "lambda": lam,
                "W": res.mean_sojourn_time,
                "Reject": res.rejection_rate
            })
            
    _plot_load_scenarios(summary, model, path)

def _run_generic(model: str, lam: float) -> Optional[SimulationResults]:
    try:
        if model == "baseline":
            return MM1KSimulation(arrival_rate=lam, service_rate=1.0, capacity=20).run(duration=5000, verbose=False)
        elif model == "waterfall":
            cfg = WaterfallConfig(
                arrival_rate=lam, num_exec_servers=4, exec_service_rate=0.25,
                exec_queue_capacity=20, return_service_rate=2.0, return_queue_capacity=10, enable_backup=True,
                simulation_time=5000
            )
            return WaterfallSimulation(cfg).run().base_results
        elif model == "channels":
            cfg = ChannelsConfig(
                standard_arrival_rate=lam*0.8, standard_service_rate=1.0,
                complex_arrival_rate=lam*0.2, complex_service_rate=0.5,
                num_servers=4, queue_capacity=20,
                simulation_time=5000
            )
            return ChannelsSimulation(cfg).run().base_results
    except Exception as e:
        print(f"Error in _run_generic: {e}")
        return None
    return None

def _plot_load_scenarios(data: List[Dict], model: str, path: Path):
    set_theme()
    
    loads = [d["load"] for d in data]
    Ws = [d["W"] for d in data]
    Rejects = [d["Reject"] * 100 for d in data]
    
    fig, ax1 = plt.subplots(figsize=FIGURE_SIZES["medium"])
    
    ax1.bar(loads, Ws, color=COLORS["primary"], alpha=0.7, label="Mean Sojourn Time")
    ax1.set_ylabel("Sojourn Time (W)")
    ax1.set_title(f"Impact of Load on {model}")
    
    ax2 = ax1.twinx()
    ax2.plot(loads, Rejects, 'r-o', linewidth=2, label="Rejection Rate")
    ax2.set_ylabel("Rejection Rate (%)")
    ax2.set_ylim(0, 100)
    
    # Legend
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")
    
    fig.tight_layout()
    fig.savefig(path / f"load_impact_{model}.png")
    rprint(f"[green]Load analysis saved to {path}[/green]")

def run_waterfall_report(
    K: int = 4,
    ks: int = 10,
    kf: int = 5,
    mu1_per_server: float = 0.25,
    mu2: float = 2.0,
    enable_backup: bool = False,
    arrival_law: str = "poisson"
):
    """Run the Waterfall Load Analysis with configurable parameters."""

    # Loads: 0.5, 0.7, 0.9, 1.1 (representing 1.0+)
    loads = [0.5, 0.7, 0.9, 1.1]
    
    from rich.table import Table
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    
    backup_status = "Enabled" if enable_backup else "Disabled"
    
    console.print(Panel.fit(
        f"[bold]Configuration Audit: Waterfall[/bold]\n"
        f"K={K}, ks={ks}, kf={kf}\n"
        f"Exec Rate (Global)={K*mu1_per_server}, Return Rate={mu2}\n"
        f"Backup: {backup_status}, Arrival Law: {arrival_law}",
        title="Analysis Parameters"
    ))
    
    table = Table(header_style="bold magenta")
    table.add_column("Load (ρ)")
    table.add_column("Arrival (λ)")
    table.add_column("Reject Exec", justify="right")
    table.add_column("Page Blanche", justify="right")
    table.add_column("Total Reject", justify="right")
    table.add_column("Mean Wait", justify="right")
    
    for rho in loads:
        global_capacity = K * mu1_per_server
        lam = rho * global_capacity 
        
        cfg = WaterfallConfig(
            arrival_rate=lam,
            num_exec_servers=K,
            exec_service_rate=mu1_per_server,
            exec_queue_capacity=ks,
            return_service_rate=mu2,
            return_queue_capacity=kf,
            enable_backup=enable_backup,
            arrival_law=arrival_law,
            simulation_time=10000,
            seed=42
        )
        
        sim = WaterfallSimulation(cfg)
        res = sim.run(verbose=False)
        
        rho_display = f"{rho:.1f}" if rho < 1.1 else "1.1+"
        
        # Color coding
        pb_style = "red" if res.page_blanche_rate > 0.01 else "white"
        
        table.add_row(
            rho_display,
            f"{lam:.2f}",
            f"{res.exec_rejection_rate:.1%}",
            f"[{pb_style}]{res.page_blanche_rate:.1%}[/{pb_style}]",
            f"{res.exec_rejection_rate + res.page_blanche_rate:.1%}",
            f"{res.base_results.mean_sojourn_time:.2f}s"
        )
        
    console.print(table)
    console.print("\n[italic]Note: 'Page Blanche' indicates overflow at the Return Stage (Stage 2).[/italic]")

def run_baseline_report(
    K: int = 4,
    lam: float = 0.8,
    mu: float = 1.0,
    duration: float = 10000
):
    """
    Run Baseline (Infinite Capacity) Analysis Report.
    
    Generates a metrics table for an ideal system with K servers.
    Corresponds to architecture A (Baseline).
    """
    from rich.table import Table
    from rich.console import Console
    from rich.panel import Panel
    import numpy as np
    
    console = Console()
    
    console.print(Panel.fit(
        f"[bold]Architecture A: Baseline (Infinite Capacity)[/bold]\n"
        f"Configuration:\n"
        f"— Infinite Queue Capacity\n"
        f"— K = {K} execution servers\n"
        f"— λ = {lam}, μ = {mu}",
        title="Baseline Report"
    ))
    
    # Run Simulation (M/M/k with infinite capacity)
    # Using MM1KSimulation but effectively M/M/k/inf by setting very large capacity
    # Limitation: MM1KSimulation in this codebase seems designed as single server?
    # Let's check MM1KSimulation implementation in baseline.py
    
    config = WaterfallConfig(
        arrival_rate=lam,
        num_exec_servers=K,
        exec_service_rate=mu,
        exec_queue_capacity=999999,
        return_service_rate=mu * 8,
        return_queue_capacity=999999,
        enable_backup=False,
        simulation_time=duration,
        seed=42
    )
    
    sim = WaterfallSimulation(config)
    res = sim.run(verbose=False)
    base = res.base_results
    
    table = Table(header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    
    table.add_row("Mean Sojourn Time", f"{base.mean_sojourn_time:.2f} s")
    table.add_row("Standard Deviation", f"{base.std_sojourn_time:.2f} s")
    table.add_row("P95 Sojourn Time", f"{base.p95_sojourn_time:.2f} s")
    table.add_row("Utilization", f"{base.server_utilization:.1%}")

    table.add_row("Rejection Rate", f"{base.rejection_rate:.1%} (Theoretical 0%)")
    
    console.print(table)

def run_incremental_gains_pipeline(
    rho: float = 0.8,
    K: int = 4,
    ks: int = 5,
    kf: int = 10
):
    """
    Générer la synthèse des gains incrémentaux (Tableau 3.4).
    Comparison: Baseline -> Finite Queues -> Backup 50% -> Backup 100%.
    """
    from rich.table import Table
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    console.print(Panel.fit(
        f"[bold]Synthèse des Gains Incrémentaux[/bold]\n"
        f"Charge système ρ = {rho}",
        title="📈 Evolution Architecture"
    ))
    
    mu1 = 0.34
    mu2 = 1.0
    lam = rho * (K * mu1)
    duration = 10000
    
    base_cfg = WaterfallConfig(
        arrival_rate=lam,
        num_exec_servers=K,
        exec_service_rate=mu1,
        exec_queue_capacity=0,
        return_service_rate=mu2,
        return_queue_capacity=0,
        enable_backup=False,
        simulation_time=duration,
        seed=42
    )

    steps = []
    
    # --- Step 0: Baseline (Infinite) ---
    cfg0 = dataclasses.replace(base_cfg)
    cfg0.exec_queue_capacity = 9999
    cfg0.return_queue_capacity = 9999
    cfg0.return_service_rate = 2.0
    
    sim0 = WaterfallSimulation(cfg0)
    res0 = sim0.run(verbose=False)
    
    steps.append({
        "name": "0. Baseline (∞)",
        "W": res0.base_results.mean_sojourn_time,
        "Pb": res0.page_blanche_rate,
        "Rej": res0.exec_rejection_rate,
        "gain": "– (référence)"
    })
    
    # --- Step 1: Finite Queues ---
    cfg1 = dataclasses.replace(base_cfg)
    cfg1.exec_queue_capacity = ks
    cfg1.return_queue_capacity = kf
    
    sim1 = WaterfallSimulation(cfg1)
    res1 = sim1.run(verbose=False)
    
    gain1 = "Réalisme"
    steps.append({
        "name": f"1. Files finies (ρ={rho})",
        "W": res1.base_results.mean_sojourn_time,
        "Pb": res1.page_blanche_rate,
        "Rej": res1.exec_rejection_rate,
        "gain": gain1
    })
    
    # --- Step 2: Backup 50% ---
    cfg2 = dataclasses.replace(cfg1)
    cfg2.enable_backup = True
    cfg2.backup_probability = 0.5
    
    sim2 = WaterfallSimulation(cfg2)
    res2 = sim2.run(verbose=False)
    
    # Calculate gain in Pb
    if res1.page_blanche_rate > 0:
        reduction = (res1.page_blanche_rate - res2.page_blanche_rate) / res1.page_blanche_rate
        gain2 = f"-{reduction:.0%} pages blanches"
    else:
        gain2 = "0% pages blanches (déjà 0)"
        
    steps.append({
        "name": "2. + Backup 50%",
        "W": res2.base_results.mean_sojourn_time,
        "Pb": res2.page_blanche_rate,
        "Rej": res2.exec_rejection_rate,
        "gain": gain2
    })
    
    # --- Step 3: Backup 100% ---
    cfg3 = dataclasses.replace(cfg1)
    cfg3.enable_backup = True
    cfg3.backup_probability = 1.0
    
    sim3 = WaterfallSimulation(cfg3)
    res3 = sim3.run(verbose=False)
    
    gain3 = "-100% pages blanches" if res3.page_blanche_rate == 0 and res1.page_blanche_rate > 0 else "Stable"
    
    steps.append({
        "name": "3. + Backup 100%",
        "W": res3.base_results.mean_sojourn_time,
        "Pb": res3.page_blanche_rate,
        "Rej": res3.exec_rejection_rate,
        "gain": gain3
    })
    
    # --- Print Table ---
    table = Table(header_style="bold magenta")
    table.add_column("Étape")
    table.add_column("W moyen", justify="right")
    table.add_column("Page blanche", justify="right")
    table.add_column("Rejet (Exec)", justify="right")
    table.add_column("Gain vs précédent", justify="right", style="cyan")
    
    for s in steps:
        table.add_row(
            s["name"],
            f"{s['W']:.2f}s",
            f"{s['Pb']:.1%}",
            f"{s['Rej']:.1%}",
            s["gain"]
        )
            
    console.print(table)