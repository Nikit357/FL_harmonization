"""
r19_harmonize_one.py — worker of the harmonization pod (called by r11 and r21).

Two modes:

--prepare  For each subset id given (comma-separated), draw the samples from the
           committed design / fold files, run `revision_lib.prepare_subset` (the frozen
           softImpute preparation + log transform by cohort) and upload
           revision_261029/<experiment>/prepared/<subset>__{exp,ann}.tsv.gz plus a
           record <subset>__prep.json. The raw matrix is loaded ONCE per process from
           the pickle cache of the frozen `load_data` (--raw-cache).
--arm      Download the prepared subset (local cache under --cache-dir), run one arm
           (a frozen METHODS entry or a covariate-free wrapper), upload
           revision_261029/<experiment>/exp/<subset>__<arm>.tsv.gz and the run record
           runs/<subset>__<arm>.json (status, seconds, shape, whether the output equals
           the input — i.e. the method fell back to returning uncorrected data).

A failure of the method itself is a RESULT (plan WP6 step 6.3, caveat C3): the record is
uploaded with status "failed" and the traceback, and the worker exits 0. Only an
infrastructure error (download / upload) exits non-zero.

Usage
-----
python r19_harmonize_one.py --experiment gradient --prepare --subset-ids grad_cap150_l0.0_r1
python r19_harmonize_one.py --experiment gradient --subset-id grad_cap150_l0.0_r1 --arm 04_sva
"""

from __future__ import annotations

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import contextlib
import io
import sys
import time
import traceback
from pathlib import Path

import numpy as np

import revision_dispatch as rd
import revision_lib as rl


class _Tee(io.TextIOBase):
    """Write to the real stdout and keep a copy (fallback messages go to the record)."""

    def __init__(self, stream: io.TextIOBase) -> None:
        self.stream, self.buffer_copy = stream, io.StringIO()

    def write(self, text: str) -> int:  # type: ignore[override]
        self.stream.write(text)
        self.stream.flush()
        return self.buffer_copy.write(text)


def prepare(experiment: str, subset_ids: list[str], raw_cache: str) -> int:
    """Prepare every subset of the list (raw data loaded once)."""
    client = rl.s3_client()
    comb_exp, _ = rl.load_raw_data(cache_path=raw_cache)
    ann_s0 = rl.load_s0_annotation()
    for subset_id in subset_ids:
        started = time.time()
        sample_ids = rd.subset_sample_ids(experiment, subset_id)
        exp_df, ann_df, record = rl.prepare_subset(sample_ids, comb_exp, ann_s0)
        rl.s3_put_tsv_gz(client, rl.s3_key_subset(experiment, subset_id, "exp"), exp_df)
        rl.s3_put_tsv_gz(client, rl.s3_key_subset(experiment, subset_id, "ann"), ann_df)
        record.update(
            {
                "experiment": experiment,
                "subset_id": subset_id,
                "seconds": round(time.time() - started, 1),
            }
        )
        rl.s3_put_json(
            client,
            f"{rl.REVISION_S3_PREFIX}/{experiment}/prepared/" f"{subset_id}__prep.json",
            record,
        )
        print(f"prepared {subset_id}: {record}", flush=True)
    return 0


def load_prepared(client: object, experiment: str, subset_id: str, cache_dir: Path):
    """Prepared exp / ann of a subset, cached on local disk (one download per subset)."""
    frames = []
    for kind in ("exp", "ann"):
        path = cache_dir / experiment / f"{subset_id}__{kind}.pkl"
        if path.exists():
            import pandas as pd

            frames.append(pd.read_pickle(path))
            continue
        frame = rl.s3_get_tsv_gz(client, rl.s3_key_subset(experiment, subset_id, kind))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        frame.to_pickle(tmp)
        tmp.replace(path)
        frames.append(frame)
    return frames[0], frames[1]


def harmonize_one(experiment: str, subset_id: str, arm: str, cache_dir: Path) -> int:
    """Run one arm on one prepared subset and upload the matrix and the run record."""
    client = rl.s3_client()
    exp_df, ann_df = load_prepared(client, experiment, subset_id, cache_dir)
    record: dict = {
        "experiment": experiment,
        "subset_id": subset_id,
        "arm": arm,
        "n_samples_in": int(exp_df.shape[0]),
        "n_genes_in": int(exp_df.shape[1]),
    }
    tee = _Tee(sys.stdout)  # type: ignore[arg-type]
    started = time.time()
    try:
        with contextlib.redirect_stdout(tee):
            out = rl.harmonize(arm, exp_df, ann_df)
        record["seconds"] = round(time.time() - started, 1)
        shared_cols = out.columns.intersection(exp_df.columns)
        same = out.shape == exp_df.shape and np.allclose(
            out[shared_cols].to_numpy(dtype=float),
            exp_df.loc[out.index, shared_cols].to_numpy(dtype=float),
            equal_nan=True,
        )
        record.update(
            {
                "status": "ok",
                "returned_input_unchanged": bool(same and arm != "01_raw"),
                "n_samples_out": int(out.shape[0]),
                "n_genes_out": int(out.shape[1]),
                "n_nan_out": int(out.isna().sum().sum()),
            }
        )
        rl.s3_put_tsv_gz(client, rl.s3_key_harmonized(experiment, subset_id, arm), out)
    except Exception:
        record.update(
            {
                "status": "failed",
                "seconds": round(time.time() - started, 1),
                "traceback": traceback.format_exc()[-4000:],
            }
        )
        print(record["traceback"], flush=True)
    record["method_messages"] = tee.buffer_copy.getvalue()[-4000:]
    rl.s3_put_json(client, rl.s3_key_run_record(experiment, subset_id, arm), record)
    print(f"{subset_id} × {arm}: {record['status']} ({record['seconds']}s)", flush=True)
    return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--experiment", choices=["gradient", "v1"], required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument(
        "--warm-cache",
        action="store_true",
        help="only build the raw-data pickle cache (run once, first)",
    )
    parser.add_argument("--subset-ids", default="", help="comma-separated (--prepare)")
    parser.add_argument("--subset-id", default="")
    parser.add_argument("--arm", default="")
    parser.add_argument(
        "--raw-cache", default=str(rd.default_log_dir() / "cache/bench_comb_data.pkl")
    )
    parser.add_argument(
        "--cache-dir", default=str(rd.default_log_dir() / "cache/prepared")
    )
    args = parser.parse_args()
    Path(args.raw_cache).parent.mkdir(parents=True, exist_ok=True)
    if args.warm_cache:
        comb_exp, comb_ann = rl.load_raw_data(cache_path=args.raw_cache)
        rl.load_s0_annotation()
        print(
            f"raw cache ready: {comb_exp.shape} expression, {comb_ann.shape} annotation"
        )
        sys.exit(0)
    if args.prepare:
        sys.exit(prepare(args.experiment, args.subset_ids.split(","), args.raw_cache))
    sys.exit(
        harmonize_one(args.experiment, args.subset_id, args.arm, Path(args.cache_dir))
    )


if __name__ == "__main__":
    main()
