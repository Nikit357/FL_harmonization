# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Directory Contains

This directory holds work on adopting **Shambhala2** — a one-sample-at-a-time cross-platform gene expression harmonizer — for the FL dissertation benchmark. It is method `20_shambhala` in `../harmonization-scripts/bench_shared.py`.

Two subdirectories:

| Path | Status | Purpose |
|---|---|---|
| `Shambhala2/` | **Active** — R + Octave pipeline | Original working implementation; called from bench pipeline via `rpy2` |
| `Shambhala_containerized/` | **Implemented** — pure-Python pipeline | Pure-Python rewrite with stdin/stdout Octave bridge; see §Shambhala_containerized below |

See `Shambhala2/CLAUDE.md` for deep documentation of the existing implementation.

---

## Running the Existing Pipeline

```bash
# Must be run from the Shambhala2/ directory — Octave uses relative paths for buffer files
cd Shambhala2/

# Run on toy example (10 samples) — takes ~2 minutes
Rscript -e 'source("Shambhala2.R")'
# OR inside R:
# source("Shambhala2.R")

# The bottom of Shambhala2.R hardcodes the target input; toggle the commented lines
# to switch between toy (Input.csv → Output.csv) and full dataset (comb_exp_log_dedup.csv)
```

**Octave binary:** `/opt/conda/bin/octave` — hardcoded in `Shambhala2.R`. If Octave crashes, check `Shambhala2/octave_debug.log`.

**R dependency:** `matrixStats` — install with `install.packages("matrixStats")` if missing.

---

## Architecture of `Shambhala2/`

### Three-step algorithm (per sample)
1. Merge sample with calibration reference `P` → quantile-normalize together.
2. Apply CuBlock normalization (k-means clustering of genes + cubic polynomial fitting per block, 30 iterations averaged).
3. Extract the sample; rescale each gene to match mean ± std of that gene in the definitive reference `Q`.

### R ↔ Octave IPC (intermediate files)

| File | Written by | Read by | Content |
|---|---|---|---|
| `P_prim.txt` | R | Octave | Merged [Input + P] matrix, tab-separated with gene symbols |
| `args.txt` | R | Octave | Three integers: NH (input samples), NP (P samples), k |
| `Cu_bis.txt` | Octave | R | CuBlock-normalized output, space-separated with gene symbols |

All three are deleted by default (`delete_buffer_files = TRUE`). Running multiple R processes from the same directory **will corrupt these files** — each process needs its own working directory.

### CSV format (Shambhala2 internal convention)
All CSVs in `Shambhala2/` use genes-first orientation:
- **Rows = genes**, first column named `SYMBOL` (HGNC symbols)
- **Columns = samples** (sample IDs as headers)
- Values are raw/non-log counts — `readExpressionData.m` applies `log2(x+1)` internally

This is **transposed** relative to the FL project convention (samples × genes). The two `_flex` functions in `bench_shared.py` handle this transposition.

### Entry points in `Shambhala2.R`
- `Shambhala2(InputFileName, PFileName, QFileName, delete_buffer_files, k)` — reads from CSV file paths
- `Shambhala2_flex(InputDataFrame, PFileName, QFileName, delete_buffer_files, k)` — accepts a pre-loaded R data.frame; this is what `bench_shared.py` calls via `rpy2`

### Custom Octave implementations (not in GitHub original)
The Conda Octave installation lacks the MATLAB Bioinformatics Toolbox and stats package. Two files were added:
- `quantilenorm.m` — standard Bolstad 2003 quantile normalization; equivalent to MATLAB's for continuous data
- `kmeans.m` — pure-random initialization (vs. k-means++ in MATLAB); CuBlock's 30× averaging mitigates the difference

See `Shambhala2/deviation_from_original_github.md` for a full diff analysis against https://github.com/BorisovNM/Shambhala2.

### Reference datasets
- **P0.csv** — 39 Affymetrix GPL570 healthy tissue samples; calibration reference
- **Q0.csv** — ~100 GTEx RNA-seq samples across multiple tissues; definitive reference (defines target shape)
- Zenodo archive of all P/Q variants: https://zenodo.org/record/6415067

### Large data files (in `Shambhala2/large_tables/`)

| File | Description |
|---|---|
| `comb_exp_log_dedup.csv` | Full FL dataset: ~21k genes × 7237 samples |
| `comb_exp_log_dedup_strict.csv` | Strict filter: 3447 genes × 7237 samples (no-NA gene set) |
| `comb_exp_log_dedup_strict_subset.csv` | First 100 samples — use for development |
| `shambhala_harmonized_*.csv` | Previously harmonized outputs |

---

## `Shambhala_containerized/`

**Status:** Implemented. See `Shambhala_containerized.md` for the full implementation plan and `Shambhala_containerized/README.md` for usage.

### Key approved decisions
- **Eliminate R entirely.** The Q-rescaling and DataFrame merge operations (the only R logic) are replaced with pure pandas/numpy. No `rpy2`.
- **Stdin/stdout Octave bridge.** Python formats pool data as TSV, pipes it to Octave via `subprocess` stdin, captures stdout. Three targeted line edits to `Shambhala2.m` → `Shambhala2_piped.m`; all other `.m` files copied verbatim.
- **All file I/O uses FL convention** (rows = samples, columns = genes). Internal transpose to genes × samples is done inside the pipeline, invisible to callers.
- **NA strategies:** `drop` is the default (removes genes with any NaN before Octave, restores as NaN columns after). `knn` uses `sklearn.impute.KNNImputer` (same approach as `bench_shared.prepare_dataset_imputed`), activated by `--na-strategy knn`. Median imputation is not used.
- **Zero-count genes in Q:** `compute_q_statistics` adds `q_pseudocount=1e-6` (default) to all Q values before log. This is negligible for non-zero values and prevents `log(0) = -Inf` for RNA-seq Q data. Pass `--q-pseudocount 0` to disable and fall back to warn-and-exclude for zero-count genes.
- **Parallelization:** `ProcessPoolExecutor` — each worker is an isolated subprocess, avoids file descriptor conflicts. `n_workers` capped at 10.
- **Octave binary default:** `'octave'` (resolved via PATH); pass `--octave-bin /opt/conda/bin/octave` explicitly for K8s.
- **Random seed:** `--random-seed` CLI argument seeds Octave's `rand`/`randn` state via the `--eval` preamble for reproducible k-means.
- **Timeout default:** `--timeout-s` defaults to 6000 seconds.
- **P/Q inputs:** Accept FL convention CSVs (rows = samples) or S3 URIs.
- **Package files:** `README.md` (full usage guide + test descriptions), `pyproject.toml`, `requirements.txt`, `setup.py` are required.

### Three edits to `Shambhala2_piped.m` (no other `.m` changes)
1. Remove `args.txt` reading block — NH, NP, k injected via `--eval` preamble.
2. `readExpressionData("P_prim.txt", 'log2')` → `readExpressionData('/dev/stdin', 'log2')`.
3. Replace `fopen/fprintf-to-file/fclose` output block with `fprintf(1, ...)` (stdout).

### Planned directory layout
```
Shambhala_containerized/
├── run_shambhala.py           # CLI entry point
├── shambhala/
│   ├── octave_bridge.py       # subprocess stdin/stdout interface
│   ├── q_rescale.py           # Q-rescaling (Python replacement of R logic)
│   ├── na_handling.py         # drop / KNN-impute strategies
│   ├── parallel.py            # ProcessPoolExecutor dispatcher
│   └── io_utils.py            # S3 + local read/write
├── octave/
│   ├── Shambhala2_piped.m     # Modified (3 edits only)
│   ├── CuBlock.m              # Verbatim copy — ZERO changes
│   ├── quantilenorm.m         # Verbatim copy
│   ├── kmeans.m               # Verbatim copy
│   └── readExpressionData.m   # Verbatim copy
└── tests/
    ├── fixtures/              # Transposed versions of Input/Output/P0/Q0 CSVs
    └── test_*.py
```

Full specification (function signatures, docstrings, test matrix): `Shambhala_containerized.md`.

---

## Integration with FL Benchmark

`Shambhala2_flex` is called from `../harmonization-scripts/bench_shared.py` as method `20_shambhala` via `rpy2`. The working directory **must be set to `Shambhala2/`** before the call because Octave resolves all `.m` file paths relative to cwd.

When `Shambhala_containerized/` is built, it will replace this integration with a direct Python call to `run_shambhala.py` or the library API — no `rpy2` required.
