#!/bin/bash

uv run sim baseline-report -l 1.4 -m 0.34 -k 4

# ╭────────────── Baseline Report ───────────────╮
# │ Architecture A: Baseline (Infinite Capacity) │
# │ Configuration:                               │
# │ — Infinite Queue Capacity                    │
# │ — K = 4 execution servers                    │
# │ — λ = 1.4, μ = 0.34                          │
# ╰──────────────────────────────────────────────╯
# ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
# ┃ Metric             ┃                 Value ┃
# ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
# │ Mean Sojourn Time  │              164.68 s │
# │ Standard Deviation │              133.99 s │
# │ P95 Sojourn Time   │              386.76 s │
# │ Utilization        │                 98.5% │
# │ Rejection Rate     │ 0.0% (Theoretical 0%) │
# └────────────────────┴───────────────────────┘