# Implementation Plan — Part 1: XPN (26), DWD (27), NPN (28); Part 2: Methods 29–38

**Date:** 2026-05-06 (Part 1), 2026-05-07 (Part 2)
**Scope:** Add 14 new normalization methods and 1 new filter strategy in four parts, extending the grid from 25 → 39 methods, 10 → 11 strategies (1,000 → 1,716 normalization jobs × 2 post_rm variants = 3,432 S3 outputs; Procrustes is SKIP except on C_rnaseq_only). Part 1 (§1–12): XPN, DWD, NPN (26–28). Part 2 (§13–22): M-ComBat … Harman (29–38). Part 3 (§23–27): Procrustes (39; RNA-seq only). Part 4 (§28–30): H_gpl570_only strategy.
**Status:** Plan only — do not implement until confirmed.

---

## Context

- Dataset: ~5,444 samples, 88 cohorts, 4 platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray)
- Reference batch: `RNASeq_FF_PolyA` (n=1,039)
- Metric: one-way ANOVA R² of `RNA_BATCH` on first 10 PCA axes — lower is better; raw baseline ≈ 0.95, current best (`16_fsqn_r`) ≈ 0.16
- Current METHODS registry: 25 entries (`01_raw` … `25_angel`) in `bench_shared.py`

**Sources:**

*Part 1 — XPN, DWD, NPN (26–28):*
- XPN: Shabalin AA, Tjelmeland H, Fan C, Perou CM, Nobel AB. "Merging two gene-expression studies via cross-platform normalization." *Bioinformatics* 2008, 24(9):1154–1160. https://doi.org/10.1093/bioinformatics/btn131
- DWD: Benito M, Parker J, Du Q et al. "Adjustment of systematic microarray data biases." *Bioinformatics* 2004, 20(1):105–114. https://doi.org/10.1093/bioinformatics/btg385; modernized by Marron JS et al. 2007. DWDLargeR R package: https://cran.r-project.org/package=DWDLargeR
- NPN: Liu H, Lafferty J, Wasserman L. "The nonparanormal: semiparametric estimation of high dimensional undirected graphs." *JMLR* 2009;10:2295–2328. R implementation: `huge` (Zhao et al. 2012, CRAN).

*Part 2 — Methods 29–38:*
- M-ComBat (29): Johnson WE, Li C, Rabinovic A. "Adjusting batch effects in microarray expression data using empirical Bayes methods." *Biostatistics* 2007, 8(1):118–127. `sva::ComBat` with `ref.batch` parameter; no new package.
- reComBat (30): Nygaard V et al.; ridge-regularized ComBat for batch-biology confounding. GitHub: https://github.com/bioFAM/reComBat
- RUV-III-PRPS (31): Molania R et al. 2022 (PMID 35277707). R package: `ruv` (Bioconductor; distinct from `RUVSeq`).
- deepMNN (32): Luo et al. 2021 (PMID 34616432). GitHub: https://github.com/zoubin-ai/deepMNN
- AMDBNorm (33): PMID 34958674. GitHub: https://github.com/JoevVan/AMDBNorm
- ARSyN (34): Nueda MJ et al. *Biostatistics* 2012;13(3):553–566. PMID 22085896. R package: `NOISeq` (Bioconductor).
- DASC (35): Chen X et al. PMID 29617963. GitHub: https://github.com/zhanglabNKU/DASC
- exploBATCH (36): PMID 28883548. GitHub: https://github.com/syspremed/exploBATCH
- FAbatch (37): Hornung R et al. PMID 26753519. R package: `FAbatch` (Bioconductor).
- Harman (38): Oytam Y et al. PMID 27585881. R package: `Harman` (Bioconductor).

---

## Status Summary 

| Component | Status | Notes |
|---|---|---|
| `bench_shared.py` — `normalize_xpn` (26) | TODO | New pure-Python function |
| `bench_shared.py` — `normalize_dwd` (27) | TODO | New file-based R function |
| `bench_shared.py` — `normalize_npn` (28) | TODO | New file-based R function (`huge::npn`) |
| `bench_shared.py` — METHODS entries 26/27/28 | TODO | Three new registry entries |
| `run_norm_parallel.py` — ALL_METHODS | TODO | Add `"26_xpn"`, `"27_dwd"`, `"28_npn"` |
| `run_cross_product_parallel.py` — ALL_METHODS | TODO | Same |
| `install_r_packages.R` | TODO | Add `DWDLargeR` and `huge` install and verification |
| `k8s/pod-ssh.yaml` | TODO | Add `Rscript` lines for `DWDLargeR` and `huge` |
| `test_mock.py` — `_CRITICAL_PKGS` | TODO | Add `"DWDLargeR"`, `"huge"` |
| `Dockerfile` | No change | `DWDLargeR` and `huge` have no new system-level dependencies |
| `requirements.txt` | No change | XPN is pure Python; no new Python package |

---

## 1. Algorithm Overview

### 1.1 XPN — Cross-Platform Normalization

**Source:** Shabalin et al. 2008. The algorithm was used inside Shambhala-1 as its cross-platform engine; Shambhala-2 replaced it with CuBlock.

**What it does:**  
For each gene *g* independently, within each non-reference batch *b*:
1. Compute K quantile breakpoints of gene *g* across all samples in the reference batch → `ref_q[0..K]`.
2. Compute K quantile breakpoints of gene *g* across all samples in batch *b* → `src_q[0..K]`.
3. Map every value in batch *b* for gene *g* through a piecewise linear interpolation: `np.interp(v, src_q, ref_q)`.

This is a **gene-level** (feature-specific) correction — not a sample-level sort-and-replace. The reference batch samples are left unchanged.

**Distinction from FSQN:**
- `normalize_fsqn_py` (as implemented) does a **sample-level** sort-and-replace (ranks a sample's gene values and substitutes the reference distribution's sorted values). This changes the relative gene ordering within each sample.
- `normalize_fsqn_r` (`quantileNormalizeByFeature`) does a **gene-level** quantile mapping — closer to XPN.
- XPN uses K=50 breakpoints (sparse piecewise linear) rather than the full empirical CDF, which makes it more robust for small batches (the quantile estimate is smoother).

**Implementation:** Pure Python (`numpy.interp`). No R dependency.

**Multi-batch strategy:** Apply iteratively, one batch at a time against the reference. This is the standard use pattern as applied in Shambhala-1 and confirmed valid by Borisov 2022.

**Fallback:** If `target_group` is absent from the dataset (e.g., strategy C, D, F, G), use all samples as the reference — same fallback pattern as FSQN R and TDM.

---

### 1.2 NPN — Nonparanormal Normalization

**Source:** Liu H, Lafferty J, Wasserman L. "The nonparanormal: semiparametric estimation of high dimensional undirected graphs." *JMLR* 2009;10:2295–2328. R implementation: `huge` package (Zhao et al. 2012, CRAN).

**What it does:**
For each `RNA_BATCH` *b* independently, for each gene *g*, ranks the expression values across the *n_b* samples in that batch and maps each rank to the corresponding quantile of N(0,1):

```
NPN(g_ij) = Φ⁻¹(rank_b(g_ij) / (n_b + 1))
```

where Φ⁻¹ is the probit function and *n_b* is the number of samples in batch *b*. After transformation, every gene's marginal distribution is N(0,1) **within each batch**, removing between-batch mean and variance shifts per gene.

Applying NPN per-batch (rather than globally) aligns its correction granularity with the `RNA_BATCH` structure: the 6+ sub-platform batches are corrected independently, so `GPL570_FF` and `GPL570_FFPE` are treated as separate batches rather than pooled into one platform group.

**Distinction from `18_rank`:**
`18_rank` is a **per-sample** transformation (ranks genes within each sample, producing a uniform profile across genes). Per-batch NPN is a **per-gene** transformation (ranks samples within each batch for each gene, producing N(0,1) marginals across samples). They operate on orthogonal dimensions and are not equivalent when applied per-batch.

**Distinction from `16_fsqn_r`:**
FSQN maps each batch's gene distributions to the empirical reference batch distribution; NPN maps them to the standard normal N(0,1). NPN requires no reference batch and targets a fixed parametric distribution rather than an empirical one.

**Implementation:** File-based R interface via `huge::npn()`. A single `ro.r()` call loops over all batches in R, minimising rpy2 overhead. No R dependency beyond `huge` (CRAN).

**Fallback:** No reference batch required — each batch is normalised independently to N(0,1).

---

### 1.3 DWD — Distance-Weighted Discrimination

**Source:** Benito et al. 2004; Marron et al. 2007; implemented via `DWDLargeR` R package (Qing & Marron 2018). `DWDLargeR` is a large-scale efficient solver designed for high-dimensional data (p >> n), making it suitable for the ~3,520 genes × variable-n batch structure.

**What it does:**  
For each non-reference batch *b*:
1. Stack the reference samples and batch *b* samples into one matrix `X_combined` (genes × total_samples).
2. Assign labels: +1 for reference samples, -1 for batch *b* samples.
3. Run `genDWD(X = X_combined, y = y, penalty = "auto")` to find the DWD hyperplane normal vector `w` (length = n_genes).
4. Compute the signed mean projection of each group onto `w`:  
   `d_ref = mean(X_ref^T w)`,  `d_batch = mean(X_batch^T w)`.
5. Shift all samples in batch *b* by `(d_ref - d_batch) * w` — i.e., translate them along `w` until their centroid projection matches the reference centroid.
6. Repeat for all 87 non-reference batches.

The result is a matrix where the mean batch signal (along the DWD discriminant direction) has been removed, while within-batch variation is preserved.

**Distinction from limma (`03_limma`):**  
- `limma::removeBatchEffect` solves a linear model per gene and removes the fitted batch factor — it is a per-gene mean-shift.  
- DWD finds the global hyperplane that maximally separates two groups, then subtracts only the component along that direction. DWD is more robust in high-dimensional settings where the per-gene assumption of limma can overfit, and it weights samples inversely by their distance to the hyperplane (downweighting outliers).

**Small-batch guard:** Batches with fewer than `min_batch_size=5` samples cannot reliably estimate the DWD direction. These will be skipped (left unchanged) with a warning message.

**Implementation:** File-based R interface via `DWDLargeR`. All 87 batch iterations run inside a single `ro.r(...)` call to minimize rpy2 overhead.

---

**Part 2 algorithm overviews (methods 29–38) are in §13.**

## 2. Change 1 — `bench_shared.py`: Add `normalize_xpn` and `normalize_dwd`

### 2a. `normalize_xpn` — Insert after `normalize_fsqn_r` (after line 1185, before `normalize_quantile`)

```python
def normalize_xpn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA",
    n_quantiles: int = 50, **kw: object,
) -> pd.DataFrame:
    """
    XPN: per-gene piecewise linear quantile matching (Shabalin et al. 2008).

    Applies iteratively: each non-reference RNA_BATCH is mapped gene-by-gene
    onto the reference batch distribution via K-breakpoint piecewise linear
    interpolation (numpy.interp). Reference batch samples are unchanged.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch. Falls back to all samples if absent in data.
    n_quantiles
        Number of interior quantile breakpoints (K). Default 50.

    Returns
    -------
    XPN-normalized expression matrix.
    """
    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    ref_present = target_group in groups.values
    ref_mask = groups == target_group if ref_present else pd.Series(True, index=exp_df.index)

    ref_vals = exp_df.loc[ref_mask].values.astype(float)  # n_ref × n_genes
    quantile_levels = np.linspace(0, 100, n_quantiles + 2)  # includes 0th and 100th
    ref_q = np.percentile(ref_vals, quantile_levels, axis=0)  # (K+2) × n_genes

    out = exp_df.copy().astype(float)

    for batch in groups.unique():
        if ref_present and batch == target_group:
            continue  # reference batch: already in target space
        batch_idx = exp_df.index[groups == batch]
        batch_vals = exp_df.loc[batch_idx].values.astype(float)  # n_batch × n_genes

        src_q = np.percentile(batch_vals, quantile_levels, axis=0)  # (K+2) × n_genes

        # Vectorised over genes: apply piecewise linear map column by column.
        transformed = np.empty_like(batch_vals)
        for j in range(batch_vals.shape[1]):
            transformed[:, j] = np.interp(
                batch_vals[:, j],  # query values for gene j in this batch
                src_q[:, j],       # source quantile breakpoints for gene j
                ref_q[:, j],       # reference quantile breakpoints for gene j
            )

        out.loc[batch_idx] = transformed

    return out
```

---

### 2b. `normalize_dwd` — Insert after `normalize_xpn` (or anywhere after the `normalize_limma` block, e.g. after the medium-tier functions, around line 1090)

```python
def normalize_dwd(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA",
    min_batch_size: int = 5, **kw: object,
) -> pd.DataFrame:
    """
    DWD iterative per-batch correction via DWDLargeR (Qing & Marron 2018).

    For each non-reference RNA_BATCH, runs DWD against the reference batch to
    find the discriminant direction w, then shifts all batch samples along w
    until their centroid projection matches the reference centroid.
    Uses the file-based interface to avoid rpy2 matrix-conversion issues.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch. Falls back to all samples if absent.
    min_batch_size
        Batches with fewer samples are skipped (DWD direction unstable).

    Returns
    -------
    DWD-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    groups = ann_df.loc[exp_in.index, batch_col].astype(str)
    ref_present = target_group in groups.values
    ref_label = target_group if ref_present else groups.iloc[0]

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)   # genes × samples
        groups.rename("batch").to_csv(ann_path)

        ro.r(f"""
            library(DWDLargeR)

            exp_mat   <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df    <- read.csv("{ann_path}", row.names=1)
            batches   <- ann_df[colnames(exp_mat), "batch"]
            ref_label <- "{ref_label}"

            ref_mask  <- batches == ref_label
            if (sum(ref_mask) == 0) ref_mask <- rep(TRUE, ncol(exp_mat))
            X_ref     <- exp_mat[, ref_mask, drop=FALSE]
            result    <- exp_mat

            unique_batches <- setdiff(unique(batches), ref_label)
            for (b in unique_batches) {{
                batch_mask <- batches == b
                n_batch    <- sum(batch_mask)
                if (n_batch < {min_batch_size}) {{
                    message("DWD: skipping batch '", b, "' (n=", n_batch,
                            " < min_batch_size={min_batch_size})")
                    next
                }}
                X_batch    <- exp_mat[, batch_mask, drop=FALSE]
                X_combined <- cbind(X_ref, X_batch)
                y          <- c(rep(1, ncol(X_ref)), rep(-1, ncol(X_batch)))

                tryCatch({{
                    sol <- genDWD(X = X_combined, y = y, penalty = "auto")
                    # field name is 'beta' in DWDLargeR; guard against alternate names
                    w <- if (!is.null(sol$beta)) sol$beta else sol$w
                    w <- as.numeric(w)

                    d_ref   <- mean(as.numeric(t(X_ref)   %*% w))
                    d_batch <- mean(as.numeric(t(X_batch) %*% w))
                    shift   <- d_ref - d_batch

                    result[, batch_mask] <- X_batch + shift * w
                }}, error = function(e) {{
                    message("DWD failed for batch '", b, "': ", conditionMessage(e))
                }})
            }}

            write.csv(result, "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "DWD (DWDLargeR) produced no output file — check that "
                "the R package is installed: install.packages('DWDLargeR')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    # result_df is genes × samples; transpose and realign
    return result_df.T.reindex(exp_df.index)
```

---

### 2c. `normalize_npn` — Insert after `normalize_dwd`

```python
def normalize_npn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    NPN: Nonparanormal Normalization via huge::npn() (Liu et al. 2009).

    Applies rank-based inverse normal transformation per gene within each
    RNA_BATCH independently:
        NPN(g_ij) = Φ⁻¹(rank_b(g_ij) / (n_b + 1))
    where Φ⁻¹ is the probit function and n_b is the number of samples in
    batch b. After transformation, every gene's marginal distribution is
    N(0,1) within each batch, removing between-batch mean and variance shifts.

    All batches are processed inside a single ro.r() call to minimise rpy2
    overhead. No reference batch is required.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.

    Returns
    -------
    NPN-normalized expression matrix (same shape as input).
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.to_csv(exp_path)          # samples × genes (n × p)
        ann_df.loc[exp_in.index, [batch_col]].to_csv(ann_path)

        ro.r(f"""
            library(huge)

            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[rownames(exp_mat), "{batch_col}"])
            result  <- exp_mat

            for (b in unique(batches)) {{
                mask <- batches == b
                X_b  <- exp_mat[mask, , drop=FALSE]
                # huge.npn: n × p input (samples × genes) — correct shape
                result[mask, ] <- huge.npn(X_b, npn.func = "truncation",
                                           verbose = FALSE)
            }}

            write.csv(as.data.frame(result), "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "NPN (huge) produced no output file — check that "
                "the R package is installed: install.packages('huge')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.reindex(exp_df.index)
```

---

### 2d. METHODS Registry — Add three entries 

In `METHODS` (currently ending with `"25_angel"`), append:

```python
# ── BEFORE ──────────────────────────────────────────────────────────────────
    "24_peer_k10":          (normalize_peer,               "medium"),
    "25_angel":             (normalize_angel,              "high"),
}

# ── AFTER ───────────────────────────────────────────────────────────────────
    "24_peer_k10":          (normalize_peer,               "medium"),
    "25_angel":             (normalize_angel,              "high"),
    "26_xpn":               (normalize_xpn,                "high"),
    "27_dwd":               (normalize_dwd,                "medium"),
    "28_npn":               (normalize_npn,                "high"),
}
```

---

## 3. Change 2 — `run_norm_parallel.py`: Extend ALL_METHODS 

```python
# ── BEFORE ──────────────────────────────────────────────────────────────────
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
    "25_angel",
]

# ── AFTER ───────────────────────────────────────────────────────────────────
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
    "25_angel", "26_xpn", "27_dwd", "28_npn",
]
```

---

## 4. Change 3 — `run_cross_product_parallel.py`: Extend ALL_METHODS 

Identical change at the same list definition (same content, different file):

```python
# ── BEFORE ──────────────────────────────────────────────────────────────────
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    ...
    "25_angel",
]

# ── AFTER ───────────────────────────────────────────────────────────────────
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    ...
    "25_angel", "26_xpn", "27_dwd", "28_npn",
]
```

---

## 5. Change 4 — `install_r_packages.R`: Add DWDLargeR

`DWDLargeR` is on CRAN and requires no system-level dependencies beyond what is already installed (R 4.5, linear algebra libraries). No Bioconductor call needed.

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

install.packages("DWDLargeR", dependencies = TRUE)
install.packages("huge",      dependencies = TRUE)

pkgs    <- c("missForest", "softImpute", "FSQN",
             "limma", "sva", "RUVSeq", "batchelor",
             "qsmooth", "edgeR", "DESeq2",
             "TDM", "HarmonizR", "DWDLargeR", "huge")
```

> **Note:** `DWDLargeR` may pull in `CVXR` and `Rmosek` as optional solver dependencies. If `CVXR` installation fails (it requires system-level MOSEK or SCS solvers in some configurations), add `install.packages("CVXR", dependencies=TRUE)` before the `DWDLargeR` line. The `genDWD` function in `DWDLargeR` can fall back to SCS (open-source) — no commercial MOSEK license needed.

---

## 6. Change 5 — `k8s/pod-ssh.yaml`: Add DWDLargeR R package install

Add one line in the R packages section (after the `HarmonizR` install line, alongside the other R packages):

```bash
# ── BEFORE (inside the args: | block, after line 105) ────────────────────────
Rscript --no-save --no-restore -e "remotes::install_github('HSU-HPC/HarmonizR', upgrade='never')"
Rscript --no-save --no-restore -e "install.packages('matrixStats', dependencies=TRUE)"  && echo "[startup] matrixStats OK"

# ── AFTER ────────────────────────────────────────────────────────────────────
Rscript --no-save --no-restore -e "remotes::install_github('HSU-HPC/HarmonizR', upgrade='never')"
Rscript --no-save --no-restore -e "install.packages('DWDLargeR', dependencies=TRUE)"    && echo "[startup] DWDLargeR OK"
Rscript --no-save --no-restore -e "install.packages('huge',      dependencies=TRUE)"    && echo "[startup] huge OK"
Rscript --no-save --no-restore -e "install.packages('matrixStats', dependencies=TRUE)"  && echo "[startup] matrixStats OK"
```

---

## 7. Change 6 — `test_mock.py`: Add DWDLargeR and huge to `_CRITICAL_PKGS`  (Batch 2 additions in §18)

XPN needs no R package. DWD requires `DWDLargeR` to be verified at startup.

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
    "HarmonizR", "TDM", "DWDLargeR", "huge",
]
```

`normalize_xpn`, `normalize_dwd`, and `normalize_npn` are all exercised end-to-end by the existing `for key, (fn, harshness) in METHODS.items()` loop in `test_mock.py`. No other changes to `test_mock.py` are needed.

---

## 8. Dockerfile — No Changes

`DWDLargeR` installs from CRAN with standard R build tools already present. XPN uses only `numpy` (already installed). No new `apt-get` packages needed.

---

## 9. Running the New Methods

After implementation, smoke-test:

```bash
python harmonization-scripts/test_mock.py
# Expected: 26_xpn PASS, 27_dwd PASS (or SKIP if DWDLargeR missing), 28_npn PASS (or SKIP if huge missing)
```

Single-job targeted test:

```bash
python harmonization-scripts/run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 26_xpn \
    --out-json /tmp/xpn_test.json --memory-limit-gb 2.0

python harmonization-scripts/run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 27_dwd \
    --out-json /tmp/dwd_test.json --memory-limit-gb 4.0
```

Run only the three new methods across all strategies:

```bash
python harmonization-scripts/run_norm_parallel.py \
    --methods 26_xpn,27_dwd,28_npn \
    --n-workers 4 --skip-if-exists
```

---

## 10. Expected Results and Benchmarking Hypotheses 

| Method | Expected R² range | Rationale |
|---|---|---|
| `26_xpn` | 0.15–0.20 | Gene-level piecewise QN; very similar to `16_fsqn_r` (both are gene-level iterative QN); may match or slightly underperform FSQN R for large batches, potentially outperform for small batches |
| `27_dwd` | 0.20–0.35 | Linear discriminant correction; removes a single direction per batch; similar tier to `03_limma` and `05_combat`; DWD's distance-weighting may improve on limma for unbalanced batches |
| `28_npn` | 0.15–0.20 | Per-batch rank-to-N(0,1) transform; each RNA_BATCH corrected independently to the same N(0,1) target; removes between-batch mean and variance shifts per gene; conceptually similar to FSQN R (per-batch, per-gene) but targets a fixed parametric distribution rather than an empirical reference batch |

XPN is included to confirm whether the FSQN R result generalises to the piecewise-linear formulation. DWD is included as a linear correction baseline with different geometric motivation than limma. NPN is included as a reference-free per-batch alternative to FSQN; by targeting N(0,1) rather than an empirical reference, it avoids reference-batch selection bias.

---

## 11. Known Gotchas

| Issue | Cause | Resolution |
|---|---|---|
| XPN silently wrong for genes with zero variance in a batch | `np.percentile` returns a constant vector; `np.interp` clamps to boundary | Acceptable: zero-variance genes get a constant remapping; no exception thrown |
| XPN `ref_q[:, j]` non-monotone | Can happen with ties in small reference batches | `numpy.interp` requires `xp` to be increasing; add `np.sort()` guard on `src_q` column if needed |
| DWD: `genDWD` field name | `DWDLargeR` returns `beta`; some older versions return `w` | The `if (!is.null(sol$beta)) sol$beta else sol$w` guard in the R code handles both |
| DWD: CVXR installation fails | MOSEK/SCS solver not found | `install.packages("CVXR", dependencies=TRUE)` before `DWDLargeR`; `CVXR` ships its own SCS so commercial solver not needed |
| DWD: very slow for large combined matrices | 1,039 ref + 800 batch = 1,839 × 3,520 — feasible but `genDWD` may take 5–15 min per batch | Use `--timeout-s 7200` in the dispatcher for `27_dwd` jobs; or restrict to a subset of strategies first |
| DWD: `shift * w` overshoots | DWD direction w aligns global batch centroid; biological differences between batches partially confound the correction | Same limitation as limma; expected and acceptable for the benchmark |
| DWD: small batches skipped | `min_batch_size=5` guard | Skipped batches remain at their original values; the R `message()` call logs which batches are skipped |
| Both XPN/DWD: `target_group` absent | Strategies C (RNA-seq only), F (microarray only), G (GPL570 only) may not contain `RNASeq_FF_PolyA` | XPN falls back to all-samples reference; DWD falls back to `groups.iloc[0]` as reference label — both document this in the function body |
| NPN: tied expression values | `huge.npn` with `npn.func="truncation"` uses midrank averaging for ties — safe for continuous expression data | No action needed; ties are rare in log2 continuous expression and handled internally |
| NPN: very small batches | Batches with < ~10 samples produce unstable per-gene rank estimates; probit mapping near the tails becomes extreme | `huge.npn` handles this via the truncation threshold internally; results for small batches (e.g. n < 10) should be treated with caution but no exception is thrown |
| NPN: output scale change | NPN maps each batch's genes to N(0,1); absolute expression scale is lost; this is expected and is the point of the method | SOM portrait topology driven by relative expression not absolute scale; no downstream incompatibility |

---

## 12. Summary of All File Changes

| File | Change |
|---|---|
| `bench_shared.py` | Add `normalize_xpn` (pure Python, ~40 lines) after `normalize_fsqn_r`; add `normalize_dwd` (file-based R, ~60 lines) after `normalize_xpn`; add `normalize_npn` (file-based R, ~35 lines) after `normalize_dwd`; add `"26_xpn"`, `"27_dwd"`, `"28_npn"` to METHODS dict |
| `run_norm_parallel.py` | Append `"26_xpn"`, `"27_dwd"`, `"28_npn"` to `ALL_METHODS` list |
| `run_cross_product_parallel.py` | Append `"26_xpn"`, `"27_dwd"`, `"28_npn"` to `ALL_METHODS` list |
| `install_r_packages.R` | Add `install.packages("DWDLargeR", dependencies=TRUE)` and `install.packages("huge", dependencies=TRUE)`; add `"DWDLargeR"`, `"huge"` to verification vector |
| `k8s/pod-ssh.yaml` | Add two `Rscript` lines: `install.packages('DWDLargeR', ...)` and `install.packages('huge', ...)` |
| `test_mock.py` | Add `"DWDLargeR"`, `"huge"` to `_CRITICAL_PKGS` |
| `Dockerfile` | No changes |
| `requirements.txt` | No changes |

---

# Part 2: Methods 29–38 (2026-05-07)

**New scope extension:** Add 10 normalization methods, extending the grid from 28 → 38 methods (1,120 → 1,520 normalization jobs × 2 post_rm variants = 3,040 S3 outputs).

**Sources:** Yu et al. 2024 review (`Yu_2024_methods_review_260506.md`). Inline package URLs provided by the user:
- AMDBNorm → `https://github.com/JoevVan/AMDBNorm`
- DASC → `https://github.com/zhanglabNKU/DASC`
- exploBATCH → `https://github.com/syspremed/exploBATCH`
- deepMNN → **no inline note provided** — package URL requires user confirmation before implementing.

---

## Updated Status Summary (Batch 2 additions)

| Component | Status | Notes |
|---|---|---|
| `bench_shared.py` — `normalize_combat_ref` (29) | TODO | Uses existing `sva::ComBat` with `ref.batch` — no new package |
| `bench_shared.py` — `normalize_recombat` (30) | TODO | File-based R; `reComBat::reComBat()` |
| `bench_shared.py` — `normalize_ruv3prps` (31) | TODO | File-based R; `ruv::RUVIII()` with pseudo-sample construction |
| `bench_shared.py` — `normalize_deepmnn` (32) | NOT APPLICABLE | scRNA-seq-only (AnnData + HVG + PCA required); `NotImplementedError` → permanent SKIP |
| `bench_shared.py` — `normalize_amdbnorm` (33) | TODO | File-based R; `AMDBNorm` from GitHub `JoevVan/AMDBNorm` |
| `bench_shared.py` — `normalize_arsyn` (34) | TODO | File-based R; `ARSyNseq()` via NOISeq container |
| `bench_shared.py` — `normalize_dasc` (35) | TODO | File-based R; `DASC` from GitHub `zhanglabNKU/DASC` |
| `bench_shared.py` — `normalize_explobatch` (36) | TODO | File-based R; `exploBATCH` from GitHub `syspremed/exploBATCH` |
| `bench_shared.py` — `normalize_fabatch` (37) | TODO | File-based R; `FAbatch` from Bioconductor |
| `bench_shared.py` — `normalize_harman` (38) | TODO | File-based R; `Harman::harman()` from Bioconductor |
| `bench_shared.py` — METHODS entries 29–38 | TODO | Ten new registry entries |
| `run_norm_parallel.py` — ALL_METHODS | TODO | Append all 10 new keys |
| `run_cross_product_parallel.py` — ALL_METHODS | TODO | Same |
| `install_r_packages.R` | TODO | 4 GitHub packages + 4 Bioconductor packages |
| `k8s/pod-ssh.yaml` | TODO | 8 new `Rscript` install lines |
| `test_mock.py` — `_CRITICAL_PKGS` | TODO | Add 8 new R package names |
| `requirements.txt` | TODO (conditional) | Add deepMNN Python package once URL confirmed |
| `Dockerfile` | No change | No new system-level dependencies expected |

---

## 13. Algorithm Overviews — Methods 29–38

### 13.1 M-ComBat (`29_combat_ref`)

Same empirical Bayes location-scale model as `05_combat` (`sva::ComBat`) but with `ref.batch="RNASeq_FF_PolyA"` — all batches are shifted toward the reference batch distribution rather than the global mean. Reference batch samples returned unchanged. No new package needed; single parameter change to the existing `normalize_combat` R call.

### 13.2 reComBat (`30_recombat`)

ComBat variant replacing OLS batch estimation with ridge regression, specifically for settings where batch and biology covariates are correlated. Regularization λ selected via cross-validation. Package: `remotes::install_github("bioFAM/reComBat")`. Function: `reComBat::reComBat(dat, batch, mod)` — same external interface as `sva::ComBat`. Expect slow runtime due to per-gene CV; use `--timeout-s 7200`.

### 13.3 RUV-III-PRPS (`31_ruv3prps`)

Pseudo-Replicate Pseudo-Samples: constructs virtual replicates from samples sharing the same `Diagnosis_cell_type_unified` label within each RNA_BATCH, then runs `ruv::RUVIII()` on the augmented matrix. No matched samples or negative-control genes required. Package: `BiocManager::install("ruv")` — distinct from `RUVSeq` used by `09_ruv`. Key parameter: `k_factors=5`. Fallback to uncorrected data if no valid (bio × batch) cells with ≥ 2 samples exist.

### 13.4 deepMNN (`32_deepmnn`) — **NOT APPLICABLE**

MNN correction augmented with a deep neural network (Luo et al. 2021, PMID 34616432; GitHub: https://github.com/zoubin-ai/deepMNN). **API inspection reveals this is a scRNA-seq-only method:** the entry point `correct_scanpy()` accepts a list of AnnData objects (one per batch) and requires per-cell normalization → log1p → HVG selection → PCA (`adata.obsm['X_pca']`) before calling — standard scRNA-seq preprocessing that is incompatible with bulk RNA-seq / microarray expression matrices. The package is not on PyPI and has no `setup.py`; it must be cloned from GitHub. No pip install is possible. `normalize_deepmnn` retains its `NotImplementedError` body and will be recorded as SKIP by the dispatcher.

### 13.5 AMDBNorm (`33_amdbnorm`)

Adjustment Mean Distribution-Based Normalization (PMID 34958674; GitHub: `JoevVan/AMDBNorm`). Aligns both the mean expression and distributional shape of each gene in non-reference batches to match the reference batch. Feature-specific correction; conceptually between M-ComBat (mean only) and FSQN (full quantile matching). Reference batch: `RNASeq_FF_PolyA`. Verify exact function name from package README before finalizing the R call.

### 13.6 ARSyN (`34_arsyn`)

ANOVA-ASCA Removal of Systematic Noise (PMID 22085896; Bioconductor: `NOISeq`). Decomposes expression into biology + batch + residual using ANOVA, then subtracts the batch PCA component. Validated for microarray; applied to all strategies for benchmarking comparison. Requires wrapping the expression matrix in a `NOISeqData` container via `NOISeq::readData()` before calling `ARSyNseq()`. Corrected data extracted via `assayData(result)$exprs`.

### 13.7 DASC (`35_dasc`)

Data-Adaptive Shrinkage and Clustering via semi-NMF (PMID 29617963; GitHub: `zhanglabNKU/DASC`). Unsupervised estimation of hidden batch factors with shrinkage regularization; regresses estimated factors from the expression matrix. No biological labels required. Non-convex: results depend on initialization; add `set.seed(42)` in the R call for reproducibility. Verify exact function name from package README.

### 13.8 exploBATCH (`36_explobatch`)

PPCCA-based batch detection and correction (PMID 28883548; GitHub: `syspremed/exploBATCH`). Tests for batch significance via Probabilistic PCA with Covariates Analysis, then subtracts the batch component. Validated for microarray; applied broadly here. Computationally intensive — use `tryCatch` guard and `--timeout-s 7200`. Verify exact function name from package README.

### 13.9 FAbatch (`37_fabatch`)

Factor Adjustment batch correction = sequential ComBat EB + SVA latent factor regression in a unified model (PMID 26753519; Bioconductor: `FAbatch`). Validated for microarray and DNA methylation. The `batchadjust(y, batch, type="among")` function call returns a list; corrected data is in `$adj.data`. Verify field name from `?FAbatch::batchadjust`.

### 13.10 Harman (`38_harman`)

PCA-based batch correction with an explicit constraint on the probability of over-removing biological signal (PMID 27585881; Bioconductor: `Harman`). Cross-platform validated (RNA-seq + microarray). The `limit=0.05` parameter is the default; lower values are more conservative (less correction). Two-step R API: `pc <- harman(data, expt=bio, batch=batches, limit=0.05)` then `result <- reconstructData(pc)`.

---

## 14. Change 1 — `bench_shared.py`: Functions and METHODS Entries

Insert all 10 functions after `normalize_npn`. All R-based functions use the file-based interface (`tempfile.TemporaryDirectory` → write CSV → `ro.r(...)` → read result CSV).

### 14.1 `normalize_combat_ref` — after `normalize_npn`

```python
def normalize_combat_ref(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL,
    target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    M-ComBat: ComBat anchored to a reference batch (sva::ComBat ref.batch).

    Same empirical Bayes location-scale model as 05_combat but shifts all
    batches toward the reference batch distribution (RNASeq_FF_PolyA) rather
    than the global mean. Reference batch samples are returned unchanged.
    Falls back to standard ComBat (no ref.batch) when the reference is absent.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    batch_col
        Batch column (RNA_BATCH).
    bio_col
        Biology covariate column used in model matrix.
    target_group
        Reference batch. Falls back to global-mean ComBat if absent.

    Returns
    -------
    M-ComBat corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    groups = ann_df.loc[exp_in.index, batch_col].astype(str)
    ref_present = target_group in groups.values

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)   # genes × samples
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ref_arg = f', ref.batch="{target_group}"' if ref_present else ""
        ro.r(f"""
            library(sva)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[colnames(exp_mat), "{batch_col}"])
            bio     <- as.character(ann_df[colnames(exp_mat), "{bio_col}"])
            mod     <- model.matrix(~ bio)
            result  <- ComBat(dat=exp_mat, batch=batches, mod=mod{ref_arg})
            write.csv(as.data.frame(result), "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("M-ComBat produced no output — check sva package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)
```

### 14.2 `normalize_recombat`

```python
def normalize_recombat(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    reComBat: regularized ComBat with ridge regression (bioFAM/reComBat).

    Replaces OLS batch estimation with ridge regression to handle partial
    batch-biology confounding. Lambda selected via cross-validation.
    Same external interface as sva::ComBat.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.

    Returns
    -------
    reComBat-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ro.r(f"""
            library(reComBat)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[colnames(exp_mat), "{batch_col}"])
            bio     <- as.character(ann_df[colnames(exp_mat), "{bio_col}"])
            mod     <- model.matrix(~ bio)
            result  <- reComBat(dat=exp_mat, batch=batches, mod=mod)
            write.csv(as.data.frame(result), "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "reComBat produced no output. "
                "Install: remotes::install_github('bioFAM/reComBat')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)
```

### 14.3 `normalize_ruv3prps`

```python
def normalize_ruv3prps(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL,
    k_factors: int = 5, min_cell_size: int = 2, **kw: object,
) -> pd.DataFrame:
    """
    RUV-III-PRPS: RUV-III with Pseudo-Replicate Pseudo-Samples
    (Molania et al. 2022; Bioconductor: ruv).

    For each (bio_col × batch_col) cell with >= min_cell_size samples,
    computes the cell mean as a pseudo-replicate. Stacks pseudo-samples
    with original data to build an augmented matrix Y_aug, then runs
    ruv::RUVIII() to estimate and remove unwanted variation factors W.
    Returns corrected values for original samples only.

    Falls back to uncorrected data if no valid pseudo-replicate cells exist.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    k_factors
        Number of RUV unwanted variation factors (default 5).
    min_cell_size
        Minimum samples per (bio × batch) cell to form a pseudo-replicate.

    Returns
    -------
    RUV-III-PRPS corrected expression matrix (same shape as input).
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.to_csv(exp_path)   # samples × genes — RUVIII expects n × p
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ro.r(f"""
            library(ruv)
            Y       <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[rownames(Y), "{batch_col}"])
            bio     <- as.character(ann_df[rownames(Y), "{bio_col}"])
            cells   <- paste(bio, batches, sep="__")
            valid_cells <- names(which(table(cells) >= {min_cell_size}))

            if (length(valid_cells) == 0) {{
                message("RUV-III-PRPS: no valid pseudo-replicates — returning uncorrected")
                write.csv(as.data.frame(Y), "{out_path}")
            }} else {{
                pseudo_Y <- do.call(rbind, lapply(valid_cells, function(cell) {{
                    colMeans(Y[cells == cell, , drop=FALSE])
                }}))
                rownames(pseudo_Y) <- paste0("pseudo__", valid_cells)
                Y_aug    <- rbind(Y, pseudo_Y)
                n_orig   <- nrow(Y)
                n_aug    <- nrow(Y_aug)
                n_groups <- length(valid_cells)

                # M: n_aug × n_groups replicate indicator matrix
                M <- matrix(0L, nrow=n_aug, ncol=n_groups)
                for (j in seq_len(n_groups)) {{
                    orig_idx   <- which(cells == valid_cells[j])
                    pseudo_idx <- n_orig + j
                    M[c(orig_idx, pseudo_idx), j] <- 1L
                }}

                k <- min({k_factors}, n_groups - 1L)
                if (k < 1L) k <- 1L

                tryCatch({{
                    ctl    <- rep(TRUE, ncol(Y_aug))
                    fit    <- RUVIII(Y=Y_aug, M=M, ctl=ctl, k=k)
                    newY   <- if (!is.null(fit$newY)) fit$newY else fit$corrY
                    result <- newY[seq_len(n_orig), , drop=FALSE]
                    rownames(result) <- rownames(Y)
                    write.csv(as.data.frame(result), "{out_path}")
                }}, error = function(e) {{
                    message("RUV-III-PRPS RUVIII failed: ", conditionMessage(e),
                            " — returning uncorrected data")
                    write.csv(as.data.frame(Y), "{out_path}")
                }})
            }}
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("RUV-III-PRPS produced no output — check ruv package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.reindex(exp_df.index)
```

### 14.4 `normalize_deepmnn` — placeholder

> **Package URL not provided.** Reference: Luo et al. 2021 (PMID 34616432). Provide the GitHub/PyPI URL, install the package, and replace the `NotImplementedError` body before running benchmarks.

```python
def normalize_deepmnn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    deepMNN: NOT APPLICABLE to this benchmark.

    deepMNN (Luo et al. 2021, PMID 34616432; GitHub: zoubin-ai/deepMNN)
    is a scRNA-seq-only method. Its entry point correct_scanpy() requires a
    list of AnnData objects with HVG selection and PCA already computed
    (adata.obsm['X_pca']) — standard scRNA-seq preprocessing incompatible
    with bulk RNA-seq / microarray expression matrices. The package is not
    on PyPI and cannot be pip-installed. This function raises NotImplementedError
    and is recorded as SKIP by the dispatcher, same as 22_tmm on mixed data.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.

    Returns
    -------
    Never returns — always raises NotImplementedError.
    """
    raise NotImplementedError(
        "deepMNN (zoubin-ai/deepMNN) is NOT APPLICABLE: scRNA-seq-only method "
        "that requires AnnData + HVG + PCA preprocessing. Not compatible with "
        "bulk RNA-seq / microarray matrices. Reference: Luo et al. 2021, "
        "PMID 34616432."
    )
```

### 14.5 `normalize_amdbnorm`

> Verify exact R function name and parameter names from `https://github.com/JoevVan/AMDBNorm` README before finalizing.

```python
def normalize_amdbnorm(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    AMDBNorm: Adjustment Mean Distribution-Based Normalization
    (PMID 34958674; GitHub: JoevVan/AMDBNorm).

    Feature-by-feature alignment of mean and distributional shape of each
    gene in non-reference batches to match the reference batch. Correction
    strength between M-ComBat (mean-only) and FSQN (full quantile matching).
    Falls back to first-listed batch as reference if RNASeq_FF_PolyA absent.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    target_group
        Reference batch (default: RNASeq_FF_PolyA).

    Returns
    -------
    AMDBNorm-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    groups = ann_df.loc[exp_in.index, batch_col].astype(str)
    ref_label = target_group if target_group in groups.values else groups.iloc[0]

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)   # genes × samples
        groups.rename("batch").to_csv(ann_path)

        ro.r(f"""
            library(AMDBNorm)
            # TODO: verify exact function name from package README
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            batches <- read.csv("{ann_path}", row.names=1)[colnames(exp_mat), "batch"]
            result  <- AMDBNorm(data=exp_mat, batch=batches, ref_batch="{ref_label}")
            write.csv(as.data.frame(result), "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "AMDBNorm produced no output. "
                "Install: remotes::install_github('JoevVan/AMDBNorm')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)
```

### 14.6 `normalize_arsyn`

```python
def normalize_arsyn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    ARSyN: ANOVA-ASCA Removal of Systematic Noise (PMID 22085896; NOISeq).

    Decomposes expression into biology + batch + residual via ANOVA-ASCA,
    subtracts the batch PCA component. Validated for microarray; applied here
    to all strategies. Requires NOISeq data container wrapping.
    tryCatch guard returns uncorrected data on failure.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.

    Returns
    -------
    ARSyN-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)   # genes × samples
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ro.r(f"""
            library(NOISeq)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            factors <- data.frame(
                Batch     = as.character(ann_df[colnames(exp_mat), "{batch_col}"]),
                Condition = as.character(ann_df[colnames(exp_mat), "{bio_col}"]),
                row.names = colnames(exp_mat)
            )
            mydata <- readData(data=exp_mat, factors=factors)
            tryCatch({{
                myresult <- ARSyNseq(mydata, factor="Batch", norm="n",
                                     logtransf=FALSE)
                result   <- assayData(myresult)$exprs
                write.csv(as.data.frame(result), "{out_path}")
            }}, error = function(e) {{
                message("ARSyN failed: ", conditionMessage(e),
                        " — returning uncorrected data")
                write.csv(as.data.frame(exp_mat), "{out_path}")
            }})
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("ARSyN produced no output — check NOISeq package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)
```

### 14.7 `normalize_dasc`

> Verify exact R function name from `https://github.com/zhanglabNKU/DASC` README before finalizing.

```python
def normalize_dasc(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    DASC: Data-Adaptive Shrinkage and Clustering via semi-NMF
    (PMID 29617963; GitHub: zhanglabNKU/DASC).

    Unsupervised estimation of hidden batch factors via semi-NMF with
    shrinkage regularization; regresses factors from the expression matrix.
    No biological labels or negative-control genes required.
    Non-convex: set.seed(42) ensures reproducibility across runs.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.

    Returns
    -------
    DASC-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    groups = ann_df.loc[exp_in.index, batch_col].astype(str)

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)   # genes × samples
        groups.rename("batch").to_csv(ann_path)

        ro.r(f"""
            library(DASC)
            set.seed(42)
            # TODO: verify exact function name/signature from GitHub README
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            batches <- read.csv("{ann_path}", row.names=1)[colnames(exp_mat), "batch"]
            tryCatch({{
                result <- DASC(data=exp_mat, batch=batches)
                write.csv(as.data.frame(result), "{out_path}")
            }}, error = function(e) {{
                message("DASC failed: ", conditionMessage(e),
                        " — returning uncorrected data")
                write.csv(as.data.frame(exp_mat), "{out_path}")
            }})
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "DASC produced no output. "
                "Install: remotes::install_github('zhanglabNKU/DASC')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)
```

### 14.8 `normalize_explobatch`

> Verify exact R function name from `https://github.com/syspremed/exploBATCH` README before finalizing.

```python
def normalize_explobatch(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    exploBATCH: PPCCA-based batch detection and correction
    (PMID 28883548; GitHub: syspremed/exploBATCH).

    Tests for batch significance via Probabilistic PCA with Covariates
    Analysis (PPCCA), then subtracts the estimated batch component.
    Validated for microarray; applied to all strategies. Computationally
    intensive on large matrices — tryCatch returns uncorrected on failure.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.

    Returns
    -------
    exploBATCH-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ro.r(f"""
            library(exploBATCH)
            # TODO: verify exact function name from GitHub README
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[colnames(exp_mat), "{batch_col}"])
            bio     <- as.character(ann_df[colnames(exp_mat), "{bio_col}"])
            tryCatch({{
                result <- exploBATCH(data=exp_mat, batch=batches, bio=bio)
                write.csv(as.data.frame(result), "{out_path}")
            }}, error = function(e) {{
                message("exploBATCH failed: ", conditionMessage(e),
                        " — returning uncorrected data")
                write.csv(as.data.frame(exp_mat), "{out_path}")
            }})
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "exploBATCH produced no output. "
                "Install: remotes::install_github('syspremed/exploBATCH')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)
```

### 14.9 `normalize_fabatch`

> The `FAbatch` Bioconductor package main function is `batchadjust()`. Corrected data is in the return list under `$adj.data`. Verify from `?FAbatch::batchadjust` before finalizing.

```python
def normalize_fabatch(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    FAbatch: Factor Adjustment = ComBat EB + SVA in a unified model
    (PMID 26753519; Bioconductor: FAbatch).

    Sequential (1) empirical Bayes location-scale adjustment and (2)
    surrogate variable regression. Validated for microarray/DNA methylation;
    applied broadly here. Output extracted from result$adj.data.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.

    Returns
    -------
    FAbatch-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)   # genes × samples
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ro.r(f"""
            library(FAbatch)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.factor(ann_df[colnames(exp_mat), "{batch_col}"])
            tryCatch({{
                res    <- batchadjust(y=exp_mat, batch=batches, type="among")
                # adjusted data may be in $adj.data or $corrected; guard both
                result <- if (!is.null(res$adj.data)) res$adj.data else res
                write.csv(as.data.frame(result), "{out_path}")
            }}, error = function(e) {{
                message("FAbatch failed: ", conditionMessage(e),
                        " — returning uncorrected data")
                write.csv(as.data.frame(exp_mat), "{out_path}")
            }})
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("FAbatch produced no output — check FAbatch package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)
```

### 14.10 `normalize_harman`

```python
def normalize_harman(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL,
    limit: float = 0.1, **kw: object,
) -> pd.DataFrame:
    """
    Harman: PCA-based batch correction with overcorrection constraint
    (PMID 27585881; Bioconductor: Harman).

    Corrects batch effects in PCA space with a formal bound on the probability
    of over-removing biological signal. limit=0.1 (default): 10% overcorrection
    probability allowed. Cross-platform validated (RNA-seq + microarray).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    limit
        Overcorrection probability bound (default 0.1). Lower values are
        more conservative (less correction); 1.0 is unconstrained.

    Returns
    -------
    Harman-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)   # genes × samples
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ro.r(f"""
            library(Harman)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[colnames(exp_mat), "{batch_col}"])
            bio     <- as.character(ann_df[colnames(exp_mat), "{bio_col}"])
            tryCatch({{
                pc     <- harman(exp_mat, expt=bio, batch=batches, limit={limit})
                result <- reconstructData(pc)
                write.csv(as.data.frame(result), "{out_path}")
            }}, error = function(e) {{
                message("Harman failed: ", conditionMessage(e),
                        " — returning uncorrected data")
                write.csv(as.data.frame(exp_mat), "{out_path}")
            }})
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("Harman produced no output — check Harman package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)
```

### 14.11 METHODS Registry — Append 10 entries

```python
# ── BEFORE ──────────────────────────────────────────────────────────────────
    "26_xpn":               (normalize_xpn,                "high"),
    "27_dwd":               (normalize_dwd,                "medium"),
    "28_npn":               (normalize_npn,                "high"),
}

# ── AFTER ───────────────────────────────────────────────────────────────────
    "26_xpn":               (normalize_xpn,                "high"),
    "27_dwd":               (normalize_dwd,                "medium"),
    "28_npn":               (normalize_npn,                "high"),
    "29_combat_ref":        (normalize_combat_ref,         "medium"),
    "30_recombat":          (normalize_recombat,           "medium"),
    "31_ruv3prps":          (normalize_ruv3prps,           "medium"),
    "32_deepmnn":           (normalize_deepmnn,            "medium"),
    "33_amdbnorm":          (normalize_amdbnorm,           "high"),
    "34_arsyn":             (normalize_arsyn,              "medium"),
    "35_dasc":              (normalize_dasc,               "medium"),
    "36_explobatch":        (normalize_explobatch,         "medium"),
    "37_fabatch":           (normalize_fabatch,            "medium"),
    "38_harman":            (normalize_harman,             "medium"),
}
```

---

## 15. Change 2 — `run_norm_parallel.py` and `run_cross_product_parallel.py`: Extend ALL_METHODS

Apply identical change to both files:

```python
# ── AFTER ───────────────────────────────────────────────────────────────────
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
    "25_angel", "26_xpn", "27_dwd", "28_npn",
    "29_combat_ref", "30_recombat", "31_ruv3prps", "32_deepmnn",
    "33_amdbnorm", "34_arsyn", "35_dasc", "36_explobatch",
    "37_fabatch", "38_harman",
]
```

`32_deepmnn` raises `NotImplementedError` immediately (placeholder); the dispatcher records it as `SKIP` — same handling as `22_tmm` on mixed data.

---

## 16. Change 3 — `install_r_packages.R`

```r
# ── INSERT after the existing remotes::install_github lines ─────────────────

# GitHub packages (Batch 2)
remotes::install_github("bioFAM/reComBat",       upgrade = "never")
remotes::install_github("JoevVan/AMDBNorm",      upgrade = "never")
remotes::install_github("zhanglabNKU/DASC",      upgrade = "never")
remotes::install_github("syspremed/exploBATCH",  upgrade = "never")

# Bioconductor packages (Batch 2)
BiocManager::install("ruv",     update = FALSE, ask = FALSE)
BiocManager::install("NOISeq",  update = FALSE, ask = FALSE)
BiocManager::install("FAbatch", update = FALSE, ask = FALSE)
BiocManager::install("Harman",  update = FALSE, ask = FALSE)

# ── UPDATE the verification vector ──────────────────────────────────────────
pkgs <- c(
    "missForest", "softImpute", "FSQN",
    "limma", "sva", "RUVSeq", "batchelor",
    "qsmooth", "edgeR", "DESeq2",
    "TDM", "HarmonizR", "DWDLargeR", "huge",
    # Batch 2:
    "reComBat", "AMDBNorm", "DASC", "exploBATCH",
    "ruv", "NOISeq", "FAbatch", "Harman"
)
```

> **Note on ARSyN:** `ARSyNseq()` is part of `NOISeq`. If a standalone Bioconductor package `ARSyN` exists separately, use `BiocManager::install("ARSyN")` instead and verify with `BiocManager::available("ARSyN")` on the pod.

> **Note on ruv vs RUVSeq:** `ruv` (base R package) is distinct from `RUVSeq` (Bioconductor package used by `09_ruv`). Both may need to be installed; they do not conflict.

---

## 17. Change 4 — `k8s/pod-ssh.yaml`

Add 8 `Rscript` lines after the existing `DWDLargeR` / `huge` lines:

```bash
Rscript --no-save --no-restore -e "remotes::install_github('bioFAM/reComBat', upgrade='never')"   && echo "[startup] reComBat OK"
Rscript --no-save --no-restore -e "remotes::install_github('JoevVan/AMDBNorm', upgrade='never')"  && echo "[startup] AMDBNorm OK"
Rscript --no-save --no-restore -e "remotes::install_github('zhanglabNKU/DASC', upgrade='never')"  && echo "[startup] DASC OK"
Rscript --no-save --no-restore -e "remotes::install_github('syspremed/exploBATCH', upgrade='never')" && echo "[startup] exploBATCH OK"
Rscript --no-save --no-restore -e "BiocManager::install('ruv',     update=FALSE, ask=FALSE)"      && echo "[startup] ruv OK"
Rscript --no-save --no-restore -e "BiocManager::install('NOISeq',  update=FALSE, ask=FALSE)"      && echo "[startup] NOISeq OK"
Rscript --no-save --no-restore -e "BiocManager::install('FAbatch', update=FALSE, ask=FALSE)"      && echo "[startup] FAbatch OK"
Rscript --no-save --no-restore -e "BiocManager::install('Harman',  update=FALSE, ask=FALSE)"      && echo "[startup] Harman OK"
```

---

## 18. Change 5 — `test_mock.py`: Extend `_CRITICAL_PKGS`

```python
# ── BEFORE ──────────────────────────────────────────────────────────────────
_CRITICAL_PKGS = [
    "FSQN", "qsmooth", "missForest", "softImpute",
    "limma", "sva", "RUVSeq", "batchelor", "edgeR", "DESeq2",
    "HarmonizR", "TDM", "DWDLargeR", "huge",
]

# ── AFTER ───────────────────────────────────────────────────────────────────
_CRITICAL_PKGS = [
    "FSQN", "qsmooth", "missForest", "softImpute",
    "limma", "sva", "RUVSeq", "batchelor", "edgeR", "DESeq2",
    "HarmonizR", "TDM", "DWDLargeR", "huge",
    # Batch 2:
    "reComBat", "AMDBNorm", "DASC", "exploBATCH",
    "ruv", "NOISeq", "FAbatch", "Harman",
]
```

`normalize_deepmnn` raises `NotImplementedError` at the Python level before any R call — no R package to verify.

---

## 19. `requirements.txt` — No Changes

deepMNN is NOT APPLICABLE (scRNA-seq domain, no PyPI package). No new Python packages are needed for any of the 13 new methods. XPN is pure NumPy; all other methods are R-based (§16). `requirements.txt` remains unchanged.

---

## 20. Expected Results (Batch 2)

| Method | Expected R² range | Rationale |
|---|---|---|
| `29_combat_ref` | 0.25–0.40 | Same EB mechanism as `05_combat` anchored to reference rather than global mean; better than combat, weaker than FSQN (batch-level not feature-level) |
| `30_recombat` | 0.30–0.45 | Ridge regularization marginal benefit over `05_combat` for moderate confounding; unlikely to beat FSQN |
| `31_ruv3prps` | 0.20–0.40 | Depends on pseudo-replicate density; sparse group × batch cells in strategies G/C may degrade estimation; could match `09_ruv` if cells are well-populated |
| `32_deepmnn` | SKIP (permanent) | NOT APPLICABLE — scRNA-seq domain; AnnData/HVG/PCA API incompatible with bulk matrices |
| `33_amdbnorm` | 0.15–0.22 | Feature-specific mean + distribution alignment; may approach `16_fsqn_r` for strategies with well-populated reference batch |
| `34_arsyn` | 0.25–0.45 | PCA batch subtraction via ANOVA decomposition; comparable to limma/ComBat tier; ANOVA balance assumption violated in our sparse 88-cohort design |
| `35_dasc` | 0.30–0.50 | Unsupervised NMF with known batches; no advantage over supervised ComBat/SVA; non-convex may give variable R² across runs |
| `36_explobatch` | 0.25–0.45 | PPCCA-based correction; scope similar to PCA subtraction; may timeout on strategy S0 |
| `37_fabatch` | 0.25–0.40 | ComBat + SVA unified; no clear advantage over running them separately; `21_harmonizr` is the closest existing comparison |
| `38_harman` | 0.20–0.35 | PCA correction with overcorrection constraint; expected higher batch R² than FSQN but lower biology R² (more biology preserved) — the trade-off this method is designed for |

---

## 21. Known Gotchas (Batch 2)

| Issue | Cause | Resolution |
|---|---|---|
| `29_combat_ref`: `ref_arg` empty in strategies C/F/G | `RNASeq_FF_PolyA` absent from RNA-seq-only or microarray-only strategies | Correctly falls back to standard ComBat (global mean) — acceptable and logged by `ref_present` check |
| `30_recombat`: slow CV for λ | Cross-validation runs per gene in R | Use `--timeout-s 7200` for `30_recombat` jobs |
| `31_ruv3prps`: `fit$newY` field name | Some `ruv` versions use `fit$corrY` | R code guards: `newY <- if (!is.null(fit$newY)) fit$newY else fit$corrY` |
| `31_ruv3prps`: k > n_groups − 1 | Cannot extract more factors than pseudo-replicate groups minus 1 | Clamped: `k <- min(k_factors, n_groups - 1L)` |
| `31_ruv3prps`: all cells sparse | Very rare (bio × batch) combinations in strategies C, G | Fallback to uncorrected with `message()` |
| `33_amdbnorm`: API unverified | GitHub package; exact function name unknown | `TODO` comment in R block; check README at `JoevVan/AMDBNorm` before running |
| `34_arsyn`: `assayData()` vs `exprs()` | NOISeq output is an S4 object; extraction method depends on Biobase availability | `assayData(myresult)$exprs` works without loading Biobase explicitly; alternative: `Biobase::exprs(myresult)` |
| `34_arsyn`: `norm="n"` | ARSyNseq `norm` argument — `"n"` means no additional normalization applied (data already log2) | Keep `norm="n"` and `logtransf=FALSE` |
| `35_dasc`: API unverified | GitHub package; exact function name may differ from `DASC(data, batch)` | `TODO` comment in R block; check README at `zhanglabNKU/DASC` |
| `35_dasc`: non-convex NMF | Results vary by random seed | `set.seed(42)` in R call ensures reproducibility |
| `36_explobatch`: API unverified | GitHub package; exact function name unknown | `TODO` comment in R block; check README at `syspremed/exploBATCH` |
| `36_explobatch`: timeout on large matrix | PPCCA is O(n²) in samples; may hang on strategy S0 (5,444 samples) | Start with strategy A only; use `--timeout-s 7200` |
| `37_fabatch`: output field name | `batchadjust()` returns list; corrected data may be in `$adj.data` or just the matrix | Guard: `if (!is.null(res$adj.data)) res$adj.data else res` |
| `38_harman`: `limit` sensitivity | Very low `limit` → very little correction (batch R² stays high); too high → overcorrects biology | Default set to 0.1 (slightly relaxed from paper's 0.05 — allows more correction while still guarding against overcorrection) |
| All GitHub packages: R 4.5 compat | Packages may not have been tested against R 4.5 / Bioconductor 3.22 | Run `test_mock.py` immediately after pod startup; failing installs appear as SKIP |

---

## 22. Updated Summary of All File Changes (Batches 1 + 2 Combined)

| File | Batch 1 (26–28) | Batch 2 (29–38) |
|---|---|---|
| `bench_shared.py` | Add `normalize_xpn/dwd/npn`; METHODS 26–28 | Add 10 functions (§14.1–14.10); METHODS 29–38 |
| `run_norm_parallel.py` | Append `"26_xpn"`, `"27_dwd"`, `"28_npn"` | Append `"29_combat_ref"` … `"38_harman"` |
| `run_cross_product_parallel.py` | Same as above | Same as above |
| `install_r_packages.R` | Add `DWDLargeR`, `huge` | Add 4 GitHub + 4 Bioconductor packages; update verification vector |
| `k8s/pod-ssh.yaml` | Add 2 `Rscript` lines | Add 8 `Rscript` lines |
| `test_mock.py` | Add `"DWDLargeR"`, `"huge"` | Add 8 new package names to `_CRITICAL_PKGS` |
| `requirements.txt` | No change | No change (deepMNN NOT APPLICABLE; see §26 for Procrustes addition) |
| `Dockerfile` | No change | No change |

---

# Part 3: Method 39 — Procrustes (2026-05-07)

**New scope:** Add 1 RNA-seq-only normalization method (method 39). Procrustes is SKIP on all non-RNA-seq strategies; only runs on `C_rnaseq_only`.

**Source:** Kotlov N et al. "Procrustes is a machine-learning approach that removes cross-platform batch effects from clinical RNA sequencing data." *Communications Biology* 2024. PMID 38555407. GitHub: https://github.com/BostonGene/Procrustes

---

## Status Summary (Part 3)

| Component | Status | Notes |
|---|---|---|
| `bench_shared.py` — `normalize_procrustes` (39) | TODO | Python; BostonGene Procrustes; `_assert_rnaseq_only` guard |
| `bench_shared.py` — METHODS entry `"39_procrustes"` | TODO | Harshness tier: `"high"` |
| `run_norm_parallel.py` — ALL_METHODS | TODO | Append `"39_procrustes"` |
| `run_cross_product_parallel.py` — ALL_METHODS | TODO | Same |
| `install_r_packages.R` | No change | Procrustes is a Python package; no R dependency |
| `k8s/pod-ssh.yaml` | TODO | Add `pip install git+https://github.com/BostonGene/Procrustes` |
| `test_mock.py` | No change | `NotImplementedError` on non-C strategies → SKIP; no new R packages |
| `requirements.txt` | TODO | Add `procrustes-bg @ git+https://github.com/BostonGene/Procrustes` |
| `Dockerfile` | TODO | Add `RUN pip install git+https://github.com/BostonGene/Procrustes` |

---

## 23. Algorithm Overview — Procrustes (`39_procrustes`)

**Source:** Kotlov et al. 2024, *Communications Biology* (PMID 38555407). BostonGene internal tool; validated on DLBCL and lymphoma cohorts including FFPE exome-capture and fresh-frozen polyA RNA-seq.

**What it does:**
Procrustes applies pre-fitted **per-gene linear coefficients** (slope + intercept, stored as kit-specific JSON files) to transform exome-capture (EC) RNA-seq expression into polyA-equivalent expression:

```
corrected_gene = slope × ec_gene + intercept
```

output is clipped to `[0, 18.5]` (the observed range of log2 polyA expression). Coefficients are trained on paired samples measured on both platforms; at inference time, no reference batch is needed — the reference is baked into the JSON.

**Kit-specific coefficient files (shipped with the package):**
| File | Target kit |
|---|---|
| `V4_coefficients.json` | Agilent SureSelect V4 |
| `V7_coefficients.json` | Agilent SureSelect V7 |
| `V7_UTR_coefficients.json` | Agilent SureSelect V7 UTR (most recent; default) |

**Benchmark applicability:**
- **RNA-seq only.** Raises `NotImplementedError` (→ SKIP) if any GPL* batch is present. Valid strategy: `C_rnaseq_only`.
- **EC batches corrected.** Identifies batches with `"Exome_capture"` in `RNA_BATCH`. Our dataset has `RNASeq_FFPE_Exome_capture` (n=939).
- **Non-EC RNA-seq batches unchanged.** `RNASeq_FF_PolyA` (reference) and other RNA-seq batches are returned as-is.
- **Gene space.** Procrustes expects Gencode v23 (~20,062 genes); benchmark uses ~3,520 genes. The function applies coefficients to available genes only; genes absent from the coefficient file are left at their original values.

**Distinction from other methods:**
- Unlike FSQN, ComBat, Harmony — which learn correction parameters at runtime from the data — Procrustes uses fixed pre-fitted coefficients. It is deterministic and parameter-free at call time.
- Unlike TDM (which rescales to match a reference distribution), Procrustes applies gene-specific linear transformations learned from paired EC/polyA samples.
- Limitation: only corrects EC → polyA. Other cross-platform and cross-batch effects within RNA-seq (FF vs FFPE, different labs, different polyA protocols) are not addressed.

**Installation:** `pip install git+https://github.com/BostonGene/Procrustes`

**API:**
```python
from procrustes_bg.transform import Procrustes_predict
corrected_df = Procrustes_predict(ec_expression_df, path_to_coeffs='V7_UTR_coefficients.json')
```

---

## 24. Change 1 — `bench_shared.py`: Add `normalize_procrustes`

### 24.1 `normalize_procrustes` — Insert after `normalize_harman`

```python
def normalize_procrustes(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL,
    ec_batch_substr: str = "Exome_capture",
    coeffs_kit: str = "V7_UTR",
    **kw: object,
) -> pd.DataFrame:
    """
    Procrustes: per-gene linear EC→polyA RNA-seq correction
    (Kotlov et al. 2024, Commun Biol; GitHub: BostonGene/Procrustes).

    Applies pre-fitted per-gene linear coefficients (slope + intercept,
    kit-specific JSON: V4 / V7 / V7_UTR) to exome-capture RNA-seq batches
    to convert them to polyA-equivalent expression. Non-EC RNA-seq batches
    are left unchanged.

    RNA-seq only: raises NotImplementedError on any GPL* (microarray) batch.
    Designed for strategy C (C_rnaseq_only); SKIP on all other strategies.
    Gene-space mismatch is handled by applying coefficients only to genes
    present in the JSON; remaining genes keep their original values.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes), log2(TPM+1).
    ann_df
        Annotation with batch_col.
    batch_col
        Batch column (RNA_BATCH).
    ec_batch_substr
        Substring identifying exome-capture batches in RNA_BATCH values.
        Default: "Exome_capture" (matches RNASeq_FFPE_Exome_capture).
    coeffs_kit
        Kit identifier for Procrustes coefficient file.
        One of "V4", "V7", "V7_UTR". Default: "V7_UTR".

    Returns
    -------
    Procrustes-corrected expression matrix (same shape as input).
    """
    import os
    import importlib

    _assert_rnaseq_only(ann_df.loc[exp_df.index], batch_col)

    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    ec_mask = groups.str.contains(ec_batch_substr, case=False)

    if not ec_mask.any():
        return exp_df.copy()

    try:
        procrustes_bg = importlib.import_module("procrustes_bg")
        from procrustes_bg.transform import Procrustes_predict
        pkg_dir = os.path.dirname(procrustes_bg.__file__)
        coeffs_path = os.path.join(pkg_dir, f"{coeffs_kit}_coefficients.json")
    except ModuleNotFoundError:
        raise NotImplementedError(
            "procrustes_bg not installed. "
            "Install: pip install git+https://github.com/BostonGene/Procrustes"
        )

    out = exp_df.copy().astype(float)
    ec_exp = exp_df.loc[ec_mask]

    corrected = Procrustes_predict(ec_exp, path_to_coeffs=coeffs_path)
    # Reindex to original gene space; genes absent from coefficients
    # retain their original values.
    corrected_aligned = corrected.reindex(columns=exp_df.columns)
    no_coeff_genes = corrected_aligned.columns[corrected_aligned.isna().all()]
    if len(no_coeff_genes):
        corrected_aligned[no_coeff_genes] = ec_exp[no_coeff_genes].values

    out.loc[ec_mask] = corrected_aligned.values
    return out
```

### 24.2 METHODS Registry — Append entry 39

```python
# ── BEFORE ──────────────────────────────────────────────────────────────────
    "38_harman":            (normalize_harman,             "medium"),
}

# ── AFTER ───────────────────────────────────────────────────────────────────
    "38_harman":            (normalize_harman,             "medium"),
    "39_procrustes":        (normalize_procrustes,         "high"),
}
```

---

## 25. Change 2 — `run_norm_parallel.py` and `run_cross_product_parallel.py`: Extend ALL_METHODS

Apply identical change to both files:

```python
# ── AFTER ───────────────────────────────────────────────────────────────────
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
    "25_angel", "26_xpn", "27_dwd", "28_npn",
    "29_combat_ref", "30_recombat", "31_ruv3prps", "32_deepmnn",
    "33_amdbnorm", "34_arsyn", "35_dasc", "36_explobatch",
    "37_fabatch", "38_harman", "39_procrustes",
]
```

`39_procrustes` raises `NotImplementedError` via `_assert_rnaseq_only` on all strategies except `C_rnaseq_only` → recorded as SKIP by the dispatcher.

---

## 26. Change 3 — `requirements.txt`: Add procrustes-bg

> **Note:** This supersedes §19, which stated `requirements.txt` has no changes.

```
# ── ADD at the end of requirements.txt ───────────────────────────────────────
procrustes-bg @ git+https://github.com/BostonGene/Procrustes
```

If the package is not pip-installable directly via the above URL (e.g., no `pyproject.toml` / `setup.py` in root), fall back to cloning and installing in the Dockerfile:

```dockerfile
RUN git clone https://github.com/BostonGene/Procrustes /opt/procrustes \
 && pip install -e /opt/procrustes
```

---

## 27. Change 4 — `k8s/pod-ssh.yaml` and `Dockerfile`: Install procrustes-bg

### 27.1 `k8s/pod-ssh.yaml` (startup script)

Add after the existing `pip install` lines (or after the R package installs):

```bash
pip install git+https://github.com/BostonGene/Procrustes && echo "[startup] procrustes-bg OK"
```

### 27.2 `Dockerfile`

Add after the `RUN pip install -r requirements.txt` line:

```dockerfile
RUN pip install git+https://github.com/BostonGene/Procrustes
```

If the direct git URL fails, use:

```dockerfile
RUN git clone https://github.com/BostonGene/Procrustes /opt/procrustes \
 && pip install -e /opt/procrustes
```

---

## Expected Results — Procrustes

| Method | Expected R² range | Rationale |
|---|---|---|
| `39_procrustes` (strategy C only) | 0.15–0.25 | Corrects EC→polyA for `RNASeq_FFPE_Exome_capture` (n=939) only; other RNA-seq batches unchanged; batch R² reduction depends on how much EC deviation drives the variance in strategy C |

Procrustes is the only method in the benchmark that uses externally pre-fitted coefficients (no runtime reference batch estimation). It provides a BostonGene-internal baseline for EC correction quality; direct comparison with `16_fsqn_r` on strategy C reveals whether the gene-specific linear model outperforms quantile-matching for the EC batch.

---

## Known Gotchas — Procrustes

| Issue | Cause | Resolution |
|---|---|---|
| SKIP on all non-C strategies | `_assert_rnaseq_only` raises `NotImplementedError` on GPL* batches | Expected; dispatcher records as SKIP |
| Kit mismatch | FFPE EC batches may have been captured with V4 or V7; V7_UTR assumed by default | Check COHORT metadata; pass `coeffs_kit="V7"` if known |
| Gene space mismatch | Procrustes coefficients cover Gencode v23 ~20,062 genes; benchmark uses ~3,520 | Missing-coefficient genes keep original values via `reindex` fallback |
| No EC batch in C | `C_rnaseq_only` after certain imputation filters may drop the EC batch entirely | Function returns unchanged `exp_df.copy()` silently |
| coeffs_path not found | Package installed but JSON not at expected path | Inspect `os.listdir(pkg_dir)` for correct filename prefix |
| pip install fails (no setup.py) | GitHub repo may lack pyproject.toml; `pip install git+...` fails | Use clone + `pip install -e` fallback in Dockerfile (see §27.2) |

---

# Part 4: Strategy H — `H_affymetrix_extended` (2026-05-07)

**Background:** The current `G_affymetrix_only` strategy keeps only batches whose `RNA_BATCH` starts with `"GPL570"` (see `bench_shared.py` line 463):

```python
affymetrix_batches = [b for b in ann_base[BATCH_COL].unique() if b.startswith("GPL570")]
```

This covers ~2,824 samples across three GPL570 sub-batches. The dataset contains additional Affymetrix microarray batches (GPL96, GPL6244, GPL13158, GPL16686, GPL17047, GPL17586, GPL10739) that are excluded from G.

**Rationale for `H_affymetrix_extended`:** Captures all Affymetrix microarray batches — ~3,821 samples total — enabling harmonisation methods to be evaluated on the full Affymetrix sub-cohort. Affymetrix arrays share a common probe chemistry (oligo-based hybridisation with Affymetrix-specific background correction / RMA normalisation); a strategy covering all Affymetrix sub-platforms tests whether cross-Affymetrix batch effects are correctable independently of RNA-seq.

> **Note on `G_affymetrix_only` name:** The strategy name is misleading — it currently captures only GPL570 batches, not all Affymetrix platforms. `H_affymetrix_extended` rectifies this. The `G` strategy is left unchanged to preserve existing S3 keys; its `CLAUDE.md` description is corrected in §30 below.

---

## Platform Verification

All GPL IDs in the user-specified batch names were verified against NCBI GEO:

| GPL ID | Platform Name | Manufacturer | Confirmed |
|---|---|---|---|
| GPL570 | HG-U133_Plus_2 (Human Genome U133 Plus 2.0 Array) | Affymetrix | ✓ |
| GPL96 | HG-U133A (Human Genome U133A Array) | Affymetrix | ✓ |
| GPL97 | HG-U133B (Human Genome U133B Array) | Affymetrix | ✓ |
| GPL6244 | HuGene-1_0-st (Human Gene 1.0 ST Array, transcript version) | Affymetrix | ✓ |
| GPL16686 | HuGene-2_0-st (Human Gene 2.0 ST Array, transcript version) | Affymetrix | ✓ |
| GPL13158 | HT_HG-U133_Plus_PM (HT HG-U133+ PM Array Plate) | Affymetrix | ✓ |
| GPL17586 | HTA-2_0 (Human Transcriptome Array 2.0, transcript version) | Affymetrix | ✓ |
| GPL17047 | HuGene-1_0-st with BrainArray CDF (Human Gene 1.0 ST, BrainArray annotation) | Affymetrix | ✓ |
| GPL10739 | HuGene-1_0-st exon version (Human Gene 1.0 ST Array, probe set / exon version) | Affymetrix | ✓ |

**All platforms confirmed Affymetrix.** GPL14951 (Illumina HumanHT-12 V3.0 beadarray, 810 samples) is explicitly excluded.

---

## Composition of `H_affymetrix_extended`

| RNA_BATCH | GPL Platform | FF/FFPE |
|---|---|---|
| `GPL570_Unknown_Unknown` | GPL570 (U133 Plus 2.0) | Unknown |
| `GPL570_FF_Unknown` | GPL570 (U133 Plus 2.0) | FF |
| `GPL570_FFPE_Unknown` | GPL570 (U133 Plus 2.0) | FFPE |
| `GPL96+97_FF_Unknown` | GPL96/97 (U133A + U133B pair) | FF |
| `GPL96_FF_Unknown` | GPL96 (U133A) | FF |
| `GPL96_FFPE_Unknown` | GPL96 (U133A) | FFPE |
| `GPL6244_FF_Unknown` | GPL6244 (HuGene 1.0 ST) | FF |
| `GPL6244_FFPE_Unknown` | GPL6244 (HuGene 1.0 ST) | FFPE |
| `GPL16686_FF_Unknown` | GPL16686 (HuGene 2.0 ST) | FF |
| `GPL13158_FF_Unknown` | GPL13158 (HT U133+ PM) | FF |
| `GPL17586_FF_Unknown` | GPL17586 (HTA 2.0) | FF |
| `GPL17047_FF_Unknown` | GPL17047 (HuGene 1.0 ST BrainArray) | FF |
| `GPL10739_FF_Unknown` | GPL10739 (HuGene 1.0 ST, exon version) | FF |
| **Total** | | **~3,821 (all Affymetrix microarray)** |

GPL570 sub-batches contribute ~2,824 samples; the remaining ~997 come from the non-GPL570 Affymetrix batches.

---

## Status Summary (Part 4)

| Component | Status | Notes |
|---|---|---|
| `bench_shared.py` — module-level constant | TODO | Add `_AFFY_EXT_BATCHES: frozenset[str]` |
| `bench_shared.py` — `build_filter_strategies` | TODO | Add `"H_affymetrix_extended"` entry using `isin(_AFFY_EXT_BATCHES)` |
| `run_norm_parallel.py` — ALL_STRATEGIES | TODO | Append `"H_affymetrix_extended"` |
| `run_cross_product_parallel.py` — ALL_STRATEGIES | TODO | Same |
| `run_prep_parallel.py` — ALL_STRATEGIES | TODO | Same (Stage 1: H × 4 = 4 new jobs, total 44) |
| `Dockerfile` / `k8s/pod-ssh.yaml` | No change | No new dependencies |
| `test_mock.py` | No change | Strategy filtering uses `build_filter_strategies` |
| `harmonization-scripts/CLAUDE.md` | TODO | Correct G description; rename H row to `H_affymetrix_extended` |

---

## 28. Change 5 — `bench_shared.py`: Add `H_affymetrix_extended` to `build_filter_strategies`

Add the constant near the top of `bench_shared.py`, after the `BAD_COHORTS_A/B` constants:

```python
# Explicit set of all Affymetrix microarray RNA_BATCH labels present in the dataset.
# Used by build_filter_strategies for H_affymetrix_extended.
# Excludes GPL14951_FFPE_Unknown (Illumina HumanHT-12 V3.0, not Affymetrix).
_AFFY_EXT_BATCHES: frozenset[str] = frozenset({
    "GPL570_Unknown_Unknown", "GPL570_FF_Unknown", "GPL570_FFPE_Unknown",
    "GPL96+97_FF_Unknown",    "GPL96_FF_Unknown",  "GPL96_FFPE_Unknown",
    "GPL6244_FF_Unknown",     "GPL6244_FFPE_Unknown",
    "GPL16686_FF_Unknown",    "GPL13158_FF_Unknown",
    "GPL17586_FF_Unknown",    "GPL17047_FF_Unknown", "GPL10739_FF_Unknown",
})
```

In `build_filter_strategies()`, append after the `G_affymetrix_only` entry:

```python
# ── BEFORE (end of strategies dict) ──────────────────────────────────────────
    "G_affymetrix_only":    ann_filt[gpl_mask].copy(),
}

# ── AFTER ─────────────────────────────────────────────────────────────────────
    "G_affymetrix_only":    ann_filt[gpl_mask].copy(),
    "H_affymetrix_extended": ann_filt[
        ann_filt[BATCH_COL].isin(_AFFY_EXT_BATCHES)
    ].copy(),
}
```

> **Note on `gpl_mask` vs `_AFFY_EXT_BATCHES`:** `G_affymetrix_only` uses `str.startswith("GPL570")` (only 3 sub-batches). `H_affymetrix_extended` uses the explicit frozenset covering all 13 Affymetrix batches — a strict superset of G. An explicit frozenset is preferred over a dynamic prefix list to prevent accidentally including future GPL-prefixed non-Affymetrix platforms.

---

## 29. Change 6 — Dispatcher Scripts: Extend ALL_STRATEGIES

Apply identical change to **`run_norm_parallel.py`**, **`run_cross_product_parallel.py`**, and **`run_prep_parallel.py`**:

```python
# ── BEFORE ───────────────────────────────────────────────────────────────────
ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad", "C_rnaseq_only",
    "D_malignant_only", "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only",
]

# ── AFTER ────────────────────────────────────────────────────────────────────
ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad", "C_rnaseq_only",
    "D_malignant_only", "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
]
```

**Impact on Stage 1 (prep):** `run_prep_parallel.py` now dispatches 11 × 4 = 44 prep jobs (was 40). The 4 new jobs are `H_affymetrix_extended × {strict, knn, missforest, softimpute}`.

**Impact on Stage 2 (norm):** `run_norm_parallel.py` dispatches up to 39 × 11 × 4 = 1,716 norm jobs (was 38 × 10 × 4 = 1,520). In practice:
- 38 methods × 11 strategies × 4 = 1,672 (all run)
- `39_procrustes` × 1 strategy (C only) × 4 = 4 effective (SKIP on 10 other strategies = 40 SKIP records)

---

## 30. Change 7 — `harmonization-scripts/CLAUDE.md`: Update Filter Strategies Table

Two corrections plus the renamed H row:

```markdown
<!-- BEFORE -->
| `G_affymetrix_only` | All Affymetrix batches (GPL* prefix, including GPL570 and GPL14951) |
| `H_gpl570_only` | GPL570 batches only (`RNA_BATCH.startswith("GPL570")`); ... |

<!-- AFTER -->
| `G_affymetrix_only` | GPL570 batches only (`RNA_BATCH.startswith("GPL570")`); ~2,824 samples — name is a misnomer vs. actual code; left unchanged to preserve existing S3 keys |
| `H_affymetrix_extended` | All 13 Affymetrix microarray batches (GPL570, GPL96/97, GPL6244, GPL13158, GPL16686, GPL17047, GPL17586, GPL10739 sub-batches); ~3,821 samples; excludes GPL14951 (Illumina HumanHT-12 V3.0, not Affymetrix) |
```

---

## 31. Complete Summary of All File Changes (Parts 1–4)

**Final grid:** 39 methods × 11 strategies × 4 imputation = 1,716 normalization jobs → **3,432 S3 outputs** (before SKIPs).

| File | Part 1 (26–28) | Part 2 (29–38) | Part 3 (39) | Part 4 (H strat) |
|---|---|---|---|---|
| `bench_shared.py` | Add `normalize_xpn/dwd/npn`; METHODS 26–28 | Add 10 functions; METHODS 29–38 | Add `normalize_procrustes`; METHODS 39 | Add `_AFFY_EXT_BATCHES` constant; add `H_affymetrix_extended` to `build_filter_strategies` |
| `run_norm_parallel.py` | Append 26–28 to ALL_METHODS | Append 29–38 | Append `"39_procrustes"` | Append `"H_affymetrix_extended"` to ALL_STRATEGIES |
| `run_cross_product_parallel.py` | Same as above | Same | Same | Same |
| `run_prep_parallel.py` | No change | No change | No change | Append `"H_affymetrix_extended"` to ALL_STRATEGIES |
| `install_r_packages.R` | Add `DWDLargeR`, `huge` | Add 4 GitHub + 4 Bioconductor | No change | No change |
| `k8s/pod-ssh.yaml` | Add 2 `Rscript` lines | Add 8 `Rscript` lines | Add 1 `pip install` line | No change |
| `requirements.txt` | No change | No change | Add `procrustes-bg` | No change |
| `Dockerfile` | No change | No change | Add `RUN pip install` | No change |
| `harmonization-scripts/CLAUDE.md` | No change | No change | No change | Correct G description; add `H_affymetrix_extended` row |
| `test_mock.py` | Add `"DWDLargeR"`, `"huge"` | Add 8 R pkg names | No change | No change |

---

# TODO Checklist (2026-05-07)

All tasks required to execute the plan from scratch. Complete **Phase 0 first** — its outputs gate several later implementation tasks. Within each phase, tasks follow the order of the plan sections referenced.

---

## Phase 0 — Pre-implementation Verification (gates Phases 1–3) ✅

- [x] **Verify AMDBNorm R function name** — confirmed 3-step workflow: `DBNorm::genDistData` → `polyFit` → per-batch `AMDBNorm()` → cbind; requires `mengqinxue/DBNorm` GitHub dep
- [x] **Verify DASC R function name** — confirmed NOT APPLICABLE: DASC returns cluster assignments, not corrected expression → implemented as permanent `NotImplementedError`
- [x] **Verify exploBATCH R function name** — confirmed: function is `expBATCH()` (not `exploBATCH()`); takes samples×genes; writes corrected file to disk; read back via glob
- [x] **Verify Procrustes pip install** — package installs via `git+https://github.com/BostonGene/Procrustes`; added to requirements.txt
- [x] **Verify Procrustes coefficient JSON paths** — implemented with glob-based path resolution and reindex fallback for missing-coefficient genes
- [x] **Confirm `G_affymetrix_only` is intentionally kept as-is** — confirmed; `G` covers only GPL570 batches; `H_affymetrix_extended` added as the correct 13-batch Affymetrix strategy

---

## Phase 1 — `bench_shared.py`: Functions 26–28 (Part 1) ✅

Reference: §2 (`normalize_xpn`), §3 (`normalize_dwd`), §4 (`normalize_npn`), §4 METHODS block

- [x] Implement `normalize_xpn(exp_df, ann_df, **kw)` — pure Python, numpy percentile + interp
- [x] Implement `normalize_dwd(exp_df, ann_df, **kw)` — file-based R via `DWDLargeR::genDWD`
- [x] Implement `normalize_npn(exp_df, ann_df, **kw)` — file-based R via `huge::npn(func="truncation")`
- [x] Add `METHODS` entries `"26_xpn"`, `"27_dwd"`, `"28_npn"`

---

## Phase 2 — `bench_shared.py`: Functions 29–38 (Part 2) ✅

Reference: §14 subsections; all R-based methods use the `tempfile.TemporaryDirectory` file-based pattern

- [x] Implement `normalize_combat_ref` — `sva::ComBat` with `ref.batch="RNASeq_FF_PolyA"`
- [x] Implement `normalize_recombat` — file-based R, `reComBat::reComBat(dat, batch, mod)`
- [x] Implement `normalize_ruv3prps` — file-based R, `ruv::RUVIII()`, pseudo-sample construction, k_factors=5
- [x] Implement `normalize_deepmnn` — permanent `NotImplementedError` (scRNA-seq-only)
- [x] Implement `normalize_amdbnorm` — file-based R, 3-step DBNorm + AMDBNorm workflow
- [x] Implement `normalize_arsyn` — file-based R, `NOISeq::readData()` + `ARSyNseq()`
- [x] Implement `normalize_dasc` — permanent `NotImplementedError` (returns cluster assignments, not corrected expression)
- [x] Implement `normalize_explobatch` — file-based R, `expBATCH()`, glob read-back of disk output
- [x] Implement `normalize_fabatch` — file-based R, `FAbatch::batchadjust()`, extracts `$adj.data`
- [x] Implement `normalize_harman` — file-based R, `harman()` + `reconstructData()`
- [x] Add `METHODS` entries `"29_combat_ref"` through `"38_harman"` (including `"32_deepmnn"`, `"35_dasc"` as skips)

---

## Phase 3 — `bench_shared.py`: Function 39 + Strategy H (Parts 3 & 4) ✅

Reference: §24 (`normalize_procrustes`), §28 (H strategy constant + `build_filter_strategies`)

- [x] Add `_AFFY_EXT_BATCHES: frozenset[str]` module-level constant — 13 explicit Affymetrix batch names
- [x] Implement `normalize_procrustes(exp_df, ann_df, **kw)` — `_assert_rnaseq_only` guard, `Procrustes_predict`, reindex fallback
- [x] Add `METHODS` entry `"39_procrustes": (normalize_procrustes, "high")`
- [x] Add `"H_affymetrix_extended"` to `build_filter_strategies()` using `ann_base[BATCH_COL].isin(_AFFY_EXT_BATCHES)`

---

## Phase 4 — Dispatcher scripts: ALL_METHODS and ALL_STRATEGIES ✅

Reference: §4.1 (26–28), §15 (29–38), §25 (final ALL_METHODS), §29 (ALL_STRATEGIES)

- [x] **`run_norm_parallel.py`** — appended keys `"26_xpn"` through `"39_procrustes"` to `ALL_METHODS`; appended `"H_affymetrix_extended"` to `ALL_STRATEGIES`
- [x] **`run_cross_product_parallel.py`** — identical `ALL_METHODS` and `ALL_STRATEGIES` changes applied
- [x] **`run_prep_parallel.py`** — appended `"H_affymetrix_extended"` to `ALL_STRATEGIES`

---

## Phase 5 — R package configuration ✅

Reference: §5 + §6 (Part 1), §16 + §17 (Part 2), §27.1 (Part 3 pod-ssh.yaml)

### `install_r_packages.R`

- [x] Added `install.packages(c("DWDLargeR", "huge"), dependencies=TRUE)`
- [x] Added `remotes::install_github("bioFAM/reComBat", upgrade="never")`
- [x] Added `remotes::install_github("JoevVan/AMDBNorm", upgrade="never")`
- [x] Added `remotes::install_github("zhanglabNKU/DASC", upgrade="never")`
- [x] Added `remotes::install_github("syspremed/exploBATCH", upgrade="never")`
- [x] Added `BiocManager::install(c("ruv", "NOISeq", "FAbatch", "Harman"), ...)`
- [x] Updated verification `pkgs` vector with all 11 new packages

### `k8s/pod-ssh.yaml`

- [x] Added combined `Rscript` install line for `DWDLargeR` + `huge`
- [x] Added `Rscript` install line for `DBNorm`
- [x] Added `Rscript` install line for `reComBat`
- [x] Added `Rscript` install line for `AMDBNorm`
- [x] Added `Rscript` install line for `DASC`
- [x] Added `Rscript` install line for `exploBATCH`
- [x] Added combined `Rscript` install line for `ruv`, `NOISeq`, `FAbatch`, `Harman`
- [x] Added `pip install git+https://github.com/BostonGene/Procrustes` line

---

## Phase 6 — Python `requirements.txt` and `Dockerfile` ✅

Reference: §8 (Dockerfile Part 1), §19 (requirements.txt Part 2), §26 (requirements.txt Part 3), §27.2 (Dockerfile Part 3)

- [x] **`requirements.txt`** — added `procrustes-bg @ git+https://github.com/BostonGene/Procrustes`
- [x] **`Dockerfile`** — no change needed; Dockerfile installs from `requirements.txt` via `pip install -r`, which now includes `procrustes-bg`

---

## Phase 7 — `test_mock.py` ✅

Reference: §7 (Part 1), §18 (Part 2)

- [x] Added `"DWDLargeR"`, `"huge"` to `_CRITICAL_PKGS`
- [x] Added `"reComBat"`, `"AMDBNorm"`, `"DASC"`, `"exploBATCH"`, `"ruv"`, `"NOISeq"`, `"FAbatch"`, `"Harman"` to `_CRITICAL_PKGS`
- [x] No changes for `normalize_deepmnn` (32) — SKIP recorded automatically
- [x] No changes for `normalize_procrustes` (39) — tested by existing loop; SKIP on non-C strategies

---

## Phase 8 — `harmonization-scripts/CLAUDE.md` ✅

Reference: §30

- [x] Added rows for `"26_xpn"` through `"39_procrustes"` to the normalization methods table (14 new rows)
- [x] Updated grid counts: `25 methods` → `39 methods`, `10 strategies` → `11 strategies`, `1,000 jobs` → `1,716 jobs`, `2,000 S3 outputs` → `3,432 S3 outputs`
- [x] `G_affymetrix_only` description corrected; `H_affymetrix_extended` row added; Purpose section updated

---

## Phase 9 — Smoke testing

Run after Phases 1–8 are complete. All tests run from the project root with the venv active.

- [ ] `python harmonization-scripts/test_mock.py` — expect PASS for all methods except known SKIPs (deepMNN=SKIP, tmm/vst=SKIP on mock mixed data, peer=SKIP, procrustes=SKIP on non-C mock strategy)
- [ ] Single-job test `26_xpn`: `run_one_job.py --strat A_confirmed_bad --imp strict --method 26_xpn --out-json /tmp/xpn_test.json`
- [ ] Single-job test `27_dwd`: same with `--method 27_dwd --memory-limit-gb 4.0 --timeout-s 7200`
- [ ] Single-job test `28_npn`: same with `--method 28_npn`
- [ ] Single-job tests for `29_combat_ref` through `38_harman` — one per method, strategy A, imp strict
- [ ] Single-job test `39_procrustes` on `C_rnaseq_only` (the only strategy where it runs): `--strat C_rnaseq_only --imp strict --method 39_procrustes`
- [ ] Single-job test `H_affymetrix_extended` strategy with `01_raw` to verify filter returns ~3,821 samples: `--strat H_affymetrix_extended --imp strict --method 01_raw`
- [ ] Review all JSON sidecars for `"status": "failed"` entries — diagnose R interface errors against verified function names from Phase 0 before proceeding to Phase 10

---

## Phase 10 — Full benchmark run

Run after Phase 9 is clean.

- [ ] Stage 1 — prep new H strategy: `run_prep_parallel.py --strats H_affymetrix_extended --n-workers 4 --skip-if-exists --timeout-s 7200 --memory-limit-gb 6.0` (4 jobs: H × {strict, knn, missforest, softimpute})
- [ ] Verify 4 new prepared datasets in S3: `aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/prepared/ | grep H_affymetrix`
- [ ] Stage 2 — new methods on all existing strategies: `run_norm_parallel.py --methods 26_xpn,27_dwd,28_npn,29_combat_ref,30_recombat,31_ruv3prps,32_deepmnn,33_amdbnorm,34_arsyn,35_dasc,36_explobatch,37_fabatch,38_harman,39_procrustes --n-workers 6 --skip-if-exists --timeout-s 7200`
- [ ] Stage 2 — all methods on new H strategy: `run_norm_parallel.py --strats H_affymetrix_extended --n-workers 6 --skip-if-exists --timeout-s 7200`
- [ ] Monitor `failed_jobs_norm.txt` — retry after diagnosing root causes
- [ ] Reload `metrics.csv` from S3 in `harmonization_benchmark.ipynb`; extend PCA R² heatmaps to cover all 39 methods and 11 strategies
- [ ] Primary comparison: `33_amdbnorm` and `26_xpn` vs `16_fsqn_r` baseline on strategy A — main scientific question for the new methods
