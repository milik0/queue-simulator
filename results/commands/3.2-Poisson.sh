#!/bin/bash

uv run sim waterfall-report --mu1 0.34

# ╭────────── Analysis Parameters ───────────╮
# │ Configuration Audit: Waterfall           │
# │ K=4, ks=10, kf=5                         │
# │ Exec Rate (Global)=1.36, Return Rate=2.0 │
# │ Backup: Disabled, Arrival Law: poisson   │
# ╰──────────────────────────────────────────╯
# ┏━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
# ┃ Load (ρ) ┃ Arrival (λ) ┃ Reject Exec ┃ Page Blanche ┃ Total Reject ┃ Mean Wait ┃
# ┡━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
# │ 0.5      │ 0.68        │        0.0% │         0.1% │         0.1% │     3.99s │
# │ 0.7      │ 0.95        │        0.3% │         0.5% │         0.8% │     4.85s │
# │ 0.9      │ 1.22        │        4.1% │         1.2% │         5.3% │     6.45s │
# │ 1.1+     │ 1.50        │       13.1% │         2.1% │        15.2% │     8.45s │
# └──────────┴─────────────┴─────────────┴──────────────┴──────────────┴───────────┘

# Note: 'Page Blanche' indicates overflow at the Return Stage (Stage 2).