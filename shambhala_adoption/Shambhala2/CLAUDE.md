# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An adoption of **Shambhala2** — a gene expression harmonization method that normalizes expression profiles one-by-one to a predefined target shape. It is used in the FL dissertation pipeline as one of 39 normalization methods in the harmonization benchmark.

**Algorithm (3 steps per sample):**
1. Merge the sample with calibration dataset `P`, then apply quantile normalization across [sample + P].
2. Apply CuBlock normalization (Junet et al., 2021, doi:10.1093/bioinformatics/btab105).
3. Extract the normalized sample; rescale each gene to match the mean and std of that gene in the reference dataset `Q`.

The process runs one sample at a time, making it slow on large datasets but embarrassingly parallelizable.

## How to Run

```r
# From the Shambhala2/ working directory — Octave must be in PATH
source("Shambhala2.R")
```

The script at the bottom of `Shambhala2.R` runs the full dataset automatically:
```r
Harmonized = Shambhala2("comb_exp_log_dedup.csv", "P0.csv", "Q0.csv", delete_buffer_files = TRUE, k = 5)
write.table(Harmonized, "shambhala_harmonized.csv", col.names = TRUE, row.names = FALSE, sep = ",")
```

**Octave path (Conda env):** `/opt/conda/bin/octave`

## Architecture

### File communication between R and Octave
R and Octave cannot call each other directly; they exchange data through intermediate files:

| File | Written by | Read by | Purpose |
|---|---|---|---|
| `P_prim.txt` | R | Octave | Merged Input+P matrix (tab-separated, with gene symbols) |
| `args.txt` | R | Octave | Three integers: NH (input samples), NP (P samples), k (k-means clusters) |
| `Cu_bis.txt` | Octave | R | CuBlock-normalized output matrix (space-separated, with gene symbols) |

All three buffer files are deleted by default after the run (`delete_buffer_files = TRUE`).

### R entry points (`Shambhala2.R`)
- `Shambhala2(InputFileName, PFileName, QFileName, delete_buffer_files, k)` — reads input from a CSV file path
- `Shambhala2_flex(InputDataFrame, PFileName, QFileName, delete_buffer_files, k)` — accepts a pre-loaded R data.frame directly (for programmatic use from the benchmark pipeline)

### Octave scripts
- `Shambhala2.m` — main loop: reads `P_prim.txt` and `args.txt`, iterates over NH samples, calls `quantilenorm` then `CuBlock`, writes `Cu_bis.txt`
- `CuBlock.m` — implementation of the CuBlock algorithm; uses k-means clustering of probes + cubic polynomial fitting per block
- `readExpressionData.m` — parses tab-separated expression files into a struct with `.Samples`, `.GeneList`, `.SamplesName`
- `quantilenorm.m` — custom quantile normalization replacing the MATLAB Bioinformatics Toolbox function (not available in Conda Octave)
- `kmeans.m` — custom k-means replacing the Octave statistics package (not available in Conda Octave)

**Why custom implementations:** The Conda Octave installation lacks both the MATLAB Bioinformatics Toolbox (`quantilenorm`) and the Octave statistics package (`kmeans`). Both are reimplemented using only Octave core functions.

## Data Files

| File | Description |
|---|---|
| `Input.csv` | Toy example input (10 synthetic samples, СTO prefix) |
| `Output.csv` | Toy example output from `Input.csv` |
| `P0.csv` | Calibration reference P: 39 public microarray samples (GSM IDs) from diverse tissues |
| `Q0.csv` | Target reference Q: ~100 GTEx RNA-seq samples across multiple tissues |
| `comb_exp_log_dedup.csv` | Full FL dataset input: ~21k genes × 7237 samples |
| `comb_exp_log_dedup_strict.csv` | Strict-filtered subset: 3447 genes × 7237 samples (no-NA gene set) |
| `comb_exp_log_dedup_strict_subset.csv` | First 100 samples of the strict subset (for quick test runs) |
| `shambhala_harmonized_*.csv` | Harmonized outputs from previous runs |

**CSV format requirement:** All input CSVs must have the first column named `SYMBOL` (HGNC gene symbols), with samples in subsequent columns. Values are raw/log-scale expression counts — `readExpressionData.m` applies `log2(x+1)` internally.

## Performance Notes

- Processing 100 samples with ~3,332 overlapping genes takes ~2 minutes on a modern workstation.
- Full 7,237-sample run is very slow due to the one-by-one design. Use the `_subset` files for development/debugging.
- `k = 5` (default k-means clusters) is the parameter most likely to affect speed vs. quality. Do not change without benchmarking.

## Integration with FL Benchmark

Shambhala2 is method `20_shambhala` in `harmonization-scripts/bench_shared.py`. The `Shambhala2_flex()` function is called from the Python benchmark via `rpy2`. The working directory must be set to this `Shambhala2/` folder before calling because Octave uses relative paths for all intermediate files.
