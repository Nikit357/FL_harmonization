"""Build the Zenodo record bundle by bundle, uploading each while the next is built.

The build host is JupyterHub with ~10 GB free and the deposit is ~45 GB, so the
pipeline stages at most ``upload_workers + 1`` bundles: one under construction, the
rest in flight to Zenodo. Building is CPU-bound and uploading is network-bound, so
running them serially left one resource idle for roughly half of every cycle.

    for each bundle, in priority order:
        wait until the bundle fits beside the uploads still in flight
        open work/<bundle>.zip
        for each member, on a pool of worker processes:
            stream the S3 object, redact + round, gzip it to work/parts/
            the parent appends it to the ZIP in order and deletes the part
        close, verify (verify_bundle.py), sha256
        hand it to the uploader pool: PUT, confirm Zenodo's MD5, delete the copy

The transform is CPU-bound: formatting ~15 billion float64 values to four decimals
saturates one core at ~59 MB of deposit per minute, which is ~12.5 h for the whole
record. The worker pool is what brings that back to a few hours. Look-ahead is capped
at `workers + 2` members so the parts directory stays small next to the growing ZIP.

There is no way to move bytes from S3 to Zenodo without them passing through this
host: Zenodo has no server-side ingest-from-URL, and every matrix has to be
transformed anyway. Nor is there any way to resume a dropped upload — Zenodo's bucket
API is a single whole-file PUT with no multipart or byte-range support, so a dropped
connection always costs the whole file. What the pipeline guarantees instead is that
nothing is written to a laptop and that on-disk bytes stay within the disk guard,
which counts bundles still in flight as well as the one being built.

Members are stored, not deflated: they are already gzip, so re-compressing costs CPU
for nothing, and stored members let a reader stream one matrix out of a bundle
without expanding the whole archive.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import itertools
import json
import os
import shutil
import sys
import threading
import time
import zipfile
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

import redact_lib as R
import build_tables as T
import verify_bundle as V
import zenodo_manifest as M

WORK = Path("work")
STATE_FILE = WORK / "deposition.json"
ROWS_FILE = WORK / "manifest_rows.jsonl"
METADATA_FILE = Path("zenodo_metadata.json")
MANIFEST_NAME = "manifest.csv"
CHECKSUMS_NAME = "SHA256SUMS.txt"
README_NAME = "README.md"
LICENSE_NAME = "LICENSE-CC-BY-4.0.txt"

# (connect, read). The read leg is generous because a multi-GB PUT holds the socket
# open while Zenodo checksums it server-side; without any timeout a hung connection
# would stall the run indefinitely.
REQUEST_TIMEOUT = (30, 1800)

# Bundles may be uploaded concurrently, but each one occupies disk until its PUT
# returns. This caps how many can be in flight; the disk guard is the real constraint
# and will usually make the builder wait before this limit is reached. 1 still buys
# the overlap between building and uploading, which is most of the win.
DEFAULT_UPLOAD_WORKERS = 1

MANIFEST_FIELDS = [
    "bundle", "member", "kind", "strategy", "imputation", "method", "post_rm",
    "n_samples", "n_genes", "n_samples_withheld", "pct_na_cells", "is_best15",
    "is_decision_tree", "sha256_bundle", "deposited",
]


# ── S3 listing ───────────────────────────────────────────────────────────────


def list_s3(prefix: str, client) -> dict[str, int]:
    """List one S3 prefix as basename -> size in bytes."""
    paginator = client.get_paginator("list_objects_v2")
    out: dict[str, int] = {}
    full = f"{R.S3_PREFIX}/{prefix}"
    for page in paginator.paginate(Bucket=R.s3_bucket(), Prefix=full):
        for obj in page.get("Contents", []):
            name = obj["Key"][len(full):]
            if name:
                out[name] = obj["Size"]
    return out


def build_index(client) -> tuple[dict[M.Key, int], dict[str, int]]:
    """Resolve the live contents of `exp/` and `prepared/`.

    Returns
    -------
    tuple[dict[Key, int], dict[str, int]]
        The harmonized-matrix index keyed by (strategy, imputation, method,
        post_rm), and the prepared-layer index keyed by basename.
    """
    exp_raw = list_s3("exp/", client)
    index: dict[M.Key, int] = {}
    for name, size in exp_raw.items():
        if not name.endswith(".tsv.gz"):
            continue
        parts = name[: -len(".tsv.gz")].split("__")
        if len(parts) == 4:
            index[tuple(parts)] = size            # type: ignore[assignment]
    prepared = {
        n: s for n, s in list_s3("prepared/", client).items()
        if n.endswith(".tsv.gz") and "/" not in n
    }
    return index, prepared


# ── Disk guard ───────────────────────────────────────────────────────────────


def free_gb(path: Path = Path(".")) -> float:
    """Free space on the filesystem holding ``path``, in GB."""
    return shutil.disk_usage(path).free / 1e9


def require_space(need_gb: float, min_free_gb: float) -> None:
    """Refuse to start work that would not fit, before any bytes are written."""
    available = free_gb()
    if available < need_gb + min_free_gb:
        raise RuntimeError(
            f"{available:.1f} GB free; need {need_gb:.1f} GB plus a "
            f"{min_free_gb:.1f} GB margin. Stop here and free space or "
            f"re-run with --resume once the uploaded bundles are gone."
        )


def wait_for_space(need_gb: float, min_free_gb: float, in_flight: dict[str, float],
                   poll_s: float = 20.0, timeout_s: float = 7200.0) -> None:
    """Block until a bundle of ``need_gb`` fits beside the uploads still in flight.

    Parameters
    ----------
    need_gb : float
        Projected size of the bundle about to be built, headroom already applied.
    min_free_gb : float
        Margin that must remain free once the bundle is written.
    in_flight : dict[str, float]
        Bundle name -> gigabytes currently held on disk by a pending upload. Reported
        in the error so a stuck uploader is identifiable from the log alone.
    poll_s : float
        Seconds between checks.
    timeout_s : float
        Give up after this long.

    Raises
    ------
    RuntimeError
        If space does not appear within ``timeout_s``.
    """
    # require_space() refuses immediately, which is right when nothing will free up.
    # Once uploads run in the background the space *will* appear when a PUT returns,
    # so the builder waits rather than killing a run that only needs a few minutes.
    deadline = time.time() + timeout_s
    while True:
        available = free_gb()
        if available >= need_gb + min_free_gb:
            return
        if time.time() > deadline:
            raise RuntimeError(
                f"{available:.1f} GB free; need {need_gb:.1f} GB plus a "
                f"{min_free_gb:.1f} GB margin after {timeout_s / 60:.0f} min of "
                f"waiting. Uploads still holding disk: {in_flight}"
            )
        time.sleep(poll_s)


def upload_one(zenodo, bucket: str, name: str, path: Path) -> tuple[str, float, float]:
    """PUT one finished bundle, confirm Zenodo's MD5, and delete the local copy.

    Runs on the uploader thread pool, so it touches nothing but its own arguments and
    the thread-local session inside ``zenodo``.

    Returns
    -------
    tuple[str, float, float]
        (bundle name, gigabytes uploaded, seconds taken).

    Raises
    ------
    RuntimeError
        If Zenodo's MD5 does not match the local one. The local file is kept in that
        case so the mismatch can be inspected.
    """
    started = time.time()
    size_gb = path.stat().st_size / 1e9
    local_md5 = V.md5_file(path)
    entry = zenodo.upload(bucket, name, path)
    remote_md5 = entry.get("checksum", "").replace("md5:", "")
    if remote_md5 != local_md5:
        raise RuntimeError(
            f"{name}: Zenodo reported MD5 {remote_md5}, local {local_md5} — "
            f"the local copy is kept for inspection"
        )
    path.unlink()
    return name, size_gb, time.time() - started


# ── Bundle assembly ──────────────────────────────────────────────────────────


_WORKER: dict = {}


def _init_worker(prop_ids: set[str], whitelist: list[str], legacy: str | None,
                 decimals: int, tmp_dir: str) -> None:
    """Give one worker process its own S3 client and a copy of the transform inputs.

    A boto3 client does not survive a fork, so each process builds its own rather
    than inheriting the parent's.
    """
    _WORKER.update(prop_ids=prop_ids, whitelist=whitelist, legacy=legacy,
                   decimals=decimals, tmp_dir=Path(tmp_dir), client=R.s3_client())


def _transform_member(task: tuple) -> tuple[str, int, int]:
    """Transform one matrix from S3 into a standalone gzip file under the temp dir.

    Runs in a worker process. Returns the temp path and the row counts; the parent
    appends the file to the ZIP in task order and deletes it.
    """
    what, source, member = task[0], task[1], task[2]
    dst = _WORKER["tmp_dir"] / f"{member.replace('/', '__')}.part"
    with dst.open("wb") as raw, \
            gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=6) as gz, \
            io.TextIOWrapper(gz, encoding="utf-8", newline="") as txt:
        if what == "ann":
            kept, dropped = R.redact_annotation(
                source, txt, _WORKER["prop_ids"], _WORKER["whitelist"],
                legacy=_WORKER["legacy"], sep="\t", client=_WORKER["client"],
            )
        else:
            body = R.open_s3_stream(source, client=_WORKER["client"])
            kept, dropped = R.redact_and_round(
                body, txt, _WORKER["prop_ids"], decimals=_WORKER["decimals"]
            )
    return str(dst), kept, dropped


def _bundle_tasks(bundle: M.Bundle, path: Path) -> list[tuple]:
    """One task per member, in the order the members are written into the ZIP.

    Each task carries everything the worker needs plus the manifest row it will
    produce, so the parent never has to re-derive either.
    """
    tasks: list[tuple] = []
    for key in bundle.keys:
        strat, imp, method, post = key
        tasks.append((
            "exp",
            f"exp/{strat}__{imp}__{method}__{post}.tsv.gz",
            M.member_name(key),
            {"bundle": path.name, "member": M.member_name(key),
             "kind": "harmonized", "strategy": strat, "imputation": imp,
             "method": M.public_method(method), "post_rm": post,
             "is_best15": key in M.best15_keys(),
             "is_decision_tree": key in set(M.DECISION_TREE_PICKS)},
        ))
    for basename in bundle.prepared:
        strat, imp, what = basename[: -len(".tsv.gz")].split("__")
        member = M.prepared_member_name(basename)
        tasks.append((
            what,
            f"prepared/{basename}",
            member,
            {"bundle": path.name, "member": member, "kind": f"prepared_{what}",
             "strategy": strat, "imputation": imp, "method": "", "post_rm": "",
             "is_best15": False, "is_decision_tree": False},
        ))
    return tasks


def write_bundle(bundle: M.Bundle, path: Path, prop_ids: set[str],
                 whitelist: list[str], legacy: str | None, decimals: int,
                 workers: int) -> list[dict]:
    """Transform every member of one bundle in parallel and assemble the ZIP.

    The transform is CPU-bound — formatting float64 values to four decimals — and a
    single process saturates one core, so members are produced by a process pool and
    appended to the archive in task order by the parent. Look-ahead is bounded at
    ``workers + 2`` members so the temp files cannot outgrow the build host's disk.

    Parameters
    ----------
    bundle : M.Bundle
        The bundle to assemble.
    path : Path
        Destination ZIP; overwritten.
    prop_ids : set[str]
        The proprietary sample identifiers.
    whitelist : list[str]
        The 191-column annotation whitelist.
    legacy : str | None
        Internal group label to rename, or None.
    decimals : int
        Decimal places for expression values.
    workers : int
        Worker processes; 1 still goes through the pool, so there is one code path.

    Returns
    -------
    list[dict]
        One manifest row per member, before the bundle checksum is known.
    """
    tasks = _bundle_tasks(bundle, path)
    tmp_dir = WORK / "parts"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    ahead = workers + 2
    pending: deque = deque()
    remaining = iter(tasks)

    with ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker,
        initargs=(prop_ids, whitelist, legacy, decimals, str(tmp_dir)),
    ) as pool, zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED,
                               allowZip64=True) as zf:
        for task in itertools.islice(remaining, ahead):
            pending.append((task, pool.submit(_transform_member, task)))
        while pending:
            task, future = pending.popleft()
            part, kept, dropped = future.result()
            zf.write(part, task[2])
            Path(part).unlink()
            rows.append({**task[3], "n_samples": kept,
                         "n_samples_withheld": dropped, "n_genes": "",
                         "deposited": True})
            nxt = next(remaining, None)
            if nxt is not None:
                pending.append((nxt, pool.submit(_transform_member, nxt)))
    return rows


# ── Zenodo client ────────────────────────────────────────────────────────────


class Zenodo:
    """Minimal Zenodo deposition client: draft, bucket upload, publish.

    Uses the legacy deposition endpoints (still fully supported) together with the
    bucket-based Files API — the legacy files endpoint caps at 100 MB per file and
    is unusable for bundles of this size.
    """

    def __init__(self, token: str, sandbox: bool = False) -> None:
        self._token = token
        self._local = threading.local()
        host = "sandbox.zenodo.org" if sandbox else "zenodo.org"
        self.base = f"https://{host}/api"

    @property
    def session(self):
        """A ``requests.Session`` owned by the calling thread.

        requests.Session is not thread-safe: concurrent PUTs sharing one would share
        its connection pool and adapter state. One session per thread costs an extra
        TLS handshake per thread and nothing else.
        """
        import requests

        if not hasattr(self._local, "session"):
            session = requests.Session()
            session.headers["Authorization"] = f"Bearer {self._token}"
            self._local.session = session
        return self._local.session

    def _request(self, method: str, url: str, retries: int = 8,
                 body_factory=None, **kwargs):
        """Issue one request, retrying 5xx and 429 with exponential backoff.

        A retried upload needs a *fresh* body: a file handle passed as ``data`` is
        already at EOF after the first attempt, so a retry would silently PUT an empty
        file. Callers sending a body therefore pass ``body_factory``, which is invoked
        once per attempt.

        Transport failures are retried on the same schedule as 5xx. Only the request
        itself is guarded, so a 4xx still fails on the first attempt rather than
        being retried eight times.
        """
        import requests

        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        for attempt in range(retries):
            try:
                if body_factory is None:
                    response = self.session.request(method, url, **kwargs)
                else:
                    with body_factory() as body:
                        response = self.session.request(method, url, data=body,
                                                        **kwargs)
            except requests.exceptions.RequestException as exc:
                # Zenodo drops the TLS connection mid-PUT often enough to matter: a
                # multi-GB upload holds the socket for minutes while the far side
                # checksums it, and the drop surfaces as SSLEOFError rather than as a
                # status code, which killed run 4 after eleven good uploads. The retry
                # is safe — body_factory hands out a fresh handle per attempt, and a
                # bucket PUT replaces whatever is at that key.
                if attempt == retries - 1:
                    raise
                # Logged because a silent retry is indistinguishable from a slow
                # upload: a restarted multi-GB PUT looks exactly like one crawling
                # along, and without this line there is no way to tell from the log
                # which of the two is happening.
                print(f"RETRY {method} {url.rsplit('/', 1)[-1]} "
                      f"attempt {attempt + 1}/{retries}: "
                      f"{type(exc).__name__}", flush=True)
                time.sleep(min(2 ** attempt, 60))
                continue
            if response.status_code < 500 and response.status_code != 429:
                response.raise_for_status()
                return response
            # Capped backoff: an upload runs for hours and will meet transient 5xx,
            # but an outage is not something to sit through — `--resume` is for that.
            time.sleep(min(2 ** attempt, 60))
        response.raise_for_status()
        return response

    def create_draft(self, metadata: dict) -> dict:
        """Create a draft deposition with a pre-reserved DOI."""
        payload = {"metadata": {**metadata, "prereserve_doi": True}}
        return self._request("POST", f"{self.base}/deposit/depositions",
                             json=payload).json()

    def find_draft(self, title: str) -> dict | None:
        """An existing unpublished draft carrying this exact title, if there is one.

        A POST that times out at the gateway may still have created the deposition,
        and `_request` retries 5xx — so a single Zenodo outage could otherwise leave
        several duplicate drafts behind, each accumulating part of a 45 GB record.
        The builder therefore looks before it creates.
        """
        for entry in self._request("GET", f"{self.base}/deposit/depositions",
                                   params={"size": 50}).json():
            if not entry.get("submitted") and entry["metadata"].get("title") == title:
                return entry
        return None

    def get_draft(self, deposition_id: int) -> dict:
        return self._request(
            "GET", f"{self.base}/deposit/depositions/{deposition_id}"
        ).json()

    def update_metadata(self, deposition_id: int, metadata: dict) -> dict:
        return self._request(
            "PUT", f"{self.base}/deposit/depositions/{deposition_id}",
            json={"metadata": metadata},
        ).json()

    def existing_files(self, deposition_id: int) -> dict[str, str]:
        """Uploaded filename -> checksum, so --resume can skip finished bundles."""
        files = self._request(
            "GET", f"{self.base}/deposit/depositions/{deposition_id}/files"
        ).json()
        return {f["filename"]: f.get("checksum", "").replace("md5:", "")
                for f in files}

    def upload(self, bucket_url: str, name: str, path: Path) -> dict:
        """PUT one file into the deposition bucket and return its file entry."""
        return self._request("PUT", f"{bucket_url}/{name}",
                             body_factory=lambda: path.open("rb")).json()

    def upload_chunked(self, bucket_url: str, name: str, source) -> dict:
        """PUT from a generator, so nothing is ever written to disk.

        Experimental, and sandbox-only by default. `requests` turns a generator body
        into `Transfer-Encoding: chunked`; Invenio's bucket endpoint is not documented
        to accept that, and a chunked PUT cannot be resumed or checksummed before it
        is sent. This is the only way to avoid a disk-backed bundle entirely — prove
        it against sandbox.zenodo.org on a small bundle before relying on it.
        """
        return self._request("PUT", f"{bucket_url}/{name}", data=source,
                             retries=1).json()

    def publish(self, deposition_id: int) -> dict:
        return self._request(
            "POST",
            f"{self.base}/deposit/depositions/{deposition_id}/actions/publish",
        ).json()


def render_readme(template_dir: Path = Path("readme_templates")) -> str:
    """Expand the record README's include marker into a single deposited file.

    The caveats block is kept in its own file so the plan, the README and any future
    per-bundle documentation quote one identical text rather than three drifting
    copies of it.
    """
    body = (template_dir / "record_readme.md").read_text()
    marker = "<!-- INCLUDE:_common_caveats.md -->"
    return body.replace(marker, (template_dir / "_common_caveats.md").read_text())


def annotate_na_fraction(rows: list[dict], table_dir: Path) -> None:
    """Fill each manifest row's `pct_na_cells` from the deposited metrics table.

    Two methods return matrices that are ~87% NaN in every run — the article's own
    analysis set filtered them out, but `status` still reads "ok", so without this
    column a reader would have to join to `metrics_comprehensive` to discover that a
    matrix is mostly empty. The value is read rather than recomputed so the record
    reports one number, not two that could disagree.
    """
    source = next(table_dir.glob("metrics_comprehensive_*.csv"), None)
    if source is None:
        return
    # The metrics table spells post-removal as True/False; member names use post0/post1.
    post_token = {"False": "post0", "True": "post1"}
    na_by_run: dict[tuple, str] = {}
    with source.open(newline="") as fh:
        for entry in csv.DictReader(fh):
            key = (entry["strat"], entry["imp"], entry["method"],
                   post_token.get(entry["post_rm"], entry["post_rm"]))
            na_by_run[key] = entry.get("pct_na_cells", "")
    for row in rows:
        row["pct_na_cells"] = na_by_run.get(
            (row["strategy"], row["imputation"], row["method"], row["post_rm"]), ""
        )


def load_metadata(path: Path = METADATA_FILE) -> dict:
    """Read the Zenodo metadata template, refusing unfilled placeholders."""
    metadata = json.loads(path.read_text())
    blob = json.dumps(metadata)
    if "FILL_ME" in blob:
        raise ValueError(
            f"{path} still contains FILL_ME placeholders — complete the creators "
            f"and related_identifiers before uploading"
        )
    return metadata


# ── Orchestration ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default="..",
                        help="checkout holding figures_for_article/ (default: ..)")
    parser.add_argument("--token-env", default="ZENODO_TOKEN")
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--bundles", default="",
                        help="comma-separated bundle names or prefixes; default all")
    parser.add_argument("--decimals", type=int, default=M.DECIMALS)
    parser.add_argument("--workers", type=int,
                        default=max(1, min(6, (os.cpu_count() or 2) - 2)),
                        help="worker processes for the member transform; the "
                             "default leaves two cores for the rest of the host")
    parser.add_argument("--upload-workers", type=int,
                        default=DEFAULT_UPLOAD_WORKERS,
                        help="bundles PUT concurrently; 1 overlaps building with "
                             "uploading, >1 also parallelises the network. Each "
                             "holds its bundle on disk until the PUT returns")
    parser.add_argument("--min-free-gb", type=float, default=M.MIN_FREE_GB)
    parser.add_argument("--max-record-gb", type=float, default=M.MAX_RECORD_GB)
    parser.add_argument("--legacy-label", default=None,
                        help="internal group label to rename (or FL_LEGACY_LABEL)")
    parser.add_argument("--dry-run", action="store_true",
                        help="resolve keys, print the plan, write nothing")
    parser.add_argument("--no-upload", action="store_true",
                        help="build and verify locally; do not touch Zenodo")
    parser.add_argument("--resume", action="store_true",
                        help="skip bundles already uploaded with a matching MD5")
    parser.add_argument("--skip-tables", action="store_true",
                        help="bundles only; the standalone tables already exist")
    parser.add_argument("--chunked-upload", action="store_true",
                        help="experimental: stream each bundle to Zenodo without "
                             "keeping it on disk; unresumable, sandbox first")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    client = R.s3_client()
    index, prepared = build_index(client)
    bundles, missing = M.build_bundles(index, prepared)

    standalone_gb = 0.40      # projected; the tables are built before the bundles
    n_standalone = 26
    kept, dropped = M.apply_budget(bundles, standalone_gb, n_standalone,
                                   max_record_gb=args.max_record_gb)

    if args.bundles:
        wanted = tuple(args.bundles.split(","))
        kept = [b for b in kept if b.name.startswith(wanted)
                or b.name.replace(".zip", "") in wanted]

    total_gb = standalone_gb + sum(b.est_gb for b in kept)
    n_matrices = sum(b.n_members for b in kept)

    print(f"{'bundle':60s} {'members':>7s} {'est GB':>7s} {'prio':>5s}")
    for bundle in kept:
        print(f"{bundle.name:60s} {bundle.n_members:7d} "
              f"{bundle.est_gb:7.2f} {bundle.priority:5d}")
    print(f"\n{len(kept)} bundles + {n_standalone} tables = "
          f"{len(kept) + n_standalone} files (cap {M.MAX_FILES})")
    print(f"{n_matrices} matrices, {total_gb:.2f} GB projected "
          f"(budget {args.max_record_gb} GB)")
    if dropped:
        print(f"\ndropped by the budget: "
              f"{', '.join(b.name for b in dropped)}")
    if missing:
        print(f"\n{len(missing)} requested combinations have no S3 output:")
        for key in sorted(missing)[:40]:
            print(f"   {'__'.join(key)}")
        if len(missing) > 40:
            print(f"   … and {len(missing) - 40} more")
    print(f"\nfree disk: {free_gb():.1f} GB")

    if args.dry_run:
        return 0

    WORK.mkdir(exist_ok=True)
    prop_ids = R.derive_prop_ids(repo_root)
    whitelist = R.annotation_whitelist(T.MASTER_ANN_KEY, prop_ids, client=client)
    (WORK / "ann_columns.txt").write_text("\n".join(whitelist) + "\n")
    legacy = R.legacy_label(args.legacy_label)
    if legacy is None:
        print("WARNING: no --legacy-label given; the R3 group-label rename will "
              "not be applied and verification will fail on the annotation twins")

    if args.chunked_upload and not args.sandbox:
        raise SystemExit(
            "--chunked-upload is unproven against production Zenodo; rehearse it "
            "with --sandbox first and remove this guard only once it has worked"
        )

    zenodo = None
    bucket = None
    deposition_id = None
    uploaded: dict[str, str] = {}
    if not args.no_upload:
        token = os.environ.get(args.token_env)
        if not token:
            raise SystemExit(f"{args.token_env} is not set")
        zenodo = Zenodo(token, sandbox=args.sandbox)
        if args.resume and STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
            deposition = zenodo.get_draft(state["id"])
        else:
            metadata = load_metadata()
            existing = zenodo.find_draft(metadata["title"])
            if existing is None:
                deposition = zenodo.create_draft(metadata)
            else:
                print(f"reusing draft {existing['id']} — an unpublished deposition "
                      f"with this title already exists")
                deposition = zenodo.get_draft(existing["id"])
            STATE_FILE.write_text(json.dumps({"id": deposition["id"]}, indent=2))
        deposition_id = deposition["id"]
        bucket = deposition["links"]["bucket"]
        uploaded = zenodo.existing_files(deposition_id)
        doi = deposition["metadata"].get("prereserve_doi", {}).get("doi")
        print(f"\ndraft {deposition_id}  reserved DOI {doi}")

    table_dir = WORK / "tables"
    manifest_rows: list[dict] = []
    if not args.skip_tables:
        print("\nbuilding standalone tables …")
        report = T.build_metric_tables(table_dir, repo_root, client=client)
        for entry in report:
            print(f"   {entry['file']:52s} {entry['rows_out']:>9} rows "
                  f"{entry['bytes'] / 1e6:8.1f} MB")
        coverage: dict[str, int] = {}
        for key in index:
            if T.is_deposited_method(key[2]):
                name = M.public_method(key[2])
                coverage[name] = coverage.get(name, 0) + 1
        T.build_registries(table_dir, repo_root, coverage=coverage)
        source_report = T.build_source_tables(
            table_dir, repo_root, prop_ids, whitelist, legacy=legacy,
            client=client, decimals=args.decimals,
        )
        print(f"   source tables: {json.dumps(source_report)}")

    in_flight: dict[str, float] = {}
    pending_uploads: dict = {}
    upload_pool = ThreadPoolExecutor(max_workers=args.upload_workers,
                                     thread_name_prefix="upload")

    def reap(block: bool = False) -> None:
        """Collect finished uploads, freeing their disk budget and logging each.

        ``future.result()`` re-raises whatever the uploader thread raised, so an MD5
        mismatch or an exhausted retry budget still stops the run — just one bundle
        later than it would have under the serial pipeline.
        """
        done = [f for f in pending_uploads if f.done()]
        if block and not done and pending_uploads:
            done = [next(as_completed(list(pending_uploads)))]
        for future in done:
            name = pending_uploads.pop(future)
            in_flight.pop(name, None)
            uploaded_name, size_gb, seconds = future.result()
            print(f"UP    {uploaded_name:56s} {size_gb:6.2f} GB  "
                  f"{seconds / 60:5.1f} min", flush=True)

    for bundle in kept:
        path = WORK / bundle.name
        if args.resume and bundle.name in uploaded:
            print(f"SKIP  {bundle.name} (already uploaded)")
            continue
        reap()
        while len(pending_uploads) >= args.upload_workers:
            reap(block=True)
        wait_for_space(bundle.est_gb * 1.3, args.min_free_gb, in_flight)
        started = time.time()
        rows = write_bundle(bundle, path, prop_ids, whitelist, legacy,
                            args.decimals, args.workers)
        expected = [r["member"] for r in rows]
        observed = V.verify_bundle(path, prop_ids, expected, checks="all",
                                   client=client)
        by_member = {o["member"]: o for o in observed}
        digest = V.sha256_file(path)
        for row in rows:
            row["sha256_bundle"] = digest
            row["n_genes"] = by_member.get(row["member"], {}).get("cols", "")
        manifest_rows.extend(rows)
        # Persisted per bundle, because manifest.csv is written once at the end of the
        # run and a resumed run builds only the bundles that are still missing. Without
        # this sidecar the final manifest would omit every bundle an earlier run
        # uploaded — the one table that indexes the whole record.
        with ROWS_FILE.open("a") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        size_gb = path.stat().st_size / 1e9
        elapsed = time.time() - started
        print(f"BUILT {bundle.name:56s} {size_gb:6.2f} GB  {elapsed / 60:5.1f} min",
              flush=True)

        if zenodo is not None:
            in_flight[bundle.name] = size_gb
            future = upload_pool.submit(upload_one, zenodo, bucket, bundle.name, path)
            pending_uploads[future] = bundle.name

    while pending_uploads:
        reap(block=True)
    upload_pool.shutdown()

    # Rows from earlier runs of the same draft, keyed so a rebuilt bundle wins.
    if ROWS_FILE.exists():
        by_key = {}
        for line in ROWS_FILE.read_text().splitlines():
            row = json.loads(line)
            by_key[(row["bundle"], row["member"])] = row
        for row in manifest_rows:
            by_key[(row["bundle"], row["member"])] = row
        manifest_rows = list(by_key.values())

    for bundle in dropped:
        manifest_rows.append({
            "bundle": bundle.name, "member": "", "kind": "harmonized",
            "strategy": "", "imputation": "", "method": "", "post_rm": "",
            "n_samples": "", "n_genes": "", "n_samples_withheld": "",
            "pct_na_cells": "", "is_best15": False, "is_decision_tree": False,
            "sha256_bundle": "", "deposited": False,
        })

    table_dir.mkdir(parents=True, exist_ok=True)
    annotate_na_fraction(manifest_rows, table_dir)
    with (table_dir / MANIFEST_NAME).open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest_rows)

    (table_dir / README_NAME).write_text(render_readme())
    license_src = Path("readme_templates") / LICENSE_NAME
    if license_src.exists():
        shutil.copyfile(license_src, table_dir / LICENSE_NAME)

    # SHA256SUMS.txt must cover every top-level file of the record, which is both the
    # standalone tables in `table_dir` and the ZIP bundles. The bundles are streamed
    # and deleted the moment their PUT returns, so they are never on disk here and
    # cannot be re-hashed; their digests come from `manifest_rows`, where the build
    # loop recorded `sha256_bundle` from the exact bytes it then uploaded. Reading
    # them back from the manifest rather than the filesystem is also what makes the
    # file correct on a resumed run, whose bundles were built by an earlier process.
    digests: dict[str, str] = {}
    for row in manifest_rows:
        if row.get("deposited") and row.get("sha256_bundle"):
            digests.setdefault(row["bundle"], row["sha256_bundle"])
    for file in sorted(table_dir.iterdir()):
        if file.name == CHECKSUMS_NAME:
            continue
        digests[file.name] = V.sha256_file(file)
    (table_dir / CHECKSUMS_NAME).write_text(
        "".join(f"{digests[name]}  {name}\n" for name in sorted(digests)))
    print(f"SUMS  {CHECKSUMS_NAME}: {len(digests)} entries "
          f"({sum(1 for n in digests if n.endswith('.zip'))} bundles, "
          f"{sum(1 for n in digests if not n.endswith('.zip'))} tables)")

    if zenodo is not None:
        for file in sorted(table_dir.iterdir()):
            if args.resume and file.name in uploaded:
                continue
            local_md5 = V.md5_file(file)
            entry = zenodo.upload(bucket, file.name, file)
            if entry.get("checksum", "").replace("md5:", "") != local_md5:
                raise RuntimeError(f"{file.name}: MD5 mismatch after upload")
            print(f"UP    {file.name:56s} {file.stat().st_size / 1e6:6.1f} MB")
        print(f"\nDraft {deposition_id} complete. Review it in the browser, then "
              f"publish deliberately — publishing is irreversible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
