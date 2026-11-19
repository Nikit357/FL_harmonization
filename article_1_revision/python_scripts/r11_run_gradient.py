"""
r11_run_gradient.py — dispatcher of the confounding gradient (plan WP6 steps 6.2–6.4).

Runs on the harmonization pod (label app=fl-revision; RUNBOOK.md). For each of the 45
designs of output/wp6/designs/designs.tsv: softImpute preparation (frozen functions via
revision_lib.prepare_subset), then the 14 arms of revision_lib.GRADIENT_ARMS (post0, no
post-removal): 01_raw, limma, SVA, SVA without the diagnosis covariate, ComBat, ComBat
without it, MNN, FSMVN, FSQN R, quantile, AMDBNorm, Harmony, and since 2026-11-07 Angel
and M-ComBat (added after the visual check selected them) → 630 harmonizations.
Outputs on S3 under FL_batch_correction/revision_261029/gradient/.

--pilot: λ = 0 and λ = 1, replicate 1, cap 150 (2 designs × 14 arms = 28 jobs; the 2026-11-01 pilot ran 24 with the 12 original arms): run time,
the covariate-free wrappers, and the λ = 1 failures of the covariate arms (a failure is
recorded as a result, plan caveat C3).

Usage (inside the pod, from /app/article_1_revision)
-----
python r11_run_gradient.py --pilot --dry-run          # 28 jobs listed
setsid nohup python r11_run_gradient.py --pilot --skip-if-exists --n-workers 4 \
    > /workspace/revision/gradient_pilot.log 2>&1 &
python r11_run_gradient.py --dry-run                  # 630 jobs listed (90 to run with --skip-if-exists)
"""

from __future__ import annotations

import argparse

import revision_dispatch as rd
import revision_lib as rl


def main() -> None:
    """Parse the flags and run the gradient."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    rd.add_common_arguments(parser)
    parser.add_argument("--n-prep-workers", type=int, default=2)
    parser.add_argument(
        "--designs",
        default="",
        help="comma-separated design ids (default: all, or the pilot)",
    )
    args = parser.parse_args()
    subsets = (
        args.designs.split(",")
        if args.designs
        else rd.gradient_subsets(pilot=args.pilot)
    )
    rd.harmonization_main("gradient", subsets, list(rl.GRADIENT_ARMS), args)


if __name__ == "__main__":
    main()
