#!/bin/bash

uv run sim waterfall-report --mu1 0.34 --backup
# ╭────────── Analysis Parameters ───────────╮
# │ Configuration Audit: Waterfall           │
# │ K=4, ks=10, kf=5                         │
# │ Exec Rate (Global)=1.36, Return Rate=2.0 │
# │ Backup: Enabled, Arrival Law: poisson    │
# ╰──────────────────────────────────────────╯
# ┏━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
# ┃ Load (ρ) ┃ Arrival (λ) ┃ Reject Exec ┃ Page Blanche ┃ Total Reject ┃ Mean Wait ┃
# ┡━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
# │ 0.5      │ 0.68        │        0.0% │         0.0% │         0.0% │     3.99s │
# │ 0.7      │ 0.95        │        0.5% │         0.0% │         0.5% │     4.89s │
# │ 0.9      │ 1.22        │        4.8% │         0.0% │         4.8% │     6.69s │
# │ 1.1+     │ 1.50        │       12.3% │         0.0% │        12.3% │     8.03s │
# └──────────┴─────────────┴─────────────┴──────────────┴──────────────┴───────────┘

# Note: 'Page Blanche' indicates overflow at the Return Stage (Stage 2).