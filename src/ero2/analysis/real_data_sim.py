
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
import matplotlib.pyplot as plt
from src.ero2.analysis.data_loader import load_submissions, compute_stats, print_stats
from src.ero2.models.waterfall import run_waterfall, analyze_backup_impact, WaterfallConfig
from src.ero2.models.scenarios import run_channels_dams, compare_regulation_policies


def run_real_data_analysis(csv_path: str = "submissions.csv"):
    """
    Run complete analysis with real data calibration.
    """
    print("=" * 70)
    print("ANALYSE AVEC DONNÉES RÉELLES DE LA FORGE")
    print("=" * 70)
    
    # Load and analyze real data
    df = load_submissions(csv_path)
    stats = compute_stats(df)
    print_stats(stats)
    
    # Determine required servers for stability (ρ < 1)
    lambda_pm = stats.lambda_per_minute
    mu_pm = stats.mu_per_minute
    
    K_required = int(np.ceil(lambda_pm / mu_pm)) + 1
    print(f"\nTo achieve rho < 1, a minimum of K = {K_required} servers is required")
    
    # Simulate with realistic K
    print("\n" + "=" * 70)
    print(f"WATERFALL SIMULATION WITH K = {K_required} SERVERS")
    print("=" * 70)
    
    # Scale parameters for simulation (use per-minute rates)
    # Note: simulation uses per-unit-time, so we scale appropriately
    sim_lambda = lambda_pm  # arrivals per minute
    sim_mu = mu_pm          # service rate per minute
    
    print(f"\nCalibrated parameters:")
    print(f"  lambda = {sim_lambda:.4f}/min")
    print(f"  mu = {sim_mu:.5f}/min")
    print(f"  rho (K={K_required}) = {sim_lambda / (K_required * sim_mu):.2f}"  )
    
    # Run waterfall simulation
    print("\n--- Without backup ---")
    results_no_backup = run_waterfall(
        arrival_rate=sim_lambda,
        num_exec_servers=K_required,
        exec_service_rate=sim_mu,
        exec_queue_capacity=50,
        return_service_rate=sim_mu * 2,  # Return is faster
        return_queue_capacity=20,
        enable_backup=False,
        duration=5000,
        seed=42
    )
    
    print("\n--- With systematic backup ---")
    results_with_backup = run_waterfall(
        arrival_rate=sim_lambda,
        num_exec_servers=K_required,
        exec_service_rate=sim_mu,
        exec_queue_capacity=50,
        return_service_rate=sim_mu * 2,
        return_queue_capacity=20,
        enable_backup=True,
        duration=5000,
        seed=42
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY (calibrated on real data)")
    print("=" * 70)
    print(f"\nWith K = {K_required} servers:")
    print(f"  Without backup:  Page blanche rate = {results_no_backup.page_blanche_rate:.2%}")
    print(f"  With backup:     Page blanche rate = {results_with_backup.page_blanche_rate:.2%}")
    
    improvement = 1 - (results_with_backup.page_blanche_rate / max(results_no_backup.page_blanche_rate, 0.001))
    print(f"\nPage blanche reduction: {improvement:.0%}")
    
    return stats, results_no_backup, results_with_backup


def plot_hourly_distribution(df, save_path: str = None):
    """Plot hourly distribution of submissions."""
    hourly = df.groupby('hour').size()
    
    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(hourly.index, hourly.values, color='steelblue', edgecolor='black')
    
    # Highlight peak hours
    peak_hours = hourly.nlargest(3).index.tolist()
    for i, bar in enumerate(bars):
        if bar.get_x() + bar.get_width()/2 in peak_hours:
            bar.set_color('coral')
    
    ax.set_xlabel('Hour of day')
    ax.set_ylabel('Number of submissions')
    ax.set_title('Hourly distribution of submissions (real Forge data)')
    ax.set_xticks(range(24))
    ax.grid(axis='y', alpha=0.3)
    
    # Add line for average
    avg = hourly.mean()
    ax.axhline(y=avg, color='red', linestyle='--', label=f'Mean: {avg:.0f}')
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Figure saved: {save_path}")
    
    return fig


def plot_service_time_distribution(df, save_path: str = None):
    """Plot service time distribution."""
    service_times_min = df['service_time'] / 60  # Convert to minutes
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Histogram
    axes[0].hist(service_times_min, bins=50, color='steelblue', edgecolor='black', alpha=0.7)
    axes[0].axvline(x=service_times_min.mean(), color='red', linestyle='--', 
                   label=f'Mean: {service_times_min.mean():.1f} min')
    axes[0].axvline(x=service_times_min.median(), color='green', linestyle='--',
                   label=f'Median: {service_times_min.median():.1f} min')
    axes[0].set_xlabel('Service time (minutes)')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('Service time distribution')
    axes[0].legend()
    
    # Box plot
    axes[1].boxplot(service_times_min, vert=True)
    axes[1].set_ylabel('Service time (minutes)')
    axes[1].set_title('Box plot')
    axes[1].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Figure saved: {save_path}")
    
    return fig


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "submissions.csv"
    
    # Run analysis
    stats, r_no_backup, r_backup = run_real_data_analysis(csv_path)
    
    # Generate plots
    print("\nGenerating plots...")
    df = load_submissions(csv_path)
    
    plot_hourly_distribution(df, "results/figures/hourly_distribution.png")
    plot_service_time_distribution(df, "results/figures/service_time_distribution.png")
    
    print("\nAnalysis complete!")
