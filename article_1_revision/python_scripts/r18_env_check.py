"""
r18_env_check.py — does the revision pod's environment reproduce the published
benchmark?

Plan `revision_pod_combobatch_image_plan_261101.md` §4 (decision B2). The revision pods
run on the ComboBatch image (`ghcr.io/nikit357/combobatch:20260830`), not on the 2026
benchmark environment, so package versions may differ. Before the pilots, this script
re-runs published approaches with the frozen code in the pod and compares the result
with the published matrices on S3. Nothing frozen is edited; only S3 is read, plus one
JSON written.

Part 1 — frozen `bench_shared` methods with deterministic output (default
`17_quantile`, `16_fsqn_r`, `10_mnn`, `04_sva`) on the published prepared pair
`<strat> × strict` (default `C_rnaseq_only`), with the exact call of the frozen
`run_norm_job.py`
(`METHODS[m][0](exp, ann, batch_col=BATCH_COL, bio_col=BIO_COL)`, post-removal off =
the `__post0` output).

Part 2 — 20_shambhala: `rl.shambhala_fast` (Shambhala2_fast, P0 / Q0 standard) on a
random subset of the samples of `<strat>` (default 200 samples, seed 0), compared with
those rows of the published `shambhala_P0std_Q0std` matrix. The input is these samples
from the prepared **S0** matrix (3,447 genes), as in the published run, which
harmonized S0 once and cut the strategies out of it. Shambhala works per sample but
CuBlock clusters genes, so the gene set matters: the same samples with `<strat>`'s own
genes give other values (2026-11-01: r 0.993 with C's 6,797 genes, 0.99999 with S0's).
Output values are on a linear scale (median ~1,400), so max |Δ| is large in absolute
terms; the verdict rests on r.

Interpretation (per method): max |Δ| < 1e-6 → "identical"; Pearson r > 0.9999 →
"equivalent" (minor version drift); anything else → "DIFFERENT": stop and report at
gate G3 before any comparison with the main benchmark.

Output: `revision_261029/env_check/env_check__<YYMMDD>.json` and a printed table.

    python r18_env_check.py
    python r18_env_check.py --methods 17_quantile --shambhala-samples 0   # quick
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import time
import traceback

import numpy as np
import pandas as pd

import revision_lib as rl

DEFAULT_METHODS: tuple[str, ...] = ("17_quantile", "16_fsqn_r", "10_mnn", "04_sva")
SHAMBHALA_PUBLISHED_NAME: str = "shambhala_P0std_Q0std"
IDENTICAL_MAX_ABS: float = 1e-6
EQUIVALENT_R: float = 0.9999
PYTHON_PACKAGES: tuple[str, ...] = (
    "numpy",
    "pandas",
    "scikit-learn",
    "rpy2",
    "harmonypy",
    "scanorama",
    "combat",
    "inmoose",
    "qnorm",
)
R_PACKAGES: tuple[str, ...] = (
    "sva",
    "limma",
    "batchelor",
    "FSQN",
    "qsmooth",
    "AMDBNorm",
)


def compare_matrices(
    new: pd.DataFrame, published: pd.DataFrame, require_same_shape: bool = True
) -> dict:
    """
    Compare a re-computed matrix with the published one on their shared cells.

    Parameters
    ----------
    new, published
        Samples × genes.
    require_same_shape
        False for Shambhala: the published matrix comes from the S0 run, whose gene
        set (input ∩ P ∩ Q after NaN-gene removal) can differ from the subset's.

    Returns
    -------
    dict
        Shapes, shared samples / genes, max and median |Δ|, Pearson r of the
        flattened shared cells (NaN in either matrix excluded) and a verdict:
        "identical", "equivalent" or "DIFFERENT".
    """
    samples = new.index.intersection(published.index)
    genes = new.columns.intersection(published.columns)
    a = new.loc[samples, genes].to_numpy(dtype=float).ravel()
    b = published.loc[samples, genes].to_numpy(dtype=float).ravel()
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    out: dict = {
        "new_shape": list(new.shape),
        "published_shape": list(published.shape),
        "shared_samples": int(len(samples)),
        "shared_genes": int(len(genes)),
        "n_cells": int(ok.sum()),
    }
    if len(a) == 0:
        return {**out, "verdict": "DIFFERENT", "reason": "no shared non-NaN cells"}
    delta = np.abs(a - b)
    r = float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else np.nan
    max_abs = float(delta.max())
    same_shape = (not require_same_shape) or list(new.shape) == list(published.shape)
    if max_abs < IDENTICAL_MAX_ABS and same_shape:
        verdict = "identical"
    elif same_shape and np.isfinite(r) and r > EQUIVALENT_R:
        verdict = "equivalent"
    else:
        verdict = "DIFFERENT"
    return {
        **out,
        "max_abs_delta": max_abs,
        "median_abs_delta": float(np.median(delta)),
        "pearson_r": r,
        "verdict": verdict,
    }


def package_versions() -> dict:
    """Python package versions (importlib.metadata) and R package versions (rpy2)."""
    versions: dict = {}
    for name in PYTHON_PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    try:
        import rpy2.robjects as ro

        versions["R"] = str(ro.r("R.version.string")[0])
        for name in R_PACKAGES:
            versions[f"R:{name}"] = str(
                ro.r(f"as.character(packageVersion('{name}'))")[0]
            )
    except Exception as exc:  # R missing on a laptop: record why, keep the check going
        versions["R"] = f"unavailable: {exc}"
    versions["Shambhala2_fast"] = os.environ.get("SHAMBHALA_FAST_COMMIT")
    return versions


def run_check(methods: list[str], strat: str, shambhala_samples: int) -> list[dict]:
    """Run part 1 (frozen methods) and part 2 (Shambhala); one result row per method."""
    import bench_shared as bs

    client = rl.s3_client()
    exp_s = bs.download_exp_from_s3(client, bs.s3_key_prepared_exp(strat, "strict"))
    ann_s = bs.download_ann_from_s3(client, bs.s3_key_prepared_ann(strat, "strict"))
    print(f"prepared {strat} × strict: {exp_s.shape}", flush=True)
    rows: list[dict] = []
    jobs = [(m, m) for m in methods]
    if shambhala_samples > 0:
        jobs.append(("20_shambhala", SHAMBHALA_PUBLISHED_NAME))
    for arm, published_name in jobs:
        row: dict = {"method": arm, "strat": strat, "imp": "strict"}
        started = time.time()
        try:
            if arm == "20_shambhala":
                rng = np.random.default_rng(0)
                n = min(shambhala_samples, len(exp_s))
                picked = sorted(rng.choice(exp_s.index.to_numpy(), n, replace=False))
                row["subset_samples"] = n
                # The published run harmonized S0 (3,447 genes) and cut the strategies
                # out of it. CuBlock clusters genes, so the same samples with another
                # gene set (e.g. C's 6,797) give other values: use the S0 input.
                exp_s0 = bs.download_exp_from_s3(
                    client, bs.s3_key_prepared_exp("S0_no_removal", "strict")
                )
                row["input"] = "S0_no_removal × strict"
                new = rl.shambhala_fast(exp_s0.loc[picked], ann_s.loc[picked])
                del exp_s0
            else:
                fn = bs.METHODS[arm][0]
                new = fn(exp_s, ann_s, batch_col=bs.BATCH_COL, bio_col=bs.BIO_COL)
            published = bs.download_exp_from_s3(
                client, bs.s3_key_exp(strat, "strict", published_name, False)
            )
            if arm == "20_shambhala":
                published = published.loc[published.index.intersection(new.index)]
            row.update(
                compare_matrices(
                    new, published, require_same_shape=arm != "20_shambhala"
                )
            )
        except Exception:
            row.update(
                {"verdict": "ERROR", "traceback": traceback.format_exc()[-3000:]}
            )
        row["seconds"] = round(time.time() - started, 1)
        print(
            f"{arm:<16} {row['verdict']:<11} "
            f"max|Δ|={row.get('max_abs_delta', float('nan')):.3g} "
            f"r={row.get('pearson_r', float('nan')):.6f} ({row['seconds']}s)",
            flush=True,
        )
        rows.append(row)
    return rows


def main() -> None:
    """Parse arguments, run the check, write the JSON to S3 and print the table."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--strat", default="C_rnaseq_only")
    parser.add_argument("--shambhala-samples", type=int, default=200)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()

    methods = [m for m in args.methods.split(",") if m]
    rows = run_check(methods, args.strat, args.shambhala_samples)
    payload = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "image": "ghcr.io/nikit357/combobatch:20260830",
        "versions": package_versions(),
        "results": rows,
    }
    table = pd.DataFrame(rows)
    columns = [
        c
        for c in ("method", "verdict", "max_abs_delta", "pearson_r", "seconds")
        if c in table
    ]
    print(table[columns].to_string(index=False))
    if not args.no_upload:
        stamp = time.strftime("%y%m%d")
        key = f"{rl.REVISION_S3_PREFIX}/env_check/env_check__{stamp}.json"
        rl.s3_put_json(rl.s3_client(), key, payload)
        print(f"written s3://{rl.S3_BUCKET}/{key}")
    bad = [r["method"] for r in rows if r["verdict"] not in ("identical", "equivalent")]
    print("ENV CHECK: " + ("OK" if not bad else f"STOP — not equivalent: {bad}"))


if __name__ == "__main__":
    main()
