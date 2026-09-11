# Add `--force-groups` flag — plan (2026-08-24)

## Overview

`run_metrics_job.py`'s incremental resume logic (`_groups_to_recompute`) skips any requested
metric group whose sentinel key is already non-null in the job's existing S3 sidecar — this is
what makes adding new groups to a completed run cheap (see `run_metrics_job.py:112-120`). It has
no way to say "recompute this specific group anyway." As discussed in the prior conversation turn
(recalculating Group N with a higher `--n-perm` after the 2026-08-23 fix), the only current
workaround is an out-of-band script that strips the group's keys from the S3 sidecar before
rerunning — functional, but manual, easy to get wrong (e.g. forgetting a key prefix), and outside
the normal dispatcher workflow.

This plan adds a `--force-groups` flag to both `run_metrics_job.py` (the worker) and
`run_metrics_parallel.py` (the dispatcher, which forwards it to each worker subprocess exactly
like `--groups` and `--n-perm` already are). Groups named in `--force-groups` are recomputed
unconditionally — bypassing the sentinel check for those letters only — while every other
requested group still goes through the normal incremental skip. **Design decision:** force is
scoped per-group, not per-job or global, because the whole point is to redo one expensive group
(e.g. Group N with new `--n-perm`) without discarding or recomputing the others (Groups A–M) in
the same sidecar — a per-job "recompute everything" flag already effectively exists (delete the
sidecar, or don't pass `--skip-if-exists` against a `prior_metrics=None` job) and isn't what was
asked for.

Recomputing a forced group naturally overwrites its own keys cleanly: `compute_group_n` (and
every other group function) always writes its complete key set on every call, so
`metrics.update(new_metrics)` in `main()` replaces all of the group's old keys with the new ones
in one step — no separate clearing step is needed, unlike the manual S3-script workaround.

---

## Background / reference data

| Quantity | Value | Source |
|---|---|---|
| Sentinel-check function | `_groups_to_recompute(prior, requested_groups)` | `run_metrics_job.py:112-120` |
| Sentinel keys | `GROUP_SENTINEL_KEYS` dict, one string key per group A–N | `run_metrics_job.py:76-91` |
| Where the dispatcher forwards worker flags | `launch()` closure inside `run_dispatcher()` | `run_metrics_parallel.py:331-375` |
| Existing analogous flag (same forwarding pattern to model on) | `--n-perm` | `run_metrics_job.py:318-323` (worker), `run_metrics_parallel.py:370-371` + `488-493` (dispatcher) |
| Existing unit test for the sentinel logic (to extend) | `test_incremental_groups_to_recompute` | `test_mock_metrics.py:266-288` |

---

## Files to change

### 1. `harmonization-metrics-calculation/run_metrics_job.py`

**1a. Extend `_groups_to_recompute()` to accept a `force_groups` set**

Before (`run_metrics_job.py:112-120`):
```python
def _groups_to_recompute(prior: dict | None, requested_groups: set[str]) -> set[str]:
    if prior is None:
        return set(requested_groups)
    missing: set[str] = set()
    for g in requested_groups:
        sentinel = GROUP_SENTINEL_KEYS.get(g)
        if sentinel is None or prior.get(sentinel) is None:
            missing.add(g)
    return missing
```

After:
```python
def _groups_to_recompute(
    prior: dict | None,
    requested_groups: set[str],
    force_groups: set[str] = frozenset(),
) -> set[str]:
    if prior is None:
        return set(requested_groups)
    missing: set[str] = set()
    for g in requested_groups:
        if g in force_groups:
            missing.add(g)
            continue
        sentinel = GROUP_SENTINEL_KEYS.get(g)
        if sentinel is None or prior.get(sentinel) is None:
            missing.add(g)
    return missing
```

Why: this is the single choke point where "already has a sentinel → skip" is decided. A group in
`force_groups` short-circuits straight into `missing` (the recompute set) without ever consulting
its sentinel. `frozenset()` is a safe immutable default (unlike a mutable `set()` literal default).
Only takes effect when `prior is not None` — matches existing behavior where a job with no prior
sidecar at all already recomputes everything requested.

**1b. Add the `--force-groups` CLI argument**

Before (`run_metrics_job.py:308-312`):
```python
    parser.add_argument(
        "--groups",
        default=None,
        help="Comma-separated metric groups to compute (e.g. A,B,E). Default: all.",
    )
```

After:
```python
    parser.add_argument(
        "--groups",
        default=None,
        help="Comma-separated metric groups to compute (e.g. A,B,E). Default: all.",
    )
    parser.add_argument(
        "--force-groups",
        default=None,
        help=(
            "Comma-separated metric groups to recompute even if their sentinel key "
            "already exists in the prior sidecar (e.g. rerun Group N with a new "
            "--n-perm). Automatically added to the requested set if --groups omits "
            "them; every other requested group still uses the normal incremental "
            "skip."
        ),
    )
```

**1c. Parse `--force-groups`, fold it into `requested_groups`, and pass it through**

Before (`run_metrics_job.py:351-370`):
```python
    # Determine requested groups
    if args.groups:
        requested_groups: set[str] = {g.upper().strip() for g in args.groups.split(",")}
    else:
        requested_groups = set("ABCDEFGHJKLMN")
    if not args.skip_wm:
        requested_groups.add("I")
    if args.skip_slow:
        requested_groups.discard("F")

    # Incremental: load any prior metrics and skip already-complete groups
    prior_metrics = _load_prior_metrics(s3, args.strat, args.imp, args.method, post_rm)
    groups_to_run = _groups_to_recompute(prior_metrics, requested_groups)

    wm_status = "enabled" if "I" in requested_groups else "skipped"
    print(
        f"[{_ts()}][{label}] Requested groups: {sorted(requested_groups)} | "
        f"WM: {wm_status} | Need to compute: {sorted(groups_to_run)}",
        flush=True,
    )
```

After:
```python
    # Determine requested groups
    if args.groups:
        requested_groups: set[str] = {g.upper().strip() for g in args.groups.split(",")}
    else:
        requested_groups = set("ABCDEFGHJKLMN")
    if not args.skip_wm:
        requested_groups.add("I")
    if args.skip_slow:
        requested_groups.discard("F")

    # --force-groups letters are always in play, even if --groups was narrower or
    # omitted them entirely; this line runs after the skip_slow/skip_wm adjustments
    # above so an explicit --force-groups F still forces F even under --skip-slow.
    force_groups: set[str] = (
        {g.upper().strip() for g in args.force_groups.split(",")}
        if args.force_groups
        else set()
    )
    requested_groups |= force_groups

    # Incremental: load any prior metrics and skip already-complete groups, except
    # any group named in --force-groups, which is always recomputed regardless of
    # its existing sentinel value.
    prior_metrics = _load_prior_metrics(s3, args.strat, args.imp, args.method, post_rm)
    groups_to_run = _groups_to_recompute(prior_metrics, requested_groups, force_groups)

    wm_status = "enabled" if "I" in requested_groups else "skipped"
    print(
        f"[{_ts()}][{label}] Requested groups: {sorted(requested_groups)} | "
        f"WM: {wm_status} | Force: {sorted(force_groups) or 'none'} | "
        f"Need to compute: {sorted(groups_to_run)}",
        flush=True,
    )
```

**1d. Add a usage example to the module docstring**

Before (`run_metrics_job.py:28-33`):
```python
# Blind final check only (groups L, M, N), reusing the cached raw reference:
python run_metrics_job.py \\
    --strat C_rnaseq_only --imp softimpute --method 04_sva --post-rm False \\
    --out-json /tmp/metrics.json --out-genes-json /tmp/genes.json \\
    --groups L,M,N --ref-cache-dir /workspace/ref_cache
"""
```

After:
```python
# Blind final check only (groups L, M, N), reusing the cached raw reference:
python run_metrics_job.py \\
    --strat C_rnaseq_only --imp softimpute --method 04_sva --post-rm False \\
    --out-json /tmp/metrics.json --out-genes-json /tmp/genes.json \\
    --groups L,M,N --ref-cache-dir /workspace/ref_cache

# Force-recompute Group N only with a higher n_perm, even though a sidecar with a
# Group N result already exists on S3 — Groups A-M are left untouched:
python run_metrics_job.py \\
    --strat C_rnaseq_only --imp softimpute --method 04_sva --post-rm False \\
    --out-json /tmp/metrics.json --out-genes-json /tmp/genes.json \\
    --groups N --force-groups N --n-perm 200
"""
```

---

### 2. `harmonization-metrics-calculation/run_metrics_parallel.py`

**2a. Add `force_groups` parameter to `run_dispatcher()` and forward it in `launch()`**

Before (`run_metrics_parallel.py:295-309`):
```python
def run_dispatcher(
    jobs: list[tuple[str, str, str, bool]],
    skip_keys: set[str],
    skip_if_exists: bool,
    skip_slow: bool,
    n_workers: int,
    timeout_s: int,
    memory_limit_gb: float,
    tmp_dir: Path,
    groups: Optional[str] = None,
    skip_wm: bool = False,
    ref_cache_dir: Optional[str] = None,
    n_perm: Optional[int] = None,
    save_gene_cohort_detail: bool = False,
    panel_groups: Optional[str] = None,
) -> tuple[set[str], set[str]]:
```

After:
```python
def run_dispatcher(
    jobs: list[tuple[str, str, str, bool]],
    skip_keys: set[str],
    skip_if_exists: bool,
    skip_slow: bool,
    n_workers: int,
    timeout_s: int,
    memory_limit_gb: float,
    tmp_dir: Path,
    groups: Optional[str] = None,
    force_groups: Optional[str] = None,
    skip_wm: bool = False,
    ref_cache_dir: Optional[str] = None,
    n_perm: Optional[int] = None,
    save_gene_cohort_detail: bool = False,
    panel_groups: Optional[str] = None,
) -> tuple[set[str], set[str]]:
```

Before (`run_metrics_parallel.py:366-371`):
```python
        if groups:
            cmd.extend(["--groups", groups])
        if ref_cache_dir:
            cmd.extend(["--ref-cache-dir", ref_cache_dir])
        if n_perm is not None:
            cmd.extend(["--n-perm", str(n_perm)])
```

After:
```python
        if groups:
            cmd.extend(["--groups", groups])
        if force_groups:
            cmd.extend(["--force-groups", force_groups])
        if ref_cache_dir:
            cmd.extend(["--ref-cache-dir", ref_cache_dir])
        if n_perm is not None:
            cmd.extend(["--n-perm", str(n_perm)])
```

**2b. Add the `--force-groups` CLI argument in `main()`**

Before (`run_metrics_parallel.py:467-472`):
```python
    parser.add_argument(
        "--groups",
        default=None,
        help="Comma-separated metric groups to compute (e.g. A,B,E). "
        "Valid: A B C D E F G H I J K L M N. Default: all groups.",
    )
```

After:
```python
    parser.add_argument(
        "--groups",
        default=None,
        help="Comma-separated metric groups to compute (e.g. A,B,E). "
        "Valid: A B C D E F G H I J K L M N. Default: all groups.",
    )
    parser.add_argument(
        "--force-groups",
        default=None,
        help=(
            "Comma-separated metric groups to recompute even if already present in "
            "a job's sidecar (bypasses the incremental sentinel check for these "
            "letters only). Forwarded to run_metrics_job.py's --force-groups."
        ),
    )
```

**2c. Pass `args.force_groups` through to `run_dispatcher(...)`**

Before (`run_metrics_parallel.py:545-560`):
```python
    newly_failed, newly_succeeded = run_dispatcher(
        jobs=jobs,
        skip_keys=skip_keys,
        skip_if_exists=args.skip_if_exists,
        skip_slow=args.skip_slow,
        n_workers=args.n_workers,
        timeout_s=args.timeout_s,
        memory_limit_gb=args.memory_limit_gb,
        tmp_dir=tmp_dir,
        groups=args.groups,
        skip_wm=args.skip_wm,
        ref_cache_dir=args.ref_cache_dir,
        n_perm=args.n_perm,
        save_gene_cohort_detail=args.save_gene_cohort_detail,
        panel_groups=args.panel_groups,
    )
```

After:
```python
    newly_failed, newly_succeeded = run_dispatcher(
        jobs=jobs,
        skip_keys=skip_keys,
        skip_if_exists=args.skip_if_exists,
        skip_slow=args.skip_slow,
        n_workers=args.n_workers,
        timeout_s=args.timeout_s,
        memory_limit_gb=args.memory_limit_gb,
        tmp_dir=tmp_dir,
        groups=args.groups,
        force_groups=args.force_groups,
        skip_wm=args.skip_wm,
        ref_cache_dir=args.ref_cache_dir,
        n_perm=args.n_perm,
        save_gene_cohort_detail=args.save_gene_cohort_detail,
        panel_groups=args.panel_groups,
    )
```

**2d. Add a usage example and flag doc entry to the module docstring**

Before (`run_metrics_parallel.py:34-38`, the line right after the existing L,M,N example block):
```python
# Resume after failure:
python run_metrics_parallel.py --n-workers 4 --skip-if-exists --retry-failed
```

After:
```python
# Force-recompute Group N only, with a higher n_perm, on attempts that already have a
# Group N result (e.g. rerun with more permutations for finer p-value resolution after
# the initial n_perm=20 pass). Groups A-M in each sidecar are left untouched.
nohup python run_metrics_parallel.py \\
    --groups N --force-groups N --only-with-metrics --skip-shambhala \\
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \\
    --n-perm 200 \\
    > /workspace/metrics_n_reforce.log 2>&1 &

# Resume after failure:
python run_metrics_parallel.py --n-workers 4 --skip-if-exists --retry-failed
```

Before (`run_metrics_parallel.py:74-76`):
```python
--n-perm N
    Label permutations for the Group N negative control (worker default: 20).

```

After:
```python
--n-perm N
    Label permutations for the Group N negative control (worker default: 20).

--force-groups LIST
    Comma-separated metric groups to recompute even if already present in a job's
    sidecar (bypasses the incremental sentinel check for these letters only). Use to
    rerun a group with different parameters, e.g. Group N with a new --n-perm. Forces
    those letters into the requested set automatically, whether or not they are also
    listed in --groups.

```

---

### 3. `harmonization-metrics-calculation/test_mock_metrics.py`

**3a. Extend `test_incremental_groups_to_recompute` with `force_groups` coverage**

Before (`test_mock_metrics.py:266-287`):
```python
def test_incremental_groups_to_recompute() -> None:
    print("\n--- test_incremental_groups_to_recompute ---")
    prior_with_e = {"n_samples": 100, "status": "ok"}
    prior_with_e_and_j = {"n_samples": 100, "pct_var_pc1": 45.0, "status": "ok"}

    result = _groups_to_recompute(prior_with_e, {"E", "J"})
    _check(result == {"J"}, "only_J_missing_when_E_present", f"got {result}")

    result = _groups_to_recompute(prior_with_e_and_j, {"E", "J"})
    _check(result == set(), "empty_when_both_present", f"got {result}")

    result = _groups_to_recompute(None, {"E", "J", "K"})
    _check(result == {"E", "J", "K"}, "all_returned_when_no_prior", f"got {result}")

    prior_null_val = {"n_samples": None, "status": "ok"}
    result = _groups_to_recompute(prior_null_val, {"E"})
    _check("E" in result, "recompute_when_sentinel_is_None", f"got {result}")

    _check("E" in GROUP_SENTINEL_KEYS, "sentinel_E_defined")
    _check("J" in GROUP_SENTINEL_KEYS, "sentinel_J_defined")
    _check("K" in GROUP_SENTINEL_KEYS, "sentinel_K_defined")
    _check("I" in GROUP_SENTINEL_KEYS, "sentinel_I_defined")
```

After:
```python
def test_incremental_groups_to_recompute() -> None:
    print("\n--- test_incremental_groups_to_recompute ---")
    prior_with_e = {"n_samples": 100, "status": "ok"}
    prior_with_e_and_j = {"n_samples": 100, "pct_var_pc1": 45.0, "status": "ok"}

    result = _groups_to_recompute(prior_with_e, {"E", "J"})
    _check(result == {"J"}, "only_J_missing_when_E_present", f"got {result}")

    result = _groups_to_recompute(prior_with_e_and_j, {"E", "J"})
    _check(result == set(), "empty_when_both_present", f"got {result}")

    result = _groups_to_recompute(None, {"E", "J", "K"})
    _check(result == {"E", "J", "K"}, "all_returned_when_no_prior", f"got {result}")

    prior_null_val = {"n_samples": None, "status": "ok"}
    result = _groups_to_recompute(prior_null_val, {"E"})
    _check("E" in result, "recompute_when_sentinel_is_None", f"got {result}")

    # --force-groups: bypasses the sentinel check for named groups only.
    result = _groups_to_recompute(prior_with_e_and_j, {"E", "J"}, force_groups={"J"})
    _check(result == {"J"}, "force_groups_recomputes_present_sentinel", f"got {result}")

    result = _groups_to_recompute(prior_with_e_and_j, {"E", "J"}, force_groups=set())
    _check(result == set(), "empty_force_groups_is_a_no_op", f"got {result}")

    result = _groups_to_recompute(prior_with_e_and_j, {"E"}, force_groups={"J"})
    _check(
        "J" not in result,
        "force_groups_has_no_effect_outside_requested_groups",
        f"got {result}",
    )

    _check("E" in GROUP_SENTINEL_KEYS, "sentinel_E_defined")
    _check("J" in GROUP_SENTINEL_KEYS, "sentinel_J_defined")
    _check("K" in GROUP_SENTINEL_KEYS, "sentinel_K_defined")
    _check("I" in GROUP_SENTINEL_KEYS, "sentinel_I_defined")
```

Why: `_groups_to_recompute` is exactly the function this flag modifies, and it already has a
dedicated test; extending it in place (rather than adding a separate test function) keeps every
case for this one function together, matching the file's existing organization.

---

### 4. `harmonization-metrics-calculation/CLAUDE.md`

**4a. Add a new "Key design patterns" entry documenting the flag**

Before (locate the existing **Incremental persistence** paragraph, added in the 2026-08-23 fix):
```
**Incremental persistence** — every group's result is uploaded to S3 as soon as it finishes (`on_group_done` callback threaded through `compute_all_metrics()` → `_upload_partial()` in `run_metrics_job.py`), not just once at the very end. A timeout or crash during a later group (e.g. Group N) no longer discards groups that already completed in the same attempt.
```

After:
```
**Incremental persistence** — every group's result is uploaded to S3 as soon as it finishes (`on_group_done` callback threaded through `compute_all_metrics()` → `_upload_partial()` in `run_metrics_job.py`), not just once at the very end. A timeout or crash during a later group (e.g. Group N) no longer discards groups that already completed in the same attempt.

**Force-recompute** — `--force-groups` (both `run_metrics_parallel.py` and `run_metrics_job.py`) bypasses the sentinel check in `_groups_to_recompute` for named groups only, so an already-populated group (e.g. Group N) can be rerun with different parameters (e.g. a higher `--n-perm`) without discarding or recomputing any other group in the same sidecar. It is folded into the requested-groups set automatically, so `--force-groups N` alone is enough even without also passing `--groups N`.
```

---

### 5. `harmonization-metrics-calculation/README.md`

**5a. Add a new "Step 10f" after the existing Step 10e (blind final check) section**

Before (locate the end of Step 10e — the paragraph right after its code block, "Groups M and N need no reference..."):
```
Groups M and N need no reference and do no extra I/O; `--groups M,N` skips the cache entirely.

### Step 11 — Aggregate results
```

After:
```
Groups M and N need no reference and do no extra I/O; `--groups M,N` skips the cache entirely.

### Step 10f — Force-recompute a single group with different parameters

To rerun a group that already has a result in every target sidecar — for example, redoing
Group N with a higher `--n-perm` for finer p-value resolution — pass `--force-groups` alongside
`--groups` for the same letters. Every other group already in each sidecar (A–M) is left exactly
as-is; only the forced group's keys are overwritten.

```bash
nohup python run_metrics_parallel.py \
    --groups N --force-groups N --only-with-metrics --skip-shambhala \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \
    --n-perm 200 \
    > /workspace/metrics_n_reforce.log 2>&1 &
```

Do not pass `--skip-if-exists` here either, for the same reason as Step 10e: every target job
already has a sidecar, so it would skip the job before `--force-groups` ever gets a chance to act.

### Step 11 — Aggregate results
```

(If the actual heading immediately following Step 10e is not `### Step 11 — Aggregate results`,
locate the real next heading and insert Step 10f directly before it instead — do not renumber
any other existing step.)

---

## Files that do NOT need to change

| File | Why not |
|---|---|
| `compute_batch_metrics.py` | `compute_all_metrics()` already recomputes exactly the groups it's told to via its `groups` parameter; it has no concept of "already done" — that decision is made entirely in `run_metrics_job.py` before calling it. Forcing a group only changes which letters end up in `groups_to_run`, which is already a plain parameter this function accepts today. |
| `run_metrics_concat.py` | Aggregation only; reads whatever is currently on S3. A force-recomputed group's new values simply appear in the next aggregation run like any other update — no special handling needed. |
| `figures_helpers.py` | Unaffected — the `_BLIND_CHECK_PREFIXES` exclusion for L/M/N is independent of how those groups' values were produced. |
| `k8s/pod-metrics.yaml`, `test_mock_metrics.py`'s other test functions | No relationship to the sentinel-skip decision. |
| `group_n_timeout_and_reference_race_fix_plan_260823.md` | Historical plan document for the prior fix; left as-is. |

---

## Side effects and caveats

- **No S3 schema change.** Forced groups overwrite their own keys in place, in the same sidecar,
  the same way any normal (non-forced) group computation already does — there is no new S3 key
  pattern, no new file, and no change to `metrics_comprehensive.csv`'s columns.
- **`--force-groups` does not imply `--groups`.** They are folded together (`requested_groups |=
  force_groups`) inside `run_metrics_job.py`'s `main()`, so passing `--force-groups N` alone (with
  no `--groups` at all) is sufficient — but if `--groups` *is* passed and deliberately narrower
  (e.g. `--groups A` with `--force-groups N`), Group N is still forced in, in addition to A. If the
  intent is "only recompute N," pass `--groups N --force-groups N` together, matching the examples
  above.
- **Interacts with `--skip-wm`/`--skip-slow`:** `requested_groups |= force_groups` runs *after*
  `--skip-slow` discards `F` and after `--skip-wm`'s conditional add of `I`, so an explicit
  `--force-groups F` (or `I`) still forces that group in even under `--skip-slow`/`--skip-wm` — the
  more specific flag wins over the more general one. This is a deliberate, if unlikely-to-be-hit,
  precedence choice, called out in a code comment (§1c) rather than validated against, since the
  combination isn't harmful, just unusual.
- **No interaction with `--skip-if-exists`.** That flag still short-circuits the entire job before
  any group logic runs at all (`run_metrics_job.py:344-349`) — `--force-groups` cannot rescue a job
  from being skipped that way. This matches the existing "do NOT pass `--skip-if-exists` for an
  L/M/N-style run" guidance and is called out again in the new README step.
- **Cost is proportional to what you force, not the whole job.** Forcing Group N only re-runs
  Group N's compute (plus whatever download/alignment the job needs regardless of which groups
  run); Groups A–M are read from the prior sidecar and passed through unchanged.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate   # or the pod's environment
cd harmonization-metrics-calculation

# 1. Smoke test — confirms the extended _groups_to_recompute and the new argparse
#    flags don't break anything (including the 3 new force_groups assertions).
python test_mock_metrics.py

# 2. Confirm the new flag is registered on both scripts.
python run_metrics_job.py --help | grep -A4 -- "--force-groups"
python run_metrics_parallel.py --help | grep -A4 -- "--force-groups"

# 3. Unit-check the sentinel bypass directly.
python -c "
from run_metrics_job import _groups_to_recompute
prior = {'n_samples': 100, 'pv_lobo3_f1_macro_mean': 0.5, 'status': 'ok'}
print(_groups_to_recompute(prior, {'E', 'N'}))                      # -> set() : both present
print(_groups_to_recompute(prior, {'E', 'N'}, force_groups={'N'}))  # -> {'N'} : N forced
"

# 4. End-to-end single-job check against a real sidecar that already has Group N
#    (e.g. A_confirmed_bad/knn/03_limma/post1 from the 2026-08-23 verification run):
#    confirm the log line shows Force: ['N'] and Group N actually recomputes with the
#    new --n-perm, while mk_rho_mean_all_genes (Group L) and xb_rank_agree (Group M)
#    in the resulting JSON are unchanged from before this run.
python run_metrics_job.py \
    --strat A_confirmed_bad --imp knn --method 03_limma --post-rm True \
    --out-json /tmp/force_test.json --out-genes-json /tmp/force_test_genes.json \
    --groups N --force-groups N --n-perm 50 --memory-limit-gb 4.0
python -c "
import json
d = json.load(open('/tmp/force_test.json'))
print('pv_n_perm (expect 50):', d.get('pv_n_perm'))
print('mk_rho_mean_all_genes (Group L, expect unchanged from prior run):', d.get('mk_rho_mean_all_genes'))
"
```

---

## TODO

- [x] `run_metrics_job.py` — extend `_groups_to_recompute()` with a `force_groups` parameter
- [x] `run_metrics_job.py` — add `--force-groups` argparse argument
- [x] `run_metrics_job.py` — parse `--force-groups`, union into `requested_groups`, pass to `_groups_to_recompute(...)`, log the forced set
- [x] `run_metrics_job.py` — add a `--force-groups` usage example to the module docstring
- [x] `run_metrics_parallel.py` — add `force_groups` parameter to `run_dispatcher()`
- [x] `run_metrics_parallel.py` — forward `--force-groups` to the worker subprocess command in `launch()`
- [x] `run_metrics_parallel.py` — add `--force-groups` argparse argument in `main()`
- [x] `run_metrics_parallel.py` — pass `force_groups=args.force_groups` into the `run_dispatcher(...)` call
- [x] `run_metrics_parallel.py` — add a `--force-groups` usage example and flag doc entry to the module docstring
- [x] `test_mock_metrics.py` — extend `test_incremental_groups_to_recompute` with the 3 new `force_groups` assertions
- [x] `CLAUDE.md` (harmonization-metrics-calculation) — add the "Force-recompute" design-pattern paragraph
- [x] `README.md` — add "Step 10f — Force-recompute a single group with different parameters"
- [x] Confirmed no syntax errors (`python3 -m py_compile` on both edited `.py` files) and re-grepped every edit location to confirm it landed correctly
- [x] Verified `_groups_to_recompute`'s new logic directly (extracted the function + `GROUP_SENTINEL_KEYS` via `ast` and exec'd them standalone, since this Mac lacks the project's scipy/sklearn env needed to import the full module): confirmed (a) an already-present sentinel is skipped without force, (b) `force_groups={"N"}` recomputes N despite its sentinel being present, (c) forcing a group outside `requested_groups` has no effect, (d) no-prior and empty-`force_groups` behavior is unchanged from before this change
- [x] Run `test_mock_metrics.py` on the pod to confirm no regressions and that the 3 new assertions pass — **172 passed, 0 failed** (169 before this change + 3 new `force_groups` assertions), run on the live pod after rsyncing this code to `/app/harmonization-metrics-calculation`
- [x] Confirm `--help` on both scripts shows the new flag with its help text — confirmed on the pod: `run_metrics_job.py --help` and `run_metrics_parallel.py --help` both list `--force-groups FORCE_GROUPS` with the intended help text
- [x] Run the end-to-end single-job check against a real already-computed sidecar (verification command 4) — ran `--strat A_confirmed_bad --imp knn --method 03_limma --post-rm True --groups N --force-groups N --n-perm 50` against the real S3 sidecar from the 2026-08-23 verification run (previously `pv_n_perm=20`). Log line confirmed `Force: ['N'] | Need to compute: ['N']` (Groups A-M correctly excluded from recomputation). Result on S3 after the run:
  - `pv_n_perm`: 20 → **50** ✓
  - `pv_lobo3_f1_perm_pvalue`: changed to **0.0196078... = 1/51**, exactly matching the `1/(n_perm+1)` floor formula for 50 permutations — proof Group N was genuinely recomputed, not just relabeled
  - `pv_lobo3_f1_macro_mean` (observed score, not permutation-dependent): **unchanged** (0.5318986715430254 both before and after), as expected since it depends only on the data/folds, not `n_perm`
  - `mk_rho_mean_all_genes` (Group L) and `xb_rank_agree` (Group M): **byte-for-byte unchanged** (0.9944781687142368 and 0.7098671849742012 respectively) — proof the force touched only Group N
