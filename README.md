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

# Generate tables for report
uv run sim baseline-report
uv run sim waterfall-report
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
- **STANDARD:** Frequent submissions, short jobs (e.g. ING)
- **COMPLEX:** Rare submissions, long jobs (e.g. PREPA)

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
| `dam` | Periodic blocking of STANDARD submissions |
| `sjf` | Shortest Job First scheduling |
| `dedicated` | Reserved servers for STANDARD |

---

### 4. Analysis Pipelines

The `pipeline` command enables complex comparisons and sensitivity analyses.

```bash
uv run sim pipeline [OPTIONS]
```

**Common Options:**
- `--mode` / `-m`: Select analysis mode (`params`, `archis`, `loads`).
- `--target` / `-t`: Select model (`baseline`, `waterfall`, `channels`, `advanced`).
- `--scenario` / `-s`: Select workload scenario (`normal`, `deadline`, `exam`).

### Pipeline Modes Detail

#### 1. `params` (Sensitivity Analysis)
Vary one parameter to observe its impact on system performance.

*   **Command**: `uv run sim pipeline --mode params [OPTIONS]`
*   **Options**:
    *   `--target`: Model to analyze.
        *   `baseline`: Standard M/M/1/K.
        *   `waterfall`: Two-stage tandem queue.
        *   `channels`: Heterogeneous populations (Standard/Complex).
        *   `advanced`: Time-varying pattern (arrival_rate = peak rate).
    *   `--param`: Parameter to sweep.
        *   `arrival_rate`: Input traffic intensity ($\lambda$). Range: `> 0` (typically `0.1` to `1.0` for normalized load, or higher for raw rate).
        *   `service_rate`: Processing speed ($\mu$). Range: `> 0` (typically `1.0`).
        *   `capacity`: Max queue size ($K$). Range: `Integer > 0`.
        *   `num_servers`: Number of active servers. Range: `Integer >= 1`.
    *   `--min` / `--max`: Range of values to test.
    *   `--steps`: Number of simulation points.

#### 2. `archis` (Architecture Comparison)
Benchmark all architectures against a specific workload scenario to identify the best design.

*   **Command**: `uv run sim pipeline --mode archis [OPTIONS]`
*   **Options**:
    *   `--scenario`: Predefined workload condition.
        *   `normal`: Standard daily activity ($\lambda=0.5$).
        *   `deadline`: High stress spike ($\lambda=0.8$).
        *   `exam`: Sustained high load ($\lambda=0.95$), increased capacity requirements ($K=50$, $c=6$).
        *   `failure`: Server outage event (1 server fails for 500 time units) during simulation.

#### 3. `loads` (Load Testing)
Evaluate robustness of a specific model by subjecting it to increasing traffic levels.

*   **Command**: `uv run sim pipeline --mode loads [OPTIONS]`
*   **Options**:
    *   `--target`: Model to stress test.
*   **Levels Tested**:
    *   **Low**: $\rho \approx 0.25$ (Light usage)
    *   **Normal**: $\rho \approx 0.60$ (Standard usage)
    *   **High**: $\rho \approx 0.95$ (Near saturation)
    *   **Overload**: $\rho > 1.0$ (System saturation)
