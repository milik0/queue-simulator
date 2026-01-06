"""Static visualization functions using Matplotlib and Seaborn.

These generate publication-quality figures for reports and presentations.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from .themes import COLORS, FIGURE_SIZES, set_theme, PALETTE_CATEGORICAL
from ..core.metrics import SimulationResults


def ensure_output_dir(output_dir: str = "results/figures") -> Path:
    """Ensure output directory exists."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def plot_sojourn_distribution(
    results: SimulationResults,
    theoretical_mean: Optional[float] = None,
    output_path: Optional[str] = None,
    title: Optional[str] = None
) -> plt.Figure:
    """
    Plot distribution of sojourn (response) times.
    
    Shows histogram with KDE, mean, median, and percentiles.
    """
    set_theme()
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["medium"])
    
    sojourn_times = [
        j.sojourn_time for j in results.completed_jobs
        if j.sojourn_time is not None
    ]
    
    if not sojourn_times:
        ax.text(0.5, 0.5, "No data available", ha='center', va='center')
        return fig
    
    # Histogram with KDE
    sns.histplot(sojourn_times, kde=True, ax=ax, color=COLORS["primary"], alpha=0.6)
    
    # Add vertical lines for key statistics
    mean = np.mean(sojourn_times)
    median = np.median(sojourn_times)
    p95 = np.percentile(sojourn_times, 95)
    
    ax.axvline(mean, color=COLORS["accent"], linestyle='-', linewidth=2, label=f'Moyenne: {mean:.2f}')
    ax.axvline(median, color=COLORS["success"], linestyle='--', linewidth=2, label=f'Médiane: {median:.2f}')
    ax.axvline(p95, color=COLORS["warning"], linestyle=':', linewidth=2, label=f'P95: {p95:.2f}')
    
    # Add theoretical mean if provided
    if theoretical_mean is not None:
        ax.axvline(theoretical_mean, color=COLORS["error"], linestyle='-.',
                   linewidth=2, label=f'Théorique: {theoretical_mean:.2f}')
    
    # Styling
    ax.set_xlabel("Temps de séjour (unités de temps)")
    ax.set_ylabel("Fréquence")
    ax.set_title(title or f"Distribution des temps de séjour\n{results.model_name}")
    ax.legend(loc='upper right')
    
    # Add statistics box
    stats_text = (
        f"n = {len(sojourn_times)}\n"
        f"σ = {np.std(sojourn_times):.2f}\n"
        f"min = {min(sojourn_times):.2f}\n"
        f"max = {max(sojourn_times):.2f}"
    )
    ax.text(0.98, 0.65, stats_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path)
        print(f"Saved: {output_path}")
    
    return fig


def plot_waiting_distribution(
    results: SimulationResults,
    output_path: Optional[str] = None
) -> plt.Figure:
    """Plot distribution of waiting times in queue."""
    set_theme()
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["medium"])
    
    waiting_times = [
        j.waiting_time for j in results.completed_jobs
        if j.waiting_time is not None
    ]
    
    if not waiting_times:
        ax.text(0.5, 0.5, "No data available", ha='center', va='center')
        return fig
    
    # Histogram
    sns.histplot(waiting_times, kde=True, ax=ax, color=COLORS["secondary"], alpha=0.6)
    
    # Statistics
    mean = np.mean(waiting_times)
    p95 = np.percentile(waiting_times, 95)
    
    ax.axvline(mean, color=COLORS["accent"], linestyle='-', linewidth=2, label=f'Moyenne: {mean:.2f}')
    ax.axvline(p95, color=COLORS["warning"], linestyle=':', linewidth=2, label=f'P95: {p95:.2f}')
    
    # Robert's threshold (30 seconds)
    if max(waiting_times) > 30:
        ax.axvline(30, color=COLORS["error"], linestyle='--', linewidth=2,
                   alpha=0.5, label='Seuil Robert (30s)')
        # Shade area above threshold
        above_threshold = sum(1 for w in waiting_times if w > 30) / len(waiting_times)
        ax.fill_betweenx([0, ax.get_ylim()[1]], 30, max(waiting_times),
                         color=COLORS["error"], alpha=0.1)
        ax.text(35, ax.get_ylim()[1] * 0.9, f'{above_threshold:.1%}', color=COLORS["error"])
    
    ax.set_xlabel("Temps d'attente (unités de temps)")
    ax.set_ylabel("Fréquence")
    ax.set_title(f"Distribution des temps d'attente\n{results.model_name}")
    ax.legend()
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path)
    
    return fig


def plot_queue_length_over_time(
    results: SimulationResults,
    output_path: Optional[str] = None,
    window: int = 100
) -> plt.Figure:
    """Plot queue length evolution over simulation time."""
    set_theme()
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["wide"])
    
    if not results.queue_length_history:
        ax.text(0.5, 0.5, "No queue length data", ha='center', va='center')
        return fig
    
    times, lengths = zip(*results.queue_length_history)
    times = np.array(times)
    lengths = np.array(lengths)
    
    # Plot raw data with low alpha
    ax.plot(times, lengths, color=COLORS["primary"], alpha=0.3, linewidth=0.5)
    
    # Plot moving average
    if len(lengths) > window:
        ma = np.convolve(lengths, np.ones(window)/window, mode='valid')
        ma_times = times[window-1:]
        ax.plot(ma_times, ma, color=COLORS["accent"], linewidth=2, label=f'Moyenne mobile ({window})')
    
    # Add mean line
    mean_length = np.mean(lengths)
    ax.axhline(mean_length, color=COLORS["success"], linestyle='--',
               label=f'Moyenne: {mean_length:.1f}')
    
    # Add max line
    max_length = max(lengths)
    ax.axhline(max_length, color=COLORS["error"], linestyle=':',
               alpha=0.5, label=f'Max: {max_length}')
    
    ax.set_xlabel("Temps")
    ax.set_ylabel("Longueur de file")
    ax.set_title(f"Évolution de la file d'attente\n{results.model_name}")
    ax.legend(loc='upper right')
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path)
    
    return fig


def plot_utilization_over_time(
    results: SimulationResults,
    output_path: Optional[str] = None,
    window: int = 50
) -> plt.Figure:
    """Plot server utilization over time."""
    set_theme()
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["wide"])
    
    if not results.utilization_history:
        ax.text(0.5, 0.5, "No utilization data", ha='center', va='center')
        return fig
    
    times, utils = zip(*results.utilization_history)
    times = np.array(times)
    utils = np.array(utils)
    
    # Moving average
    if len(utils) > window:
        ma = np.convolve(utils, np.ones(window)/window, mode='valid')
        ma_times = times[window-1:]
        ax.fill_between(ma_times, 0, ma, color=COLORS["primary"], alpha=0.3)
        ax.plot(ma_times, ma, color=COLORS["primary"], linewidth=2)
    
    # Add mean
    mean_util = np.mean(utils)
    ax.axhline(mean_util, color=COLORS["accent"], linestyle='--', linewidth=2,
               label=f'ρ moyen: {mean_util:.2%}')
    
    # Danger zone (>90%)
    ax.axhline(0.9, color=COLORS["warning"], linestyle=':', alpha=0.5)
    ax.fill_between([times[0], times[-1]], 0.9, 1.0, color=COLORS["error"], alpha=0.1)
    
    ax.set_xlabel("Temps")
    ax.set_ylabel("Utilisation")
    ax.set_title(f"Utilisation du serveur\n{results.model_name}")
    ax.set_ylim(0, 1.05)
    ax.legend()
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path)
    
    return fig


def plot_load_vs_sojourn(
    sweep_results: List[Dict[str, Any]],
    output_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot sojourn time vs system load (ρ).
    
    Shows both simulated and theoretical curves.
    """
    set_theme()
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["medium"])
    
    rhos = [r["rho"] for r in sweep_results]
    sim_W = [r["mean_sojourn_time"] for r in sweep_results]
    theory_W = [r.get("theoretical_W", np.nan) for r in sweep_results]
    sim_std = [r.get("std_sojourn_time", 0) for r in sweep_results]
    
    # Simulated with error bars
    ax.errorbar(rhos, sim_W, yerr=sim_std, fmt='o-', color=COLORS["primary"],
                capsize=4, markersize=8, label='Simulation', linewidth=2)
    
    # Theoretical
    ax.plot(rhos, theory_W, 's--', color=COLORS["secondary"],
            markersize=6, label='Théorique', linewidth=2)
    
    # Add ρ=1 reference line
    ax.axvline(1.0, color=COLORS["error"], linestyle=':', alpha=0.5, label='ρ=1 (saturation)')
    
    ax.set_xlabel("Charge système (ρ = λ/μ)")
    ax.set_ylabel("Temps de séjour moyen (W)")
    ax.set_title("Temps de séjour vs Charge système\nModèle M/M/1/K")
    ax.legend()
    ax.set_xlim(0, max(rhos) * 1.1)
    ax.set_ylim(bottom=0)
    
    # Add annotation for high load
    if max(rhos) > 0.9:
        ax.annotate('Zone critique', xy=(0.95, sim_W[-1] * 0.8),
                    fontsize=10, color=COLORS["error"])
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path)
    
    return fig


def plot_validation_comparison(
    simulated: Dict[str, float],
    theoretical: Dict[str, float],
    output_path: Optional[str] = None
) -> plt.Figure:
    """
    Bar chart comparing simulated vs theoretical values.
    """
    set_theme()
    fig, ax = plt.subplots(figsize=FIGURE_SIZES["medium"])
    
    metrics = ["W", "Wq", "rho", "Pb"]
    metric_labels = ["Temps séjour (W)", "Temps attente (Wq)", 
                     "Utilisation (ρ)", "Taux rejet (Pb)"]
    sim_keys = ["mean_sojourn_time", "mean_waiting_time", 
                "server_utilization", "rejection_rate"]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    sim_values = [simulated.get(k, 0) for k in sim_keys]
    theory_values = [theoretical.get(k, 0) for k in metrics]
    
    bars1 = ax.bar(x - width/2, theory_values, width, label='Théorique',
                   color=COLORS["secondary"], alpha=0.8)
    bars2 = ax.bar(x + width/2, sim_values, width, label='Simulation',
                   color=COLORS["primary"], alpha=0.8)
    
    # Add value labels
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.3f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)
    
    autolabel(bars1)
    autolabel(bars2)
    
    ax.set_ylabel('Valeur')
    ax.set_title('Comparaison Simulation vs Théorie')
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels, rotation=15, ha='right')
    ax.legend()
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path)
    
    return fig


def plot_population_comparison(
    results: SimulationResults,
    output_path: Optional[str] = None
) -> plt.Figure:
    """
    Compare metrics between ING and PREPA populations.
    
    Shows side-by-side distributions and bar charts.
    """
    set_theme()
    fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZES["wide"])
    
    pop_metrics = results.metrics_by_population
    
    if not pop_metrics:
        for ax in axes:
            ax.text(0.5, 0.5, "No population data", ha='center', va='center')
        return fig
    
    # Left: Sojourn time comparison
    ax1 = axes[0]
    
    pops = list(pop_metrics.keys())
    means = [pop_metrics[p]["mean_sojourn_time"] for p in pops]
    stds = [pop_metrics[p]["std_sojourn_time"] for p in pops]
    
    colors = [COLORS.get(p, COLORS["primary"]) for p in pops]
    
    bars = ax1.bar(pops, means, yerr=stds, color=colors, alpha=0.8, capsize=5)
    ax1.set_ylabel("Temps de séjour moyen")
    ax1.set_title("Temps de séjour par population")
    
    # Add value labels
    for bar, mean in zip(bars, means):
        ax1.annotate(f'{mean:.2f}', xy=(bar.get_x() + bar.get_width()/2, mean),
                     xytext=(0, 5), textcoords="offset points",
                     ha='center', fontsize=10, fontweight='bold')
    
    # Right: Count and P95
    ax2 = axes[1]
    
    counts = [pop_metrics[p]["count"] for p in pops]
    p95s = [pop_metrics[p]["p95_sojourn_time"] for p in pops]
    
    x = np.arange(len(pops))
    width = 0.35
    
    ax2.bar(x - width/2, counts, width, label='Nombre jobs', color=COLORS["info"], alpha=0.7)
    ax2_twin = ax2.twinx()
    ax2_twin.bar(x + width/2, p95s, width, label='P95', color=COLORS["warning"], alpha=0.7)
    
    ax2.set_xticks(x)
    ax2.set_xticklabels(pops)
    ax2.set_ylabel("Nombre de jobs")
    ax2_twin.set_ylabel("P95 temps de séjour")
    ax2.set_title("Volume et P95 par population")
    
    # Combined legend
    handles = [Patch(color=COLORS["info"], alpha=0.7, label='Nombre jobs'),
               Patch(color=COLORS["warning"], alpha=0.7, label='P95')]
    ax2.legend(handles=handles, loc='upper right')
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path)
    
    return fig


def plot_rejection_analysis(
    sweep_results: List[Dict[str, Any]],
    output_path: Optional[str] = None
) -> plt.Figure:
    """
    Analyze rejection rates vs system parameters.
    
    Useful for Alex (tech) persona to size queues.
    """
    set_theme()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGURE_SIZES["wide"])
    
    rhos = [r["rho"] for r in sweep_results]
    rejection_rates = [r["rejection_rate"] for r in sweep_results]
    theory_Pb = [r.get("theoretical_Pb", 0) for r in sweep_results]
    
    # Left: Rejection rate vs load
    ax1.plot(rhos, rejection_rates, 'o-', color=COLORS["primary"],
             linewidth=2, markersize=8, label='Simulation')
    ax1.plot(rhos, theory_Pb, 's--', color=COLORS["secondary"],
             linewidth=2, markersize=6, label='Théorique')
    
    # Add threshold lines
    ax1.axhline(0.01, color=COLORS["success"], linestyle=':', alpha=0.7, label='1% (acceptable)')
    ax1.axhline(0.05, color=COLORS["warning"], linestyle=':', alpha=0.7, label='5% (limite)')
    ax1.axhline(0.10, color=COLORS["error"], linestyle=':', alpha=0.7, label='10% (critique)')
    
    ax1.set_xlabel("Charge système (ρ)")
    ax1.set_ylabel("Taux de rejet")
    ax1.set_title("Taux de rejet vs Charge")
    ax1.legend(loc='upper left')
    ax1.set_ylim(0, max(rejection_rates) * 1.2 if rejection_rates else 0.1)
    
    # Right: Implied queue sizing
    ax2.text(0.5, 0.5, "Configuration recommandée\n\n"
             "Pour ρ < 0.8:\n  K = 10 suffit\n\n"
             "Pour ρ < 0.9:\n  K ≥ 20 recommandé\n\n"
             "Pour ρ > 0.9:\n  Scaling nécessaire",
             ha='center', va='center', fontsize=12,
             transform=ax2.transAxes,
             bbox=dict(boxstyle='round', facecolor=COLORS["light"], alpha=0.8))
    ax2.axis('off')
    ax2.set_title("📋 Recommandations Alex", fontsize=12)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path)
    
    return fig


def create_baseline_report(
    results: SimulationResults,
    theoretical: Dict[str, float],
    output_dir: str = "results/figures"
) -> List[str]:
    """
    Generate all baseline visualizations.
    
    Returns:
        List of generated file paths
    """
    output_path = ensure_output_dir(output_dir)
    generated = []
    
    # 1. Sojourn time distribution
    fig = plot_sojourn_distribution(
        results,
        theoretical_mean=theoretical.get("W"),
        output_path=str(output_path / "baseline_sojourn_dist.png")
    )
    plt.close(fig)
    generated.append(str(output_path / "baseline_sojourn_dist.png"))
    
    # 2. Waiting time distribution
    fig = plot_waiting_distribution(
        results,
        output_path=str(output_path / "baseline_waiting_dist.png")
    )
    plt.close(fig)
    generated.append(str(output_path / "baseline_waiting_dist.png"))
    
    # 3. Queue length over time
    fig = plot_queue_length_over_time(
        results,
        output_path=str(output_path / "baseline_queue_length.png")
    )
    plt.close(fig)
    generated.append(str(output_path / "baseline_queue_length.png"))
    
    # 4. Utilization over time
    fig = plot_utilization_over_time(
        results,
        output_path=str(output_path / "baseline_utilization.png")
    )
    plt.close(fig)
    generated.append(str(output_path / "baseline_utilization.png"))
    
    # 5. Validation comparison
    fig = plot_validation_comparison(
        results.to_dict(),
        theoretical,
        output_path=str(output_path / "baseline_validation.png")
    )
    plt.close(fig)
    generated.append(str(output_path / "baseline_validation.png"))
    
    print(f"\n✅ Generated {len(generated)} baseline figures in {output_dir}/")
    
    return generated
