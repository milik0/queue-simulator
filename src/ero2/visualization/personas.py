"""
Persona-specific visualizations.

Creates tailored dashboards for each stakeholder:
- Robert (Student): Focus on waiting time and reliability
- Valerie (Admin): Focus on SLAs and costs
- Alex (Tech): Focus on system metrics and configuration
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns

from .themes import COLORS, FIGURE_SIZES, set_theme, get_persona_style
from ..core.metrics import SimulationResults


def create_robert_dashboard(
    results: SimulationResults,
    output_path: Optional[str] = None,
    wait_threshold: float = 30.0,
    page_blanche_threshold: float = 0.01
) -> plt.Figure:
    """
    Create dashboard for Robert (Student).
    
    Focus: "Will I get my results quickly and reliably?"
    
    Key visualizations:
    - Waiting time distribution with 30s threshold
    - Probability of "quick" result
    - Reliability indicator (no page blanche)
    """
    set_theme()
    fig = plt.figure(figsize=(14, 8))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    style = get_persona_style("robert")
    
    # Title
    fig.suptitle(f"{style['title_prefix']}: Expérience de Robert", 
                 fontsize=16, fontweight='bold', color=style['color'])
    
    # 1. Waiting time distribution with threshold
    ax1 = fig.add_subplot(gs[0, :2])
    waiting_times = [j.waiting_time for j in results.completed_jobs if j.waiting_time is not None]
    
    if waiting_times:
        # Histogram
        n, bins, patches = ax1.hist(waiting_times, bins=50, alpha=0.7, color=COLORS["info"])
        
        # Color bars above threshold in red
        for bin_val, patch in zip(bins, patches):
            if bin_val >= wait_threshold:
                patch.set_facecolor(COLORS["error"])
        
        # Threshold line
        ax1.axvline(wait_threshold, color=COLORS["error"], linestyle='--', linewidth=2)
        ax1.fill_betweenx([0, ax1.get_ylim()[1]], wait_threshold, max(waiting_times) if waiting_times else wait_threshold,
                          color=COLORS["error"], alpha=0.1)
        
        # Stats
        pct_under = sum(1 for w in waiting_times if w < wait_threshold) / len(waiting_times) * 100
        ax1.text(0.98, 0.95, f"{pct_under:.1f}% < {wait_threshold}s", 
                 transform=ax1.transAxes, ha='right', va='top',
                 fontsize=14, fontweight='bold',
                 color=COLORS["success"] if pct_under > 90 else COLORS["error"])
    
    ax1.set_xlabel("Temps d'attente (s)")
    ax1.set_ylabel("Fréquence")
    ax1.set_title("Combien de temps vais-je attendre?")
    
    # 2. Big number: chances of quick result
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis('off')
    
    if waiting_times:
        quick_pct = sum(1 for w in waiting_times if w < wait_threshold) / len(waiting_times) * 100
        color = COLORS["success"] if quick_pct >= 90 else COLORS["warning"] if quick_pct >= 70 else COLORS["error"]
        
        ax2.text(0.5, 0.6, f"{quick_pct:.0f}%", ha='center', va='center',
                 fontsize=48, fontweight='bold', color=color)
        ax2.text(0.5, 0.3, "Chances d'avoir\nun résultat rapide", ha='center', va='center',
                 fontsize=12, color=COLORS["medium"])
        
        # Status indicator
        status = "✓ Excellent" if quick_pct >= 90 else "⚠ Correct" if quick_pct >= 70 else "✗ Lent"
        ax2.text(0.5, 0.1, status, ha='center', va='center', fontsize=14, 
                 fontweight='bold', color=color)
    
    # 3. Sojourn time over time (to see if it gets worse)
    ax3 = fig.add_subplot(gs[1, :2])
    
    completed = [(j.arrival_time, j.sojourn_time) for j in results.completed_jobs 
                 if j.sojourn_time is not None]
    
    if completed:
        times, sojourns = zip(*sorted(completed))
        
        # Moving average
        window = min(100, len(sojourns) // 10) if len(sojourns) > 10 else 1
        if window > 1:
            ma = np.convolve(sojourns, np.ones(window)/window, mode='valid')
            ma_times = times[window-1:]
            ax3.plot(ma_times, ma, color=COLORS["primary"], linewidth=2, label='Moyenne mobile')
        
        ax3.scatter(times[::10], sojourns[::10], alpha=0.3, s=10, color=COLORS["info"])
        ax3.axhline(np.mean(sojourns), color=COLORS["success"], linestyle='--', label=f'Moyenne: {np.mean(sojourns):.1f}s')
    
    ax3.set_xlabel("Temps de simulation")
    ax3.set_ylabel("Temps de séjour (s)")
    ax3.set_title("Est-ce que ça s'améliore ou ça empire?")
    ax3.legend(loc='upper right')
    
    # 4. Rejection/reliability indicator
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.axis('off')
    
    reject_rate = results.rejection_rate
    reliable = reject_rate < page_blanche_threshold
    
    # Big status
    if reliable:
        ax4.text(0.5, 0.6, "✓", ha='center', va='center', fontsize=72, color=COLORS["success"])
        ax4.text(0.5, 0.25, "Système fiable", ha='center', va='center', fontsize=14, fontweight='bold')
        ax4.text(0.5, 0.1, f"Seulement {reject_rate:.2%} de pertes", ha='center', va='center',
                 fontsize=11, color=COLORS["medium"])
    else:
        ax4.text(0.5, 0.6, "⚠", ha='center', va='center', fontsize=72, color=COLORS["warning"])
        ax4.text(0.5, 0.25, "Risque de page blanche", ha='center', va='center', fontsize=14, fontweight='bold')
        ax4.text(0.5, 0.1, f"{reject_rate:.2%} de pertes", ha='center', va='center',
                 fontsize=11, color=COLORS["error"])
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    
    return fig


def create_valerie_dashboard(
    results: SimulationResults,
    output_path: Optional[str] = None,
    sla_threshold: float = 120.0,  # 2 minutes
    sla_target: float = 0.95       # 95% under threshold
) -> plt.Figure:
    """
    Create dashboard for Valérie (Administration).
    
    Focus: "Are we meeting our SLAs? What's the cost?"
    
    Key visualizations:
    - SLA compliance (% under 2 minutes)
    - Cost-benefit analysis
    - Risk assessment
    """
    set_theme()
    fig = plt.figure(figsize=(14, 8))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    style = get_persona_style("valerie")
    
    fig.suptitle(f"{style['title_prefix']}: Tableau de Bord Qualité", 
                 fontsize=16, fontweight='bold', color=style['color'])
    
    # 1. SLA Gauge
    ax1 = fig.add_subplot(gs[0, 0])
    
    sojourn_times = [j.sojourn_time for j in results.completed_jobs if j.sojourn_time is not None]
    
    if sojourn_times:
        under_sla = sum(1 for s in sojourn_times if s < sla_threshold) / len(sojourn_times)
        
        # Gauge visualization
        theta = np.linspace(0, np.pi, 100)
        r = 1
        
        # Background arc
        ax1.plot(r * np.cos(theta), r * np.sin(theta), color=COLORS["light"], linewidth=20)
        
        # Filled arc based on SLA
        fill_theta = np.linspace(0, np.pi * under_sla, 100)
        color = COLORS["success"] if under_sla >= sla_target else COLORS["warning"] if under_sla >= 0.8 else COLORS["error"]
        ax1.plot(r * np.cos(fill_theta), r * np.sin(fill_theta), color=color, linewidth=20)
        
        # Value
        ax1.text(0, 0.2, f"{under_sla:.1%}", ha='center', va='center', fontsize=24, fontweight='bold')
        ax1.text(0, -0.1, f"< {sla_threshold}s", ha='center', va='center', fontsize=10, color=COLORS["medium"])
        
        # Target line
        target_angle = np.pi * sla_target
        ax1.plot([0.8 * np.cos(target_angle), 1.1 * np.cos(target_angle)],
                 [0.8 * np.sin(target_angle), 1.1 * np.sin(target_angle)],
                 color=COLORS["dark"], linewidth=2)
        ax1.text(1.2 * np.cos(target_angle), 1.2 * np.sin(target_angle), f"{sla_target:.0%}",
                 ha='center', va='center', fontsize=9)
    
    ax1.set_xlim(-1.5, 1.5)
    ax1.set_ylim(-0.3, 1.5)
    ax1.axis('off')
    ax1.set_title("Conformité SLA")
    
    # 2. Distribution with percentiles
    ax2 = fig.add_subplot(gs[0, 1:])
    
    if sojourn_times:
        sns.histplot(sojourn_times, kde=True, ax=ax2, color=COLORS["secondary"], alpha=0.6)
        
        # Percentile lines
        p50 = np.percentile(sojourn_times, 50)
        p95 = np.percentile(sojourn_times, 95)
        p99 = np.percentile(sojourn_times, 99)
        
        ax2.axvline(p50, color=COLORS["success"], linestyle='-', label=f'P50: {p50:.1f}s')
        ax2.axvline(p95, color=COLORS["warning"], linestyle='--', label=f'P95: {p95:.1f}s')
        ax2.axvline(p99, color=COLORS["error"], linestyle=':', label=f'P99: {p99:.1f}s')
        
        # SLA threshold
        ax2.axvline(sla_threshold, color=COLORS["dark"], linestyle='-', linewidth=2, alpha=0.5)
        ax2.fill_betweenx([0, ax2.get_ylim()[1]], sla_threshold, max(sojourn_times),
                          color=COLORS["error"], alpha=0.1)
    
    ax2.set_xlabel("Temps de séjour (s)")
    ax2.set_ylabel("Fréquence")
    ax2.set_title("Distribution des temps de réponse")
    ax2.legend()
    
    # 3. Key metrics cards
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.axis('off')
    
    metrics = [
        ("Jobs traités", f"{results.total_completed:,}"),
        ("Taux de rejet", f"{results.rejection_rate:.2%}"),
        ("Utilisation", f"{results.server_utilization:.1%}"),
    ]
    
    for i, (label, value) in enumerate(metrics):
        y = 0.8 - i * 0.3
        ax3.text(0.1, y, label, fontsize=11, color=COLORS["medium"])
        ax3.text(0.9, y, value, fontsize=14, fontweight='bold', ha='right')
    
    ax3.set_title("Métriques Clés")
    
    # 4. Risk assessment
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')
    
    # Calculate risk score
    risks = []
    if results.rejection_rate > 0.05:
        risks.append(("Taux de rejet élevé", "HIGH"))
    elif results.rejection_rate > 0.01:
        risks.append(("Taux de rejet modéré", "MEDIUM"))
    
    if results.server_utilization > 0.9:
        risks.append(("Serveurs saturés", "HIGH"))
    elif results.server_utilization > 0.8:
        risks.append(("Charge élevée", "MEDIUM"))
    
    if sojourn_times and np.percentile(sojourn_times, 95) > sla_threshold:
        risks.append(("P95 hors SLA", "HIGH"))
    
    if not risks:
        risks.append(("Aucun risque majeur", "LOW"))
    
    ax4.text(0.5, 0.95, "Analyse des Risques", ha='center', fontsize=12, fontweight='bold')
    
    for i, (risk, level) in enumerate(risks):
        y = 0.75 - i * 0.2
        color = COLORS["error"] if level == "HIGH" else COLORS["warning"] if level == "MEDIUM" else COLORS["success"]
        marker = "●" 
        ax4.text(0.1, y, marker, fontsize=14, color=color)
        ax4.text(0.2, y, risk, fontsize=10)
    
    # 5. Cost efficiency
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.axis('off')
    
    # Simple cost model: cost proportional to servers, benefit to throughput
    throughput = results.total_completed / results.simulation_time
    efficiency = throughput / results.num_servers if results.num_servers else 0
    
    ax5.text(0.5, 0.7, f"{efficiency:.2f}", ha='center', fontsize=36, fontweight='bold', color=COLORS["primary"])
    ax5.text(0.5, 0.4, "jobs/serveur/unité temps", ha='center', fontsize=10, color=COLORS["medium"])
    ax5.text(0.5, 0.2, "Efficacité", ha='center', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    
    return fig


def create_alex_dashboard(
    results: SimulationResults,
    output_path: Optional[str] = None
) -> plt.Figure:
    """
    Create dashboard for Alex (Tech Lead).
    
    Focus: "What config values do I need? Where are the bottlenecks?"
    
    Key visualizations:
    - Queue length over time
    - Server utilization heatmap
    - Configuration recommendations
    """
    set_theme()
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)
    
    style = get_persona_style("alex")
    
    fig.suptitle(f"{style['title_prefix']}: Configuration Système", 
                 fontsize=16, fontweight='bold', color=style['color'])
    
    # 1. Queue length timeline
    ax1 = fig.add_subplot(gs[0, :])
    
    if results.queue_length_history:
        times, lengths = zip(*results.queue_length_history)
        ax1.fill_between(times, 0, lengths, alpha=0.3, color=COLORS["primary"])
        ax1.plot(times, lengths, color=COLORS["primary"], linewidth=0.5, alpha=0.5)
        
        # Moving average
        window = min(50, len(lengths) // 10) if len(lengths) > 10 else 1
        if window > 1:
            ma = np.convolve(lengths, np.ones(window)/window, mode='valid')
            ax1.plot(times[window-1:], ma, color=COLORS["accent"], linewidth=2, label='Moyenne mobile')
        
        # Thresholds
        ax1.axhline(results.queue_capacity * 0.8, color=COLORS["warning"], linestyle='--', 
                    alpha=0.5, label='80% capacité')
        ax1.axhline(results.queue_capacity, color=COLORS["error"], linestyle='-', 
                    alpha=0.5, label='Capacité max')
        
        ax1.legend(loc='upper right')
    
    ax1.set_xlabel("Temps")
    ax1.set_ylabel("Jobs en file")
    ax1.set_title("Évolution de la longueur de file")
    ax1.set_ylim(bottom=0)
    
    # 2. Utilization timeline
    ax2 = fig.add_subplot(gs[1, :2])
    
    if results.utilization_history:
        times, utils = zip(*results.utilization_history)
        
        # Smooth
        window = min(20, len(utils) // 10) if len(utils) > 10 else 1
        if window > 1:
            ma = np.convolve(utils, np.ones(window)/window, mode='valid')
            times_ma = times[window-1:]
            ax2.fill_between(times_ma, 0, ma, alpha=0.3, color=COLORS["info"])
            ax2.plot(times_ma, ma, color=COLORS["info"], linewidth=2)
        
        # Danger zones
        ax2.axhline(0.9, color=COLORS["warning"], linestyle='--', alpha=0.7)
        ax2.fill_between([times[0], times[-1]], 0.9, 1.0, color=COLORS["error"], alpha=0.1)
        ax2.text(times[-1], 0.92, "Zone critique", ha='right', fontsize=9, color=COLORS["error"])
    
    ax2.set_xlabel("Temps")
    ax2.set_ylabel("Utilisation")
    ax2.set_title("Utilisation des serveurs")
    ax2.set_ylim(0, 1.05)
    
    # 3. Key system metrics
    ax3 = fig.add_subplot(gs[1, 2])
    ax3.axis('off')
    
    metrics = [
        ("ρ (utilisation)", f"{results.server_utilization:.2%}"),
        ("Max queue", f"{results.max_queue_length}"),
        ("Avg queue", f"{results.mean_queue_length:.1f}"),
        ("Reject rate", f"{results.rejection_rate:.2%}"),
    ]
    
    for i, (label, value) in enumerate(metrics):
        y = 0.85 - i * 0.22
        ax3.text(0.1, y, label, fontsize=10, color=COLORS["medium"])
        ax3.text(0.95, y, value, fontsize=12, fontweight='bold', ha='right',
                 fontfamily='monospace')
    
    ax3.set_title("Métriques Système")
    
    # 4. Configuration recommendations (as code-like format)
    ax4 = fig.add_subplot(gs[2, :2])
    ax4.axis('off')
    
    # Generate recommendations based on results
    recommendations = []
    
    if results.server_utilization > 0.9:
        recommendations.append(f"# ⚠ CRITICAL: Utilization > 90%")
        recommendations.append(f"num_servers: {results.num_servers} → {results.num_servers + 2}")
    
    if results.rejection_rate > 0.05:
        recommendations.append(f"# ⚠ WARNING: Rejection rate > 5%")
        new_capacity = int(results.queue_capacity * 1.5)
        recommendations.append(f"queue_capacity: {results.queue_capacity} → {new_capacity}")
    
    if results.max_queue_length > results.queue_capacity * 0.9:
        recommendations.append(f"# Queue nearly full at peak")
        recommendations.append(f"warning_threshold: {int(results.queue_capacity * 0.8)}")
    
    if not recommendations:
        recommendations.append("# ✓ System running optimally")
        recommendations.append(f"num_servers: {results.num_servers}  # OK")
        recommendations.append(f"queue_capacity: {results.queue_capacity}  # OK")
    
    config_text = "\n".join(recommendations)
    ax4.text(0.05, 0.9, "# Recommended config.yaml", fontfamily='monospace', fontsize=11,
             fontweight='bold', va='top')
    ax4.text(0.05, 0.75, config_text, fontfamily='monospace', fontsize=10, va='top',
             linespacing=1.5)
    ax4.set_title("Configuration Recommandée")
    
    # 5. Bottleneck analysis
    ax5 = fig.add_subplot(gs[2, 2])
    ax5.axis('off')
    
    # Simple bottleneck detection
    bottlenecks = []
    
    if results.server_utilization > 0.85:
        bottlenecks.append(("Serveurs", "HIGH", COLORS["error"]))
    elif results.server_utilization > 0.7:
        bottlenecks.append(("Serveurs", "MED", COLORS["warning"]))
    else:
        bottlenecks.append(("Serveurs", "OK", COLORS["success"]))
    
    if results.mean_queue_length > results.queue_capacity * 0.5:
        bottlenecks.append(("File", "HIGH", COLORS["error"]))
    else:
        bottlenecks.append(("File", "OK", COLORS["success"]))
    
    ax5.text(0.5, 0.9, "Goulots d'étranglement", ha='center', fontsize=11, fontweight='bold')
    
    for i, (component, level, color) in enumerate(bottlenecks):
        y = 0.65 - i * 0.25
        # Bar representation
        ax5.barh(y, 0.8 if level == "HIGH" else 0.5 if level == "MED" else 0.2,
                 height=0.15, color=color, alpha=0.7)
        ax5.text(0.05, y, component, va='center', fontsize=10)
        ax5.text(0.95, y, level, va='center', ha='right', fontsize=9, fontweight='bold', color=color)
    
    ax5.set_xlim(0, 1)
    ax5.set_ylim(0, 1)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    
    return fig


def create_all_persona_dashboards(
    results: SimulationResults,
    output_dir: str = "results/figures"
) -> List[str]:
    """Generate dashboards for all personas."""
    from pathlib import Path
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    generated = []
    
    # Robert
    fig = create_robert_dashboard(results, str(output_path / "persona_robert.png"))
    plt.close(fig)
    generated.append(str(output_path / "persona_robert.png"))
    
    # Valérie
    fig = create_valerie_dashboard(results, str(output_path / "persona_valerie.png"))
    plt.close(fig)
    generated.append(str(output_path / "persona_valerie.png"))
    
    # Alex
    fig = create_alex_dashboard(results, str(output_path / "persona_alex.png"))
    plt.close(fig)
    generated.append(str(output_path / "persona_alex.png"))
    
    print(f"\n✅ Generated persona dashboards in {output_dir}/")
    return generated
