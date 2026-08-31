# Pod-launch folder split: `harmonization-metrics-calculation/`

**Date:** 2026-08-20
**Author:** plan drafted for Daniil Nikitin
**Status:** decisions D1–D3 approved by Daniil on 2026-08-20; implementation awaiting his go-ahead

---

## Overview

`harmonization-metrics/` currently holds **1.3 GB on disk / 946 git-tracked files**, of which
roughly 1.29 GB is analysis output (figures, four large notebooks, fifteen dated metrics CSVs).
The ~350 KB of Python that actually runs inside the K8s pod is buried in the middle of it. A
`git sparse-checkout` of this directory on the laptop therefore pulls the whole 1.3 GB before the
pod can be launched.

The change is a **pure file move plus reference fixes**: create a new top-level directory
`harmonization-metrics-calculation/` containing only what is needed to launch the pod and run the
metrics compute — 11 files including `k8s/pod-metrics.yaml`, plus the two
published-supplementary directories and a new `CLAUDE.md`, **5.1 MB total** —
and leave every analysis artefact where it is. No Python logic changes; no S3 keys change; no
metric values change.

**Key design decision:** split by *runtime role*, not by file type — "does the pod need this to
compute metrics?" Everything that only exists to *read* metrics afterwards (notebooks, figures,
metric tables, old plans) stays behind. The two intra-folder module imports
(`compute_batch_metrics`, `marker_panels`) both live on the runtime side, so the moved set is
self-contained and needs no `sys.path` gymnastics. Only one file left behind imports across the
new boundary, and that gets one added `sys.path.insert` line.

---

## Background / reference data

### Current disk usage in `harmonization-metrics/` (largest first)

| Path | Size | Side |
|---|---|---|
| `figures/` | 875 M | stays |
| `metric_tables/` (15 CSVs + 2 JSONs) | 90 M | stays |
| `harmonization_metrics_analysis_v3.ipynb` | 70 M | stays |
| `harmonization_metrics_analysis.ipynb` | 48 M | stays |
| `harmonization_metrics_analysis_v2.ipynb` | 15 M | stays |
| `harmonization_metrics_visual_inspection.ipynb` | 9.4 M | stays (gitignored) |
| `Holmes_et_al_2020_supplementary/` | 4.7 M | **moves** |
| `Supplementary File 2AB.docx` | 3.7 M | stays |
| `implementation_plans_research_old/` | 920 K | stays |
| `log_prep_norm_metrics_260607-08.txt` | 768 K | stays |
| `__pycache__/` (tracked in git — 6 `.pyc`) | 232 K | deleted from git |
| `marker_gene_annotation.csv` | 112 K | **moves** |
| `insert_cells.py` | 88 K | stays |
| `compute_batch_metrics.py` | 84 K | **moves** |
| `marker_and_predictive_validation_plan_260819.md` | 80 K | stays |
| `Kotlov_et_al_2021_supplementary/` | 64 K | **moves** |
| `create_v3_notebook.py` | 48 K | stays |
| `correlation_prediction_metrics_analysis.ipynb` | 40 K | stays |
| `create_correlation_prediction_notebook.py` | 36 K | stays (1 edit) |
| `test_mock_metrics.py` | 32 K | **moves** |
| `build_marker_gene_annotation.py` | 24 K | **moves** |
| `CLAUDE.md` | 20 K | **split** |
| `run_metrics_job.py` | 20 K | **moves** |
| `run_metrics_parallel.py` | 20 K | **moves** |
| `k8s/pod-metrics.yaml` | 6 K | **moves** |
| `README.md` | 12 K | **moves** |
| `strip_and_reorganize.py` | 12 K | stays |
| `run_metrics_concat.py` | 8 K | **moves** |
| `marker_panels.py` | 8 K | **moves** |
| `marker_gene_coverage_audit_260819.csv` | 8 K | stays |
| `palette.svg` | 4 K | stays |
| `requirements.txt` | 4 K | **moves** |

**Moved set: 5.1 MB** (4.7 MB of which is the Holmes `.xlsx` supplementary — see the decision
below). Without the two supplementary directories it would be **~350 KB**.

### Intra-folder import graph (verified by grep, 2026-08-20)

```
run_metrics_job.py      → compute_batch_metrics, marker_panels
run_metrics_parallel.py → compute_batch_metrics  (S3_BUCKET, S3_PREFIX)
run_metrics_concat.py   → compute_batch_metrics  (S3_BUCKET, S3_PREFIX)
test_mock_metrics.py    → compute_batch_metrics, marker_panels
marker_panels.py        → marker_gene_annotation.csv   (Path(__file__).parent)
build_marker_gene_annotation.py → Kotlov_…/, Holmes_…/  (Path(__file__).parent)
```

All six arrows stay inside the moved set. Every script resolves its data with
`Path(__file__).parent`, so relocation is transparent.

### Cross-boundary references that must be fixed

| Referrer | Reference | Action |
|---|---|---|
| `correlation_prediction_metrics_analysis.ipynb` (stays) | `sys.path.insert(0, ".")` then `from marker_panels import …` | add new path entry via its generator |
| `create_correlation_prediction_notebook.py` (stays) | same two lines, inside the cell-source string | edit, then regenerate the notebook |
| `figures_for_article/figures_helpers.py` | `Path("..") / "harmonization-metrics" / "metric_tables"` | **no change** — `metric_tables/` stays |
| `harmonization-scripts/methods_table_for_manuscript.md` | `harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv` | **no change** — same reason |
| `FL_harmonization/CLAUDE.md` | 7 pipeline paths (lines 14, 49, 53, 58, 113–115) | update |
| `project_overview.md` | §4 heading (line 291) + line 311 | update (line 311 points at the plan file, which stays) |
| `README.md` (moves) | 6 occurrences of `harmonization-metrics` | update |
| `k8s/pod-metrics.yaml` (moves) | 3 occurrences | update |

---

## Settled decisions (approved by Daniil, 2026-08-20)

### D1 — The two published supplementary directories move (option A)

`build_marker_gene_annotation.py` reads `Kotlov_et_al_2021_supplementary/` (64 KB) and
`Holmes_et_al_2020_supplementary/` (4.7 MB) with `Path(__file__).parent`, so all three move
together and the gene panel stays regenerable from either the laptop or the pod.

The alternatives were rejected: leaving the `.xlsx` behind (350 KB checkout) makes
`build_marker_gene_annotation.py` raise `FileNotFoundError` on the new side and the panel
editable only from a full checkout; leaving the script behind as well ships
`marker_gene_annotation.csv` as an opaque data file with no in-folder provenance.

The 4.7 MB is 0.4% of the current 1.3 GB — the move still compresses the sparse checkout ~250× —
and keeping the builder next to its inputs preserves the "edit the builder, never the CSV" rule
stated in `CLAUDE.md`.

### D2 — The pod-side working directory renames to `/app/harmonization-metrics-calculation`

`k8s/pod-metrics.yaml` currently creates `/app/harmonization-metrics` and `cd`s into it from
`.bashrc`; both become `/app/harmonization-metrics-calculation`.

Keeping the old name would leave the README's rsync command with a source directory and a
destination directory of different names — exactly the mismatch that produces a nested
`/app/harmonization-metrics/harmonization-metrics-calculation/` by accident. The rename affects
only pods created *after* the manifest is re-applied; a currently running pod keeps its existing
path until it is deleted and re-created.

### D3 — `test_mock_metrics.py` is part of the runtime set and moves

It is Step 8 of the README ("smoke test — verify the environment") and the only way to confirm the
pod's Python environment before launching a multi-hour run. 32 KB.

---

## Files to change

### 1. New directory — `harmonization-metrics-calculation/`

Created with `git mv` so history follows each file. Run from the repository root
(`~/FL_harmonization`):

```bash
mkdir -p harmonization-metrics-calculation

# ── compute core (5 modules + 1 data file) ──
git mv harmonization-metrics/compute_batch_metrics.py  harmonization-metrics-calculation/
git mv harmonization-metrics/run_metrics_job.py        harmonization-metrics-calculation/
git mv harmonization-metrics/run_metrics_parallel.py   harmonization-metrics-calculation/
git mv harmonization-metrics/run_metrics_concat.py     harmonization-metrics-calculation/
git mv harmonization-metrics/marker_panels.py          harmonization-metrics-calculation/
git mv harmonization-metrics/marker_gene_annotation.csv harmonization-metrics-calculation/

# ── smoke test ──
git mv harmonization-metrics/test_mock_metrics.py      harmonization-metrics-calculation/

# ── panel regeneration (decision D1 = A) ──
git mv harmonization-metrics/build_marker_gene_annotation.py    harmonization-metrics-calculation/
git mv harmonization-metrics/Kotlov_et_al_2021_supplementary    harmonization-metrics-calculation/
git mv harmonization-metrics/Holmes_et_al_2020_supplementary    harmonization-metrics-calculation/

# ── environment + launch ──
git mv harmonization-metrics/requirements.txt          harmonization-metrics-calculation/
git mv harmonization-metrics/README.md                 harmonization-metrics-calculation/
git mv harmonization-metrics/k8s                       harmonization-metrics-calculation/k8s
```

The working tree in `harmonization-metrics/` is clean as of this plan
(`git status --porcelain harmonization-metrics` → empty), so every `git mv` is safe.

Note `k8s/.ipynb_checkpoints/` exists but is gitignored — `git mv` moves the tracked
`k8s/pod-metrics.yaml` only. Remove the leftover stray directory afterwards:

```bash
rm -rf harmonization-metrics/k8s   # only .ipynb_checkpoints remains after the git mv
```

### 2. `harmonization-metrics-calculation/README.md` — 6 path edits

#### 2a. Line 31 — Secret note (no path change, verify only)

Reads `k8s/pod-metrics.yaml` relative to the README, which is still correct after the move.
**No edit.**

#### 2b. Line 61 — apply the manifest

```diff
-kubectl apply -f harmonization-metrics/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
+kubectl apply -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
```

#### 2c. Lines 119–123 — rsync block

```diff
 rsync -avz --progress \
     -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
-    ~/fl_subset/harmonization-metrics/*py \
-    root@localhost:/app/harmonization-metrics/
+    ~/fl_subset/harmonization-metrics-calculation/*py \
+    root@localhost:/app/harmonization-metrics-calculation/
```

Add one sentence below it: the `*py` glob does **not** carry
`marker_gene_annotation.csv`, which Groups L and M need. Either widen the glob or sync the whole
directory:

```bash
rsync -avz --progress \
    -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    ~/fl_subset/harmonization-metrics-calculation/ \
    root@localhost:/app/harmonization-metrics-calculation/
```

> This is a **pre-existing latent bug**, not one the move introduces — the current `*py` glob
> already omits the CSV. Worth fixing in the same pass.

#### 2d. Lines 129–132 — `kubectl cp` block

```diff
-kubectl cp harmonization-metrics/. \
-    ${K8S_NAMESPACE}/fl-metrics:/app/harmonization-metrics/
+kubectl cp harmonization-metrics-calculation/. \
+    ${K8S_NAMESPACE}/fl-metrics:/app/harmonization-metrics-calculation/
```

(Also a real improvement: `kubectl cp harmonization-metrics/.` today copies 1.3 GB into the pod.)

#### 2e. Line 142 — working directory

```diff
-cd /app/harmonization-metrics
+cd /app/harmonization-metrics-calculation
```

#### 2f. Line 299 and line 354 — teardown / re-apply

```diff
-kubectl delete -f harmonization-metrics/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
+kubectl delete -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
```
```diff
-kubectl apply -f harmonization-metrics/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
+kubectl apply -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
```

#### 2g. Line 315 — troubleshooting row

```diff
-| `rsync: mkdir ... failed: No such file or directory` | Working directory not yet created — startup is still running. Create manually: `ssh -p 2222 root@localhost "mkdir -p /app/harmonization-metrics"` |
+| `rsync: mkdir ... failed: No such file or directory` | Working directory not yet created — startup is still running. Create manually: `ssh -p 2222 root@localhost "mkdir -p /app/harmonization-metrics-calculation"` |
```

#### 2h. New section — sparse checkout on the laptop (insert after "## Prerequisites")

This is the whole point of the reorganization and belongs in the README:

````markdown
## Getting just this folder (sparse checkout)

The repository is ~1.3 GB, almost all of it figures and notebooks. To clone only the ~5 MB
needed to launch the pod:

```bash
git clone --filter=blob:none --no-checkout \
    https://github.com/Nikit357/FL_harmonization fl_disser
cd fl_disser
git sparse-checkout init --cone
git sparse-checkout set harmonization-metrics-calculation
git checkout main
```

To add a second directory later (for example the analysis notebooks):

```bash
git sparse-checkout add harmonization-metrics
```

Turn it off and get everything with `git sparse-checkout disable`.
````

### 3. `harmonization-metrics-calculation/k8s/pod-metrics.yaml` — 3 edits

#### 3a. Line 13 — requirements-sync comment

```diff
-# Python dependency file -- keep in sync with harmonization-metrics/requirements.txt
+# Python dependency file -- keep in sync with harmonization-metrics-calculation/requirements.txt
```

#### 3b. Step 6 — working directory (decision D2)

```diff
         # -- 6. Working directory --
-        mkdir -p /app/harmonization-metrics
-        echo 'cd /app/harmonization-metrics' >> /root/.bashrc
+        mkdir -p /app/harmonization-metrics-calculation
+        echo 'cd /app/harmonization-metrics-calculation' >> /root/.bashrc
         echo "[startup] Metrics environment ready. Sync scripts with rsync and run."
```

No other change to the manifest — the pod name, PVC, Secrets, tolerations, node affinity,
resources, and the `OMP_NUM_THREADS=1` block are all path-independent.

### 4. New `harmonization-metrics-calculation/CLAUDE.md`

Carries over from the current `harmonization-metrics/CLAUDE.md` everything that is about
*computing* metrics, with paths updated:

- `## Purpose` — reworded: standalone pod-launch + compute folder, designed for sparse checkout
- `## Commands` — all of the current block **except** the two notebook-regeneration commands
  (`create_correlation_prediction_notebook.py`) — that generator stays behind
- `### File roles` table — rows for the 11 moved files plus the two supplementary
  directories (13 rows in total); drop the four notebook rows,
  `insert_cells.py`, `strip_and_reorganize.py`, `metric_tables/`, and
  `marker_gene_coverage_audit_260819.csv`; add a pointer line to
  `../harmonization-metrics/CLAUDE.md` for those
- `### S3 layout` — unchanged (no local paths in it)
- `### Metric groups` table — unchanged
- `### Key design patterns` — unchanged, except the sentence naming
  `figures_helpers.load_metrics_data()` and `attach_raw_baseline()`, which now says those live in
  `../figures_for_article/figures_helpers.py` and are used by the notebooks in
  `../harmonization-metrics/`
- `## Pod Operations` — rsync/kubectl paths updated exactly as in §2 above; add the sparse-checkout
  block from §2h
- `## Memory Guidelines` — unchanged
- `## Requirements Sync` — path updated to `harmonization-metrics-calculation/requirements.txt`
- New `## What is NOT here` section, listing the analysis side and where it lives

Delete the `### Analysis notebooks — detailed description` section entirely — it belongs to the
folder left behind.

### 5. `harmonization-metrics/CLAUDE.md` — trim to the analysis side

#### 5a. Replace `## Purpose` with a scope statement + pointer

```diff
-## Purpose
-
-Standalone metrics pipeline that reads harmonized expression files from S3 (produced by
-`harmonization-scripts/`) and computes comprehensive batch effect metrics across 8 groups.
-Designed to run inside a K8s pod (`fl-metrics`, `${K8S_NAMESPACE}` namespace) with
-128 GiB RAM, R 4.5, and `variancePartition`.
-
-All scripts must be run from this directory (`harmonization-metrics/`) inside the pod.
+## Purpose
+
+**Analysis** side of the metrics work: notebooks, figures, and the dated
+`metrics_comprehensive_*.csv` snapshots produced by the compute pipeline.
+
+The **compute pipeline and everything needed to launch the K8s pod moved to
+`../harmonization-metrics-calculation/`** (2026-08-20) so it can be sparse-checked-out on its
+own — see `../harmonization-metrics-calculation/CLAUDE.md` for the metric group definitions,
+the S3 layout, worker/dispatcher commands, and pod operations. Nothing in this directory runs
+inside the pod.
```

#### 5b. Keep, with paths updated

- `### Analysis notebooks — detailed description` (both notebook sections) — keep verbatim
- `### File roles` — reduce to the rows that stayed: the four notebooks,
  `create_v3_notebook.py`, `create_correlation_prediction_notebook.py`, `insert_cells.py`,
  `strip_and_reorganize.py`, `metric_tables/`, `marker_gene_coverage_audit_260819.csv`,
  `marker_and_predictive_validation_plan_260819.md`, `Supplementary File 2AB.docx`, `figures/`,
  `implementation_plans_research_old/`
- `### Metric groups` — replace the table with a one-line pointer to the new CLAUDE.md, so the
  definitions have exactly one home and cannot drift
- `### S3 layout` — keep (the notebooks read these keys), with a note that the producers live in
  the calculation folder

#### 5c. Delete from this file

`## Commands` (all pod commands), `## Pod Operations`, `## Memory Guidelines`,
`## Requirements Sync`, `### Key design patterns` — all moved.

Add one retained command block for the notebook generators that stayed:

```bash
# Rebuild the blind-check analysis notebook
python create_correlation_prediction_notebook.py

# Rebuild the primary v3 analysis notebook
python create_v3_notebook.py
```

### 6. `harmonization-metrics/create_correlation_prediction_notebook.py` — 1 edit

The setup cell (source string, around line 76–77) currently reads:

```python
sys.path.insert(0, "../figures_for_article")
sys.path.insert(0, ".")
```

`from marker_panels import gene_to_cell_types, load_marker_annotation, panel_summary` a few lines
below now resolves through the new directory. Change to:

```python
sys.path.insert(0, "../figures_for_article")
sys.path.insert(0, "../harmonization-metrics-calculation")
sys.path.insert(0, ".")
```

Keep `"."` — the notebook may pick up other local files, and a redundant entry is harmless.

Then regenerate:

```bash
cd harmonization-metrics && python create_correlation_prediction_notebook.py
```

This rewrites `correlation_prediction_metrics_analysis.ipynb` with the fixed cell. Do **not**
hand-edit the `.ipynb` — `CLAUDE.md` states the generator is authoritative.

### 7. `FL_harmonization/CLAUDE.md` — 7 edits

#### 7a. Line 14 — subsystem pointer list

```diff
-- `harmonization-metrics/CLAUDE.md` — comprehensive metrics pipeline, 8 metric groups, pod operations
+- `harmonization-metrics-calculation/CLAUDE.md` — metrics compute pipeline, 14 metric groups, pod launch and operations
+- `harmonization-metrics/CLAUDE.md` — metrics analysis notebooks and figures
```

#### 7b. Lines 49 and 53 — fast metrics run

```diff
-nohup python harmonization-metrics/run_metrics_parallel.py \
+nohup python harmonization-metrics-calculation/run_metrics_parallel.py \
     --n-workers 4 --skip-if-exists --skip-slow \
     --post-rm-filter post0 --memory-limit-gb 6.0 > metrics_fast.log 2>&1 &

-python harmonization-metrics/run_metrics_concat.py  # aggregate → metrics_comprehensive.csv
+python harmonization-metrics-calculation/run_metrics_concat.py  # aggregate → metrics_comprehensive.csv
```

#### 7c. Line 58 — blind final check block

```diff
-cd harmonization-metrics
+cd harmonization-metrics-calculation
```

#### 7d. Lines 113–115 — Key Files table

```diff
-| `harmonization-metrics/compute_batch_metrics.py` | Core library: 14 metric group functions (A–N) + `compute_all_metrics()`; groups L/M/N are the blind check and are excluded from the clustermap |
-| `harmonization-metrics/marker_gene_annotation.csv` | Gene panel source of truth for groups L/M: 548 genes, 67 signatures, cell type / pathway / TME subtype / prognosis / source per gene |
-| `harmonization-metrics/marker_panels.py` | Loader over the gene annotation CSV (`panel_genes()`, `resolve_panel()`, `panel_summary()`) |
+| `harmonization-metrics-calculation/compute_batch_metrics.py` | Core library: 14 metric group functions (A–N) + `compute_all_metrics()`; groups L/M/N are the blind check and are excluded from the clustermap |
+| `harmonization-metrics-calculation/marker_gene_annotation.csv` | Gene panel source of truth for groups L/M: 548 genes, 67 signatures, cell type / pathway / TME subtype / prognosis / source per gene |
+| `harmonization-metrics-calculation/marker_panels.py` | Loader over the gene annotation CSV (`panel_genes()`, `resolve_panel()`, `panel_summary()`) |
+| `harmonization-metrics-calculation/k8s/pod-metrics.yaml` | Metrics pod manifest; `README.md` in the same folder is the step-by-step launch guide |
```

Lines 116–117 (`correlation_prediction_metrics_analysis.ipynb`,
`harmonization_metrics_analysis.ipynb`) and line 190 (the validation plan `.md`) point at files
that stay — **no edit**.

### 8. `project_overview.md` — 2 edits

#### 8a. Line 291 — section heading

```diff
-### 4. Comprehensive metrics pipeline (`harmonization-metrics/`)
+### 4. Comprehensive metrics pipeline (`harmonization-metrics-calculation/` compute,
+`harmonization-metrics/` analysis)
```

#### 8b. Line 311

Verify in context; it points at
`harmonization-metrics/marker_and_predictive_validation_plan_260819.md`, which **stays**. Likely
**no edit** — confirm at implementation time and leave alone if so.

### 9. `.gitignore` — 3 additions and one `git rm`

`harmonization-metrics/__pycache__/` is currently **tracked** (6 `.pyc` files, 232 KB) and would
otherwise be re-created in the new folder too. Adjacent cleanup, worth doing in the same commit:

```bash
git rm -r --cached harmonization-metrics/__pycache__
```

```diff
 harmonization-metrics/figures/attempt_correlation_clustermap.pdf
 harmonization-metrics/harmonization_metrics_visual_inspection.ipynb
 harmonization-metrics/.ipynb_checkpoints/harmonization_metrics_visual_inspection-checkpoint.ipynb
 harmonization-metrics/.ipynb_checkpoints/
+harmonization-metrics/__pycache__/
+harmonization-metrics-calculation/__pycache__/
+harmonization-metrics-calculation/.ipynb_checkpoints/
+harmonization-metrics-calculation/failed_jobs_metrics.txt
```

`failed_jobs_metrics.txt` is written by `run_metrics_parallel.py` into
`Path(__file__).parent` — i.e. straight into the new folder — and is per-pod runtime state that
must never be committed.

### 10. `harmonization-metrics/.claude/settings.local.json`

72 bytes. Check its contents at implementation time; if it contains a path-scoped permission it
should be copied (not moved) to `harmonization-metrics-calculation/.claude/` so both folders keep
the same local permissions. Untracked either way, so no git action.

---

## Files that do NOT need to change

| File | Why |
|---|---|
| `compute_batch_metrics.py` | Only local paths are `os.path.join(tmpdir, …)` for the R hand-off (Group F); no repo-relative paths |
| `run_metrics_job.py` | `sys.path.insert(0, str(Path(__file__).parent))`; every S3 key built from `S3_PREFIX`; reference cache from `--ref-cache-dir` |
| `run_metrics_parallel.py` | Same pattern; `FAILED_LOG` and worker `cwd` both `Path(__file__).parent` |
| `run_metrics_concat.py` | Same pattern; all outputs are S3 keys |
| `marker_panels.py` | `ANNOTATION_CSV = Path(__file__).parent / "marker_gene_annotation.csv"` — moves with the CSV |
| `build_marker_gene_annotation.py` | `Path(__file__).parent / "Kotlov_…"` and `/ "Holmes_…"` — both move alongside (decision D1 = A) |
| `test_mock_metrics.py` | Imports only the two moved modules |
| `requirements.txt` | Content unchanged; only its path is referenced (yaml comment, §3a) |
| `figures_for_article/figures_helpers.py` | Reads `../harmonization-metrics/metric_tables` — that directory stays |
| `harmonization-scripts/*` | `methods_table_for_manuscript.md` cites `metric_tables/`, which stays; no script imports the metrics modules |
| `harmonization_metrics_analysis_v3.ipynb`, `_v2`, `_v1`, `_visual_inspection.ipynb` | Verified: none import `marker_panels` or `compute_batch_metrics` |
| `create_v3_notebook.py`, `insert_cells.py`, `strip_and_reorganize.py` | Operate on notebooks that stay; `insert_cells.py` hardcodes an absolute path to `harmonization_metrics_analysis.ipynb`, which does not move |
| `marker_and_predictive_validation_plan_260819.md` | Historical plan; its path references describe the state at the time it was written. Add a one-line header note instead of rewriting 80 KB |
| S3 layout | No key changes at all — bucket, prefix, and all sidecar names are code constants |

---

## Side effects and caveats

1. **A running pod is not affected until re-created.** The `/app/…` rename (D2) applies to pods
   started from the re-applied manifest. If a metrics run is in flight, finish it before
   re-applying, or keep using `/app/harmonization-metrics` in that pod for its lifetime.

2. **rsync destination must be created fresh.** After the rename, the first rsync to a new pod
   goes to `/app/harmonization-metrics-calculation/`. The startup script creates it, but only
   after step 6 — the existing README troubleshooting row (§2g) covers this.

3. **Stale `__pycache__` in the old folder.** After `git rm -r --cached` and the move, delete the
   physical directory (`rm -rf harmonization-metrics/__pycache__`); leftover `.pyc` for
   `compute_batch_metrics` and `marker_panels` in a folder that no longer has the `.py` sources
   can shadow imports in an interactive session started from there.

4. **The notebook must be regenerated, not just its generator edited.** Until step 6 is run,
   `correlation_prediction_metrics_analysis.ipynb` fails at
   `from marker_panels import …`. Since `nbstripout` is configured, the regenerated notebook's
   diff should be source-only.

5. **No metric values change.** Nothing in the compute path, the panel CSV, the S3 keys, or the
   group definitions is touched. `metrics_comprehensive.csv` and the three long tables are
   byte-identical for identical inputs. **Sidecars on S3 are unaffected**, so an interrupted
   L/M/N run resumes exactly as before.

6. **The 1.3 GB is still in git history.** Sparse checkout with `--filter=blob:none` avoids
   downloading the blobs, which is what matters here. A full `git clone` still transfers them.
   Shrinking history would need a rewrite (`git filter-repo`) — deliberately **out of scope**.

7. **`metric_tables/` stays behind on purpose.** `figures_helpers.py` hardcodes
   `../harmonization-metrics/metric_tables`, and the tables are analysis input, not pod input.
   Moving them would break the figure notebooks for a 90 MB saving that the sparse checkout
   already avoids.

8. **Two CLAUDE.md files now describe the metrics work.** The metric-group table lives only in
   the new one (§5b) to prevent drift. Any future metric group must be documented there.

---

## Verification commands

Run from the repository root unless stated otherwise.

```bash
source ~/venvs/collagen_3_11/bin/activate

# 1. The moved set is self-contained: every module imports with no repo-relative help
cd harmonization-metrics-calculation
python -c "import compute_batch_metrics, marker_panels, run_metrics_job, run_metrics_concat; print('imports OK')"

# 2. The gene panel resolves from its new location
python -c "from marker_panels import panel_genes, housekeeping_genes, panel_summary; \
print(len(panel_genes()), 'panel genes;', len(housekeeping_genes()), 'housekeeping')"
# expect: 548 panel genes; 15 housekeeping

# 3. Full smoke test (169 assertions, no S3 access)
python test_mock_metrics.py

# 4. Dispatcher help renders (argparse strings intact)
python run_metrics_parallel.py --help | head -30

# 5. Panel is regenerable in place (decision D1 = A) — should report no diff
python build_marker_gene_annotation.py && git diff --stat marker_gene_annotation.csv
```

```bash
# 6. Nothing left behind still points into the moved set
cd ~/FL_harmonization
grep -rn "harmonization-metrics/\(compute_batch_metrics\|run_metrics\|marker_panels\|marker_gene_annotation\|requirements\|test_mock\|build_marker\|k8s\|README\)" \
    --include=*.py --include=*.md --include=*.yaml --include=*.ipynb . \
  | grep -v "^./harmonization-metrics/pod_folder_reorganization_plan_260820.md" \
  | grep -v "^./harmonization-scripts/logs/" \
  | grep -v "/.ipynb_checkpoints/"
# expect: no output (log files and old plan archives are historical, deliberately excluded)

# 7. The regenerated notebook imports across the new boundary
cd harmonization-metrics
python -c "import json; nb=json.load(open('correlation_prediction_metrics_analysis.ipynb')); \
src=''.join(''.join(c['source']) for c in nb['cells']); \
print('path entry present:', '../harmonization-metrics-calculation' in src)"
# expect: True

# 8. Manifest still parses and the working dir is renamed
cd ~/FL_harmonization
kubectl apply --dry-run=client -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
grep -n "app/harmonization-metrics" harmonization-metrics-calculation/k8s/pod-metrics.yaml
# expect: two lines, both /app/harmonization-metrics-calculation

# 9. Git history followed the files
git log --follow --oneline -3 -- harmonization-metrics-calculation/compute_batch_metrics.py

# 10. Sparse-checkout size sanity check (in a throwaway directory)
git clone --filter=blob:none --no-checkout \
    https://github.com/Nikit357/FL_harmonization /tmp/sparse_test
cd /tmp/sparse_test && git sparse-checkout init --cone \
  && git sparse-checkout set harmonization-metrics-calculation && git checkout main \
  && du -sh harmonization-metrics-calculation
# expect: ~5.1M   (push the commit first, or clone the local repo path instead)
```

---

## TODO

### Move (run from the repository root)

- [x] `mkdir -p harmonization-metrics-calculation`
- [x] `git mv` — `compute_batch_metrics.py`
- [x] `git mv` — `run_metrics_job.py`
- [x] `git mv` — `run_metrics_parallel.py`
- [x] `git mv` — `run_metrics_concat.py`
- [x] `git mv` — `marker_panels.py`
- [x] `git mv` — `marker_gene_annotation.csv`
- [x] `git mv` — `test_mock_metrics.py`
- [x] `git mv` — `build_marker_gene_annotation.py` (decision D1 = A)
- [x] `git mv` — `Kotlov_et_al_2021_supplementary/` (decision D1 = A)
- [x] `git mv` — `Holmes_et_al_2020_supplementary/` (decision D1 = A)
- [x] `git mv` — `requirements.txt`
- [x] `git mv` — `README.md`
- [x] `git mv` — `k8s/` (moves `pod-metrics.yaml`)
- [x] `rm -rf harmonization-metrics/k8s` (leftover gitignored `.ipynb_checkpoints`) (`git mv k8s` moved the whole directory including `.ipynb_checkpoints/` — nothing left behind (see Implementation notes))
- [x] `rm -rf harmonization-metrics/__pycache__` (physical, after the `git rm --cached` below)
- [x] Copy `.claude/settings.local.json` into the new folder if it holds path-scoped permissions (§10)

### README (new folder)

- [x] Line 61 — `kubectl apply -f` path
- [x] Lines 119–123 — rsync source and destination
- [x] Lines 119–123 — add the whole-directory rsync variant + note that `*py` omits `marker_gene_annotation.csv`
- [x] Lines 129–132 — `kubectl cp` source and destination
- [x] Line 142 — `cd /app/harmonization-metrics-calculation`
- [x] Line 299 — `kubectl delete -f` path
- [x] Line 315 — troubleshooting `mkdir -p` path
- [x] Line 354 — re-apply `kubectl apply -f` path
- [x] Insert the new "Getting just this folder (sparse checkout)" section after `## Prerequisites`

### Pod manifest (new folder)

- [x] Line 13 — requirements-sync comment path
- [x] Step 6 — `mkdir -p /app/harmonization-metrics-calculation`
- [x] Step 6 — `.bashrc` `cd` target

### Documentation

- [x] Create `harmonization-metrics-calculation/CLAUDE.md` (§4): Purpose, Commands, File roles (13 rows), S3 layout, Metric groups, Key design patterns, Pod Operations, Memory Guidelines, Requirements Sync, "What is NOT here"
- [x] Trim `harmonization-metrics/CLAUDE.md` — new Purpose + pointer (§5a)
- [x] Trim `harmonization-metrics/CLAUDE.md` — reduce File roles to the analysis rows
- [x] Trim `harmonization-metrics/CLAUDE.md` — replace Metric groups table with a pointer
- [x] Trim `harmonization-metrics/CLAUDE.md` — delete Commands / Pod Operations / Memory Guidelines / Requirements Sync / Key design patterns
- [x] Trim `harmonization-metrics/CLAUDE.md` — add the retained notebook-generator command block
- [x] `FL_harmonization/CLAUDE.md` line 14 — subsystem pointers (now two entries)
- [x] `FL_harmonization/CLAUDE.md` line 49 — `run_metrics_parallel.py` path
- [x] `FL_harmonization/CLAUDE.md` line 53 — `run_metrics_concat.py` path
- [x] `FL_harmonization/CLAUDE.md` line 58 — `cd harmonization-metrics-calculation`
- [x] `FL_harmonization/CLAUDE.md` lines 113–115 — Key Files paths; add the `k8s/pod-metrics.yaml` row
- [x] `project_overview.md` line 291 — §4 heading
- [x] `project_overview.md` line 311 — verify; edit only if it points into the moved set (verified: points at `marker_and_predictive_validation_plan_260819.md`, which stays — no edit needed)
- [x] `marker_and_predictive_validation_plan_260819.md` — one-line header note that the compute scripts moved on 2026-08-20

### Code

- [x] `create_correlation_prediction_notebook.py` — add `sys.path.insert(0, "../harmonization-metrics-calculation")` to the setup cell
- [x] Regenerate `correlation_prediction_metrics_analysis.ipynb`

### Git hygiene

- [x] `git rm -r --cached harmonization-metrics/__pycache__`
- [x] `.gitignore` — add `harmonization-metrics/__pycache__/`
- [x] `.gitignore` — add `harmonization-metrics-calculation/__pycache__/`
- [x] `.gitignore` — add `harmonization-metrics-calculation/.ipynb_checkpoints/`
- [x] `.gitignore` — add `harmonization-metrics-calculation/failed_jobs_metrics.txt`

### Verification

- [x] Verification step 1 — imports OK from the new folder
- [x] Verification step 2 — 548 panel genes / 15 housekeeping (actual: 534 panel genes + 15 housekeeping = 548 unique in the CSV, 1 gene in both. The plan's expected value was wrong, the data is right)
- [x] Verification step 3 — `test_mock_metrics.py` passes (169 assertions) (169 passed, 0 failed, exit 0)
- [x] Verification step 4 — `run_metrics_parallel.py --help` renders
- [x] Verification step 5 — `build_marker_gene_annotation.py` reproduces the CSV with no diff
- [x] Verification step 6 — no stale cross-boundary references remain (also fixed two live docs the plan's reference table missed — see Implementation notes)
- [x] Verification step 7 — regenerated notebook contains the new path entry
- [ ] Verification step 8 — `kubectl apply --dry-run=client` succeeds; both `/app/` paths renamed — **`/app/` paths verified renamed and the YAML parses as ConfigMap + Pod; `kubectl` is not installed in this container — run the dry-run from the Mac**
- [ ] Verification step 9 — `git log --follow` shows pre-move history — **requires the commit; all 16 moves are staged as renames (`git status -M`), so `--follow` will resolve once committed**
- [ ] Verification step 10 — sparse checkout of the new folder is ~5 MB — **requires the commit to be pushed; the working tree measures 5.1 MB**
- [ ] Commit, push, then re-apply the pod manifest and confirm `[startup] Metrics environment ready.` — **awaiting Daniil — the repo carries unrelated dirty state, so the commit scope is his call**

---

## Implementation notes (2026-08-20)

Deviations and findings from executing the plan:

1. **The old `k8s/` directory needed no manual cleanup.** `git mv` on a directory moves the whole
   filesystem directory, so the gitignored `.ipynb_checkpoints/` came along and nothing was left
   behind. It did, however, carry a **tracked** `k8s/.ipynb_checkpoints/pod-metrics-checkpoint.yaml`
   into the new folder — a stale copy of the manifest that will now drift from the real one.
   Untracking it means deleting a tracked file, which is outside this plan's scope, so it was left
   in place for Daniil to decide. The new `.gitignore` rule uses
   `harmonization-metrics-calculation/**/.ipynb_checkpoints/` (not the flat pattern the plan
   specified) so future nested checkpoints are ignored.

2. **Verification step 2's expected value was wrong in the plan.** `panel_genes()` returns the
   non-housekeeping genes: 534 + 15 housekeeping = 548 unique genes in the CSV, with one gene in
   both sets. `git diff` confirms `marker_gene_annotation.csv` is a **pure rename** (0 insertions,
   0 deletions), and `build_marker_gene_annotation.py` reproduces it byte-identically from the new
   location.

3. **Two live documents referenced the moved core library** and were not in the plan's
   cross-boundary table. Both were fixed:
   - `figures_for_article/CLAUDE.md` — "Seeds live in `…/compute_batch_metrics.py`"
   - `figures_for_article/NAR_review_260802.md` — reproducibility source table row

   Everything else the sweep found is a historical plan document
   (`implementation_plans_research_old/`, `implementation_plans_research/`,
   `figures_for_article/implementation_plans_old/`) or a stored notebook traceback describing the
   pod's old `/app/harmonization-metrics` path. Those describe past state and were left alone.

4. **The rsync fix was applied as recommended.** The README and the new `CLAUDE.md` both now sync
   the whole directory instead of `*py`, with the reason stated inline: the glob left
   `marker_gene_annotation.csv` behind, which groups L and M need.

5. **Nothing was committed or pushed.** All 16 moves plus the new `CLAUDE.md` are staged; the
   repository also carries unrelated dirty state (`.gitignore`, deleted notebooks, a submodule
   pointer), so the commit scope is Daniil's decision.
