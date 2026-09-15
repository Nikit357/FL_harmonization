"""Measure whether Zenodo's slowness is per-connection or global.

The deposit stalled on 2026-09-14 because multi-GB PUTs were being dropped after
25-45 min on the wire. Parallel uploads would fix that only if Zenodo shapes each
connection separately; if the limit is this host's egress or a per-account shaper,
N connections split one pipe N ways and every file gets *more* likely to be dropped.
This script settles the question before any pipeline code is written.

Method: upload the same set of throwaway payloads to the live draft twice — once one
after another, once on N threads — and report aggregate MB/s for each. Payloads are
random bytes under `_probe_` names and are deleted from the draft afterwards, so the
deposit is never touched. Random bytes, not real data, because the deposit's own
files would be gzip-incompressible anyway and using them risks leaving a half-written
deposit file behind.

Run it when nothing else is uploading — a concurrent build run competes for the same
pipe and invalidates the comparison.

Usage
-----
    export ZENODO_TOKEN=$(tr -d '\\n\\r ' < ~/.zenodo_token)
    python probe_upload_concurrency.py --size-mb 80 --threads 3
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build_and_upload import Zenodo  # noqa: E402

DEPOSITION_ID = 22737294
PROBE_PREFIX = "_probe_"
SCRATCH = Path("work/probe")


def make_payload(path: Path, size_mb: int) -> None:
    """Write `size_mb` of random bytes, which no transport will compress away."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        for _ in range(size_mb):
            fh.write(os.urandom(1_000_000))


def put_one(zenodo: Zenodo, bucket: str, path: Path) -> tuple[str, float, float]:
    """Upload one probe payload; return (name, megabytes, seconds)."""
    name = PROBE_PREFIX + path.name
    started = time.time()
    # retries=1: a probe that needs a retry is not a measurement, it is an outlier,
    # and silently retrying would inflate the reported time instead of failing loudly.
    zenodo._request("PUT", f"{bucket}/{name}", retries=1,
                    body_factory=lambda: path.open("rb"))
    return name, path.stat().st_size / 1e6, time.time() - started


def run_serial(zenodo: Zenodo, bucket: str,
               paths: list[Path]) -> tuple[float, list[float]]:
    """Upload every payload one after another. Returns (aggregate MB/s, per-file MB/s)."""
    started = time.time()
    per_file = []
    for path in paths:
        _, mb, seconds = put_one(zenodo, bucket, path)
        per_file.append(mb / seconds)
        print(f"   serial   {path.name:16s} {mb:6.1f} MB  {seconds:6.1f}s  "
              f"{mb / seconds:5.2f} MB/s", flush=True)
    total_mb = sum(p.stat().st_size for p in paths) / 1e6
    return total_mb / (time.time() - started), per_file


def run_parallel(zenodo: Zenodo, bucket: str, paths: list[Path],
                 threads: int) -> tuple[float, list[float], int]:
    """Upload every payload concurrently.

    A dropped connection is part of what this measures, not a reason to abandon the
    measurement: one unlucky PUT used to destroy the whole experiment. Failures are
    counted and the rate is reported over the payloads that did land.

    Returns
    -------
    tuple[float, list[float], int]
        (aggregate MB/s over successful uploads, per-file MB/s, number dropped).
    """
    def attempt(path: Path):
        try:
            return put_one(zenodo, bucket, path)
        except Exception as exc:
            return path.name, 0.0, 0.0, type(exc).__name__

    started = time.time()
    with ThreadPoolExecutor(max_workers=threads) as pool:
        results = list(pool.map(attempt, paths))
    elapsed = time.time() - started

    per_file, ok_mb, dropped = [], 0.0, 0
    for result, path in zip(results, paths):
        if len(result) == 4:
            dropped += 1
            print(f"   parallel {path.name:16s} DROPPED ({result[3]})", flush=True)
            continue
        _, mb, seconds = result
        ok_mb += mb
        per_file.append(mb / seconds)
        print(f"   parallel {path.name:16s} {mb:6.1f} MB  {seconds:6.1f}s  "
              f"{mb / seconds:5.2f} MB/s", flush=True)
    return (ok_mb / elapsed if ok_mb else 0.0), per_file, dropped


def cleanup(zenodo: Zenodo, deposition_id: int) -> int:
    """Delete every `_probe_` file from the draft. Returns how many were removed."""
    files = zenodo._request(
        "GET", f"{zenodo.base}/deposit/depositions/{deposition_id}/files"
    ).json()
    removed = 0
    for entry in files:
        if entry["filename"].startswith(PROBE_PREFIX):
            zenodo._request(
                "DELETE",
                f"{zenodo.base}/deposit/depositions/{deposition_id}/files/{entry['id']}",
            )
            removed += 1
    return removed


def cleanup_local() -> int:
    """Delete leftover payloads from work/probe/. Returns how many were removed.

    The run's own `finally` normally handles this, but a probe killed outside Python
    — the OOM killer, a Ctrl-C at the wrong moment — leaves 240 MB of random bytes on
    a volume that has under 5 GB free.
    """
    if not SCRATCH.exists():
        return 0
    removed = 0
    for path in SCRATCH.glob("probe*.bin"):
        path.unlink()
        removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deposition", type=int, default=DEPOSITION_ID)
    parser.add_argument("--token-env", default="ZENODO_TOKEN")
    parser.add_argument("--size-mb", type=int, default=80)
    parser.add_argument("--threads", type=int, default=3)
    parser.add_argument("--cleanup-only", action="store_true",
                        help="just remove leftover _probe_ files and exit")
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"{args.token_env} is not set")
    zenodo = Zenodo(token)

    if args.cleanup_only:
        print(f"removed {cleanup(zenodo, args.deposition)} probe file(s) from the draft")
        print(f"removed {cleanup_local()} local payload(s) from {SCRATCH}")
        return 0

    draft = zenodo.get_draft(args.deposition)
    bucket = draft["links"]["bucket"]
    print(f"draft {args.deposition}, {len(draft.get('files', []))} files on it now")

    paths = [SCRATCH / f"probe{i + 1}.bin" for i in range(args.threads)]
    print(f"\nwriting {args.threads} x {args.size_mb} MB of random bytes …")
    for path in paths:
        make_payload(path, args.size_mb)

    try:
        print(f"\nserial ({args.threads} uploads, one at a time):")
        serial_rate, serial_each = run_serial(zenodo, bucket, paths)
        print(f"\nparallel ({args.threads} uploads at once):")
        parallel_rate, parallel_each, dropped = run_parallel(zenodo, bucket, paths,
                                                             args.threads)
    finally:
        cleanup_local()
        print(f"\nremoved {cleanup(zenodo, args.deposition)} probe file(s) from the draft",
              flush=True)

    speedup = parallel_rate / serial_rate if serial_rate else 0.0
    print(f"\n{'':4}aggregate serial   : {serial_rate:6.2f} MB/s "
          f"(per-file median {sorted(serial_each)[len(serial_each) // 2]:.2f})")
    if parallel_each:
        print(f"{'':4}aggregate parallel : {parallel_rate:6.2f} MB/s "
              f"(per-file median {sorted(parallel_each)[len(parallel_each) // 2]:.2f}, "
              f"{dropped} dropped)")
    else:
        print(f"{'':4}aggregate parallel : every upload dropped ({dropped}/"
              f"{args.threads}) — no rate to report")
    print(f"{'':4}speedup            : {speedup:6.2f}x")

    if not parallel_each:
        # No measurement is not evidence of scaling. The decision rule adopts Option B
        # only on positive evidence, so an all-dropped parallel leg falls through to
        # the same verdict as measured non-scaling.
        print(f"{'':4}verdict            : parallel leg produced no measurement -> "
              f"SKIP Option B")
        return 0

    if speedup >= 2.0:
        verdict = "per-connection shaping -> ADOPT Option B (--upload-workers 2)"
    elif speedup >= 1.2:
        verdict = "partial benefit -> adopt Option B only if disk allows"
    else:
        verdict = "global bandwidth cap -> SKIP Option B, do A + C only"
    print(f"{'':4}verdict            : {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
