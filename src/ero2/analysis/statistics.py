"""Statistical analysis utilities for simulation validation."""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from scipy import stats
from dataclasses import dataclass

from .theoretical import TheoreticalMetrics


def confidence_interval(
    data: List[float],
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate confidence interval for the mean using t-distribution.
    
    Args:
        data: Sample data
        confidence: Confidence level (default 95%)
    
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if len(data) < 2:
        mean = data[0] if data else 0.0
        return (mean, mean)
    
    n = len(data)
    mean = np.mean(data)
    se = stats.sem(data)
    h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
    
    return (mean - h, mean + h)


def bootstrap_ci(
    data: List[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    statistic: str = "mean"
) -> Tuple[float, float]:
    """
    Calculate bootstrap confidence interval.
    
    More robust for non-normal distributions (like waiting times).
    
    Args:
        data: Sample data
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level
        statistic: "mean", "median", or "p95"
    
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if len(data) < 2:
        val = data[0] if data else 0.0
        return (val, val)
    
    data_array = np.array(data)
    rng = np.random.default_rng(42)
    
    # Generate bootstrap samples
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        sample = rng.choice(data_array, size=len(data_array), replace=True)
        if statistic == "mean":
            bootstrap_stats.append(np.mean(sample))
        elif statistic == "median":
            bootstrap_stats.append(np.median(sample))
        elif statistic == "p95":
            bootstrap_stats.append(np.percentile(sample, 95))
    
    # Calculate percentile confidence interval
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))
    
    return (lower, upper)


def compare_distributions(
    data1: List[float],
    data2: List[float],
    alpha: float = 0.05,
    test_type: str = "mannwhitney"
) -> Dict[str, Any]:
    """
    Compare two distributions statistically.
    
    Args:
        data1: First sample
        data2: Second sample
        alpha: Significance level
        test_type: "mannwhitney" or "ks" (Kolmogorov-Smirnov)
    
    Returns:
        Dictionary with test results
    """
    if len(data1) < 3 or len(data2) < 3:
        return {
            "error": "Insufficient data",
            "n1": len(data1),
            "n2": len(data2)
        }
    
    result = {
        "n1": len(data1),
        "n2": len(data2),
        "mean1": np.mean(data1),
        "mean2": np.mean(data2),
        "std1": np.std(data1),
        "std2": np.std(data2),
        "median1": np.median(data1),
        "median2": np.median(data2),
    }
    
    if test_type == "mannwhitney":
        stat, pvalue = stats.mannwhitneyu(data1, data2, alternative='two-sided')
        result["test"] = "Mann-Whitney U"
    else:  # Kolmogorov-Smirnov
        stat, pvalue = stats.ks_2samp(data1, data2)
        result["test"] = "Kolmogorov-Smirnov"
    
    result["statistic"] = stat
    result["p_value"] = pvalue
    result["significant"] = pvalue < alpha
    result["alpha"] = alpha
    
    # Effect size (Cohen's d)
    pooled_std = np.sqrt((np.var(data1) + np.var(data2)) / 2)
    if pooled_std > 0:
        result["cohens_d"] = (np.mean(data1) - np.mean(data2)) / pooled_std
    else:
        result["cohens_d"] = 0.0
    
    return result


@dataclass
class ValidationResult:
    """Result of validating simulation against theory."""
    metric_name: str
    theoretical_value: float
    simulated_value: float
    ci_lower: float
    ci_upper: float
    relative_error: float
    within_ci: bool
    acceptable: bool  # Within 10% or CI contains theoretical value


def validate_against_theory(
    simulated: Dict[str, float],
    theoretical: TheoreticalMetrics,
    sojourn_times: Optional[List[float]] = None,
    waiting_times: Optional[List[float]] = None,
    tolerance: float = 0.10
) -> Dict[str, ValidationResult]:
    """
    Validate simulated metrics against theoretical predictions.
    
    Args:
        simulated: Dictionary of simulated metrics
        theoretical: Theoretical values
        sojourn_times: Raw sojourn time data for CI
        waiting_times: Raw waiting time data for CI
        tolerance: Acceptable relative error (default 10%)
    
    Returns:
        Dictionary of ValidationResult for each metric
    """
    results = {}
    
    # Define metrics to validate
    validations = [
        ("utilization", theoretical.rho, simulated.get("server_utilization", 0)),
        ("mean_sojourn_time", theoretical.W, simulated.get("mean_sojourn_time", 0)),
        ("mean_waiting_time", theoretical.Wq, simulated.get("mean_waiting_time", 0)),
        ("mean_queue_length", theoretical.Lq, simulated.get("mean_queue_length", 0)),
    ]
    
    if theoretical.Pb > 0:
        validations.append(
            ("rejection_rate", theoretical.Pb, simulated.get("rejection_rate", 0))
        )
    
    for name, theory_val, sim_val in validations:
        # Calculate relative error
        if theory_val != 0:
            rel_error = abs(sim_val - theory_val) / theory_val
        else:
            rel_error = 0.0 if sim_val == 0 else float('inf')
        
        # Calculate CI if raw data available
        ci_lower, ci_upper = sim_val, sim_val
        if name == "mean_sojourn_time" and sojourn_times:
            ci_lower, ci_upper = confidence_interval(sojourn_times)
        elif name == "mean_waiting_time" and waiting_times:
            ci_lower, ci_upper = confidence_interval(waiting_times)
        
        # Check if theoretical value is within CI
        within_ci = ci_lower <= theory_val <= ci_upper
        
        # Acceptable if within tolerance OR within CI
        acceptable = rel_error <= tolerance or within_ci
        
        results[name] = ValidationResult(
            metric_name=name,
            theoretical_value=theory_val,
            simulated_value=sim_val,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            relative_error=rel_error,
            within_ci=within_ci,
            acceptable=acceptable
        )
    
    return results


def print_validation_results(results: Dict[str, ValidationResult]):
    """Pretty print validation results."""
    print("\n" + "=" * 80)
    print(" SIMULATION VALIDATION RESULTS")
    print("=" * 80)
    print(f"{'Metric':<25} {'Theory':>10} {'Simulated':>10} {'95% CI':>20} {'Error':>8} {'OK?':>6}")
    print("-" * 80)
    
    for name, r in results.items():
        ci_str = f"[{r.ci_lower:.3f}, {r.ci_upper:.3f}]"
        ok_str = "✓" if r.acceptable else "✗"
        error_str = f"{r.relative_error*100:.1f}%"
        
        print(f"{name:<25} {r.theoretical_value:>10.4f} {r.simulated_value:>10.4f} {ci_str:>20} {error_str:>8} {ok_str:>6}")
    
    print("=" * 80)
    
    all_ok = all(r.acceptable for r in results.values())
    if all_ok:
        print("✓ All metrics within acceptable tolerance")
    else:
        failed = [name for name, r in results.items() if not r.acceptable]
        print(f"✗ Metrics outside tolerance: {', '.join(failed)}")


def aggregate_runs(
    results_list: List[Dict[str, float]]
) -> Dict[str, Dict[str, float]]:
    """
    Aggregate statistics across multiple simulation runs.
    
    Args:
        results_list: List of result dictionaries from multiple runs
    
    Returns:
        Dictionary with mean, std, and CI for each metric
    """
    if not results_list:
        return {}
    
    # Get all metric names from first result
    metric_names = list(results_list[0].keys())
    
    aggregated = {}
    for name in metric_names:
        values = [r[name] for r in results_list if name in r]
        if values and all(isinstance(v, (int, float)) for v in values):
            ci_low, ci_high = confidence_interval(values)
            aggregated[name] = {
                "mean": np.mean(values),
                "std": np.std(values),
                "min": min(values),
                "max": max(values),
                "ci_lower": ci_low,
                "ci_upper": ci_high,
                "n_runs": len(values)
            }
    
    return aggregated
