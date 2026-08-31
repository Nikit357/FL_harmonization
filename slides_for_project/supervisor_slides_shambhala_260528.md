# Supervisor Update: Shambhala Harmonization
**Daniil Nikitin — BostonGene — 28 May 2026**

---

## Slide 1 — Overview: Two Weeks of Work

**Three workstreams completed:**

1. **Shambhala containerization** — pure-Python rewrite, no R, no rpy2
2. **Parallelization & speed-up research** — 9 combinations tested; A_E approved and deployed
3. **Full benchmark run** — 1,296 harmonizations completed; metrics calculation ~45% done

**Timeline:**
- May 13 — containerized pipeline passes all 30 tests
- May 17 — first Shambhala runs start on K8s pod
- May 22 — A_E speed-up deployed; throughput jumps ~10×
- May 24–26 — metrics calculation running

---

## Slide 2 — Original Pipeline: Why It Had to Change

**The original pipeline (R + Octave, file-based IPC):**

```
R wrapper (Shambhala2.R)
  → writes P_prim.txt to disk     — merged [Input + P] matrix for QN
  → writes args.txt to disk       — 3 integers: NH (samples), NP (P size), k (k-means)
  → spawns Octave subprocess      — Octave reads P_prim.txt and args.txt
  → Octave writes Cu_bis.txt      — CuBlock-normalized output matrix
  → R reads Cu_bis.txt            — applies Q-rescaling
```

**Why each file exists:**
- `P_prim.txt` — the merged [Input + P] matrix; QN operates on the combined set so that all samples share the same rank map
- `args.txt` — Octave cannot receive Python/R variables directly; integers (how many input, P, and k-means clusters) are passed as plain text
- `Cu_bis.txt` — Octave cannot return data to R; CuBlock output is written to disk for R to read back

**Problems:** requires a full R installation; file collisions when running multiple jobs in parallel from the same directory; rpy2 version conflicts on newer Python.

---

## Slide 3 — New Pipeline: Python + Octave via Stdin/Stdout

**All three intermediate files are eliminated. Data flows through the process stdin/stdout stream instead of disk:**

```
Python (run_shambhala.py)
  → gene intersection + NA handling (drop / KNN)
  → format [batch + P] as TSV → pipe to Octave stdin
  → Octave (Shambhala2_piped.m) reads /dev/stdin
  → Octave writes normalized matrix to stdout
  → Python parses stdout → Q-rescaling in NumPy/pandas
```

**Only 3 targeted changes to `Shambhala2_piped.m`:**
1. Remove `args.txt` reading — NH, NP, k injected via Octave `--eval` before script start
2. `readExpressionData("P_prim.txt")` → `readExpressionData('/dev/stdin')`
3. `fopen / fprintf-to-file / fclose` → `fprintf(1, ...)` (stdout = file descriptor 1)

**`CuBlock.m` is untouched** — the core algorithm is verbatim from the original.

---

## Slide 4 — Module Map

```
Shambhala_containerized/
├── run_shambhala.py           ← CLI entry point; orchestrates all steps
├── shambhala/
│   ├── octave_bridge.py       ← sends TSV to Octave stdin; reads result from stdout
│   ├── parallel.py            ← splits samples into worker batches; assembles results
│   ├── progress_display.py    ← live progress bars in terminal; plain log in K8s
│   ├── q_rescale.py           ← Q reference stats; gene-level mean/std alignment
│   ├── na_handling.py         ← missing gene handling (drop or KNN-impute)
│   └── io_utils.py            ← reads/writes local files and S3 (.csv/.tsv/.tsv.gz)
├── octave/
│   ├── Shambhala2_piped.m     ← 3 targeted edits (stdin/stdout)
│   ├── CuBlock.m              ← VERBATIM — zero changes
│   └── *.m (3 files)          ← verbatim copies (QN, kmeans, readExpressionData)
├── harmonization_scripts/     ← cross-product benchmark (18 P/Q × 3 imp = 54 jobs)
└── tests/ (30 passing tests)
```

**Notes on `progress_display.py`:** "TTY" = interactive terminal (the window you type in). "ANSI" = standard escape codes that move the cursor and change colors in a terminal. In TTY mode, workers show live progress bars that update in place. In K8s (no interactive terminal), it falls back to plain timestamped log lines instead.

**`ProcessPoolExecutor`** (not threads) — each worker is an independent system process with its own Octave subprocess, so stdin/stdout pipes can never interfere with each other.

---

## Slide 5 — Initial Parallelization: Shambhala-Workers

**Problem before parallelization:** Shambhala processes one sample at a time (sequential loop inside Octave). Running the full 5,444-sample FL dataset in a single Octave process took **~9 hours** for P0std × Q0std.

**Solution: `--n-shambhala-workers` splits samples into batches:**
- The input is divided into N equal batches
- Each batch is sent to a separate Octave subprocess (independent process, own stdin/stdout pipe)
- All batches run in parallel using `ProcessPoolExecutor`
- Results are assembled and Q-rescaling is applied once on the merged output

**Result on K8s pod (32 vCPU, 240 GB RAM, 30 workers):**

| Configuration | Time for P0std × Q0std, full dataset (strict) |
|---|---|
| 1 worker (sequential Octave) | **~9 hours** |
| 30 workers (parallel batches) | **~1–2 hours** |

**Problem that remained:** Large P variants (ANTE, GTExAffy, NBGPL570 with NP=250) still took 6–8 hours even with 30 workers, because QN and CuBlock both slow down when P is larger. For KNN and softimpute imputation (more genes after imputation), time grew 4–5×. A single large-P run under knn or softimpute could take 2–3 days — the full 54-job benchmark was projected to take weeks.

---

## Slide 6 — P/Q Reference Datasets: What Was Tested

Shambhala requires two external reference sets: **P** (calibration anchor for QN) and **Q** (target distribution for final rescaling).
FL input (S0, strict imputation): **7,174 samples × 3,447 genes**.

### P datasets (9 variants) — sample counts from K8s pod logs (2026-05-17/18)

| Name | Samples | Genes in P | Genes shared with FL (strict) | Source / Notes |
|---|---|---|---|---|
| **P0std** | **39** | 11,768 | 2,293 (+Q0std) / 3,447 (+QNBKass) | Original Borisov 2021 / Zenodo; diverse tissues; standard benchmark reference |
| **NBKass** | **141** | 11,768 | 2,366 (+Q0std) / 3,447 (+QNBKass) | Normal B cells, Kassandra classifier; B-cell specific |
| **NBRNAseq** | **317** | 11,768 | 2,366 (+Q0std) / 3,447 (+QNBKass) | Normal B cells, RNA-seq; platform match for RNA-seq cohorts |
| **NBGPL570** | **250** | 11,768 | 2,366 (+Q0std) / 3,447 (+QNBKass) | Normal B cells, GPL570 Affymetrix; largest NP → **slowest** |
| **ANTE** | **202** | 36,596 | 2,366 (+Q0std) / 3,447 (+QNBKass) | Affymetrix reference cohort; large gene panel |
| **NBlegacy** | **733** | 11,768 | 2,366 (+Q0std) / 3,447 (+QNBKass) | Normal B cells, Normal_B_cells classifier; BostonGene-curated |
| **NBext** | **878** | 11,768 | 2,366 (+Q0std) / 3,447 (+QNBKass) | Normal B cells, extended set; broadest B-cell coverage |
| **Oncobox** | **779** | 36,596 | 2,366 (+Q0std) / 3,447 (+QNBKass) | Cancer reference samples; exploratory — oncology-biased anchor |
| **GTExAffy** | **651** | 20,254 | ~8,370 (knn+Q0std) | GTEx Affymetrix; tissue-diverse; note: strict run failed (gene ID mismatch) |

### Q datasets (2 variants)

| Name | Samples | Genes in Q | Notes |
|---|---|---|---|
| **Q0std** | **100** | 11,887 | Original paper reference (GTEx RNA-seq); ~2,293–2,366 genes survive intersection with strict FL input |
| **QNBKass** | **141** | 11,768 | Normal B cells, Kassandra; **perfect gene overlap with strict FL input → 3,447 genes retained** |

**Key observation from logs:** Q0std causes ~31–69% gene loss depending on imputation strategy, because it covers a different gene set than the FL panel. QNBKass shares the exact gene set with the FL strict-imputation input — zero gene loss when paired with any P dataset from the same panel.

**Pros of B-cell-specific P/Q:** closer to FL/DLBCL biology; potentially better preserves tumor-relevant signal; QNBKass avoids gene loss.
**Cons:** NBext and NBlegacy have >700 samples — larger than the FL cohort subgroups; risk of over-calibrating toward a normal B-cell expression baseline and compressing tumor subtype signal.

---

## Slide 7 — Speed-Up Motivation: Why Another Layer Was Needed

**Even with 30 parallel Octave workers, per-run times were prohibitive:**

| Scenario | Imputation | Estimated time / Shambhala run |
|---|---|---|
| P0std (NP=39), strict | strict | ~1 h |
| Large P (ANTE, GTExAffy, NBext, NBGPL570), strict | strict | 6–8 h |
| Large P, knn or softimpute | knn / softimpute | **2–3 days** |

KNN and softimpute produce more surviving genes (fewer dropped due to NAs) → larger input matrix → more work per sample in QN and CuBlock.

**Total benchmark cost without speed-up:** 54 jobs × average ~12 h = ~27 days of computation on a single pod.

**Goal:** reduce per-run time by caching computations that are identical across all N worker batches within one job.

---

## Slide 8 — Speed-Up Approaches: Plain Description of Each

**What all approaches have in common:** they pre-compute or approximate something that Octave otherwise recomputes for every sample. The tradeoff is always between speed and fidelity to the original algorithm.

| Combo | What it does (plain language) | Speedup | Mean distortion |
|---|---|---|---|
| **baseline** | Run Octave exactly as designed, no caching | 1.0× | 0.00% |
| **A** — Python QN reference | Compute the quantile normalization sort order from P **once** in Python; inject into every Octave batch instead of recomputing from P each time | ~1.0× | 0.98% |
| **C_40** — P subsampling to 40 | If P has >40 samples, replace with 40 centroids. At NP=39, has no effect. At NP=250, reduces QN matrix size significantly | ~1.0× at NP=39 | 0.00% |
| **C_20** — P subsampling to 20 | Same as C_40 but more aggressive. Faster on large P; introduces small distortion | ~1.6× | 2.45% |
| **E** — pre-run k-means clustering | Run k-means on the P gene matrix **once** in Python; pass the resulting cluster labels to all Octave batches. Octave skips its own k-means. | ~10.6× | 1.26% |
| **A_D** — Python QN + synthetic single-column P | Replace P matrix with one synthetic centroid column for CuBlock. Eliminates large-P overhead entirely but changes what CuBlock normalizes against | ~5.3× | 14.67% |
| **⭐ A_E** — Python QN + pre-run clusters | Pre-compute both: QN reference (flag A) and k-means cluster labels (flag E). Two caches, no structural change to the algorithm | **~8.6×** | **1.39%** |
| **A_D_E** | All three non-G flags combined | ~16.8× | 9.00% |
| **G** — Python CuBlock | Replace the entire Octave CuBlock with a pure Python version | — | **XFAIL** |

**Why G fails (deadlock):** Python's random number generator (PCG64) and Octave's (Mersenne Twister) produce different k-means clusters from the same seed → 226% distortion. Additionally, returning a large NumPy array from a subprocess via `ProcessPoolExecutor`'s shared queue causes a permanent hang (`QueueFeederThread` blocks on serialization). Not fixable without redesigning the inter-process communication.

**Distortion metric:** mean relative difference across all genes. Values reach ~100,000 in Q-rescaled scale, so maximum absolute difference would be dominated by one outlier gene and is not a useful metric.

---

## Slide 9 — A_E Approved Approach: How Each Flag Works

**A_E** = `--precompute-qn-reference` + `--precompute-cublock-clusters`

### Flag A — pre-compute QN reference in Python
**What it does:** Before launching worker processes, sort each gene in P by expression value and record the rank-to-value mapping. Inject this pre-computed lookup table into every Octave subprocess so it can perform QN without re-sorting P.

**Why it helps:** QN on a large P matrix (NP=250 for NBGPL570) is the single biggest bottleneck. Without caching, each of the 30 worker batches recomputes the same sort on the same P data.

**Risk:** The Python `qnorm` library and Octave's quantile normalization agree to within 0.98% on continuous data (Bolstad 2003 method). For integer/tie-heavy data the implementations can diverge slightly. In our dataset this stays below 1%.

### Flag E — pre-compute k-means clusters
**What it does:** Run k-means clustering on P genes once in Python using a fixed random seed, producing k=5 cluster labels. Pass these labels to Octave via `--eval` so Octave skips its own k-means initialization.

**Why it helps:** CuBlock's inner loop runs k-means 30 times per sample (averaging over random initializations). Pre-computing removes all 30 × N_samples random k-means calls.

**Why 1.39% distortion is acceptable:** CuBlock already averages 30 stochastic k-means runs to smooth out randomness. The single Python k-means pass uses a slightly different PRNG than Octave — the deviation (1.39%) is comparable to the natural run-to-run variability of the baseline itself.

---

## Slide 10 — A_E Performance Summary

### Lab test results (10-sample fixture, 8,174 genes, P0std NP=39)

| | Baseline | A_E |
|---|---|---|
| Wall time | ~48 s | ~5.6 s |
| Speedup | 1.0× | **8.6×** |
| Mean relative distortion | 0.00% | 1.39% |

### Real-world performance on K8s pod (S0 strategy, ~5,444 samples)

Consecutive S0 Shambhala runs from S3 timestamps after deployment:

| Variant | Timestamp | Interval |
|---|---|---|
| ANTE × Q0std (knn) | 2026-05-22 16:01:51 | — |
| NBGPL570 × Q0std (knn) | 2026-05-22 16:42:36 | **41 min** |
| NBKass × Q0std (knn) | 2026-05-22 17:22:49 | **40 min** |
| NBRNAseq × Q0std (knn) | 2026-05-22 18:03:40 | **41 min** |

**~40 minutes per run for all P/Q variants**, including the largest ones (NBGPL570, NP=250).

### Before vs after A_E deployment

| Metric | Before A_E | After A_E | Gain |
|---|---|---|---|
| Files per day | ~53 | ~517 | **~10×** |
| Large-P run time (estimated) | ~4–6 h | ~40 min | **~6–9×** |

---

## Slide 11 — Metrics Implemented: What Is Measured

The metrics pipeline (`harmonization-metrics/`) computes 11 groups of quality indicators for each harmonized expression file. Groups added or extended during this work period:

### Group J — PC variance distribution *(new)*
`pct_var_pc1` through `pct_var_pc10` and `pct_var_cum_top10`: what percentage of total gene expression variance is explained by each of the top 10 principal components.
- **Purpose:** track whether batch effects (which inflate PC1 variance) are removed. Good harmonization should have a flat distribution across PCs rather than one dominant component.
- **Before FSQN:** PC1 alone explains ~95% of variance (dominated by RNA_BATCH).
- **After good normalization:** PC1 drops to single-digit percent.

### Group K — NA retention statistics *(new)*
`pct_genes_noNA`, `pct_samples_noNA`, `n_na_cells`, `pct_na_cells`: how much data survived the normalization without missing values.
- **Purpose:** detect methods that silently drop genes or samples (e.g., strict imputation removes all genes with any NA, reducing the feature space).

### Group I — WaterMelon score *(extended)*
`wm_mean_batch`, `wm_mean_bio`, `wm_ratio_bio_batch`: entropy-based clustering quality score (Zolotovskaya et al. 2020).
- **Low `wm_mean_batch`** = samples from the same RNA batch are NOT clustered together = good batch removal.
- **High `wm_mean_bio`** = samples with the same diagnosis (FL, DLBCL, Normal) DO cluster together = biology preserved.
- **`wm_ratio_bio_batch`** combines both into a single score to rank methods.

### Previously implemented groups (A–H)
PCA R², kBET, iLISI, cLISI, ASW (batch + biology), UMAP/tSNE centroid dispersion, pairwise KS tests, variancePartition mixed-model decomposition, kNN graph connectivity, intra/inter-group distance ratios.

---

## Slide 12 — Benchmark Progress: Expression Files

**S3 bucket:** `$FL_S3_BUCKET/FL_batch_correction/exp/`
**Log date:** 2026-05-26

### Shambhala harmonizations

```
████████████████████████████████████████████████████████████████████████████████ 100%
1,297 / 1,296 expected
18 P/Q variants × 3 imputations × 12 strategies × 2 post_rm variants
```

*All combinations complete. One extra file is an exploratory speed-up test.*

### All-methods expression files on S3

```
████████████████████████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░  75%
3,282 total  (Shambhala: 1,297  |  Other methods: 1,985)
```

**12 strategies covered:** S0 (all samples), A–I batch exclusion variants, C RNA-seq only, D malignant only, F–H platform subsets, I rare-batch removal.

---

## Slide 13 — Benchmark Progress: Metrics Files

**S3 bucket:** `$FL_S3_BUCKET/FL_batch_correction/metrics/`
**Log date:** 2026-05-26

### Shambhala metrics calculated

```
████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%
579 / 1,296 expected
```

*Started 2026-05-24 on fl-metrics pod. Expected completion: ~2 more days.*

### All-methods metrics on S3

```
██████████████████████████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░  66%
2,401 total  (Shambhala: 579  |  Other methods: 1,822)
```

**Metrics date range for Shambhala:** 2026-05-24 15:40 → 2026-05-26 13:05

**Completed Shambhala metrics strategies:** A, B, C, D, E1, E2, E3, S0 ✓
**In progress:** F, G, H, I

---

## Slide 14 — Summary

### Built and deployed
- Pure-Python Shambhala pipeline — no R, no rpy2, no intermediate files
- 30-worker parallelization (shambhala-workers): 9 h → 1–2 h for P0std
- A_E speed-up approved: 8.6× lab / ~10× real-world throughput gain
- 1,296 Shambhala expression harmonizations — **100% complete**

### Running now
- Metrics: 579/1,296 Shambhala files done (~45%); projected completion ~2026-05-28
- Once complete → aggregate into `shambhala_metrics.csv` → load into `harmonization_metrics_analysis.ipynb`

### Open questions
- Which P/Q combination performs best by batch metrics? (answer pending metrics completion)
- Should Shambhala runs be restricted to RNA-seq only (same decision as for SOM pipeline)?
- Is the normal B cell Q reference (QNBKass) biologically more appropriate for FL cohorts than GTEx (Q0std)?

---

## Slide 15 — Planned Work (Next Steps)

*Translated from Russian:*

1. **Presentation on Shambhala and its adaptation** — document which normalizations ran before and after the speed-up; describe quantitatively how much faster the pipeline became; present the parallelization approach. *(This presentation.)*

2. **Comparison of test dataset before and after speed-up** — show that the output expression values do not change materially (1.39% mean relative diff); explain what was accelerated.

3. **Verify completeness of harmonizations; estimate per-run time for each Shambhala variant** via AWS S3 file listing timestamps. *(Done above — slides 10 and 12–13.)*

4. **Select the best Shambhala attempt from those available** by Wednesday evening — once metrics are complete, rank all 18 P/Q variants and pick the top performer for downstream SOM analysis.

5. **Continue trend analysis** — extend `harmonization_metrics_analysis.ipynb` with Shambhala results; compare with the 39-method benchmark.

6. **Propose a decision tree** — document the normalization choice logic (platform, imputation, post-removal) as a practical decision tree for the manuscript.

7. **Start writing the article** — begin drafting the harmonization benchmark methods and results section.

---

*Generated: 2026-05-28 | Data source: aws s3 ls logs from 2026-05-26*
*Pipeline code: `shambhala_adoption/Shambhala_containerized/` | K8s pod: `fl-shambhala`*
