"""
ERO2 Command Line Interface.
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

app = typer.Typer(
    name="sim",
    help="ERO2 - Simulation de files d'attente pour la moulinette",
    add_completion=False
)
console = Console()


@app.command()
def baseline(
    arrival_rate: float = typer.Option(0.8, "--lambda", "-l", help="Taux d'arrivée λ"),
    service_rate: float = typer.Option(1.0, "--mu", "-m", help="Taux de service μ"),
    capacity: int = typer.Option(10, "--capacity", "-k", help="Capacité du système K"),
    duration: float = typer.Option(10000, "--duration", "-d", help="Durée de simulation"),
    warmup: float = typer.Option(1000, "--warmup", "-w", help="Période de chauffe"),
    seed: Optional[int] = typer.Option(42, "--seed", "-s", help="Graine aléatoire"),
    no_plots: bool = typer.Option(False, "--no-plots", help="Désactiver les graphiques"),
    output_dir: str = typer.Option("results/figures", "--output", "-o", help="Dossier de sortie")
):
    """
    Exécuter la simulation M/M/1/K baseline.
    
    C'est le modèle de référence pour toutes les comparaisons.
    """
    rprint(Panel.fit(
        "[bold blue]Simulation Baseline M/M/1/K[/bold blue]\n"
        f"λ={arrival_rate}, μ={service_rate}, K={capacity}",
        title="🚀 ERO2"
    ))
    
    from .models.baseline import MM1KSimulation
    from .analysis.theoretical import mm1k_metrics
    from .visualization.static import create_baseline_report
    
    # Run simulation
    sim = MM1KSimulation(
        arrival_rate=arrival_rate,
        service_rate=service_rate,
        capacity=capacity,
        seed=seed
    )
    
    results = sim.run(duration=duration, warmup=warmup)
    validation = sim.validate()
    
    # Display results table
    theory = mm1k_metrics(arrival_rate, service_rate, capacity)
    
    table = Table(title="Résultats de la Simulation")
    table.add_column("Métrique", style="cyan")
    table.add_column("Simulé", style="green")
    table.add_column("Théorique", style="yellow")
    table.add_column("Erreur", style="magenta")
    
    metrics = [
        ("Utilisation (ρ)", results.server_utilization, theory.rho),
        ("Temps séjour (W)", results.mean_sojourn_time, theory.W),
        ("Temps attente (Wq)", results.mean_waiting_time, theory.Wq),
        ("Taux rejet (Pb)", results.rejection_rate, theory.Pb),
    ]
    
    for name, sim_val, theory_val in metrics:
        error = abs(sim_val - theory_val) / theory_val * 100 if theory_val != 0 else 0
        table.add_row(name, f"{sim_val:.4f}", f"{theory_val:.4f}", f"{error:.1f}%")
    
    console.print(table)
    
    # Generate visualizations
    if not no_plots:
        rprint("\n[bold]Génération des visualisations...[/bold]")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        figures = create_baseline_report(results, theory.to_dict(), output_dir)
        
        for fig in figures:
            rprint(f"  ✅ {fig}")
    
    rprint("\n[green]✓ Simulation baseline terminée[/green]")


@app.command()
def waterfall(
    arrival_rate: float = typer.Option(0.8, "--lambda", "-l"),
    exec_servers: int = typer.Option(4, "--exec-servers", "-k"),
    exec_capacity: int = typer.Option(10, "--exec-capacity"),
    return_capacity: int = typer.Option(5, "--return-capacity"),
    backup: bool = typer.Option(True, "--backup/--no-backup"),
    duration: float = typer.Option(10000, "--duration", "-d"),
    seed: Optional[int] = typer.Option(42, "--seed", "-s"),
):
    """
    Exécuter le modèle Waterfall (files en tandem).
    
    Simule le système en deux étapes: exécution puis renvoi.
    """
    rprint(Panel.fit(
        "[bold purple]Modèle Waterfall[/bold purple]\n"
        f"λ={arrival_rate}, K={exec_servers} serveurs\n"
        f"Backup: {'✓' if backup else '✗'}",
        title="🌊 Waterfall"
    ))
    
    from .models.waterfall import WaterfallConfig, WaterfallSimulation
    
    config = WaterfallConfig(
        arrival_rate=arrival_rate,
        num_exec_servers=exec_servers,
        exec_service_rate=0.3,
        exec_queue_capacity=exec_capacity,
        return_service_rate=1.0,
        return_queue_capacity=return_capacity,
        enable_backup=backup,
        simulation_time=duration,
        warmup_time=duration * 0.1,
        seed=seed
    )
    
    sim = WaterfallSimulation(config)
    results = sim.run()
    
    # Results table
    table = Table(title="Résultats Waterfall")
    table.add_column("Métrique", style="cyan")
    table.add_column("Valeur", style="green")
    
    table.add_row("Jobs complétés", str(len(sim._completed)))
    table.add_row("Rejets exécution", f"{results.exec_rejection_rate:.2%}")
    table.add_row("Pages blanches", f"{results.page_blanche_rate:.2%}")
    table.add_row("Temps séjour moyen", f"{results.base_results.mean_sojourn_time:.2f}")
    
    if backup:
        table.add_row("Jobs sauvegardés", str(results.backed_up_jobs))
    
    console.print(table)
    
    rprint("\n[green]✓ Simulation Waterfall terminée[/green]")


@app.command()
def channels(
    regulation: str = typer.Option("none", "--regulation", "-r",
                                   help="Politique: none, dam, sjf, dedicated"),
    duration: float = typer.Option(10000, "--duration", "-d"),
    seed: Optional[int] = typer.Option(42, "--seed", "-s"),
    compare_all: bool = typer.Option(False, "--compare", "-c", 
                                     help="Comparer toutes les politiques"),
):
    """
    Exécuter le modèle Channels & Dams.
    
    Simule les populations hétérogènes ING vs PREPA.
    """
    from .models.channels import run_channels, compare_regulations
    
    if compare_all:
        rprint(Panel.fit(
            "[bold yellow]Comparaison des Politiques[/bold yellow]",
            title="⚖️ Channels & Dams"
        ))
        
        results = compare_regulations(n_runs=3, duration=duration)
        
        table = Table(title="Comparaison des Régulations")
        table.add_column("Politique", style="cyan")
        table.add_column("ING (W)", style="blue")
        table.add_column("PREPA (W)", style="yellow")
        table.add_column("Ratio", style="magenta")
        
        for policy, metrics in results.items():
            table.add_row(
                policy,
                f"{metrics['ing_mean']:.2f}",
                f"{metrics['prepa_mean']:.2f}",
                f"{metrics['ratio_mean']:.2f}"
            )
        
        console.print(table)
    else:
        rprint(Panel.fit(
            f"[bold yellow]Modèle Channels & Dams[/bold yellow]\n"
            f"Régulation: {regulation}",
            title="⚖️ Channels"
        ))
        
        results = run_channels(regulation=regulation, duration=duration, seed=seed)
        
        table = Table(title=f"Résultats ({regulation})")
        table.add_column("Population", style="cyan")
        table.add_column("Count", style="white")
        table.add_column("Temps séjour (W)", style="green")
        table.add_column("P95", style="yellow")
        
        table.add_row("ING", str(results.ing_count), 
                      f"{results.ing_mean_sojourn:.2f}", f"{results.ing_p95_sojourn:.2f}")
        table.add_row("PREPA", str(results.prepa_count),
                      f"{results.prepa_mean_sojourn:.2f}", f"{results.prepa_p95_sojourn:.2f}")
        
        console.print(table)
        rprint(f"\n[dim]Ratio ING/PREPA: {results.sojourn_ratio:.2f}[/dim]")
    
    rprint("\n[green]✓ Simulation Channels terminée[/green]")


@app.command()
def dashboard(
    model: str = typer.Option("baseline", "--model", "-m",
                              help="Modèle: baseline, waterfall, channels"),
):
    """
    Ouvrir le dashboard interactif Plotly.
    """
    rprint("[bold]Lancement du dashboard interactif...[/bold]")
    
    from .visualization.interactive import show_dashboard
    from .models.baseline import run_baseline
    from .analysis.theoretical import mm1k_metrics
    
    if model == "baseline":
        results = run_baseline(duration=5000, warmup=500)
        theory = mm1k_metrics(0.8, 1.0, 10)
        show_dashboard(results, theory.to_dict())
    else:
        rprint(f"[yellow]Dashboard pour {model} pas encore implémenté[/yellow]")
        # Could extend for other models


@app.command()
def sweep(
    min_rho: float = typer.Option(0.1, help="ρ minimum"),
    max_rho: float = typer.Option(0.95, help="ρ maximum"),
    steps: int = typer.Option(10, help="Nombre de points"),
    output_dir: str = typer.Option("results/figures", "--output", "-o"),
):
    """
    Balayage de paramètres pour courbe charge vs temps séjour.
    """
    import numpy as np
    
    rprint(Panel.fit(
        f"[bold]Balayage de paramètres[/bold]\n"
        f"ρ ∈ [{min_rho}, {max_rho}], {steps} points",
        title="📊 Parameter Sweep"
    ))
    
    from .models.baseline import parameter_sweep
    from .visualization.static import plot_load_vs_sojourn, ensure_output_dir
    
    arrival_rates = list(np.linspace(min_rho, max_rho, steps))
    
    results = parameter_sweep(
        arrival_rates=arrival_rates,
        service_rate=1.0,
        capacity=10,
        duration=5000,
        n_runs=3
    )
    
    output_path = ensure_output_dir(output_dir)
    fig = plot_load_vs_sojourn(results, str(output_path / "sweep_load_vs_sojourn.png"))
    
    rprint(f"\n[green]✓ Graphique généré: {output_path / 'sweep_load_vs_sojourn.png'}[/green]")


@app.command()
def scenarios(
    scenario: str = typer.Option("normal", "--scenario", "-s",
                                  help="Scenario: normal, deadline, exam, failure"),
    model: str = typer.Option("baseline", "--model", "-m"),
    run_all: bool = typer.Option(False, "--all", "-a", help="Run all scenarios"),
):
    """
    Run pre-defined test scenarios.
    
    Tests system behavior under different conditions.
    """
    from .analysis.scenarios import Scenario, run_scenario, run_all_scenarios, compare_scenarios
    
    if run_all:
        rprint(Panel.fit(
            "[bold]Running All Test Scenarios[/bold]",
            title="🎭 Scenarios"
        ))
        results = run_all_scenarios(model=model)
        compare_scenarios(results)
    else:
        rprint(Panel.fit(
            f"[bold]Scenario: {scenario}[/bold]",
            title="🎭 Scenario Test"
        ))
        try:
            sc = Scenario(scenario)
            run_scenario(sc, model=model, verbose=True)
        except ValueError:
            rprint(f"[red]Unknown scenario: {scenario}[/red]")
            rprint("Available: normal, deadline, exam, failure")
    
    rprint("\n[green]✓ Scenario testing complete[/green]")


@app.command()
def personas(
    output_dir: str = typer.Option("results/figures", "--output", "-o"),
    duration: float = typer.Option(10000, "--duration", "-d"),
):
    """
    Generate persona-specific dashboards.
    
    Creates tailored visualizations for:
    - Robert (Student): Wait times, reliability
    - Valérie (Admin): SLAs, costs
    - Alex (Tech): System metrics, config
    """
    rprint(Panel.fit(
        "[bold]Generating Persona Dashboards[/bold]\n"
        "📱 Robert | 📊 Valérie | ⚙️ Alex",
        title="👥 Personas"
    ))
    
    from .models.baseline import MM1KSimulation
    from .visualization.personas import create_all_persona_dashboards
    
    # Run simulation
    sim = MM1KSimulation(arrival_rate=0.8, service_rate=1.0, capacity=15, seed=42)
    results = sim.run(duration=duration, warmup=duration*0.1, verbose=False)
    
    # Generate dashboards
    generated = create_all_persona_dashboards(results, output_dir)
    
    for path in generated:
        rprint(f"  ✅ {path}")
    
    rprint("\n[green]✓ Persona dashboards generated[/green]")


@app.command()
def stress(
    max_rho: float = typer.Option(1.5, help="Maximum load to test"),
    steps: int = typer.Option(10, help="Number of load levels"),
):
    """
    Stress test to find system breaking points.
    
    Useful for capacity planning.
    """
    rprint(Panel.fit(
        f"[bold red]Stress Test[/bold red]\n"
        f"Testing ρ up to {max_rho}",
        title="💥 Stress Test"
    ))
    
    from .analysis.scenarios import stress_test
    stress_test(max_rho=max_rho, steps=steps)
    
    rprint("\n[green]✓ Stress test complete[/green]")

@app.command()
def advanced(
    pattern: str = typer.Option("daily", "--pattern", "-p",
                                 help="Pattern: constant, daily, deadline"),
    hours: float = typer.Option(24.0, "--hours", "-h", help="Simulation hours"),
    peak_rate: float = typer.Option(40.0, "--peak", help="Peak arrival rate"),
    seed: Optional[int] = typer.Option(42, "--seed", "-s"),
):
    """
    Run advanced simulation with time-varying arrivals.
    
    Models realistic daily patterns based on observed data:
    - Peak at 20:00-21:00 (40 pushes/min)
    - Low activity at night
    """
    rprint(Panel.fit(
        f"[bold cyan]Advanced Simulation[/bold cyan]\n"
        f"Pattern: {pattern}, {hours:.0f} hours\n"
        f"Peak λ = {peak_rate}",
        title="⏰ λ(t) Simulation"
    ))
    
    from .models.advanced import AdvancedConfig, AdvancedSimulation
    
    config = AdvancedConfig(
        pattern=pattern,
        simulation_hours=hours,
        peak_rate=peak_rate,
        seed=seed
    )
    
    sim = AdvancedSimulation(config)
    results = sim.run()
    
    table = Table(title="Advanced Simulation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Completed", f"{results.total_completed:,}")
    table.add_row("Rejected", f"{results.total_rejected:,}")
    table.add_row("Rejection rate", f"{results.rejection_rate:.2%}")
    table.add_row("Mean sojourn", f"{results.mean_sojourn_time:.2f}")
    table.add_row("P95 sojourn", f"{results.p95_sojourn_time:.2f}")
    
    console.print(table)
    rprint("\n[green]✓ Advanced simulation complete[/green]")


@app.command()
def export(
    model: str = typer.Option("baseline", "--model", "-m"),
    duration: float = typer.Option(5000, "--duration", "-d"),
    output_dir: str = typer.Option("results", "--output", "-o"),
    include_jobs: bool = typer.Option(False, "--jobs", help="Include raw job data"),
):
    """
    Run simulation and export results to CSV/JSON.
    
    Generates files in results/data/ for external analysis.
    """
    rprint(Panel.fit(
        f"[bold]Export Simulation Data[/bold]\n"
        f"Model: {model}",
        title="📤 Export"
    ))
    
    from .models.baseline import MM1KSimulation
    from .analysis.export import generate_report
    
    # Run simulation
    sim = MM1KSimulation(arrival_rate=0.8, service_rate=1.0, capacity=15, seed=42)
    results = sim.run(duration=duration, warmup=duration*0.1, verbose=True)
    
    # Generate exports
    files = generate_report(results, output_dir, include_jobs=include_jobs)
    
    for name, path in files.items():
        rprint(f"  ✅ {name}: {path}")
    
    rprint("\n[green]✓ Export complete[/green]")


@app.command()
def info():
    """Show project information."""
    rprint(Panel.fit(
        "[bold blue]ERO2 - Queue System Simulator[/bold blue]\n\n"
        "Simulation framework for EPITA's moulinette system.\n\n"
        "[dim]Available models:[/dim]\n"
        "  • baseline  - M/M/1/K reference model\n"
        "  • waterfall - Tandem queues\n"
        "  • channels  - Heterogeneous populations\n"
        "  • advanced  - Time-varying λ(t)\n\n"
        "[dim]Commands:[/dim]\n"
        "  uv run sim baseline     # Run baseline simulation\n"
        "  uv run sim waterfall    # Run Waterfall model\n"
        "  uv run sim channels -c  # Compare regulations\n"
        "  uv run sim advanced     # Daily pattern simulation\n"
        "  uv run sim scenarios -a # Run all test scenarios\n"
        "  uv run sim personas     # Generate persona dashboards\n"
        "  uv run sim sweep        # Parameter sweep\n"
        "  uv run sim stress       # Stress test\n"
        "  uv run sim export       # Export to CSV/JSON",
        title="ℹ️  About"
    ))


if __name__ == "__main__":
    app()
