"""Interactive visualizations using Plotly.

Provides dashboards and explorable visualizations for real-time analysis.
"""

from typing import Dict, Any, Optional, List
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from .themes import COLORS
from ..core.metrics import SimulationResults


def create_sojourn_interactive(
    results: SimulationResults,
    title: str = "Distribution des temps de séjour"
) -> go.Figure:
    """Create interactive histogram of sojourn times."""
    
    sojourn_times = [
        j.sojourn_time for j in results.completed_jobs
        if j.sojourn_time is not None
    ]
    
    if not sojourn_times:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5)
        return fig
    
    fig = go.Figure()
    
    # Histogram
    fig.add_trace(go.Histogram(
        x=sojourn_times,
        nbinsx=50,
        name="Fréquence",
        marker_color=COLORS["primary"],
        opacity=0.7
    ))
    
    # Statistics lines
    mean = np.mean(sojourn_times)
    median = np.median(sojourn_times)
    p95 = np.percentile(sojourn_times, 95)
    
    for val, name, color in [
        (mean, "Moyenne", COLORS["accent"]),
        (median, "Médiane", COLORS["success"]),
        (p95, "P95", COLORS["warning"])
    ]:
        fig.add_vline(
            x=val, line_dash="dash", line_color=color,
            annotation_text=f"{name}: {val:.2f}",
            annotation_position="top"
        )
    
    fig.update_layout(
        title=title,
        xaxis_title="Temps de séjour",
        yaxis_title="Fréquence",
        template="plotly_white",
        hovermode="x unified"
    )
    
    return fig


def create_metrics_gauge(
    results: SimulationResults,
    theoretical: Optional[Dict[str, float]] = None
) -> go.Figure:
    """Create gauge charts for key metrics."""
    
    fig = make_subplots(
        rows=1, cols=3,
        specs=[[{"type": "indicator"}] * 3],
        subplot_titles=["Utilisation (ρ)", "Taux de Rejet", "Temps Séjour Moyen"]
    )
    
    # Utilization gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=results.server_utilization * 100,
        domain={'row': 0, 'column': 0},
        title={'text': "Utilisation (%)"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': COLORS["primary"]},
            'steps': [
                {'range': [0, 70], 'color': '#E0E7FF'},
                {'range': [70, 90], 'color': '#FDE68A'},
                {'range': [90, 100], 'color': '#FECACA'}
            ],
            'threshold': {
                'line': {'color': COLORS["error"], 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ), row=1, col=1)
    
    # Rejection rate gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=results.rejection_rate * 100,
        number={'suffix': "%"},
        title={'text': "Taux de Rejet (%)"},
        gauge={
            'axis': {'range': [0, 20]},
            'bar': {'color': COLORS["secondary"]},
            'steps': [
                {'range': [0, 1], 'color': '#D1FAE5'},
                {'range': [1, 5], 'color': '#FDE68A'},
                {'range': [5, 20], 'color': '#FECACA'}
            ]
        }
    ), row=1, col=2)
    
    # Sojourn time gauge
    max_sojourn = max(results.mean_sojourn_time * 2, 10)
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=results.mean_sojourn_time,
        delta={'reference': theoretical.get('W', 0) if theoretical else 0},
        title={'text': "Temps Séjour"},
        gauge={
            'axis': {'range': [0, max_sojourn]},
            'bar': {'color': COLORS["accent"]},
        }
    ), row=1, col=3)
    
    fig.update_layout(
        height=300,
        template="plotly_white"
    )
    
    return fig


def create_queue_animation(
    results: SimulationResults,
    sample_rate: int = 10
) -> go.Figure:
    """Create animated queue length visualization."""
    
    if not results.queue_length_history:
        fig = go.Figure()
        fig.add_annotation(text="No queue data", x=0.5, y=0.5)
        return fig
    
    times, lengths = zip(*results.queue_length_history[::sample_rate])
    
    fig = go.Figure()
    
    # Area plot
    fig.add_trace(go.Scatter(
        x=times,
        y=lengths,
        mode='lines',
        fill='tozeroy',
        line=dict(color=COLORS["primary"], width=1),
        fillcolor=f'rgba(99, 102, 241, 0.3)',
        name='Longueur file'
    ))
    
    # Mean line
    mean_length = np.mean(lengths)
    fig.add_hline(
        y=mean_length,
        line_dash="dash",
        line_color=COLORS["success"],
        annotation_text=f"Moyenne: {mean_length:.1f}"
    )
    
    fig.update_layout(
        title="Évolution de la longueur de file",
        xaxis_title="Temps",
        yaxis_title="Nombre en file",
        template="plotly_white",
        hovermode="x unified"
    )
    
    # Add range slider
    fig.update_xaxes(rangeslider_visible=True)
    
    return fig


def create_population_sunburst(
    results: SimulationResults
) -> go.Figure:
    """Create sunburst chart showing population breakdown."""
    
    pop_metrics = results.metrics_by_population
    
    if not pop_metrics:
        fig = go.Figure()
        fig.add_annotation(text="No population data", x=0.5, y=0.5)
        return fig
    
    # Build hierarchy data
    labels = ["Total"]
    parents = [""]
    values = [results.total_completed]
    colors = [COLORS["primary"]]
    
    for pop, metrics in pop_metrics.items():
        labels.append(pop)
        parents.append("Total")
        values.append(metrics["count"])
        colors.append(COLORS.get(pop, COLORS["secondary"]))
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors),
        branchvalues="total"
    ))
    
    fig.update_layout(
        title="Répartition par population",
        template="plotly_white"
    )
    
    return fig


def create_dashboard(
    results: SimulationResults,
    theoretical: Optional[Dict[str, float]] = None,
    title: str = "Tableau de bord - Simulation"
) -> go.Figure:
    """
    Create comprehensive interactive dashboard.
    
    Combines multiple visualizations into a single view.
    """
    
    fig = make_subplots(
        rows=3, cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy", "colspan": 2}, None]
        ],
        subplot_titles=[
            "Utilisation Serveur", "Taux de Rejet",
            "Distribution Temps de Séjour", "Distribution Temps d'Attente",
            "Évolution Longueur de File"
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    # Row 1: Gauges
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=results.server_utilization * 100,
        number={'suffix': "%"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': COLORS["primary"]},
            'steps': [
                {'range': [0, 70], 'color': '#E0E7FF'},
                {'range': [70, 90], 'color': '#FDE68A'},
                {'range': [90, 100], 'color': '#FECACA'}
            ]
        }
    ), row=1, col=1)
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=results.rejection_rate * 100,
        number={'suffix': "%", 'valueformat': ".2f"},
        gauge={
            'axis': {'range': [0, 10]},
            'bar': {'color': COLORS["secondary"]},
            'steps': [
                {'range': [0, 1], 'color': '#D1FAE5'},
                {'range': [1, 5], 'color': '#FDE68A'},
                {'range': [5, 10], 'color': '#FECACA'}
            ]
        }
    ), row=1, col=2)
    
    # Row 2: Distributions
    sojourn_times = [j.sojourn_time for j in results.completed_jobs if j.sojourn_time]
    waiting_times = [j.waiting_time for j in results.completed_jobs if j.waiting_time]
    
    if sojourn_times:
        fig.add_trace(go.Histogram(
            x=sojourn_times,
            nbinsx=30,
            marker_color=COLORS["primary"],
            opacity=0.7,
            name="Séjour"
        ), row=2, col=1)
    
    if waiting_times:
        fig.add_trace(go.Histogram(
            x=waiting_times,
            nbinsx=30,
            marker_color=COLORS["secondary"],
            opacity=0.7,
            name="Attente"
        ), row=2, col=2)
    
    # Row 3: Queue length timeline
    if results.queue_length_history:
        times, lengths = zip(*results.queue_length_history[::5])  # Sample for performance
        fig.add_trace(go.Scatter(
            x=times,
            y=lengths,
            mode='lines',
            fill='tozeroy',
            line=dict(color=COLORS["primary"], width=1),
            fillcolor=f'rgba(99, 102, 241, 0.3)',
            name='File'
        ), row=3, col=1)
    
    # Layout
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b><br><sup>λ={results.arrival_rate}, μ={results.service_rate}, K={results.queue_capacity}</sup>",
            x=0.5
        ),
        height=900,
        showlegend=False,
        template="plotly_white"
    )
    
    # Axis labels
    fig.update_xaxes(title_text="Temps de séjour", row=2, col=1)
    fig.update_xaxes(title_text="Temps d'attente", row=2, col=2)
    fig.update_xaxes(title_text="Temps", row=3, col=1)
    fig.update_yaxes(title_text="Fréquence", row=2, col=1)
    fig.update_yaxes(title_text="Fréquence", row=2, col=2)
    fig.update_yaxes(title_text="Longueur file", row=3, col=1)
    
    return fig


def create_comparison_dashboard(
    results_list: List[SimulationResults],
    labels: List[str]
) -> go.Figure:
    """
    Create dashboard comparing multiple scenarios.
    """
    
    fig = make_subplots(
        rows=2, cols=2,
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "box", "colspan": 2}, None]
        ],
        subplot_titles=[
            "Temps de Séjour Moyen", "Taux de Rejet",
            "Distribution Temps de Séjour"
        ]
    )
    
    colors = [COLORS["primary"], COLORS["secondary"], COLORS["accent"], 
              COLORS["success"], COLORS["warning"]]
    
    # Bar charts
    means = [r.mean_sojourn_time for r in results_list]
    rejections = [r.rejection_rate * 100 for r in results_list]
    
    fig.add_trace(go.Bar(
        x=labels,
        y=means,
        marker_color=colors[:len(labels)],
        name="Temps séjour"
    ), row=1, col=1)
    
    fig.add_trace(go.Bar(
        x=labels,
        y=rejections,
        marker_color=colors[:len(labels)],
        name="Rejet %"
    ), row=1, col=2)
    
    # Box plots
    for i, (results, label) in enumerate(zip(results_list, labels)):
        sojourn_times = [j.sojourn_time for j in results.completed_jobs if j.sojourn_time]
        if sojourn_times:
            fig.add_trace(go.Box(
                y=sojourn_times,
                name=label,
                marker_color=colors[i % len(colors)]
            ), row=2, col=1)
    
    fig.update_layout(
        title="Comparaison des Scénarios",
        height=700,
        template="plotly_white"
    )
    
    return fig


def show_dashboard(
    results: SimulationResults,
    theoretical: Optional[Dict[str, float]] = None,
    port: int = 8050
):
    """
    Launch interactive dashboard in browser.
    
    Note: This requires dash to be installed.
    For simple usage, just call create_dashboard() and use fig.show()
    """
    fig = create_dashboard(results, theoretical)
    fig.show()
