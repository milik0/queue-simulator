#!/bin/bash

uv run sim waterfall-report --mu1 0.34 --arrival deadline

# ╭────────── Analysis Parameters ───────────╮
# │ Configuration Audit: Waterfall           │
# │ K=4, ks=10, kf=5                         │
# │ Exec Rate (Global)=1.36, Return Rate=2.0 │
# │ Backup: Disabled, Arrival Law: deadline  │
# ╰──────────────────────────────────────────╯
# ┏━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
# ┃ Load (ρ) ┃ Arrival (λ) ┃ Reject Exec ┃ Page Blanche ┃ Total Reject ┃ Mean Wait ┃
# ┡━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
# │ 0.5      │ 0.68        │       54.9% │         0.7% │        55.6% │     7.52s │
# │ 0.7      │ 0.95        │       61.7% │         1.0% │        62.7% │     8.73s │
# │ 0.9      │ 1.22        │       69.0% │         0.9% │        69.9% │    10.17s │
# │ 1.1+     │ 1.50        │       74.5% │         0.8% │        75.2% │    10.83s │
# └──────────┴─────────────┴─────────────┴──────────────┴──────────────┴───────────┘

# Note: 'Page Blanche' indicates overflow at the Return Stage (Stage 2).