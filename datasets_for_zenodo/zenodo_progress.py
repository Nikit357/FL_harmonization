"""Print upload progress for the Zenodo draft: files, gigabytes and a bar.

Reads the live file list from the Zenodo API and compares it with the bundle plan
in `zenodo_manifest.py`, so the totals are the ones the builder is actually working
towards rather than a figure typed here. Safe to run while a build is in flight —
it only issues GETs.

Usage
-----
    export ZENODO_TOKEN=$(tr -d '\\n\\r ' < ~/.zenodo_token)
    python zenodo_progress.py
    python zenodo_progress.py --watch 60     # refresh every 60 s
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))

import redact_lib as R  # noqa: E402
import zenodo_manifest as M  # noqa: E402
from build_and_upload import build_index  # noqa: E402

DEPOSITION_ID = 22737294
STANDALONE_FILES = 26
STANDALONE_GB = 0.40
BAR_WIDTH = 44


def draft_files(deposition_id: int, token: str) -> list[dict]:
    """Filename and size of every file currently on the draft."""
    response = requests.get(
        f"https://zenodo.org/api/deposit/depositions/{deposition_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("files", [])


def planned_bundles() -> list[M.Bundle]:
    """The bundle plan the builder follows, in its own priority order."""
    index, prepared = build_index(R.s3_client())
    bundles, _ = M.build_bundles(index, prepared)
    kept, _ = M.apply_budget(bundles, STANDALONE_GB, STANDALONE_FILES)
    return kept


def active_run_filter() -> tuple[str, ...] | None:
    """The `--bundles` filter of the builder currently running, if there is one.

    Read from the live process rather than passed in, because the whole point is
    that a partial run's queue differs from the plan: reporting the plan's next
    bundle while a filtered run skips it is exactly the wrong thing to print.
    Returns None when no builder is running or when it is building everything.
    """
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            argv = (proc / "cmdline").read_bytes().decode().split("\0")
        except OSError:
            continue
        if not any("build_and_upload.py" in part for part in argv):
            continue
        if "--bundles" in argv:
            value = argv[argv.index("--bundles") + 1]
            return tuple(v for v in value.split(",") if v)
        return None
    return None


def bar(fraction: float, width: int = BAR_WIDTH) -> str:
    """A single-line progress bar; the partial cell makes slow motion visible."""
    filled = fraction * width
    whole = int(filled)
    part = "▏▎▍▌▋▊▉"[min(int((filled - whole) * 8), 6)] if filled - whole else ""
    return ("█" * whole + part).ljust(width, "░")


def render(deposition_id: int, token: str) -> str:
    """One progress report: bundles, tables, gigabytes, and what is still to come."""
    kept = planned_bundles()
    planned_gb = {b.name: b.est_gb for b in kept}
    total_gb = sum(planned_gb.values()) + STANDALONE_GB
    total_files = len(kept) + STANDALONE_FILES

    files = draft_files(deposition_id, token)
    done_names = {f["filename"] for f in files}
    done_gb = sum(f["filesize"] for f in files) / 1e9
    done_bundles = [b for b in kept if b.name in done_names]
    done_tables = len(done_names) - len(done_bundles)

    # Measured bytes for what has landed, planned estimates for what has not: the
    # estimate runs ~7% low against the real ZIPs, so mixing the two would show a
    # percentage that walks backwards as each bundle lands.
    remaining_gb = sum(gb for name, gb in planned_gb.items() if name not in done_names)
    projected_gb = done_gb + remaining_gb + (
        0.0 if done_tables else STANDALONE_GB
    )
    by_gb = done_gb / projected_gb if projected_gb else 0.0
    by_files = len(done_names) / total_files if total_files else 0.0

    pending = [b.name for b in kept if b.name not in done_names]
    active = active_run_filter()
    if active is not None:
        queued = [n for n in pending
                  if n.startswith(active) or n.replace(".zip", "") in active]
        deferred = [n for n in pending if n not in queued]
    else:
        queued, deferred = pending, []

    lines = [
        f"Zenodo draft {deposition_id}   https://zenodo.org/deposit/{deposition_id}",
        f"reserved DOI  10.5281/zenodo.{deposition_id}   (unpublished)",
        "",
        f"  {bar(by_gb)}  {by_gb * 100:5.1f}%  by size",
        f"  {bar(by_files)}  {by_files * 100:5.1f}%  by file",
        "",
        f"  datasets : {len(done_bundles):2d} / {len(kept)} bundles"
        f"   +  {done_tables:2d} / {STANDALONE_FILES} tables"
        f"   =  {len(done_names):2d} / {total_files} files",
        f"  gigabytes: {done_gb:6.2f} / {projected_gb:6.2f} GB uploaded"
        f"   ({projected_gb - done_gb:5.2f} GB to go,"
        f" budget {M.MAX_RECORD_GB:.0f} GB)",
    ]
    if queued:
        lines += ["", f"  next up  : {queued[0]}"]
        if len(queued) > 1:
            lines += [f"  then     : {', '.join(queued[1:4])}"
                      + (f" … +{len(queued) - 4} more" if len(queued) > 4 else "")]
    elif pending:
        lines += ["", "  the running build has no bundles left in its queue"]
    else:
        lines += ["", "  all bundles uploaded"]
    if deferred:
        lines += [f"  deferred : {len(deferred)} bundle(s) the running build skips "
                  f"— {', '.join(n.replace('.zip', '') for n in deferred)}"]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deposition", type=int, default=DEPOSITION_ID)
    parser.add_argument("--token-env", default="ZENODO_TOKEN")
    parser.add_argument("--watch", type=int, default=0,
                        help="refresh every N seconds instead of printing once")
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"{args.token_env} is not set")

    while True:
        print(render(args.deposition, token))
        if not args.watch:
            return 0
        time.sleep(args.watch)
        print()


if __name__ == "__main__":
    sys.exit(main())
