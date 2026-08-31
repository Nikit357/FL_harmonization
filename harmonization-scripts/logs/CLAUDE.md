# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Directory Purpose

Archive of captured pod run logs and diagnostic screenshots from K8s benchmark runs. Files here are historical artifacts — not inputs to any script.

## Contents

| File | Contents |
|---|---|
| `norm_log_affy.txt` | `run_norm_parallel.py` stdout for `G_affymetrix_only` strategy (3 prepared pairs × 24 methods = 72 jobs); captured via `cat norm_affy.log` inside the pod |
| `norm_log_microarrays.txt` | Same for `F_microarray_only` strategy (72 jobs) |
| `htop_pod_screenshot.png` | `htop` screenshot from inside the pod during a normalization run — shows CPU/RAM usage per worker subprocess |

## Log Format

Each line follows the pattern:
```
[HH:MM:SS] START {strat}×{imp}×{method} | free=NNN.NGB
  [N/total] {strat}×{imp}×{method} (Ns) → ['status', 'status']
```
`status` values: `ok` (ran and uploaded), `cached` (S3 key already existed — skip-if-exists), `skipped` (NotImplementedError), `failed`.

The `DtypeWarning` lines about mixed-type columns are harmless — they come from `pd.read_csv` on the annotation file and do not affect results.
