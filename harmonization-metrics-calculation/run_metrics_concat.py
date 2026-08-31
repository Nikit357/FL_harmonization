"""
run_metrics_concat.py — Aggregation: concatenate all per-harmonization metrics JSONs.

Reads:   FL_batch_correction/metrics/*_metrics.json  (from S3)
Writes:  FL_batch_correction/metrics_comprehensive.csv           (to S3)
         FL_batch_correction/marker_gene_correlations_long.csv   (to S3)
         FL_batch_correction/marker_cohort_correlations_long.csv (to S3)
         FL_batch_correction/prediction_folds_long.csv           (to S3)

Groups L, M and N add nested-dict values (per-gene, per-cohort and per-fold detail).
Those never enter the wide CSV — pandas would stringify them into unusable cells — so
they are split out into the three long-format tables above.

The S3 keys are undated — they are the "latest" pointers that the analysis side reads.
Local copies are dated instead: --out-dir plus --date-tag write all four tables into one
folder with a YYMMDD postfix, so a re-run never overwrites a previous snapshot.

Usage
-----
python run_metrics_concat.py
python run_metrics_concat.py --out-dir ../harmonization-metrics/metric_tables --date-tag 260827
python run_metrics_concat.py --out-csv /tmp/metrics_comprehensive.csv
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import boto3
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from compute_batch_metrics import S3_BUCKET, S3_PREFIX

METADATA_COLS = [
    "strat",
    "imp",
    "method",
    "post_rm",
    "harshness",
    "status",
    "compute_time_s",
]

# Nested-dict metric keys, split into long-format tables instead of wide columns.
GENE_DICT_KEY = "mk_rho_by_gene"
GENE_COUNT_KEY = "mk_rho_n_cohorts_by_gene"
COHORT_DICT_KEY = "mk_rho_by_cohort"
FOLD_DICT_KEYS = {"pv_lobo3_folds": "3class", "pv_lobo2_folds": "2class"}
# Small enough to pivot into the wide table as one column per diagnosis.
DIAG_DICT_KEY = "xb_rank_agree_by_diagnosis"


def _list_metrics_keys(s3_client: object) -> list[str]:
    prefix = f"{S3_PREFIX}/metrics/"
    keys: list[str] = []
    paginator = s3_client.get_paginator("list_objects_v2")  # type: ignore[attr-defined]
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            k = obj["Key"]
            if k.endswith("_metrics.json"):
                keys.append(k)
    return keys


def _download_json(s3_client: object, key: str) -> dict:
    body = s3_client.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read().decode()  # type: ignore[attr-defined]
    return json.loads(body)


def _run_id(d: dict) -> str:
    pm = "1" if d.get("post_rm") else "0"
    return f"{d.get('strat')}__{d.get('imp')}__{d.get('method')}__post{pm}"


def _split_nested(d: dict, run_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Pop the nested-dict keys out of one metrics record into long-format rows.

    Mutates `d` so the wide CSV only ever sees scalars.

    Returns
    -------
    tuple of (gene_rows, cohort_rows, fold_rows)
    """
    gene_rows: list[dict] = []
    cohort_rows: list[dict] = []
    fold_rows: list[dict] = []

    by_gene = d.pop(GENE_DICT_KEY, None) or {}
    n_cohorts = d.pop(GENE_COUNT_KEY, None) or {}
    for gene, rho in by_gene.items():
        gene_rows.append(
            {
                "run_id": run_id,
                "gene": gene,
                "rho": rho,
                "n_cohorts": n_cohorts.get(gene),
            }
        )

    by_cohort = d.pop(COHORT_DICT_KEY, None) or {}
    for cohort, rho in by_cohort.items():
        cohort_rows.append({"run_id": run_id, "cohort": cohort, "rho": rho})

    for key, target in FOLD_DICT_KEYS.items():
        folds = d.pop(key, None) or {}
        for batch, vals in folds.items():
            fold_rows.append(
                {
                    "run_id": run_id,
                    "target": target,
                    "batch": batch,
                    "n": vals.get("n"),
                    "n_classes": vals.get("n_classes"),
                    "f1_macro": vals.get("f1_macro"),
                    "auc": vals.get("auc"),
                }
            )

    # Pivot the per-diagnosis agreement into scalar columns.
    by_diag = d.pop(DIAG_DICT_KEY, None) or {}
    for diag, val in by_diag.items():
        d[f"xb_rank_agree_{diag}"] = val

    return gene_rows, cohort_rows, fold_rows


def _drop_remaining_containers(rows: list[dict]) -> int:
    """Strip any dict/list value that survived, so the wide CSV stays scalar-only."""
    n_dropped = 0
    offenders: set[str] = set()
    for row in rows:
        for key in [k for k, v in row.items() if isinstance(v, (dict, list))]:
            del row[key]
            offenders.add(key)
            n_dropped += 1
    if offenders:
        print(
            f"  Dropped non-scalar keys from the wide CSV: {sorted(offenders)}",
            flush=True,
        )
    return n_dropped


def _resolve_out_path(
    explicit: str | None, stem: str, args: argparse.Namespace
) -> Path | None:
    """
    Local output path for one table.

    An explicit --out-<table> path wins; otherwise --out-dir builds
    {out_dir}/{stem}_{date_tag}.csv. With neither, a bare --out-csv still places the
    long tables undated beside it, which is what that flag did before --out-dir existed.
    Returns None when nothing is given, keeping the historical S3-only behaviour.
    """
    if explicit:
        return Path(explicit)
    if args.out_dir:
        tag = args.date_tag or time.strftime("%y%m%d")
        return Path(args.out_dir) / f"{stem}_{tag}.csv"
    if args.out_csv:
        return Path(args.out_csv).parent / f"{stem}.csv"
    return None


def _write(
    df: pd.DataFrame, s3_client: object, s3_key: str, local: Path | None
) -> None:
    s3_client.put_object(  # type: ignore[attr-defined]
        Bucket=S3_BUCKET, Key=s3_key, Body=df.to_csv(index=False).encode()
    )
    print(
        f"Uploaded: s3://{S3_BUCKET}/{s3_key} ({len(df)} rows × {len(df.columns)} cols)",
        flush=True,
    )
    if local is not None:
        local.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(local, index=False)
        print(f"Local copy: {local}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate all per-harmonization metrics JSONs into a single CSV."
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory for every local output table. Combined with --date-tag it "
        "produces metrics_comprehensive_{tag}.csv, "
        "marker_gene_correlations_long_{tag}.csv, "
        "marker_cohort_correlations_long_{tag}.csv and "
        "prediction_folds_long_{tag}.csv. (default: no local output)",
    )
    parser.add_argument(
        "--date-tag",
        default=None,
        help="Postfix appended to every local output filename, e.g. 260827. "
        "Default: today's date as YYMMDD.",
    )
    parser.add_argument(
        "--out-csv",
        default=None,
        help="Override the metrics_comprehensive local path. Wins over --out-dir.",
    )
    parser.add_argument(
        "--out-gene-long",
        default=None,
        help="Override the marker_gene_correlations_long local path.",
    )
    parser.add_argument(
        "--out-cohort-long",
        default=None,
        help="Override the marker_cohort_correlations_long local path.",
    )
    parser.add_argument(
        "--out-folds-long",
        default=None,
        help="Override the prediction_folds_long local path.",
    )
    parser.add_argument(
        "--s3-key",
        default=f"{S3_PREFIX}/metrics_comprehensive.csv",
        help="S3 key for the aggregated CSV output.",
    )
    args = parser.parse_args()

    s3 = boto3.client("s3")

    print("Listing metrics JSON files on S3 ...", flush=True)
    keys = _list_metrics_keys(s3)
    print(f"Found {len(keys)} metrics files.", flush=True)

    if not keys:
        print("No metrics files found — exiting.", flush=True)
        sys.exit(0)

    rows: list[dict] = []
    gene_rows: list[dict] = []
    cohort_rows: list[dict] = []
    fold_rows: list[dict] = []
    n_ok = 0
    n_failed = 0
    n_cached = 0
    n_other = 0

    for i, key in enumerate(keys):
        if i % 50 == 0:
            print(f"  [{i}/{len(keys)}] downloading ...", flush=True)
        try:
            d = _download_json(s3, key)
        except Exception as exc:
            print(f"  SKIP {key}: {exc}", flush=True)
            continue

        status = d.get("status", "unknown")
        if status == "cached":
            n_cached += 1
            continue
        elif status == "failed":
            n_failed += 1
        elif status == "ok":
            n_ok += 1
        else:
            n_other += 1

        g, c, f = _split_nested(d, _run_id(d))
        gene_rows.extend(g)
        cohort_rows.extend(c)
        fold_rows.extend(f)
        rows.append(d)

    print(
        f"\nSummary: {n_ok} ok, {n_failed} failed, {n_cached} cached, {n_other} other.",
        flush=True,
    )
    print(f"Building DataFrame from {len(rows)} rows ...", flush=True)

    _drop_remaining_containers(rows)
    df = pd.DataFrame(rows)

    # Reorder: metadata columns first, then the rest alphabetically
    existing_meta = [c for c in METADATA_COLS if c in df.columns]
    other_cols = sorted(c for c in df.columns if c not in METADATA_COLS)
    df = df[existing_meta + other_cols]

    _write(
        df,
        s3,
        args.s3_key,
        _resolve_out_path(args.out_csv, "metrics_comprehensive", args),
    )

    long_tables = [
        (gene_rows, "marker_gene_correlations_long", args.out_gene_long),
        (cohort_rows, "marker_cohort_correlations_long", args.out_cohort_long),
        (fold_rows, "prediction_folds_long", args.out_folds_long),
    ]
    for table_rows, stem, explicit in long_tables:
        if not table_rows:
            print(
                f"  {stem}.csv: no rows yet (groups L/M/N not computed) — skipped.",
                flush=True,
            )
            continue
        _write(
            pd.DataFrame(table_rows),
            s3,
            f"{S3_PREFIX}/{stem}.csv",
            _resolve_out_path(explicit, stem, args),
        )


if __name__ == "__main__":
    main()
