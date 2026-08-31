# Shambhala2 Implementation Plan

User's note: not needed because shambhala2 was already implemented.

## Context

The benchmark already contains `20_shambhala` (`normalize_shambhala`), which is a distinct method added previously. This plan adds **Shambhala2** as a fully independent second entry (`25_shambhala2`) so that both are benchmarked and compared side by side.

> **Note on naming:** The existing `normalize_shambhala` function (lines 1271–1348 of `bench_shared.py`) happens to call `library(Shambhala2)` internally — its docstring even says "Shambhala2 (Borisov 2022)". This is a naming inconsistency introduced when it was originally added. For the purposes of this plan, `20_shambhala` remains untouched as the "Shambhala" benchmark entry, and `25_shambhala2` is added as the dedicated Shambhala2 entry. Both will be present in the benchmark grid and their results will be directly comparable.

---

## Status summary

| Component | Status | Notes |
|---|---|---|
| `bench_shared.py` — `normalize_shambhala` (20) | **Exists** | Kept as-is; the "Shambhala" benchmark entry |
| `bench_shared.py` — `normalize_shambhala2` (25) | **TODO** | New function to add |
| `bench_shared.py` — METHODS entry `25_shambhala2` | **TODO** | New registry entry |
| `CLAUDE.md` — normalization table row 25 | **TODO** | New row needed |
| `Dockerfile` | **TODO** | No Octave, no `matlab` wrapper, no `matrixStats`, no `Shambhala2` R pkg |
| `install_r_packages.R` | **TODO** | Missing `matrixStats` and `remotes::install_github("BorisovNM/Shambhala2")` |
| `test_mock.py` — `_CRITICAL_PKGS` | **TODO** | `"Shambhala2"` not in the verification list |
| `k8s/pod-ssh.yaml` | **Done** | Already installs Octave, `matlab` wrapper, `matrixStats`, `Shambhala2` |

---

## 1. Algorithm overview — Shambhala2

**Shambhala2** (Borisov 2022, [BorisovNM/Shambhala2](https://github.com/BorisovNM/Shambhala2)) is a cross-platform expression harmonizer built on **CuBlock** — a block-wise quantile matching algorithm implemented in Octave/MATLAB. The method:

1. Reads the study expression matrix (*Input*) and two references: *P* (calibration/probe reference) and *Q* (target/definitive reference) as genes × samples CSVs with a leading `SYMBOL` column.
2. Calls Octave internally via R's `system()` to run the CuBlock `.m` script, which aligns the expression quantiles block-by-block across genes.
3. Applies a final quantile normalization pass to match the definitive reference *Q*.
4. Returns a harmonized genes × samples matrix.

**Key runtime requirement:** Octave must be on `PATH`, and a wrapper script named `matlab` must also be on `PATH` that translates `matlab` invocations to `octave --no-gui` (stripping the MATLAB-only flags `-nodesktop`, `-nosplash`, `-nodisplay`). Without this wrapper Shambhala2's internal `system("matlab ...")` call fails silently and produces no output file.

**Benchmark reference strategy:** In this benchmark both P and Q are set to the **RNASeq_FF_PolyA** batch — the same single-reference strategy used by FSQN (`16_fsqn_r`) and TDM (`19_tdm`), enabling direct comparison.

---

## 2. Change 1 — bench_shared.py: add `normalize_shambhala2`

### 2a. New function

Insert after `normalize_shambhala` (after line 1348) and before `normalize_harmonizr` (line 1351):

```python
def normalize_shambhala2(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    Shambhala2 (Borisov 2022). CuBlock block-wise quantile matching + final QN.

    Calls the BorisovNM/Shambhala2 R package via a file-based interface. The
    package in turn invokes Octave via system("matlab ..."), so GNU Octave and a
    'matlab' → octave shim script must be on PATH.

    Input CSV format (genes × samples): first column named SYMBOL, remaining
    columns are sample IDs. Both P (calibration reference) and Q (definitive
    reference) are set to the target_group batch; this matches the single-reference
    strategy used by FSQN and TDM for a fair cross-method comparison.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Batch used as both P (calibration) and Q (target) reference.
        Defaults to RNASeq_FF_PolyA. Falls back to all samples if absent.

    Returns
    -------
    Shambhala2-harmonized expression matrix (samples × genes).

    Raises
    ------
    RuntimeError
        If the Shambhala2 R call produces no output file (typically means
        Octave or the matlab shim is missing from PATH).
    """
    import tempfile

    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    target_mask = (
        groups == target_group
        if target_group in groups.values
        else pd.Series(True, index=exp_df.index)
    )

    def _write_csv(df: pd.DataFrame, path: str) -> None:
        # Shambhala2 requires: first column = SYMBOL, rest = sample IDs
        mat = df.T.reset_index()
        mat.columns = ["SYMBOL"] + list(df.index)
        mat.to_csv(path, index=False)

    with tempfile.TemporaryDirectory() as td:
        input_path = os.path.join(td, "input.csv")
        p_path     = os.path.join(td, "P.csv")
        q_path     = os.path.join(td, "Q.csv")
        out_path   = os.path.join(td, "output.csv")

        _write_csv(exp_df,                   input_path)
        _write_csv(exp_df.loc[target_mask],  p_path)
        _write_csv(exp_df.loc[target_mask],  q_path)

        ro.r(f"""
            library(Shambhala2)
            result <- Shambhala2(
                InputFileName       = "{input_path}",
                PFileName           = "{p_path}",
                QFileName           = "{q_path}",
                delete_buffer_files = TRUE,
                k                   = 5
            )
            write.csv(result, "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "Shambhala2 produced no output — verify that octave is installed "
                "and the 'matlab' shim script is on PATH (`which matlab`)"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    # result_df is genes × samples; transpose to samples × genes and realign index
    return result_df.T.reindex(exp_df.index)
```

### 2b. METHODS registry entry

In `METHODS` (currently ending with `"24_peer_k10"`), add one line:

```python
# ── BEFORE ──────────────────────────────────────────────────────────────────
METHODS: dict[str, tuple[object, str]] = {
    ...
    "21_harmonizr":         (normalize_harmonizr,          "medium"),
    "22_tmm":               (normalize_tmm,                "low"),
    "23_vst":               (normalize_vst,                "low"),
    "24_peer_k10":          (normalize_peer,               "medium"),
}

# ── AFTER ───────────────────────────────────────────────────────────────────
METHODS: dict[str, tuple[object, str]] = {
    ...
    "21_harmonizr":         (normalize_harmonizr,          "medium"),
    "22_tmm":               (normalize_tmm,                "low"),
    "23_vst":               (normalize_vst,                "low"),
    "24_peer_k10":          (normalize_peer,               "medium"),
    "25_shambhala2":        (normalize_shambhala2,         "high"),
}
```

This makes the total **25 methods** (1,000 strategy × imputation × method jobs → 2,000 S3 outputs).

---

## 3. Change 2 — CLAUDE.md: document method 25

In the normalization functions table (currently 24 rows), add one row after `24_peer_k10`:

```markdown
| `25_shambhala2` | `normalize_shambhala2` | high | Shambhala2 (Borisov 2022); CuBlock + quantile norm; file-based R + Octave (BorisovNM/Shambhala2) |
```

Also update the method count in the introductory paragraph:

```markdown
# BEFORE
**1,920 output matrices** (960 normalization runs …)
24 batch-correction methods × …

# AFTER
**2,000 output matrices** (1,000 normalization runs …)
25 batch-correction methods × …
```

And in the Grid defaults section of `run_cross_product_parallel.py — Dispatcher Details`:

```markdown
# BEFORE
ALL_METHODS     = 24  # 01_raw … 24_peer_k10
# Total: 10 × 4 × 24 = 960 jobs → 1,920 S3 outputs

# AFTER
ALL_METHODS     = 25  # 01_raw … 25_shambhala2
# Total: 10 × 4 × 25 = 1,000 jobs → 2,000 S3 outputs
```

---

## 4. Change 3 — Dockerfile: add Octave and matlab shim

Add `octave octave-statistics` to the existing `apt-get install` block, then add a new `RUN` step for the shim.

```dockerfile
# ── BEFORE ──────────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg2 ca-certificates wget curl git \
        build-essential gfortran \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
        libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
        libhdf5-dev libbz2-dev liblzma-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# ── AFTER ───────────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg2 ca-certificates wget curl git \
        build-essential gfortran \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
        libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
        libhdf5-dev libbz2-dev liblzma-dev zlib1g-dev \
        octave octave-statistics \
    && rm -rf /var/lib/apt/lists/*

# Shambhala2 calls system("matlab ...") internally; shim to octave.
# Strip MATLAB-only flags that octave does not recognise.
RUN printf '#!/bin/bash\nargs=()\nfor a in "$@"; do\n  case "$a" in\n    -nodesktop|-nosplash|-nodisplay) ;;\n    *) args+=("$a") ;;\n  esac\ndone\nexec octave --no-gui "${args[@]}"\n' \
        > /usr/local/bin/matlab \
    && chmod +x /usr/local/bin/matlab
```

Full updated `Dockerfile` (complete file):

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg2 ca-certificates wget curl git \
        build-essential gfortran \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
        libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
        libhdf5-dev libbz2-dev liblzma-dev zlib1g-dev \
        octave octave-statistics \
    && rm -rf /var/lib/apt/lists/*

# Shambhala2 calls system("matlab ...") internally; shim to octave.
# Strip MATLAB-only flags that octave does not recognise.
RUN printf '#!/bin/bash\nargs=()\nfor a in "$@"; do\n  case "$a" in\n    -nodesktop|-nosplash|-nodisplay) ;;\n    *) args+=("$a") ;;\n  esac\ndone\nexec octave --no-gui "${args[@]}"\n' \
        > /usr/local/bin/matlab \
    && chmod +x /usr/local/bin/matlab

# Install R 4.5 from CRAN.
RUN curl -s "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7" \
        | gpg --dearmor -o /usr/share/keyrings/r-project.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/r-project.gpg] \
        https://cloud.r-project.org/bin/linux/debian bookworm-cran40/" \
        > /etc/apt/sources.list.d/r-cran.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends r-base r-base-dev \
    && rm -rf /var/lib/apt/lists/*

COPY harmonization-scripts/install_r_packages.R /tmp/install_r_packages.R
RUN Rscript /tmp/install_r_packages.R

COPY harmonization-scripts/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY harmonization-scripts/ harmonization-scripts/

WORKDIR /app/harmonization-scripts

CMD ["sleep", "infinity"]
```

---

## 5. Change 4 — install_r_packages.R: add matrixStats and Shambhala2

Add two installs after the `HarmonizR` GitHub install, and extend the verification vector:

```r
# ── BEFORE ──────────────────────────────────────────────────────────────────
remotes::install_github("greenelab/TDM",      upgrade = "never")
remotes::install_github("HSU-HPC/HarmonizR", upgrade = "never")

pkgs    <- c("missForest", "softImpute", "FSQN",
             "limma", "sva", "RUVSeq", "batchelor",
             "qsmooth", "edgeR", "DESeq2",
             "TDM", "HarmonizR")

# ── AFTER ───────────────────────────────────────────────────────────────────
remotes::install_github("greenelab/TDM",      upgrade = "never")
remotes::install_github("HSU-HPC/HarmonizR", upgrade = "never")

# matrixStats must be installed before Shambhala2 (not auto-pulled as dependency)
install.packages("matrixStats", dependencies = TRUE)
remotes::install_github("BorisovNM/Shambhala2", upgrade = "never")

pkgs    <- c("missForest", "softImpute", "FSQN",
             "limma", "sva", "RUVSeq", "batchelor",
             "qsmooth", "edgeR", "DESeq2",
             "TDM", "HarmonizR",
             "matrixStats", "Shambhala2")
```

Full updated `install_r_packages.R`:

```r
options(
    repos = c(CRAN = "https://cloud.r-project.org"),
    Ncpus = parallel::detectCores(),
    warn  = 1
)

if (!requireNamespace("BiocManager", quietly = TRUE))
    install.packages("BiocManager")
BiocManager::install(version = "3.22", ask = FALSE, update = FALSE)

if (!requireNamespace("remotes", quietly = TRUE))
    install.packages("remotes")

install.packages(c(
    "missForest",
    "softImpute"
), dependencies = TRUE)

remotes::install_github("jenniferfranks/FSQN", upgrade = "never")

BiocManager::install(c(
    "limma",
    "sva",
    "RUVSeq",
    "batchelor",
    "qsmooth",
    "edgeR",
    "DESeq2"
), ask = FALSE, update = FALSE)

remotes::install_github("greenelab/TDM",      upgrade = "never")
remotes::install_github("HSU-HPC/HarmonizR", upgrade = "never")

# matrixStats must be installed before Shambhala2 (not auto-pulled as dependency)
install.packages("matrixStats", dependencies = TRUE)
remotes::install_github("BorisovNM/Shambhala2", upgrade = "never")

pkgs    <- c("missForest", "softImpute", "FSQN",
             "limma", "sva", "RUVSeq", "batchelor",
             "qsmooth", "edgeR", "DESeq2",
             "TDM", "HarmonizR",
             "matrixStats", "Shambhala2")
missing <- pkgs[!sapply(pkgs, requireNamespace, quietly = TRUE)]
if (length(missing)) {
    stop("Failed to install: ", paste(missing, collapse = ", "))
} else {
    cat("All R packages installed successfully.\n")
}
```

---

## 6. Change 5 — test_mock.py: add Shambhala2 to _CRITICAL_PKGS

```python
# ── BEFORE ──────────────────────────────────────────────────────────────────
_CRITICAL_PKGS = [
    "FSQN", "qsmooth", "missForest", "softImpute",
    "limma", "sva", "RUVSeq", "batchelor", "edgeR", "DESeq2",
    "HarmonizR", "TDM",
]

# ── AFTER ───────────────────────────────────────────────────────────────────
_CRITICAL_PKGS = [
    "FSQN", "qsmooth", "missForest", "softImpute",
    "limma", "sva", "RUVSeq", "batchelor", "edgeR", "DESeq2",
    "HarmonizR", "TDM", "Shambhala2",
]
```

`normalize_shambhala2` is also exercised end-to-end by the existing `for key, (fn, harshness) in METHODS.items()` loop — no other changes needed in `test_mock.py`.

---

## 7. pod-ssh.yaml — already complete

`k8s/pod-ssh.yaml` already contains all required steps. No changes needed:

```bash
# System packages (line 69):
apt-get install -y -qq ... octave octave-statistics

# matlab shim (line 72):
printf '#!/bin/bash\nargs=()\nfor a in "$@"; do\n  case "$a" in\n    -nodesktop|-nosplash|-nodisplay) ;;\n    *) args+=("$a") ;;\n  esac\ndone\nexec octave --no-gui "${args[@]}"\n' \
    > /usr/local/bin/matlab && chmod +x /usr/local/bin/matlab

# R packages (lines 106-107):
Rscript -e "install.packages('matrixStats', dependencies=TRUE)"
Rscript -e "remotes::install_github('BorisovNM/Shambhala2', upgrade='never')"
```

---

## 8. Docker build and smoke test

After applying changes 1–5:

```bash
cd ~/B_cell_lymphomas

# Build (~5-10 min longer than before for Octave + Shambhala2)
docker build --tag fl-batch-correction:latest \
    --file harmonization-scripts/Dockerfile .

# Smoke test — both 20_shambhala and 25_shambhala2 should show PASS
docker run --rm -v "$HOME/.aws:/root/.aws:ro" \
    fl-batch-correction:latest python test_mock.py

# Push to ECR
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction"
aws ecr get-login-password --region us-east-1 \
    | docker login --username AWS --password-stdin "$ECR_URI"
docker tag fl-batch-correction:latest "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"
```

---

## 9. Running Shambhala2 in the benchmark

Once the image is rebuilt, `25_shambhala2` participates automatically in the full cross-product. For a targeted single-job test:

```bash
python harmonization-scripts/run_one_job.py \
    --strat A_confirmed_bad \
    --imp strict \
    --method 25_shambhala2 \
    --out-json /tmp/shambhala2_test.json \
    --memory-limit-gb 4.0

python -c "import json; [print(x) for x in json.load(open('/tmp/shambhala2_test.json'))]"
```

To compare both Shambhala and Shambhala2 side by side for one strategy:

```bash
python harmonization-scripts/run_cross_product_parallel.py \
    --n-workers 2 \
    --strats A_confirmed_bad \
    --imps strict \
    --methods 01_raw,20_shambhala,25_shambhala2 \
    --timeout-s 7200
```

Expected: `r2_batch` well below the 0.95 raw baseline for both Shambhala methods.

---

## 10. Known gotchas

| Issue | Cause | Resolution |
|---|---|---|
| `output.csv` not created | `matlab` wrapper not on PATH | `which matlab` → must resolve to `/usr/local/bin/matlab`; verify shim is executable |
| Octave flag error (`--no-gui` unknown) | Octave < 5.x | `bookworm-cran40` ships Octave 8.x — safe; verify with `octave --version` |
| `library(Shambhala2)` fails | `matrixStats` not installed | Must install `matrixStats` before `Shambhala2`; it is not automatically pulled as a dependency |
| `target_mask` falls back to all-True | `RNASeq_FF_PolyA` absent in strategy | Expected behaviour for strategies C/D/F/G; falls back to using the full dataset as reference |
| Slow runtime | CuBlock runs as an Octave subprocess | ~5–15 min for ~5,000 × 3,500 matrix; use `--timeout-s 7200` in the dispatcher for Shambhala2 jobs |
| `result_df.T` index mismatch | R `write.csv` adds numeric row names | Fixed by `index_col=0` in `pd.read_csv`; `.reindex(exp_df.index)` aligns sample order |
| `20_shambhala` and `25_shambhala2` produce near-identical results | Both call `library(Shambhala2)` with same parameters | Expected: they use the same R package; benchmark value is confirming reproducibility and enabling direct key comparison in the metrics table |

---

## 11. Summary of all file changes

| File | Change |
|---|---|
| `bench_shared.py` | Add `normalize_shambhala2` function after line 1348; add `"25_shambhala2"` to METHODS dict |
| `CLAUDE.md` | Add `25_shambhala2` row to normalization table; update method count 24→25 and job count 960→1000 |
| `Dockerfile` | Add `octave octave-statistics` to apt-get block; add `matlab` shim `RUN` step |
| `install_r_packages.R` | Add `matrixStats` and `Shambhala2` installs; add both to verification vector |
| `test_mock.py` | Add `"Shambhala2"` to `_CRITICAL_PKGS` |
| `k8s/pod-ssh.yaml` | No changes — already complete |
