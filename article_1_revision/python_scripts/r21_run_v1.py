"""
r21_run_v1.py — dispatcher of the leave-cohort-out validation (plan WP7 step 7.2; D8).

Runs on the harmonization pod (RUNBOOK.md). For each scenario (C RNA-seq only, K FFPE
only, J FF only, S0 all samples) × fold 1–5, the TRAINING part (4/5 of the cohorts) and
the TEST part (1/5) of output/wp7/fold_samples.tsv are prepared (softImpute) and
harmonized SEPARATELY with all 31 analysed methods (revision_lib.ANALYSED_METHODS), post0
→ 40 subsets × 31 = 1,240 harmonizations, on S3 under revision_261029/v1/.

--pilot: scenario C, fold 1, train + test (2 × 31 = 62 jobs): run time per method and
failure modes. The fallback of decision D8 is decided at gate G3 and applied with
--exclude-methods. Gate G3 (Daniil, 2026-11-03): every method is kept except exploBATCH
(36_explobatch, excluded by default: its R dependency fMM is not in the ComboBatch image —
the pilot runs stopped after 2 s with "fMM R package not available"); the time limit is
6 h per run (--timeout-s 21600, the default), a run over it is recorded as "timeout".

Usage (inside the pod, from /app/article_1_revision)
-----
python r21_run_v1.py --pilot --dry-run                # 62 jobs listed
python r21_run_v1.py --dry-run                        # 1,240 jobs listed
python r21_run_v1.py --scenario C --skip-if-exists --n-workers 4 > /workspace/revision/v1_C.log 2>&1
"""

from __future__ import annotations

import argparse

import revision_dispatch as rd
import revision_lib as rl


def main() -> None:
    """Parse the flags and run the leave-cohort-out harmonizations."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    rd.add_common_arguments(parser)
    parser.add_argument("--n-prep-workers", type=int, default=2)
    parser.add_argument(
        "--scenario", default="", help="C, K, J or S0 (comma-separated)"
    )
    parser.add_argument("--fold", default="", help="1–5 (comma-separated)")
    parser.add_argument(
        "--exclude-methods",
        default="36_explobatch",
        help="comma-separated method ids dropped by the D8 fallback",
    )
    args = parser.parse_args()
    scenarios = args.scenario.split(",") if args.scenario else None
    folds = [int(f) for f in args.fold.split(",")] if args.fold else None
    subsets = rd.v1_subsets(pilot=args.pilot, scenarios=scenarios, folds=folds)
    excluded = set(filter(None, args.exclude_methods.split(",")))
    methods = [m for m in rl.ANALYSED_METHODS if m not in excluded]
    rd.harmonization_main("v1", subsets, methods, args)


if __name__ == "__main__":
    main()
