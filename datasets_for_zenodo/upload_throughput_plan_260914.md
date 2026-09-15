# Speeding up the Zenodo upload — options and implementation plan

**Date:** 2026-09-14
**Working directory:** `$FL_REPO_ROOT/datasets_for_zenodo/`
**Draft:** Zenodo `22737294`, reserved DOI `10.5281/zenodo.22737294`, unpublished
**Status when written:** 15 of 53 files on the draft (21.67 GB of ~48.5 GB projected)

---

## Overview

The deposit stalled. `grid_strict__J_ff_only.zip` (1.63 GB) has burned 4 of its 8 retries,
each attempt restarting the whole PUT from byte zero after Zenodo dropped the TLS
connection roughly half an hour in. Earlier, `grid_strict__I_rare_batches_removed_part1.zip`
(3.16 GB) exhausted all 8 attempts over 2 h 46 min and the run died without uploading it.

Two measurements frame every option below:

- **Zenodo's throughput is swinging by an order of magnitude.** `I_part2` (0.62 GB) went up
  at **4.5 MB/s** at 11:10; `J_ff_only` has been crawling at **0.4–1.0 MB/s** since 11:14.
  This morning's bundles averaged **4.9 MB/s**.
- **Small files always succeed.** Two standalone tables (3.6 MB and 11.9 MB) uploaded on the
  first attempt with matching MD5 while `J` was failing. Zenodo is not down; it drops
  connections that stay open for tens of minutes.

The pipeline is also **strictly serial**: it builds a bundle (5–9 min, CPU-bound), verifies
it, then uploads it (6–9 min, network-bound), and only then starts the next build. Roughly
half of every cycle leaves one of the two resources idle.

**Design decision to settle first:** whether Zenodo's slowness is *per connection* or
*global*. If per connection, parallel uploads multiply throughput. If global, they buy
nothing and only raise disk pressure. Phase 0 measures this before any code is written.

---

## 1. Background — measured reference data

### 1a. Observed transfer rates, 2026-09-14

| Bundle | Size | Outcome | Rate |
|---|---|---|---|
| `grid_strict__E2_iterative_r2` | 2.55 GB | uploaded 8.8 min | 4.8 MB/s |
| `grid_strict__H_affymetrix_extended` | 2.54 GB | uploaded 8.6 min | 4.9 MB/s |
| `grid_strict__I_..._part1` | 3.16 GB | **failed, 8/8 retries**, 2 h 46 min | — |
| `grid_strict__I_..._part2` | 0.62 GB | uploaded 2.3 min, after 1 retry | 4.5 MB/s |
| `grid_strict__J_ff_only` | 1.63 GB | **4/8 retries burned**, still trying | 0.4–1.0 MB/s |
| `comb_ann_public.csv` | 3.6 MB | uploaded first attempt | 0.43 MB/s |
| `metrics_comprehensive_260905.csv` | 11.9 MB | uploaded first attempt | 1.26 MB/s |

**Reading of the table:** failure correlates with *time on the wire*, not with size as such.
A 3.16 GB file at 4.9 MB/s needs 11 min and succeeded this morning; the same file at
1.0 MB/s needs 53 min and never finished. The drop window looks like ~25–45 min.

### 1b. What remains to upload

| Bundle | est GB | In run 8's queue? |
|---|---|---|
| `grid_strict__J_ff_only` | 1.49 | in flight |
| `grid_strict__K_ffpe_only` | 1.85 | yes |
| `prepared_inputs__strict` | 0.59 | yes |
| `sweep_strategies__04_sva__softimpute__post0` | 1.52 | yes |
| `sweep_strategies__10_mnn__softimpute__post0` | 1.66 | yes |
| `sweep_strategies__16_fsqn_r__softimpute__post0` | 1.40 | yes |
| `sweep_methods__A_confirmed_bad__softimpute__post0_part2` | 0.73 | yes |
| `prepared_inputs__softimpute` | 1.65 | yes |
| `prepared_inputs__knn` | 1.63 | yes |
| `sweep_methods__A_confirmed_bad__knn__post0_part2` | 1.05 | yes |
| **`grid_strict__I_rare_batches_removed_part1`** | **2.93** | **deferred — large** |
| **`grid_strict__S0_no_removal`** | **2.23** | **deferred — large** |
| **`sweep_methods__A_confirmed_bad__softimpute__post0_part1`** | **2.84** | **deferred — large** |
| **`sweep_methods__A_confirmed_bad__knn__post0_part1`** | **2.85** | **deferred — large** |

Plus 24 standalone tables (~0.41 GB), of which 2 are already up.

### 1c. Zenodo's documented limits

Checked against `developers.zenodo.org` and `inveniordm.docs.cern.ch` on 2026-09-14:

| Limit | Value | Relevance |
|---|---|---|
| Authenticated request rate | **100/min, 5000/hour** | No obstacle: 4 concurrent PUTs is 4 requests |
| Files per record | 100 | We are at 53; re-splitting has room |
| Bytes per record | 50 GB (200 GB on request) | We project ~48.5 GB |
| Resumable / multipart upload | **does not exist** | See §1d |

### 1d. Multipart upload is not available — this option is closed

Daniil asked specifically about multipart. It cannot be done, and the reason is worth
recording so nobody re-opens it:

- Zenodo's bucket API is `PUT /api/files/{bucket_id}/{filename}` — **one request carrying
  the whole file**. The docs describe it only as supporting larger files (50 GB) than the
  legacy 100 MB endpoint, never as resumable.
- InvenioRDM's newer API (`PUT /api/records/{id}/draft/files/{name}/content`, then
  `POST .../commit`) *looks* like multipart but is not: `content` is still a single PUT of
  the raw bytes, and `commit` only finalises. There is no part number, no byte range, no
  ETag-per-part, no "list parts" endpoint.
- `Content-Range` / byte-range resumption is not offered on either endpoint.
- The existing `Zenodo.upload_chunked()` in `build_and_upload.py:381` is **not** multipart.
  It sends `Transfer-Encoding: chunked` from a generator — still one request, still
  unresumable, and explicitly guarded to `--sandbox` only.

**Conclusion:** a dropped connection always costs the whole file. No client-side work
changes that. The only levers are *shorter time on the wire* (Options A, C) and
*more wire in parallel* (Option B).

---

## 2. The three options

### Option A — Overlap building and uploading (async uploader, 1 worker)

**Idea.** Stop blocking the builder on the network. Hand each finished bundle to a
background uploader thread and immediately start building the next one.

**Why it helps.** Build and upload are currently serial and use different resources
(CPU vs network). A typical cycle today is ~7 min build + ~8 min upload = 15 min; overlapped
it is ~max(7, 8) = 8 min. **Roughly a 45% cut in wall clock** across the remaining bundles,
and it costs nothing in extra connections or Zenodo load.

**Why it does not fix the stall.** A single upload is exactly as likely to be dropped as it
is today. This is a throughput win, not a reliability win.

**Cost.** Two bundles on disk at once instead of one. Peak disk goes from ~3.2 GB to
~6.4 GB against ~9 GB free — tight but workable if the disk guard accounts for in-flight
bytes.

**Risk.** Low. The upload path itself is unchanged.

---

### Option B — Parallel uploads (async uploader, N workers)

**Idea.** Option A's architecture with `--upload-workers N`, so N bundles are PUT
concurrently.

**Why it might help a lot.** If Zenodo is shaping *per connection*, N connections give N×
the aggregate rate, and — more importantly — each individual file still takes the same
wall-clock time, so **the drop probability per file is unchanged while the queue drains N
times faster**. The rate-limit budget is untouched (§1c).

**Why it might help nothing.** If the bottleneck is the host's egress bandwidth or a global
per-account shaper, N connections just split the same pipe N ways, every file takes N times
longer on the wire, and the drop probability per file gets **worse**. This is the risk that
makes Phase 0 mandatory.

**Cost.** N+1 bundles on disk. With ~9 GB free and bundles up to 3.2 GB, **N = 2 is the
practical ceiling**; N = 3 only for the sub-1.5 GB bundles.

**Risk.** Medium. `requests.Session` is **not thread-safe** — a per-thread session is
required (see §4.1c). Failure handling gets more complex: one thread's failure must not
leave the others writing into a doomed run.

---

### Option C — Re-split the four large bundles (targeted, not global)

**Idea.** Cut only the four deferred bundles (§1b) into ~1.2 GB pieces, so each PUT finishes
in ~5 min at the slow rate and ~4 min at the fast one — comfortably inside the observed
25–45 min drop window.

**Why it helps.** This is the only option that attacks the **failure**, not the speed.
`I_part1` at 3.16 GB has never once completed; at 1.2 GB it would have the same per-attempt
odds as `I_part2`, which succeeded.

**Cost.** Adds ~6 files (53 → ~59, still far below the 100 cap). Changes the record's file
layout, so `manifest.csv` must be regenerated and the README's contents table updated.

**The trap this plan must avoid.** `MAX_BUNDLE_GB` is **global** and `_split()` names pieces
`_part1`, `_part2`, … *by position* (`zenodo_manifest.py:228-254`). Lowering the global cap
would rename every bundle above it, so `--resume` would stop recognising the 21.67 GB
already uploaded. Worse, the `I` bundle is *already* split: re-splitting it at a lower cap
produces a **different** `part2` holding different members under a name already on the
draft — a silently wrong file rather than a missing one. The implementation below therefore
adds a **second-level split keyed on the produced part name**, touching only names that
have never been uploaded.

---

### Recommendation

**Do Phase 0, then Option A + Option C. Adopt Option B only if Phase 0 proves parallelism
scales.**

Option A is a guaranteed ~45% win at low risk. Option C is the only thing that makes the
four large bundles finishable at all. Option B is potentially the biggest win but rests on
an assumption that costs 15 minutes to test and could make things worse if wrong.

---

## 3. Phase 0 — measure before building (mandatory, ~15 min)

Write `probe_upload_concurrency.py`. It uploads the same payload to the live draft twice —
once serially, once with N threads — and reports aggregate MB/s for each.

Use **throwaway payloads**, not deposit files: generate N temporary 80 MB files of random
bytes, upload them under names prefixed `_probe_`, then delete them from the draft via
`DELETE {bucket}/{name}`. 80 MB at the slow rate is ~80 s per file, long enough to be
representative and short enough that a drop is unlikely to confound the measurement.

**Decision rule, to be fixed before seeing the numbers:**

| Aggregate rate with 3 threads | Verdict | Action |
|---|---|---|
| ≥ 2.0× the serial rate | per-connection shaping | adopt Option B, `--upload-workers 2` |
| 1.2–2.0× | partial benefit | adopt Option B only if disk allows, `--upload-workers 2` |
| < 1.2× | global bandwidth cap | **skip Option B**, do A + C only |

Record the numbers in this document under §3a before proceeding.

### 3a. Result, 2026-09-14 15:20 — Option B is NOT adopted

Run with `--size-mb 80 --threads 3`, with no build running so the pipe was quiet.

**Serial leg — completed:**

| Payload | Size | Time | Rate |
|---|---|---|---|
| `probe1.bin` | 80 MB | 271.2 s | 0.29 MB/s |
| `probe2.bin` | 80 MB | 81.0 s | 0.99 MB/s |
| `probe3.bin` | 80 MB | 92.0 s | 0.87 MB/s |
| **aggregate** | 240 MB | 444.2 s | **0.54 MB/s** |

**Parallel leg — did not complete.** The first of the three concurrent PUTs died on
`ssl.SSLEOFError` after seconds, and because the probe deliberately uses `retries=1`
(a retried probe is not a measurement) that killed the whole leg. No parallel rate
exists.

**Verdict: skip Option B.** The decision rule adopts Option B only on measured evidence
of ≥1.2× scaling. There is no such measurement, so the rule's default applies and the
deposit proceeds with **Option A alone** (`--upload-workers 1`), plus Option C when it
is approved.

Two observations that are *suggestive but not conclusive*, and must not be quoted as
findings:

- Three 80 MB PUTs each succeeded when sent one at a time; the first 80 MB PUT of the
  concurrent batch was dropped immediately. That is consistent with concurrency making
  drops *more* likely, which is the failure mode §2 Option B warns about — but it is a
  single event against a server that drops connections unpredictably anyway.
- The serial aggregate of 0.54 MB/s is ~9× below this morning's 4.9 MB/s, confirming the
  degradation is Zenodo-side and not specific to large files.

**The probe needs a fix before it is re-run** (see the TODO): the parallel leg must
tolerate individual failures and report them as a drop count alongside whatever rate the
survivors achieved, because a drop *is* part of the phenomenon being measured. As
written, one unlucky PUT destroys the experiment.

### 3b. Option C outcome, 2026-09-14 — the re-split works

| Sub-part | Size | Build | Upload | Rate | Attempts |
|---|---|---|---|---|---|
| `I_..._part1_s1` | 1.24 GB | 5.3 min | 18.2 min | 1.14 MB/s | 1 |
| `I_..._part1_s2` | 1.18 GB | 4.3 min | 7.6 min | 2.59 MB/s | 1 |
| `I_..._part1_s3` | 0.74 GB | 2.8 min | 2.4 min | 5.14 MB/s | 1 |

Zenodo's rate climbed 4.5× across the three (1.14 → 5.14 MB/s), so these numbers measure
the server's recovery as much as the re-split. What the re-split is responsible for is the
**attempt count**: three for three, against 0/8 for the same data as one 3.16 GB file. Even
`s1` at the worst rate of the three stayed inside the 25-45 min drop window that the
un-split bundle always exceeded.


### 3c. Deposit completed, 2026-09-14 20:25 — what actually mattered

The draft reached **60 files / 48.17 GB** at 20:25. Counting from the 21.67 GB stalled
state this plan was written against, the remaining 26.5 GB went up in about 3 h 20 min
across runs 11 and 12.

| Lever | Verdict |
|---|---|
| **Option C** (targeted re-split) | **Decisive.** All four deferred bundles are deposited; three of them had never completed a single PUT. 11 sub-parts, 10 on their first attempt. |
| **Option A** (async uploader) | **No measurable effect.** The `while len(pending_uploads) >= args.upload_workers` gate in §4.1f blocks the builder until the previous PUT returns, so at `--upload-workers 1` build and upload still alternate. No `BUILT`/`UP` pair ever overlapped. |
| **Option B** (parallel uploads) | Never adopted, never needed. |
| **Zenodo's own recovery** | **The dominant factor.** Rates ran 0.29-22 MB/s within the same evening — a 75× spread with no change on our side. |

The honest reading: the re-split is what made the four impossible bundles possible, and the
server's recovery is what made the rest fast. Option A as implemented contributed nothing,
and its gate should be `>= args.upload_workers + 1` if it is ever wanted — that is the
one-bundle-ahead behaviour §2 Option A describes and costs the second bundle on disk that
§2 already budgets for.

Two measurements worth keeping for any future deposit:

- **`est_gb` underestimates by 12-20% consistently** (`s3` 0.62→0.74, `J` 1.49→1.63,
  `K` 1.85→2.09, `prepared_inputs__knn` 1.63→1.77). That eats the `est_gb * 1.3` disk
  headroom and is most of why the record landed at 48.17 GB against a 46 GB budget.
  `RESPLIT_CAP_GB` should be keyed on measured, not estimated, size.
- **1.2 GB is not a safe size in the degraded regime.** `A_..._softimpute__post0_part1_s1`
  is 1.15 GB — inside the cap — and still burned 3 retries. The cap widens the odds; it
  does not eliminate the drop.

Failure tally across both runs: 5 bundles hit `SSLError`, every one recovered by retry
(worst was attempt 4 of 8). One run died outright, from a missing `FL_LEGACY_LABEL` rather
than from anything network-related — see §6 caveat 9.

---

## 4. Files to change

### 4.1 `build_and_upload.py` — the async uploader (Options A and B)

#### 4.1a Module docstring — the serial guarantee is no longer true

**Before** (lines 1–23, extract):

```
The build host is JupyterHub with ~10 GB free and the deposit is ~45 GB, so the
pipeline never stages more than a single bundle:
...
What the pipeline guarantees instead is that nothing is written
to a laptop and that at most one bundle exists on disk at a time.
```

**After:**

```
The build host is JupyterHub with ~10 GB free and the deposit is ~45 GB, so the
pipeline stages at most `upload_workers + 1` bundles: one being built, the rest in
flight to Zenodo. Uploading runs on a thread pool so the CPU-bound transform and the
network-bound PUT overlap instead of taking turns.
...
What the pipeline guarantees instead is that nothing is written to a laptop and that
on-disk bytes never exceed the disk guard, which counts in-flight uploads as well as
the bundle under construction.
```

#### 4.1b New constant, after `REQUEST_TIMEOUT` (line 63)

```python
# Bundles may be uploaded concurrently, but every one of them sits on disk until its
# PUT returns. This caps how many can be in flight at once; the disk guard is the
# real constraint and will refuse a build before this limit is reached.
DEFAULT_UPLOAD_WORKERS = 1
```

#### 4.1c `Zenodo` — a session per thread

`requests.Session` is not thread-safe; sharing one across concurrent PUTs risks
interleaved connection-pool state. Replace the single session with a `threading.local`.

**Before** (`__init__`, lines 278–285):

```python
def __init__(self, token: str, sandbox: bool = False) -> None:
    import requests

    self.session = requests.Session()
    self.session.headers["Authorization"] = f"Bearer {token}"
    host = "sandbox.zenodo.org" if sandbox else "zenodo.org"
    self.base = f"https://{host}/api"
```

**After:**

```python
def __init__(self, token: str, sandbox: bool = False) -> None:
    self._token = token
    self._local = threading.local()
    host = "sandbox.zenodo.org" if sandbox else "zenodo.org"
    self.base = f"https://{host}/api"

@property
def session(self):
    """A requests.Session owned by the calling thread.

    requests.Session is not thread-safe: concurrent PUTs sharing one session share
    its connection pool and adapter state. One session per thread keeps the uploader
    pool honest at the cost of one extra TLS handshake per thread.
    """
    import requests

    if not hasattr(self._local, "session"):
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {self._token}"
        self._local.session = session
    return self._local.session
```

Add `import threading` to the stdlib imports (line ~42).

#### 4.1d New helper — disk accounting that knows about in-flight uploads

Insert after `require_space()` (line ~130):

```python
def wait_for_space(need_gb: float, min_free_gb: float, in_flight: dict[str, float],
                   poll_s: float = 20.0, timeout_s: float = 7200.0) -> None:
    """Block until a bundle of ``need_gb`` fits beside the uploads still in flight.

    `require_space` refuses immediately; that is right for a serial pipeline where
    nothing is going to free up. With an async uploader the space *will* appear when
    a PUT returns, so the builder waits instead of dying.

    Parameters
    ----------
    need_gb : float
        Projected size of the bundle about to be built, with headroom applied.
    min_free_gb : float
        Margin that must remain free once the bundle is written.
    in_flight : dict[str, float]
        Bundle name -> gigabytes currently held on disk by a pending upload.
    poll_s : float
        Seconds between checks.
    timeout_s : float
        Give up after this long; a stuck uploader should surface as an error rather
        than a silent hang.

    Raises
    ------
    RuntimeError
        If space does not appear within ``timeout_s``.
    """
    deadline = time.time() + timeout_s
    while True:
        if free_gb() >= need_gb + min_free_gb:
            return
        if time.time() > deadline:
            raise RuntimeError(
                f"{free_gb():.1f} GB free; need {need_gb:.1f} GB plus a "
                f"{min_free_gb:.1f} GB margin after {timeout_s / 60:.0f} min of "
                f"waiting. In flight: {in_flight}"
            )
        time.sleep(poll_s)
```

#### 4.1e New helper — the upload task

Insert after `wait_for_space()`:

```python
def upload_one(zenodo, bucket: str, name: str, path: Path) -> tuple[str, float, float]:
    """PUT one finished bundle, confirm Zenodo's MD5, and delete the local copy.

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
```

#### 4.1f `main()` — replace the serial upload with a pool

**Before** (lines ~560–600, the bundle loop):

```python
    for bundle in kept:
        path = WORK / bundle.name
        if args.resume and bundle.name in uploaded:
            print(f"SKIP  {bundle.name} (already uploaded)")
            continue
        require_space(bundle.est_gb * 1.3, args.min_free_gb)
        started = time.time()
        rows = write_bundle(bundle, path, prop_ids, whitelist, legacy,
                            args.decimals, args.workers)
        ...
        if zenodo is not None:
            local_md5 = V.md5_file(path)
            entry = zenodo.upload(bucket, bundle.name, path)
            remote_md5 = entry.get("checksum", "").replace("md5:", "")
            if remote_md5 != local_md5:
                raise RuntimeError(...)
            path.unlink()
            print(f"UP    {bundle.name:56s} {size_gb:6.2f} GB  {elapsed / 60:5.1f} min")
        else:
            print(f"BUILT {bundle.name:56s} {size_gb:6.2f} GB  {elapsed / 60:5.1f} min")
```

**After:**

```python
    in_flight: dict[str, float] = {}
    pending_uploads: dict = {}
    upload_pool = ThreadPoolExecutor(max_workers=args.upload_workers,
                                     thread_name_prefix="upload")

    def reap(block: bool = False) -> None:
        """Collect finished uploads, releasing their disk budget and logging them."""
        done = [f for f in pending_uploads if f.done()]
        if block and not done and pending_uploads:
            done = [next(as_completed(pending_uploads))]
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
        # Counting in-flight bundles as occupied disk is what lets the builder run
        # ahead of the network without the two of them together overrunning the volume.
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
        with ROWS_FILE.open("a") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        size_gb = path.stat().st_size / 1e9
        print(f"BUILT {bundle.name:56s} {size_gb:6.2f} GB  "
              f"{(time.time() - started) / 60:5.1f} min", flush=True)
        if zenodo is not None:
            in_flight[bundle.name] = size_gb
            future = upload_pool.submit(upload_one, zenodo, bucket, bundle.name, path)
            pending_uploads[future] = bundle.name

    while pending_uploads:
        reap(block=True)
    upload_pool.shutdown()
```

Add `from concurrent.futures import ThreadPoolExecutor, as_completed` to the imports
(line ~43, beside the existing `ProcessPoolExecutor`).

#### 4.1g New argparse flag, after `--workers` (line ~437)

```python
    parser.add_argument("--upload-workers", type=int, default=DEFAULT_UPLOAD_WORKERS,
                        help="bundles PUT concurrently; 1 overlaps building with "
                             "uploading, >1 also parallelises the network. Each one "
                             "holds its bundle on disk until the PUT returns")
```

---

### 4.2 `zenodo_manifest.py` — second-level split (Option C)

#### 4.2a New constant, after `MAX_BUNDLE_GB` (line 48)

```python
# Second-level split, keyed on a name `_split()` has already produced. Zenodo drops a
# TLS connection held open for 25-45 min, and at the 1 MB/s it served on 2026-09-14
# anything above ~1.5 GB exceeds that window and can never complete (measured: the
# 3.16 GB I_part1 failed 8/8 attempts, the 0.62 GB I_part2 succeeded). Keyed rather
# than a lower global MAX_BUNDLE_GB because lowering the cap renames bundles that are
# already uploaded — and would give the already-uploaded I_..._part2 a different
# member list under the same name.
RESPLIT_CAP_GB: dict[str, float] = {
    "grid_strict__I_rare_batches_removed_part1.zip": 1.2,
    "grid_strict__S0_no_removal.zip": 1.2,
    "sweep_methods__A_confirmed_bad__softimpute__post0_part1.zip": 1.2,
    "sweep_methods__A_confirmed_bad__knn__post0_part1.zip": 1.2,
}
```

#### 4.2b `_split()` — apply the second level

**Before** (lines 249–254):

```python
    if len(parts) == 1:
        return [(name, parts[0])]
    return [
        (name.replace(".zip", f"_part{i + 1}.zip"), part)
        for i, part in enumerate(parts)
    ]
```

**After:**

```python
    if len(parts) == 1:
        named = [(name, parts[0])]
    else:
        named = [
            (name.replace(".zip", f"_part{i + 1}.zip"), part)
            for i, part in enumerate(parts)
        ]
    return [out for part_name, part_keys in named
            for out in _resplit(part_name, part_keys, index)]


def _resplit(name: str, keys: list[Key],
             index: dict[Key, int]) -> list[tuple[str, list[Key]]]:
    """Split one already-named part again if RESPLIT_CAP_GB lists it.

    Sub-parts are suffixed `_s1`, `_s2`, … rather than renumbering `_partN`, so every
    name that is already on the Zenodo draft keeps its exact spelling and `--resume`
    keeps working.
    """
    cap = RESPLIT_CAP_GB.get(name)
    if cap is None:
        return [(name, keys)]
    pieces: list[list[Key]] = []
    current: list[Key] = []
    running = 0.0
    for key in sorted(keys):
        size = estimate_gb([key], index)
        if current and running + size > cap:
            pieces.append(current)
            current, running = [], 0.0
        current.append(key)
        running += size
    if current:
        pieces.append(current)
    if len(pieces) == 1:
        return [(name, pieces[0])]
    return [(name.replace(".zip", f"_s{i + 1}.zip"), piece)
            for i, piece in enumerate(pieces)]
```

---

### 4.3 `zenodo_progress.py` — no change needed

It derives bundle names from `M.build_bundles()`, so it picks up the new names and the
new file total automatically.

### 4.4 `readme_templates/record_readme.md` — contents table

The record README lists the bundles. Re-splitting changes four names into ~10, so the
contents table needs regenerating. Check whether it is generated from `build_bundles()`
or typed; if typed, update it.

---

## 5. Files that do NOT change

| File | Why |
|---|---|
| `redact_lib.py` | The transform is untouched; only scheduling and file layout change |
| `verify_bundle.py` | Verification is per-bundle and name-agnostic |
| `build_tables.py` | Standalone tables are unaffected |
| `zenodo_metadata.json` | Record metadata does not enumerate files |
| `zenodo_manifest.py` `MAX_BUNDLE_GB` | Deliberately left at 3.0 — see §2 Option C trap |

---

## 6. Side effects and caveats

1. **Peak disk rises with `--upload-workers`.** At N=1 two bundles coexist (~6.4 GB worst
   case) against ~9 GB free. At N=2, three bundles (~9.6 GB) **will not fit** unless Option C
   has already shrunk the large ones. Sequence matters: **land Option C before raising
   `--upload-workers` above 1.**
2. **`--resume` must be re-checked after Option C.** The four re-split bundles have never
   been uploaded, so no uploaded name changes — but this must be *verified* against the live
   draft, not assumed, before the first run with the new layout.
3. **`manifest.csv` and `SHA256SUMS.txt` must be deleted from the draft before the final
   run** (already logged in the deposit plan's Phase 7). Option C makes this sharper: a
   manifest written before the re-split would index bundle names that no longer exist.
4. **`manifest_rows.jsonl` will hold stale rows** for `grid_strict__I_..._part1` and the
   other three under their old names, from builds that were completed but never uploaded.
   The final manifest is keyed on `(bundle, member)`, so the old names would appear as
   phantom bundles. They must be filtered out — see the TODO.
5. **An upload failure now surfaces late.** In the serial pipeline a bad PUT stopped the
   build immediately; with a pool, the builder may be two bundles ahead. `future.result()`
   re-raises in `reap()`, so the run still dies — but after more work has been done. This is
   an acceptable trade and worth knowing when reading a traceback.
6. **Thread-safety of the S3 client.** `write_bundle()` uses a `ProcessPoolExecutor` and is
   unaffected, but `upload_one` runs in threads and touches only the `Zenodo` object, which
   §4.1c makes thread-safe. No boto3 client is shared with the uploader threads.
7. **Option B could make things worse.** If egress is the bottleneck, N parallel PUTs each
   take N× longer and each is N× more likely to be dropped. Phase 0's decision rule exists
   precisely to prevent adopting it on hope.
8. **None of this reduces total bytes.** The record is ~48.5 GB either way; these options
   change how long it takes and how often a transfer has to start over.
9. **`FL_LEGACY_LABEL` must be exported, and a `nohup` run will not tell you.** Run 11 was
   launched without it, built six bundles fine, and then died on `prepared_inputs__strict`
   — the first bundle carrying annotation twins — with
   `VerificationError: unexpected Major_group values ['<internal label>']` — quoted
   redacted, since printing the label here would defeat its removal. Nothing incorrect was
   uploaded: `verify_bundle()` runs before the PUT, and the label rename lives only on the
   annotation path (`redact_annotation(legacy=...)`), while expression members go through
   `redact_and_round()`, which takes no `legacy` argument at all. The cost was one wasted
   bundle build. `build_and_upload.py:630` prints a warning here rather than exiting, which
   is unmissable in a foreground run and invisible under `nohup`; making it a hard error
   when uploading is enabled would have cost nothing and saved the build.

---

## 7. Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd "$FL_REPO_ROOT/datasets_for_zenodo"

# 0. Phase 0 concurrency probe (writes nothing to the deposit; cleans up after itself)
export ZENODO_TOKEN=$(tr -d '\n\r ' < ~/.zenodo_token)
python probe_upload_concurrency.py --sizes-mb 80 --threads 3

# 1. Imports and syntax after the edits
python -c "import ast; [ast.parse(open(f).read()) for f in
    ('build_and_upload.py','zenodo_manifest.py')]; print('syntax OK')"
python -m pytest test_transforms.py -q

# 2. The new bundle layout, without touching Zenodo. Expect the four large bundles
#    replaced by ~10 sub-parts, every already-uploaded name unchanged, total <= 100 files
python build_and_upload.py --dry-run | tail -25

# 3. Prove no uploaded name disappeared from the plan
python - <<'PY'
import os, sys, requests
sys.path.insert(0, ".")
import redact_lib as R, zenodo_manifest as M
from build_and_upload import build_index
index, prepared = build_index(R.s3_client())
bundles, _ = M.build_bundles(index, prepared)
planned = {b.name for b in bundles}
r = requests.get("https://zenodo.org/api/deposit/depositions/22737294",
                 headers={"Authorization": f"Bearer {os.environ['ZENODO_TOKEN']}"},
                 timeout=60)
on_draft = {f["filename"] for f in r.json()["files"] if f["filename"].endswith(".zip")}
orphans = on_draft - planned
print("uploaded bundles no longer in the plan:", orphans or "none (good)")
PY

# 4. First real run: Option A only, one upload worker, large bundles still deferred
nohup python build_and_upload.py --token-env ZENODO_TOKEN --resume --skip-tables \
    --upload-workers 1 >> zenodo_build.log 2>&1 &

# 5. Watch both halves of the pipeline; BUILT and UP should now interleave
grep -E "^BUILT |^UP |^RETRY " zenodo_build.log | tail -20
python zenodo_progress.py --watch 120
```

---

## TODO

### Phase 0 — measure (blocking; do not write Options A/B code first)
- [x] Write `probe_upload_concurrency.py` — N throwaway 80 MB payloads, serial then threaded,
      report aggregate MB/s, `DELETE` each probe file from the draft afterwards
- [x] Run it against the live draft while the current slow conditions hold
- [x] Record serial and 3-thread rates in a new §3a of this document (serial 0.54 MB/s;
      parallel leg dropped on its first PUT and produced no rate)
- [x] Apply the §3 decision rule and write down the verdict for Option B — **skip B**,
      no measured evidence of scaling

### Phase 1 — Option A, async uploader with one worker
- [x] `build_and_upload.py` — add `import threading`, and `ThreadPoolExecutor`/`as_completed`
      to the existing `concurrent.futures` import
- [x] `build_and_upload.py` — add `DEFAULT_UPLOAD_WORKERS` after `REQUEST_TIMEOUT`
- [x] `build_and_upload.py` — replace `Zenodo.session` with the `threading.local` property
- [x] `build_and_upload.py` — add `wait_for_space()` after `require_space()`
- [x] `build_and_upload.py` — add `upload_one()`
- [x] `build_and_upload.py` — rewrite the bundle loop with `reap()` and the pool
- [x] `build_and_upload.py` — add `--upload-workers` to argparse
- [x] `build_and_upload.py` — update the module docstring's "one bundle at a time" claim
- [x] Syntax check + `test_transforms.py`
- [x] Run with `--upload-workers 1` — run 9 started 2026-09-14 15:23 (`BUILT`/`UP`
      interleaving still to be confirmed from the log)

### Phase 2 — Option C, targeted re-split *(only after Phase 1 is stable)*
- [x] `zenodo_manifest.py` — add `RESPLIT_CAP_GB` after `MAX_BUNDLE_GB`
- [x] `zenodo_manifest.py` — add `_resplit()` and call it from `_split()`
- [x] `--dry-run` confirmed: four bundles became **11** sub-parts (max 1.19 GB),
      **34 bundles + 26 tables = 60 files**, 995 matrices and 44.66 GB unchanged
- [x] Verification command 3 — 13 bundles on draft, 34 in plan, **orphans: none**
- [x] Filtered `manifest_rows.jsonl`: 44 stale `I_..._part1` rows dropped, 767 kept;
      backup at `work/manifest_rows.jsonl.pre_resplit`
- [x] Run 10 started 2026-09-14 17:20 over **all** remaining bundles (no `--bundles`
      filter needed now that every piece is ≤1.2 GB)
- [x] `readme_templates/record_readme.md` — the contents table uses glob patterns, so no
      enumeration was stale; added a Naming paragraph explaining `_partN` / `_sN` pieces
- [x] Run 10 died mid-build of `I_..._part1_s2` after uploading `s1`; run 11 resumed it
      at 17:56 with the same flags (`--resume --skip-tables --upload-workers 1`)
- [x] **Option C validated.** `grid_strict__I_rare_batches_removed_part1`, which failed
      8/8 attempts over 2 h 46 min at 3.16 GB, is fully deposited as three sub-parts,
      **each on its first attempt** — see §3b

### Phase 3 — Option B, parallel uploads — **dropped, never needed**
- [x] Not pursued. The deposit completed on `--upload-workers 1` once Zenodo's rate
      recovered (§3c), so there was nothing left for parallelism to accelerate. Option B
      remains unmeasured; if a future deposit needs it, fix the probe's parallel leg first
      (§3a) rather than adopting it on the strength of this run.

### Phase 4 — finish the deposit
- [x] Delete `manifest.csv` and `SHA256SUMS.txt` from the draft — unnecessary, neither
      had ever been uploaded; run 12 wrote both fresh and uploaded them last
- [x] **`SHA256SUMS.txt` had to be rewritten 2026-09-15.** Run 12's copy listed only the
      25 files in `work/tables/`; all 34 bundles were missing, because the streaming
      design this plan relies on deletes each bundle as soon as its PUT returns, so
      nothing is left to hash at the end of the run. The digests were recovered from
      `manifest.csv`'s `sha256_bundle` and the file re-uploaded with 59 entries. This is a
      direct side effect of streaming, not of the Option A/C work — see
      `zenodo_deposit_plan_260913.md` §6 caveat 27
- [x] Final run: run 12 uploaded the last 14 bundles, then all 24 remaining tables plus
      `manifest.csv`, `README.md`, `SHA256SUMS.txt` and the licence
- [x] **60 files (34 bundles + 26 tables), 48.17 GB, every MD5 matched**, no missing
      bundles and no orphans against `build_bundles()`
- [x] `zenodo_deposit_plan_260913.md` §3d totals, caveat 12 and the Phase 7 checklist
      updated to the measured record
- [ ] Publish, or set the embargo date — **Daniil's call; the draft is still unpublished
      and publishing is irreversible**
