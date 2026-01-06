# Design Document - ERO2 Queue Simulator

> Implementation details, design choices, and persona preferences.

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Architecture Decisions](#architecture-decisions)
3. [Model Implementations](#model-implementations)
4. [Persona Analysis](#persona-analysis)
5. [Statistical Validation](#statistical-validation)
6. [Limitations &amp; Trade-offs](#limitations--trade-offs)

---

## Design Philosophy

### Core Principles

1. **Start Simple, Validate, then Extend**

   - Begin with M/M/1/K baseline that has closed-form solutions
   - Validate simulation against theory before adding complexity
   - Coach feedback: *"Commencer par des modèles simples/naïfs type M/M/1/K"*
2. **Distributions, Not Just Means**

   - Track percentiles (P50, P95, P99), variance, min/max
   - Coach feedback: *"Analyser la distribution des temps (min/max, percentiles, variance)"*
3. **Contextualize for Stakeholders**

   - Every metric should be interpretable by at least one persona
   - Evaluation grid: *"Contextualisation des métriques au regard des différents acteurs"*

---

## Architecture Decisions

### Why SimPy?

| Alternative     | Pros                                       | Cons                                 | Decision  |
| --------------- | ------------------------------------------ | ------------------------------------ | --------- |
| **SimPy** | Python-native, generators, well-documented | Slower than compiled                 | ✅ Chosen |
| salabim         | More features                              | Less popular, steeper learning curve | ❌        |
| Custom loop     | Full control                               | Reinventing the wheel                | ❌        |
| Arena/Simul8    | GUI, industry standard                     | Not Python, not free                 | ❌        |

**Rationale:** SimPy's generator-based approach integrates seamlessly with Python. For academic simulation of ~10K jobs, performance is acceptable.

---

### Why Separate Core/Models/Visualization?

```
core/        → Reusable primitives (Job, Queue, Server)
models/      → Specific simulation scenarios
visualization/ → Decoupled from simulation logic
analysis/    → Statistical tools independent of models
```

**Benefits:**

- Test each layer independently
- Add new model = add new file in `models/`
- Change visualization library without touching simulation
- Matches evaluation criteria: "démarche itérative"

---

### Why Typer for CLI?

| Alternative     | Decision                                    |
| --------------- | ------------------------------------------- |
| argparse        | Verbose, no auto-help                       |
| click           | Good, but Typer is newer and simpler        |
| **Typer** | ✅ Auto-completion, type hints, rich output |

**Rationale:** `uv run sim baseline --lambda 0.8` is readable and self-documenting.

---

## Model Implementations

### 1. Baseline M/M/1/K

**Purpose:** Establish ground truth for validation.

**Implementation Details:**

```python
# Queue capacity = K-1 (since 1 job can be in service)
queue = Queue(env, capacity=K-1)

# Jobs rejected when system size >= K
system_size = len(queue) + (1 if server.is_busy else 0)
if system_size >= K:
    job.status = REJECTED
```

**Key Design Choice:** We interpret K as *total system capacity* (queue + server), not just queue capacity. This matches the standard M/M/1/K definition.

**Validation Results (ρ=0.8, K=10):**

| Metric | Theoretical | Simulated | Error |
| ------ | ----------- | --------- | ----- |
| ρ     | 0.800       | 0.769     | 3.9%  |
| W      | 3.797       | 3.380     | 11.0% |
| Pb     | 2.35%       | 1.63%     | 30.8% |

**Note:** Higher error on Pb is expected for rare events. Longer simulations reduce variance.

---

### 2. Waterfall (Tandem Queues)

**Purpose:** Model the real moulinette architecture.

```
[Arrival] → [Exec Queue (k_s)] → [K Servers] → [Return Queue (k_f)] → [1 Server] → [Done]
                 ↓                                    ↓
            [Rejected]                          [Page Blanche]
                                                unless backup
```

**Implementation Details:**

```python
# Stage 1: Execution
exec_queue = Queue(capacity=k_s)
exec_pool = ServerPool(num_servers=K)

# Stage 2: Return
return_queue = Queue(capacity=k_f)
return_server = Server()

# Backup before return queue
if config.enable_backup:
    job.backed_up = True
  
if not return_queue.enqueue(job):
    if not job.backed_up:
        # Page blanche!
        job.status = REJECTED
```

**Key Design Choice:** Backup happens *before* attempting to enqueue in return queue, consistent with the subject's description.

---

### 3. Channels & Dams

**Purpose:** Model heterogeneous populations (ING vs PREPA).

**Population Parameters:**

| Population | λ (arrivals/min) | μ (service rate) | Job Duration      |
| ---------- | ----------------- | ----------------- | ----------------- |
| ING        | 2.0               | 1.0               | Short (1 min avg) |
| PREPA      | 0.5               | 0.2               | Long (5 min avg)  |

**Regulation Policies:**

#### FIFO (none)

- Simple first-come-first-served
- No differentiation between populations
- **Result:** Similar wait times for both

#### Dam

- Block ING arrivals for `t_b` seconds
- Open for `t_b/2` seconds
- Repeat cycle
- **Result:** Higher wait times for everyone, PREPA slightly benefits during ING block

#### SJF (Shortest Job First)

```python
if discipline == SJF:
    # Insert sorted by service_time
    for i, queued_job in enumerate(queue):
        if job.service_time < queued_job.service_time:
            queue.insert(i, job)
            break
```

- **Result:** ING dramatically favored (W=4 vs W=48 for PREPA)
- **Controversy:** Is this fair?

#### Dedicated Lanes

- Reserve `n` servers exclusively for ING
- Remaining servers shared
- **Result:** Marginal improvement, complex to tune

---

## Persona Analysis

### 🎓 Robert (Student) - "What do I care about?"

**Primary Metrics:**

| Metric            | Threshold    | Why                                 |
| ----------------- | ------------ | ----------------------------------- |
| Waiting time      | < 30 seconds | "I lose my train of thought"        |
| Page blanche rate | < 1%         | "I need to know my code was tested" |
| P95 sojourn       | < 2 minutes  | "I can't wait forever"              |

**Preferred Configuration:**

```bash
uv run sim waterfall --backup  # Ensure no page blanches
uv run sim channels --regulation sjf  # If I'm ING, fast results!
```

**Dashboard View:** Focus on waiting time distribution, highlight threshold violations.

---

### 📊 Valérie (Administration) - "What matters for the school?"

**Primary Metrics:**

| Metric                 | Threshold                  | Why                |
| ---------------------- | -------------------------- | ------------------ |
| 95th percentile < 2min | 95% of students acceptable | SLA-like guarantee |
| Server cost            | Minimize K                 | Budget constraints |
| Rejection rate         | < 5%                       | Avoid complaints   |

**Preferred Configuration:**

```bash
uv run sim sweep  # Find optimal K for target rejection rate
```

**Trade-off Analysis:**

| K (servers) | Rejection Rate | Cost Index |
| ----------- | -------------- | ---------- |
| 3           | 15%            | Low        |
| 5           | 5%             | Medium     |
| 10          | 1%             | High       |

**Recommendation:** K=5 with backup enabled balances cost and quality.

---

### ⚙️ Alex (Tech Lead) - "Give me the config values"

**Primary Metrics:**

| Metric           | Parameter          | Why              |
| ---------------- | ------------------ | ---------------- |
| Queue length max | k_s, k_f           | Memory bounds    |
| Utilization      | ρ < 0.9           | Avoid saturation |
| Bottleneck       | Stage 1 vs Stage 2 | Where to scale   |

**Preferred Configuration:**

```bash
uv run sim waterfall --exec-capacity 20 --return-capacity 10
```

**Config Recommendations:**

```yaml
# config.yaml (example output format)
execution:
  servers: 4
  queue_capacity: 20
  warning_threshold: 15

return:
  servers: 1
  queue_capacity: 10
  backup_enabled: true
  backup_mode: systematic  # vs random

regulation:
  policy: none  # or dam with t_b=30s
  dam_block_time: 30
  dam_open_time: 15
```

---

## Statistical Validation

### Warm-up Period

We discard the first 10% of simulation time to reach steady-state:

```python
warmup = duration * 0.1
if job.arrival_time >= warmup:
    collector.record_job(job)
```

**Justification:** Queue starts empty, initial transient behavior not representative.

### Confidence Intervals

Using t-distribution for mean estimates:

```python
def confidence_interval(data, confidence=0.95):
    n = len(data)
    mean = np.mean(data)
    se = stats.sem(data)
    h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
    return (mean - h, mean + h)
```

### Multiple Runs

For parameter sweeps, we average over `n_runs=5` with different seeds:

```python
for run in range(n_runs):
    sim = MM1KSimulation(seed=42 + run)
    results.append(sim.run())
# Report mean ± std
```

---

## Limitations & Trade-offs

### 1. Exponential Distribution Assumption

**Assumption:** Service times are exponentially distributed.

**Reality:** Code execution times may be:

- Deterministic (fixed test suite)
- Multi-modal (simple vs complex submissions)
- Heavy-tailed (compilation failures, infinite loops)

**Mitigation:** The framework supports custom arrival generators (`NonHomogeneousArrivals`, `BatchArrivals`). Extend for other distributions.

### 2. Simplified Backup

**Current:** Backup is instantaneous with no capacity limit.

**Reality:** Backup storage has latency and finite capacity.

**Future:** Add backup queue with its own capacity/service time.

### 3. Population Homogeneity

**Current:** All ING students have same λ, μ.

**Reality:** Individual students have varying habits.

**Mitigation:** Batch arrivals model captures some group behavior.

### 4. Single Server Return Stage

**Current:** Return stage has exactly 1 server.

**Reality:** Could be parallelized.

**Extension:** Use `ServerPool` for return stage with configurable `k`.

---

## Conclusion

This simulator provides a robust foundation for analyzing the moulinette queue system. The modular architecture allows for:

1. **Validation** against known theoretical results
2. **Exploration** of different configurations
3. **Communication** with stakeholders via tailored metrics

Each persona gets actionable insights:

- **Robert:** Use backup, expect < 30s wait
- **Valérie:** K=5 balances cost and quality
- **Alex:** Set k_s=20, k_f=10, enable backup

Future work: Real data calibration, non-exponential service times, multi-tenancy.
