"""
build_marker_gene_coverage.py — Per-gene coverage of the marker panel across attempts.

Reads the genes/*.json sidecars that run_metrics_job.py already wrote for every
attempt — one JSON list of the gene symbols present in that expression matrix — so no
expression file is downloaded and the whole audit runs in a couple of minutes.

Coverage measured over harmonized attempts is contaminated by the harmonizers
themselves: a method that drops genes changes the denominator. The primary column is
therefore present_in_all_raw_pairs, computed over the 42 unharmonized
01_raw__post0 matrices (14 strategies x 3 imputations) alone.

Supersedes ../../harmonization-metrics/marker_gene_coverage_audit_260819.csv, which
predates the 2026-08-26 panel regeneration and is per (strat, imp) pair rather than per
attempt.

Usage
-----
python build_marker_gene_coverage.py --out-dir /workspace/gene_panel_tables --date-tag 260827
python build_marker_gene_coverage.py --out-dir /tmp --no-s3
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

import boto3
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from compute_batch_metrics import S3_BUCKET, S3_PREFIX
from marker_panels import GENE_ALIASES, panel_genes
from run_gene_corr_parallel import SHAMBHALA_DEFAULT_METHOD, keep_shambhala

RAW_METHOD = "01_raw"


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _default_date_tag() -> str:
    return time.strftime("%y%m%d")


def _list_gene_keys(s3_client: object) -> list[str]:
    keys: list[str] = []
    paginator = s3_client.get_paginator("list_objects_v2")  # type: ignore[attr-defined]
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=f"{S3_PREFIX}/genes/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("_genes.json"):
                keys.append(obj["Key"])
    return sorted(keys)


def _parse_run_id(run_id: str) -> tuple[str, str, str, bool] | None:
    parts = run_id.split("__")
    if len(parts) != 4 or parts[3] not in ("post0", "post1"):
        return None
    return (parts[0], parts[1], parts[2], parts[3] == "post1")


def _present_panel_genes(available: set[str], panel: list[str]) -> set[str]:
    """
    Canonical panel genes present in one matrix, honouring the alias fallbacks.

    A gene counts as present when the HGNC symbol or any of its legacy aliases is in
    the matrix, and is reported under the canonical symbol — otherwise a platform that
    still carries CD20 rather than MS4A1 would look like a coverage gap.
    """
    present: set[str] = set()
    for gene in panel:
        if gene in available or any(a in available for a in GENE_ALIASES.get(gene, [])):
            present.add(gene)
    return present


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the per-gene marker panel coverage table from genes/*.json."
    )
    parser.add_argument(
        "--out-dir", default=".", help="Directory for the output table."
    )
    parser.add_argument(
        "--date-tag",
        default=None,
        help="Postfix appended to the output filename, e.g. 260827. "
        "Default: today's date as YYMMDD.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Explicit output path; wins over --out-dir and --date-tag.",
    )
    parser.add_argument(
        "--no-s3", action="store_true", help="Write the local file only."
    )
    parser.add_argument(
        "--shambhala-mode",
        choices=["all", "none", "default-only"],
        default="default-only",
        help=f"Which Shambhala variants count towards the analysis scope columns. "
        f"'default-only' keeps only {SHAMBHALA_DEFAULT_METHOD}. "
        "(default: default-only)",
    )
    args = parser.parse_args()

    date_tag = args.date_tag or _default_date_tag()
    out_path = (
        Path(args.out)
        if args.out
        else Path(args.out_dir) / f"marker_gene_coverage_by_attempt_{date_tag}.csv"
    )

    s3 = boto3.client("s3")
    print(f"[{_ts()}] Listing gene sidecars on S3 ...", flush=True)
    keys = _list_gene_keys(s3)
    print(f"  {len(keys)} sidecars found.", flush=True)
    if not keys:
        print("Nothing to do — exiting.", flush=True)
        sys.exit(0)

    panel = panel_genes(include_housekeeping=True)
    print(f"  Panel: {len(panel)} annotated genes.", flush=True)

    # Per-gene tallies over three nested scopes plus one per strategy.
    n_all = 0
    n_scope = 0
    n_raw_pairs = 0
    count_all: dict[str, int] = {g: 0 for g in panel}
    count_scope: dict[str, int] = {g: 0 for g in panel}
    count_raw: dict[str, int] = {g: 0 for g in panel}
    per_strat_total: dict[str, int] = {}
    per_strat_count: dict[str, dict[str, int]] = {}

    for i, key in enumerate(keys):
        if i % 500 == 0:
            print(f"  [{i}/{len(keys)}] reading ...", flush=True)
        run_id = Path(key).name[: -len("_genes.json")]
        parsed = _parse_run_id(run_id)
        if parsed is None:
            continue
        strat, _imp, method, post_rm = parsed
        try:
            available = set(
                json.loads(s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read())
            )
        except Exception as exc:
            print(f"  SKIP {key}: {exc}", flush=True)
            continue

        present = _present_panel_genes(available, panel)

        n_all += 1
        for gene in present:
            count_all[gene] += 1

        if keep_shambhala(method, args.shambhala_mode):
            n_scope += 1
            for gene in present:
                count_scope[gene] += 1

            per_strat_total[strat] = per_strat_total.get(strat, 0) + 1
            strat_counts = per_strat_count.setdefault(strat, {})
            for gene in present:
                strat_counts[gene] = strat_counts.get(gene, 0) + 1

        if method == RAW_METHOD and not post_rm:
            n_raw_pairs += 1
            for gene in present:
                count_raw[gene] += 1

    strats = sorted(per_strat_total)
    print(
        f"[{_ts()}] Tallied {n_all} attempts, {n_scope} in scope, "
        f"{n_raw_pairs} raw (strat, imp) pairs, {len(strats)} strategies.",
        flush=True,
    )

    rows: list[dict] = []
    for gene in panel:
        row: dict[str, object] = {
            "gene": gene,
            "n_raw_pairs_present": count_raw[gene],
            "frac_raw_pairs_present": (
                count_raw[gene] / n_raw_pairs if n_raw_pairs else float("nan")
            ),
            "present_in_all_raw_pairs": bool(
                n_raw_pairs and count_raw[gene] == n_raw_pairs
            ),
            "n_attempts_present": count_all[gene],
            "frac_attempts_present": count_all[gene] / n_all if n_all else float("nan"),
            "n_attempts_present_scope": count_scope[gene],
            "frac_attempts_present_scope": (
                count_scope[gene] / n_scope if n_scope else float("nan")
            ),
        }
        n_strats_present = 0
        for strat in strats:
            total = per_strat_total[strat]
            got = per_strat_count.get(strat, {}).get(gene, 0)
            row[f"present_in_{strat}"] = bool(total and got == total)
            row[f"frac_in_{strat}"] = got / total if total else float("nan")
            if got:
                n_strats_present += 1
        row["n_strats_present"] = n_strats_present
        row["n_strats_total"] = len(strats)
        rows.append(row)

    df = pd.DataFrame(rows)
    # Keep the summary columns in front of the 28 per-strategy columns.
    lead = [
        "gene",
        "n_raw_pairs_present",
        "frac_raw_pairs_present",
        "present_in_all_raw_pairs",
        "n_attempts_present",
        "frac_attempts_present",
        "n_attempts_present_scope",
        "frac_attempts_present_scope",
        "n_strats_present",
        "n_strats_total",
    ]
    df = df[lead + [c for c in df.columns if c not in lead]]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"  wrote {out_path}  ({len(df)} genes x {len(df.columns)} cols)", flush=True)

    if not args.no_s3:
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"{S3_PREFIX}/marker_gene_coverage_by_attempt.csv",
            Body=buf.getvalue(),
        )
        print(
            f"  uploaded s3://{S3_BUCKET}/{S3_PREFIX}/"
            f"marker_gene_coverage_by_attempt.csv",
            flush=True,
        )

    n_ref = int(df["present_in_all_raw_pairs"].sum())
    n_scope_full = int((df["frac_attempts_present_scope"] == 1.0).sum())
    print(
        f"[{_ts()}] Reference set (present in all {n_raw_pairs} raw pairs): "
        f"{n_ref} genes.",
        flush=True,
    )
    print(
        f"[{_ts()}] Present in every in-scope attempt: {n_scope_full} genes.",
        flush=True,
    )


if __name__ == "__main__":
    main()
