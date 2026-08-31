"""
run_gene_corr_concat.py — Aggregate the per-attempt gene correlation and QC outputs.

Reads:   FL_batch_correction/gene_corr/*_genecorr.npz
         FL_batch_correction/gene_qc/*_geneqc.json
Writes:  gene_gene_consensus_within_{tag}.csv.gz     consensus correlation, within-cohort
         gene_gene_consensus_global_{tag}.csv.gz     consensus correlation, all samples
         gene_gene_consensus_sd_{tag}.csv.gz         SD of Fisher z per gene pair
         gene_gene_consensus_n_{tag}.csv.gz          attempts contributing per pair
         gene_qc_long_{tag}.csv.gz                   run_id x gene QC table
         gene_gene_consensus_by_strat_{tag}/         per-strategy consensus (--by-strat)

Correlations are averaged on the Fisher z scale (Fisher 1921; Silver & Dunlap 1987):
averaging raw r under-estimates the consensus. The accumulators are float64 even
though each job stores float16, so the consensus is not degraded beyond the per-job
quantisation.

Every job carries its own gene order — panels differ per attempt because coverage
differs per strategy — so each matrix is mapped onto the union gene index before being
added. Nothing larger than one job's matrix is ever held in memory.

Usage
-----
python run_gene_corr_concat.py --out-dir /workspace/gene_panel_tables --date-tag 260827
python run_gene_corr_concat.py --out-dir /tmp --by-strat --no-s3
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path
from typing import Optional

import boto3
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from compute_batch_metrics import S3_BUCKET, S3_PREFIX
from gene_panel_structure import fisher_z, inverse_fisher_z, unpack_upper_triangle
from run_gene_corr_parallel import SHAMBHALA_DEFAULT_METHOD, keep_shambhala

FLAVOR_KEYS = {"within": "r_within", "global": "r_global"}


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _default_date_tag() -> str:
    return time.strftime("%y%m%d")


def _list_keys(s3_client: object, prefix: str, suffix: str) -> list[str]:
    keys: list[str] = []
    paginator = s3_client.get_paginator("list_objects_v2")  # type: ignore[attr-defined]
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(suffix):
                keys.append(obj["Key"])
    return sorted(keys)


def _run_id_from_key(key: str, suffix: str) -> str:
    return Path(key).name[: -len(suffix)]


def _parse_run_id(run_id: str) -> tuple[str, str, str, str]:
    parts = run_id.split("__")
    if len(parts) != 4:
        return ("", "", "", "")
    return (parts[0], parts[1], parts[2], parts[3])


class ConsensusAccumulator:
    """
    Streaming Fisher-z accumulator over the union gene index.

    Holds three G x G float64 matrices (sum of z, sum of z squared, contributing job
    count) — about 2.6 MB each at G = 572, so the whole benchmark aggregates inside a
    few tens of megabytes regardless of how many attempts are streamed through it.
    """

    def __init__(self, genes: list[str]) -> None:
        self.genes = genes
        self.index = {g: i for i, g in enumerate(genes)}
        n = len(genes)
        self.sum_z = np.zeros((n, n), dtype=float)
        self.sum_z2 = np.zeros((n, n), dtype=float)
        self.counts = np.zeros((n, n), dtype=np.int32)
        self.n_jobs = 0

    def add(self, mat: np.ndarray, job_genes: list[str]) -> None:
        pos = np.array([self.index[g] for g in job_genes if g in self.index])
        keep = np.array([g in self.index for g in job_genes])
        if pos.size < 2:
            return
        sub = mat[np.ix_(keep, keep)]
        finite = np.isfinite(sub)
        z = np.zeros_like(sub)
        z[finite] = fisher_z(sub[finite])

        grid = np.ix_(pos, pos)
        self.sum_z[grid] += np.where(finite, z, 0.0)
        self.sum_z2[grid] += np.where(finite, z**2, 0.0)
        self.counts[grid] += finite.astype(np.int32)
        self.n_jobs += 1

    def mean_r(self) -> pd.DataFrame:
        with np.errstate(invalid="ignore", divide="ignore"):
            mean_z = np.where(
                self.counts > 0, self.sum_z / np.maximum(self.counts, 1), np.nan
            )
        out = inverse_fisher_z(mean_z)
        np.fill_diagonal(out, 1.0)
        return pd.DataFrame(out, index=self.genes, columns=self.genes)

    def sd_z(self) -> pd.DataFrame:
        n = np.maximum(self.counts, 1)
        with np.errstate(invalid="ignore", divide="ignore"):
            var = self.sum_z2 / n - (self.sum_z / n) ** 2
            sd = np.where(self.counts > 1, np.sqrt(np.maximum(var, 0.0)), np.nan)
        return pd.DataFrame(sd, index=self.genes, columns=self.genes)

    def count_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.counts, index=self.genes, columns=self.genes)


def _write_frame(
    df: pd.DataFrame,
    out_dir: Path,
    stem: str,
    date_tag: str,
    s3_client: Optional[object],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stem}_{date_tag}.csv.gz"
    df.to_csv(path)
    print(f"  wrote {path}  ({df.shape[0]} x {df.shape[1]})", flush=True)
    if s3_client is not None:
        buf = io.BytesIO()
        df.to_csv(buf, compression="gzip")
        s3_client.put_object(  # type: ignore[attr-defined]
            Bucket=S3_BUCKET, Key=f"{S3_PREFIX}/{stem}.csv.gz", Body=buf.getvalue()
        )
        print(f"  uploaded s3://{S3_BUCKET}/{S3_PREFIX}/{stem}.csv.gz", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate per-attempt gene correlation matrices and QC tables."
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        help="Directory for every output table. (default: current directory)",
    )
    parser.add_argument(
        "--date-tag",
        default=None,
        help="Postfix appended to every output filename, e.g. 260827. "
        "Default: today's date as YYMMDD.",
    )
    parser.add_argument(
        "--no-s3", action="store_true", help="Write local files only; skip the upload."
    )
    parser.add_argument(
        "--by-strat",
        action="store_true",
        help="Also write one consensus matrix per filter strategy.",
    )
    parser.add_argument(
        "--shambhala-mode",
        choices=["all", "none", "default-only"],
        default="default-only",
        help=f"Which Shambhala variants to aggregate. 'default-only' keeps only "
        f"{SHAMBHALA_DEFAULT_METHOD}. (default: default-only)",
    )
    parser.add_argument(
        "--post-rm-filter", choices=["post0", "post1", "both"], default="both"
    )
    parser.add_argument(
        "--flavors",
        default="within,global",
        help="Comma-separated correlation flavours to aggregate.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    date_tag = args.date_tag or _default_date_tag()
    flavors = [f.strip() for f in args.flavors.split(",") if f.strip()]
    s3 = boto3.client("s3")
    s3_out = None if args.no_s3 else s3

    print(f"[{_ts()}] Listing gene_corr objects on S3 ...", flush=True)
    corr_keys = _list_keys(s3, f"{S3_PREFIX}/gene_corr/", "_genecorr.npz")
    qc_keys = _list_keys(s3, f"{S3_PREFIX}/gene_qc/", "_geneqc.json")
    print(f"  {len(corr_keys)} correlation files, {len(qc_keys)} QC files.", flush=True)

    if not corr_keys and not qc_keys:
        print("Nothing to aggregate — exiting.", flush=True)
        sys.exit(0)

    def in_scope(run_id: str) -> bool:
        strat, imp, method, pm = _parse_run_id(run_id)
        if not strat:
            return False
        if not keep_shambhala(method, args.shambhala_mode):
            return False
        if args.post_rm_filter != "both" and pm != args.post_rm_filter:
            return False
        return True

    corr_keys = [k for k in corr_keys if in_scope(_run_id_from_key(k, "_genecorr.npz"))]
    qc_keys = [k for k in qc_keys if in_scope(_run_id_from_key(k, "_geneqc.json"))]
    print(
        f"  in scope: {len(corr_keys)} correlation, {len(qc_keys)} QC "
        f"(--shambhala-mode {args.shambhala_mode}, --post-rm-filter {args.post_rm_filter}).",
        flush=True,
    )

    # ── Pass 1: union gene index ──────────────────────────────────────────────
    # Read only the `genes` array of each npz; numpy lazily decompresses members, so
    # this pass costs a fraction of a full load.
    print(f"[{_ts()}] Pass 1/2 — building the union gene index ...", flush=True)
    union: set[str] = set()
    job_genes_cache: dict[str, list[str]] = {}
    for i, key in enumerate(corr_keys):
        if i % 200 == 0:
            print(f"  [{i}/{len(corr_keys)}]", flush=True)
        try:
            body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
            with np.load(io.BytesIO(body), allow_pickle=True) as npz:
                genes = [str(g) for g in npz["genes"]]
        except Exception as exc:
            print(f"  SKIP {key}: {exc}", flush=True)
            continue
        job_genes_cache[key] = genes
        union |= set(genes)

    all_genes = sorted(union)
    print(f"  Union gene index: {len(all_genes)} genes.", flush=True)

    # ── Pass 2: accumulate ────────────────────────────────────────────────────
    print(f"[{_ts()}] Pass 2/2 — accumulating Fisher z ...", flush=True)
    accs = {f: ConsensusAccumulator(all_genes) for f in flavors}
    by_strat: dict[str, dict[str, ConsensusAccumulator]] = {}

    for i, key in enumerate(corr_keys):
        if key not in job_genes_cache:
            continue
        if i % 200 == 0:
            print(f"  [{i}/{len(corr_keys)}]", flush=True)
        run_id = _run_id_from_key(key, "_genecorr.npz")
        strat = _parse_run_id(run_id)[0]
        genes = job_genes_cache[key]
        try:
            body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
            with np.load(io.BytesIO(body), allow_pickle=True) as npz:
                for flavor in flavors:
                    arr_key = FLAVOR_KEYS[flavor]
                    if arr_key not in npz:
                        continue
                    mat = unpack_upper_triangle(npz[arr_key], len(genes))
                    accs[flavor].add(mat, genes)
                    if args.by_strat:
                        strat_accs = by_strat.setdefault(strat, {})
                        if flavor not in strat_accs:
                            strat_accs[flavor] = ConsensusAccumulator(all_genes)
                        strat_accs[flavor].add(mat, genes)
        except Exception as exc:
            print(f"  SKIP {key}: {exc}", flush=True)
            continue

    print(f"[{_ts()}] Writing consensus matrices ...", flush=True)
    for flavor in flavors:
        acc = accs[flavor]
        if acc.n_jobs == 0:
            print(f"  {flavor}: no jobs contributed — skipped.", flush=True)
            continue
        print(f"  {flavor}: {acc.n_jobs} attempts contributed.", flush=True)
        _write_frame(
            acc.mean_r(), out_dir, f"gene_gene_consensus_{flavor}", date_tag, s3_out
        )
    # The SD and count matrices describe the within-cohort flavour, which is the one
    # the panel selection uses; the global flavour is descriptive only.
    primary = "within" if "within" in flavors else flavors[0]
    if accs[primary].n_jobs:
        _write_frame(
            accs[primary].sd_z(), out_dir, "gene_gene_consensus_sd", date_tag, s3_out
        )
        _write_frame(
            accs[primary].count_frame(),
            out_dir,
            "gene_gene_consensus_n",
            date_tag,
            s3_out,
        )

    if args.by_strat and by_strat:
        strat_dir = out_dir / f"gene_gene_consensus_by_strat_{date_tag}"
        strat_dir.mkdir(parents=True, exist_ok=True)
        for strat, strat_accs in sorted(by_strat.items()):
            for flavor, acc in strat_accs.items():
                if acc.n_jobs == 0:
                    continue
                path = strat_dir / f"{strat}_{flavor}.csv.gz"
                acc.mean_r().to_csv(path)
        print(f"  per-strategy consensus written to {strat_dir}", flush=True)

    # ── QC long table ─────────────────────────────────────────────────────────
    print(f"[{_ts()}] Building the QC long table ...", flush=True)
    qc_rows: list[dict] = []
    for i, key in enumerate(qc_keys):
        if i % 200 == 0:
            print(f"  [{i}/{len(qc_keys)}]", flush=True)
        run_id = _run_id_from_key(key, "_geneqc.json")
        strat, imp, method, pm = _parse_run_id(run_id)
        try:
            payload = json.loads(
                s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read().decode()
            )
        except Exception as exc:
            print(f"  SKIP {key}: {exc}", flush=True)
            continue
        if payload.get("status") != "ok":
            continue
        for rec in payload.get("genes", []):
            row = {
                "run_id": run_id,
                "strat": strat,
                "imp": imp,
                "method": method,
                "post_rm": pm == "post1",
            }
            row.update(rec)
            qc_rows.append(row)

    if qc_rows:
        qc_df = pd.DataFrame(qc_rows)
        out_dir.mkdir(parents=True, exist_ok=True)
        qc_path = out_dir / f"gene_qc_long_{date_tag}.csv.gz"
        qc_df.to_csv(qc_path, index=False)
        print(f"  wrote {qc_path}  ({len(qc_df)} rows)", flush=True)
        if s3_out is not None:
            buf = io.BytesIO()
            qc_df.to_csv(buf, index=False, compression="gzip")
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=f"{S3_PREFIX}/gene_qc_long.csv.gz",
                Body=buf.getvalue(),
            )
            print(
                f"  uploaded s3://{S3_BUCKET}/{S3_PREFIX}/gene_qc_long.csv.gz",
                flush=True,
            )
    else:
        print("  no QC rows found — skipped.", flush=True)

    print(f"[{_ts()}] Done.", flush=True)


if __name__ == "__main__":
    main()
