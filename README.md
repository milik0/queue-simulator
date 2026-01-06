# ERO2 - Queue System Simulator

> Discrete event simulation framework for analyzing the EPITA "moulinette" automatic grading system.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/package%20manager-uv-blueviolet)](https://docs.astral.sh/uv/)

## 🚀 Quick Start

```bash
# Install dependencies
uv sync

# Run baseline M/M/1/K simulation
uv run sim baseline

# Run Waterfall (tandem queues) model
uv run sim waterfall

# Compare regulation policies for heterogeneous populations
uv run sim channels --compare

# Generate persona-specific dashboards (Robert, Valérie, Alex)
uv run sim personas

# Run test scenarios (normal, deadline, exam, failure)
uv run sim scenarios --all

# Stress test to find breaking points
uv run sim stress

# Parameter sweep (load vs sojourn time curve)
uv run sim sweep

# Open interactive dashboard
uv run sim dashboard
```

## 📊 Available Models

### 1. Baseline M/M/1/K
The foundational model for all comparisons. Single server, finite capacity queue with Poisson arrivals and exponential service times.

```bash
uv run sim baseline --lambda 0.8 --mu 1.0 --capacity 10 --duration 10000
```

**Key metrics:** Validates against closed-form theoretical formulas.

---

### 2. Waterfall (Tandem Queues)
Models the two-stage moulinette architecture:
1. **Execution stage:** K parallel servers process submitted code
2. **Return stage:** Single server sends results back to students

```bash
uv run sim waterfall --exec-servers 4 --backup
```

**Key features:**
- Finite queues at each stage
- Backup system to prevent "blank pages"
- Analysis of rejection points

---

### 3. Channels & Dams (Heterogeneous Populations)
Models two distinct user populations:
- **ING:** Frequent submissions, short jobs
- **PREPA:** Rare submissions, long jobs

```bash
# Compare all regulation policies
uv run sim channels --compare

# Run specific policy
uv run sim channels --regulation sjf
```

**Available policies:**
| Policy | Description |
|--------|-------------|
| `none` | FIFO, no regulation |
| `dam` | Periodic blocking of ING submissions |
| `sjf` | Shortest Job First scheduling |
| `dedicated` | Reserved servers for ING |

---

## 📈 Visualizations

All figures are saved to `results/figures/`:

| File | Description |
|------|-------------|
| `baseline_sojourn_dist.png` | Sojourn time distribution with statistics |
| `baseline_waiting_dist.png` | Waiting time distribution |
| `baseline_queue_length.png` | Queue length evolution over time |
| `baseline_utilization.png` | Server utilization timeline |
| `baseline_validation.png` | Theory vs simulation comparison |

### Interactive Dashboard
```bash
uv run sim dashboard
```
Opens a Plotly dashboard with gauges, distributions, and time series.

---

## 🔧 Command Reference

```bash
uv run sim --help              # Show all commands
uv run sim info                # Project information
uv run sim baseline --help     # Baseline options
uv run sim waterfall --help    # Waterfall options
uv run sim channels --help     # Channels options
```

### Common Options

| Option | Description |
|--------|-------------|
| `--lambda, -l` | Arrival rate (λ) |
| `--mu, -m` | Service rate (μ) |
| `--duration, -d` | Simulation duration |
| `--seed, -s` | Random seed for reproducibility |
| `--no-plots` | Disable visualization generation |
| `--output, -o` | Output directory for figures |
