# Narrow marker panel metrics (Group L, `_narrow_set`) — implementation plan

**Date:** 2026-09-04
**Author:** Claude Code, at Daniil's request
**Status:** awaiting approval — no code changed yet

---

## Overview

Group L currently reports one family of marker-correlation aggregates computed over the
**whole** 633-gene panel. Coverage across that panel is uneven (45 genes resolve in no
`(strat, imp)` pair at all, 325 in only some), and many resolved genes sit in the log2
noise band, so the panel mean mixes reliably measured genes with genes that carry almost
no rank information. This plan adds a **second, integrative-only family of the same
aggregates restricted to a 56-gene QC-filtered subset**, every key suffixed
`_narrow_set`. Nothing in the existing family changes: the two families live side by side
in the same JSON sidecars and the same `metrics_comprehensive.csv`, so any analysis can
read either or both.

**Key design decision — one correlation pass, two aggregations.** Per-gene Spearman ρ is
computed independently per gene and per cohort, so the narrow-set aggregates are exact
re-aggregations of the *same* ρ values the full-panel family already uses. The narrow
family is therefore implemented as a second reduction over the ρ array that
`compute_group_l()` already builds — **no second correlation pass, no second reference
download, no measurable extra runtime**. It also guarantees the two families are
numerically comparable: a difference between `mk_rho_mean_all_genes` and
`mk_rho_mean_all_genes_narrow_set` can only come from the gene set, never from a
different computation.

**Second design decision — the gene list lives in the annotation CSV, not in code.**
`marker_gene_annotation.csv` is the panel source of truth (project convention: gene lists
are edited in `build_marker_gene_annotation.py`, never in `marker_panels.py` and never in
the CSV by hand). The narrow set becomes a new boolean column `in_narrow_set`, exactly
parallel to the existing `is_housekeeping` column.

**Third design decision — two housekeeping controls, not one.** Only one of the 56 narrow
genes (`PGK1`) is a housekeeping control, so the marker-minus-housekeeping margin can be
formed either against the full 15-gene housekeeping panel (stable, but a control set that
is *not* itself coverage-filtered) or against `PGK1` alone (a control drawn from the same
QC-filtered pool as the markers, but n = 1). Both are computed and reported under
distinct names — `mk_rho_marker_minus_hk_narrow_set` and
`mk_rho_marker_minus_PGK1_only_narrow_set` — so the noisier of the two can be identified
empirically rather than argued about. The narrow notebook carries a dedicated
dispersion comparison for exactly this question.

**Fourth design decision — resume without `--force-groups`.** Group L's incremental
sentinel becomes a *tuple* of keys, and a group counts as complete only when every listed
key is populated. Adding `mk_rho_mean_all_genes_narrow_set` as a second sentinel makes
all 2,323 existing sidecars recompute Group L automatically on the next run, and skip on
every run after that. No `--force-groups L`, and no risk of a stale narrow column.

**Analysis notebooks** get separate `_narrow_set` versions, produced by the *same*
generator under a `--narrow-set` flag rather than by a forked copy of a 966-line script.

---

## Background / reference data

### The narrow gene set (56 genes)

Daniil's selection criteria, as stated:

1. present in **all 42** `01_raw__post0` matrices (14 batch-removal strategies × 3
   imputations), and
2. mean **`frac_lt_1` < 0.20** on those raw references — i.e. fewer than 20 % of samples
   sit below 1 on the log2 scale, so the gene is out of the noise band.

Both quantities come from the existing `gene_panel_analysis/` sub-pipeline:
`frac_lt_1` from `gene_panel_structure.py` (per-gene QC), coverage from
`marker_gene_coverage_by_attempt_260828.csv`.

Verified against the committed tables while writing this plan:

| Check | Result |
|---|---|
| All 56 genes present in `marker_gene_annotation.csv` | ✅ yes, 0 missing |
| All 56 flagged `present_in_all_raw_pairs` in `marker_gene_coverage_by_attempt_260828.csv` | ✅ yes |
| Narrow set ⊂ the 193 genes present in all 42 raw pairs | ✅ yes (56 of 193) |
| Housekeeping genes inside the narrow set | **1** — `PGK1` |
| Minimum `frac_attempts_present` across the 56 | 0.980 — so a few *harmonized* attempts still resolve fewer than 56 |

The gene list, verbatim:

```
ZNF277  DDX21   ICAM1   IFNGR1  IMPDH2  LIMD1   CSTB    CNN2
POU2F2  SKI     STMN1   TPD52   VCL     PGK1    PCNA    MCM6
SNX2    IFITM2  FHIT    METAP2  AKT1    FXYD5   ANXA6   CAMK1
CCND2   CHPT1   SLA     PRELP   LMO2    CDK2    ENTPD1  IFIT1
CCNE1   CDK4    CD5     FBLN1   SP140   CD44    CCND1   EGR3
IFI44   BIRC3   PLEK    CD53    JAM3    CD72    VIM     ITPKB
RGS1    BCL2A1  CD22    CCNB1   CD83    FEZ1    EZH2    BCL2
```

### The housekeeping reference for the narrow margin — both variants are computed

Only `PGK1` is a housekeeping gene inside the narrow set, so the marker-minus-housekeeping
margin has two defensible reference sets, with opposite weaknesses:

| Variant | Control set | Weakness | Metric name |
|---|---|---|---|
| **A** — panel-internal | narrow ∩ housekeeping = `PGK1` alone (n = 1) | a single gene: high variance, and one dropped gene makes the margin NaN | `mk_rho_marker_minus_PGK1_only_narrow_set` |
| **B** — full housekeeping panel **(primary)** | the full **15**-gene housekeeping control, resolved against the same matrix and the same cohorts | the control set is *not* itself coverage-filtered, so its composition varies across attempts (see below) | `mk_rho_marker_minus_hk_narrow_set` |

**Both are computed and reported**, under the two distinct names above, so their relative
noise is measured rather than assumed. B is the primary margin (it is what the manuscript
should quote unless the comparison says otherwise); A is the control-matched alternative.
`mk_n_hk_genes_used_narrow_set` records how many of the 15 controls actually resolved in
each attempt, which is what makes B auditable, and
`mk_rho_mean_PGK1_only_narrow_set` is emitted so A's margin can be decomposed into its
marker and control halves.

So, explicitly:

- `mk_rho_marker_minus_hk_narrow_set` = mean ρ over the **55 non-housekeeping narrow
  genes** − mean ρ over the **resolved housekeeping controls (≤ 15)**;
- `mk_rho_marker_minus_PGK1_only_narrow_set` = the same 55-gene mean − ρ of **`PGK1`
  alone**.

**Why the comparison is not merely academic** — checked against
`marker_gene_coverage_by_attempt_260828.csv` while acknowledging this comment:

| Housekeeping gene | Present in all 42 raw pairs | Fraction of attempts resolving it |
|---|---|---|
| `B2M`, `EEF1A1`, `HPRT1`, `PGK1`, `PPIA`, `TBP` | ✅ yes | 0.93 – 0.98 |
| `ACTB`, `GAPDH`, `PSMB4`, `RPL13A`, `RPLP0`, `SDHA`, `TUBB`, `UBC`, `YWHAZ` | ❌ no (26–33 of 42) | 0.60 – 0.72 |

So only **6 of the 15** housekeeping controls clear the same all-42-pairs coverage bar the
narrow markers had to clear. Variant B's control is therefore a *variable-composition*
set — roughly 6 genes on a `strict` attempt, up to 15 on a `knn` / `softimpute` one —
which is the very comparability problem the narrow panel exists to remove. Variant A's
control is coverage-matched but has n = 1. Neither is obviously right, which is exactly
why both ship and the notebook compares their dispersion.

`PGK1` itself resolves in all 42 raw pairs and in 98.0 % of attempts, so variant A's
margin is populated almost everywhere; the ~2 % of attempts where it is NaN are dropped
pairwise in the comparison.

One thing that could **not** be checked locally: why the other five fully-covered
housekeeping genes (`B2M`, `EEF1A1`, `HPRT1`, `PPIA`, `TBP`) fall outside the narrow set —
that requires their `frac_lt_1` values, and `gene_qc_long` lives on S3 / the pod, not in
the repository. `HPRT1` and `TBP` are genuinely low-expressed and would plausibly fail a
`frac_lt_1 < 0.20` gate; `B2M` and `EEF1A1` would not, so it is worth a glance at the QC
table on the pod before the manuscript describes the selection. It changes nothing in this
plan either way — the narrow list is taken as given.

### The 15 new columns

Integrative scalars only — **no dicts, no per-gene or per-cohort detail**, therefore no
new long-format table and no change to `run_metrics_concat.py`.

| # | New key | Definition |
|---|---|---|
| 1 | `mk_rho_mean_all_genes_narrow_set` | mean ρ over resolved narrow genes (housekeeping included, mirroring the full-panel definition) |
| 2 | `mk_rho_median_all_genes_narrow_set` | median of the same |
| 3 | `mk_rho_p10_all_genes_narrow_set` | 10th percentile |
| 4 | `mk_rho_min_all_genes_narrow_set` | minimum |
| 5 | `mk_rho_frac_genes_above_0.9_narrow_set` | fraction of narrow genes with ρ > 0.9 |
| 6 | `mk_rho_mean_markers_narrow_set` | mean ρ over the 55 non-housekeeping narrow genes |
| 7 | `mk_rho_mean_housekeeping_narrow_set` | mean ρ over the resolved housekeeping controls (variant B, ≤ 15 genes) |
| 8 | `mk_rho_marker_minus_hk_narrow_set` | #6 − #7 — the **primary** margin |
| 9 | `mk_rho_mean_by_cohort_mean_narrow_set` | mean over cohorts of (mean ρ over narrow genes in that cohort) |
| 10 | `mk_n_panel_genes_used_narrow_set` | narrow genes resolved in this matrix (≤ 56) |
| 11 | `mk_n_genes_null_narrow_set` | narrow genes with no match under any alias |
| 12 | `mk_panel_coverage_frac_narrow_set` | #10 / 56 |
| 13 | `mk_n_hk_genes_used_narrow_set` | housekeeping controls resolved (≤ 15) — the audit column for #7 |
| 14 | `mk_rho_mean_PGK1_only_narrow_set` | ρ of `PGK1` alone — variant A's control half |
| 15 | `mk_rho_marker_minus_PGK1_only_narrow_set` | #6 − #14 — the **coverage-matched** margin |

Deliberately **not** duplicated, because they are identical by construction between the
two families: `mk_is_self_reference`, `mk_n_cohorts_used`,
`mk_n_cohorts_skipped_small` (the same reference, the same cohorts, the same
`min_cohort_n = 20`).

`mk_` column count in `metrics_comprehensive.csv`: **15 → 30**. All 15 are auto-excluded
from the Figure 3 clustermap and the composite score by the existing
`_BLIND_CHECK_PREFIXES = ("mk_", "xb_", "pv_")` filter — no change needed there, and the
existing leak assertion covers them.

**Keeping the `PGK1` name honest.** `mk_rho_marker_minus_PGK1_only_narrow_set` names a
gene symbol in a column name, which is only correct while `narrow ∩ housekeeping ==
{PGK1}`. That identity is asserted in `build_marker_gene_annotation.py` and re-checked in
`test_mock_metrics.py`, so a future change to the narrow list that adds or removes a
housekeeping gene fails loudly instead of quietly turning the column name into a lie.

### Out of scope (stated so the boundary is explicit)

- **Group M (`xb_`) narrow variant.** Group M is rank agreement across sample pairs, not
  marker correlation, and unlike Group L it cannot be re-aggregated from an existing
  array — a narrow variant needs a second block-wise pair matrix, i.e. real extra
  runtime. Not part of this request; say the word and it becomes a separate plan.
- **Group N (`pv_`).** Uses PCs of the whole matrix, not the marker panel at all.
- **Per-gene narrow long table.** Not needed: the 56 narrow genes are a subset of the
  633-gene panel, so their per-gene ρ values are *already* in
  `marker_gene_correlations_long.csv`. The narrow notebook rebuilds every gene-level view
  from that table by filtering on `in_narrow_set`.

---

## Files to change

### 1. `harmonization-metrics-calculation/build_marker_gene_annotation.py`

Source of truth for the gene list. Three edits.

#### 1a. Docstring — document the new provenance value (near line 13–40, the "Provenance values" block)

**Before** (end of the block, after `housekeeping`):
```
housekeeping
    Invariant-expression control panel; see the note in the plan on why these are
    expected to behave differently from biologically variable markers.

A gene may appear in several signatures, so (gene, gene_group) is the table key,
not gene alone. panel_genes() in marker_panels.py de-duplicates on gene.
"""
```

**After:**
```
housekeeping
    Invariant-expression control panel; see the note in the plan on why these are
    expected to behave differently from biologically variable markers.

A gene may appear in several signatures, so (gene, gene_group) is the table key,
not gene alone. panel_genes() in marker_panels.py de-duplicates on gene.

The `in_narrow_set` column is orthogonal to signature membership: it flags the
QC-filtered subset used by the Group L `_narrow_set` aggregates (see
NARROW_SET_GENES below and narrow_marker_panel_metrics_plan_260904.md). It is a
data-derived flag, not a literature annotation, so it changes only when the gene
QC is rerun — never as a side effect of editing a signature block.
"""
```

#### 1b. New constant, after the source-article constants (near line 60, before the `BLOCKS` definition)

```python
# QC-filtered narrow panel (selected 2026-09-04). Two criteria, both evaluated on the
# unharmonized references only:
#   1. the gene resolves in all 42 `01_raw__post0` matrices (14 strategies x 3
#      imputations), per marker_gene_coverage_by_attempt_260828.csv — 193 genes pass;
#   2. mean `frac_lt_1` < 0.20 on those references, per gene_panel_analysis/ QC — i.e.
#      fewer than 20% of samples sit in the log2 noise band.
# 56 genes survive both, one of which (PGK1) is a housekeeping control. Group L reports
# a second family of integrative aggregates over this subset, suffixed `_narrow_set`;
# see narrow_marker_panel_metrics_plan_260904.md.
NARROW_SET_GENES: frozenset[str] = frozenset(
    {
        "AKT1", "ANXA6", "BCL2", "BCL2A1", "BIRC3", "CAMK1", "CCNB1", "CCND1",
        "CCND2", "CCNE1", "CD22", "CD44", "CD5", "CD53", "CD72", "CD83", "CDK2",
        "CDK4", "CHPT1", "CNN2", "CSTB", "DDX21", "EGR3", "ENTPD1", "EZH2",
        "FBLN1", "FEZ1", "FHIT", "FXYD5", "ICAM1", "IFI44", "IFIT1", "IFITM2",
        "IFNGR1", "IMPDH2", "ITPKB", "JAM3", "LIMD1", "LMO2", "MCM6", "METAP2",
        "PCNA", "PGK1", "PLEK", "POU2F2", "PRELP", "RGS1", "SKI", "SLA", "SNX2",
        "SP140", "STMN1", "TPD52", "VCL", "VIM", "ZNF277",
    }
)
```

#### 1c. `build()` — emit the column (line 713–732)

**Before:**
```python
                    "provenance": provenance,
                    "is_housekeeping": provenance == "housekeeping",
                }
```

**After:**
```python
                    "provenance": provenance,
                    "is_housekeeping": provenance == "housekeeping",
                    "in_narrow_set": gene in NARROW_SET_GENES,
                }
```

#### 1d. `main()` — report and guard (line 738–748)

**Before:**
```python
def main() -> None:
    df = build()
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}")
    print(f"  rows (gene x gene_group): {len(df)}")
    print(f"  unique genes:             {df['gene'].nunique()}")
    print(f"  gene groups:              {df['gene_group'].nunique()}")
    print(f"  housekeeping genes:       {int(df['is_housekeeping'].sum())}")
```

**After:**
```python
def main() -> None:
    df = build()
    # A narrow-set gene that is not in the panel would silently shrink the
    # `_narrow_set` denominator instead of failing, so check it here.
    absent = sorted(NARROW_SET_GENES - set(df["gene"]))
    assert not absent, f"narrow-set genes absent from the panel: {absent}"
    # Group L names this gene in a metric key (mk_rho_marker_minus_PGK1_only_narrow_set),
    # so the column name stays truthful only while it is the sole housekeeping gene in
    # the narrow panel. Fail here rather than let the name quietly become wrong.
    hk_in_narrow = set(df.loc[df["in_narrow_set"] & df["is_housekeeping"], "gene"])
    assert hk_in_narrow == {"PGK1"}, (
        f"housekeeping genes inside the narrow set changed: {sorted(hk_in_narrow)}. "
        f"Rename mk_rho_*_PGK1_only_narrow_set in compute_batch_metrics.py to match."
    )
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}")
    print(f"  rows (gene x gene_group): {len(df)}")
    print(f"  unique genes:             {df['gene'].nunique()}")
    print(f"  gene groups:              {df['gene_group'].nunique()}")
    print(f"  housekeeping genes:       {int(df['is_housekeeping'].sum())}")
    print(f"  narrow-set genes:         {df.loc[df['in_narrow_set'], 'gene'].nunique()}")
    print(f"  housekeeping in narrow:   {sorted(hk_in_narrow)}")
```

---

### 2. `harmonization-metrics-calculation/marker_gene_annotation.csv`

Regenerated by 1 above, not hand-edited. Result: 834 rows × **11** columns (was 10),
with `in_narrow_set` True on **86** rows covering the 56 narrow genes — several of them
sit in more than one signature, so the row count is well above the gene count. Verified
after regeneration: the CSV is identical to the committed version apart from the appended
column. Commit it alongside the script, as the existing convention requires.

---

### 3. `harmonization-metrics-calculation/marker_panels.py`

#### 3a. Module docstring (line 1–12)

Add one sentence after the existing paragraph:

```
The table also carries two gene-level boolean flags that are orthogonal to signature
membership: `is_housekeeping` (the invariant-expression control panel) and
`in_narrow_set` (the QC-filtered 56-gene subset behind the Group L `_narrow_set`
aggregates). Read them with housekeeping_genes() and narrow_set_genes().
```

#### 3b. `load_marker_annotation()` — cast the new column (line 47–61)

**Before:**
```python
    df = pd.read_csv(ANNOTATION_CSV)
    df["is_housekeeping"] = df["is_housekeeping"].astype(bool)
    return df
```

**After:**
```python
    df = pd.read_csv(ANNOTATION_CSV)
    df["is_housekeeping"] = df["is_housekeeping"].astype(bool)
    # Tolerate a pre-2026-09-04 CSV (e.g. a pod that has not been rsynced yet): the
    # narrow-set metrics then resolve to zero genes and report NaN, which is visible in
    # mk_n_panel_genes_used_narrow_set, rather than raising and taking all of Group L
    # down with it.
    if "in_narrow_set" in df.columns:
        df["in_narrow_set"] = df["in_narrow_set"].astype(bool)
    return df
```

Also update the `Returns` section of the docstring to list `in_narrow_set`.

#### 3c. New accessor, immediately after `housekeeping_genes()` (line ~89)

```python
def narrow_set_genes() -> list[str]:
    """
    Return the sorted gene symbols of the QC-filtered narrow panel.

    The narrow panel is the subset of the marker table that resolves in all 42
    `01_raw__post0` matrices and whose mean `frac_lt_1` on those references is below
    0.20 — 56 genes, one of them (PGK1) a housekeeping control. Group L reports a
    second family of integrative aggregates over this subset, suffixed `_narrow_set`.

    Returns
    -------
    list of str
        Empty if the annotation CSV predates the `in_narrow_set` column, in which case
        the `_narrow_set` metrics are reported as NaN rather than raising.
    """
    df = load_marker_annotation()
    if "in_narrow_set" not in df.columns:
        return []
    return sorted(df.loc[df["in_narrow_set"], "gene"].unique().tolist())
```

---

### 4. `harmonization-metrics-calculation/compute_batch_metrics.py`

The substantive change. Four edits.

#### 4a. Module docstring — Group L line (line 11)

**Before:**
```
    L (mk_*) marker gene correlation preservation — needs a raw reference matrix
```

**After:**
```
    L (mk_*) marker gene correlation preservation — needs a raw reference matrix.
             Reported twice: over the full annotation panel, and over the QC-filtered
             56-gene narrow panel with every key suffixed `_narrow_set`. Both families
             are reductions over one correlation pass, so they are exactly comparable.
```

#### 4b. Import and new constants (line 55, and the constants block near line 84–91)

**Before:**
```python
from marker_panels import housekeeping_genes, panel_genes, resolve_panel
```

**After:**
```python
from marker_panels import (
    housekeeping_genes,
    narrow_set_genes,
    panel_genes,
    resolve_panel,
)
```

Add next to `MIN_COHORT_N` (line 86):

```python
# Suffix for the Group L aggregates restricted to the QC-filtered narrow panel. The two
# families share one correlation pass, so the suffix marks a different gene subset, never
# a different computation.
NARROW_SET_SUFFIX: str = "_narrow_set"

# The nine Group L rho aggregates. Named once so the full-panel family, the narrow-set
# family and the zero-gene fallback can never drift apart.
_MK_AGG_KEYS: tuple[str, ...] = (
    "mk_rho_mean_all_genes",
    "mk_rho_median_all_genes",
    "mk_rho_p10_all_genes",
    "mk_rho_min_all_genes",
    "mk_rho_frac_genes_above_0.9",
    "mk_rho_mean_markers",
    "mk_rho_mean_housekeeping",
    "mk_rho_marker_minus_hk",
    "mk_rho_mean_by_cohort_mean",
)

# Aggregates that exist only in the narrow family: the coverage-matched housekeeping
# control. `narrow ∩ housekeeping == {PGK1}` is asserted in
# build_marker_gene_annotation.py, so the gene symbol in these names cannot go stale
# silently.
_MK_NARROW_ONLY_KEYS: tuple[str, ...] = (
    "mk_rho_mean_PGK1_only",
    "mk_rho_marker_minus_PGK1_only",
)
```

#### 4c. New shared aggregation helper, immediately before `compute_group_l` (line ~1604)

```python
def _mk_rho_aggregates(
    rho_by_gene: np.ndarray,
    all_mask: np.ndarray,
    marker_mask: np.ndarray,
    hk_mask: np.ndarray,
    per_cohort: dict[str, float],
    suffix: str = "",
) -> dict:
    """
    Reduce a per-gene rho vector to the nine Group L aggregates.

    Called twice per job with different masks over the same rho vector: once for the
    full annotation panel and once for the narrow panel. Sharing the reduction is what
    guarantees `mk_rho_mean_all_genes` and `mk_rho_mean_all_genes_narrow_set` differ
    only by gene set.

    Parameters
    ----------
    rho_by_gene : np.ndarray
        Per-gene mean Spearman rho, NaN where no cohort produced a value.
    all_mask : np.ndarray of bool
        Genes forming the "all genes" population for this family.
    marker_mask, hk_mask : np.ndarray of bool
        Genes forming the marker and housekeeping populations. For the narrow family
        hk_mask is the full housekeeping control panel rather than the single
        housekeeping gene inside the narrow panel; the coverage-matched one-gene variant
        of the margin is emitted separately by compute_group_l as
        mk_rho_marker_minus_PGK1_only_narrow_set, and mk_n_hk_genes_used_narrow_set
        records how many controls this mask actually resolved.
    per_cohort : dict
        Per-cohort mean rho already restricted to this family's genes.
    suffix : str
        Appended to every key; "" for the full panel, "_narrow_set" for the narrow one.

    Returns
    -------
    dict of nine mk_*{suffix} keys.
    """
    result: dict = {}
    ok = ~np.isnan(rho_by_gene)
    vals = rho_by_gene[all_mask & ok]

    if vals.size:
        result[f"mk_rho_mean_all_genes{suffix}"] = float(np.mean(vals))
        result[f"mk_rho_median_all_genes{suffix}"] = float(np.median(vals))
        result[f"mk_rho_p10_all_genes{suffix}"] = float(np.percentile(vals, 10))
        result[f"mk_rho_min_all_genes{suffix}"] = float(np.min(vals))
        result[f"mk_rho_frac_genes_above_0.9{suffix}"] = float(np.mean(vals > 0.9))
    else:
        for key in _MK_AGG_KEYS[:5]:
            result[f"{key}{suffix}"] = np.nan

    marker_vals = rho_by_gene[marker_mask & ok]
    hk_vals = rho_by_gene[hk_mask & ok]
    result[f"mk_rho_mean_markers{suffix}"] = (
        float(np.mean(marker_vals)) if marker_vals.size else np.nan
    )
    result[f"mk_rho_mean_housekeeping{suffix}"] = (
        float(np.mean(hk_vals)) if hk_vals.size else np.nan
    )
    result[f"mk_rho_marker_minus_hk{suffix}"] = (
        float(np.mean(marker_vals) - np.mean(hk_vals))
        if marker_vals.size and hk_vals.size
        else np.nan
    )
    result[f"mk_rho_mean_by_cohort_mean{suffix}"] = (
        float(np.mean(list(per_cohort.values()))) if per_cohort else np.nan
    )
    return result
```

#### 4d. `compute_group_l()` — rewrite the body around one pass and two reductions (line 1606–1762)

Signature and docstring:

**Before:**
```python
def compute_group_l(
    exp_df: pd.DataFrame,
    ref_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    panel: Optional[list[str]] = None,
    min_cohort_n: int = MIN_COHORT_N,
    collect_detail: bool = False,
) -> dict:
```

**After:**
```python
def compute_group_l(
    exp_df: pd.DataFrame,
    ref_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    panel: Optional[list[str]] = None,
    min_cohort_n: int = MIN_COHORT_N,
    collect_detail: bool = False,
    narrow_panel: Optional[list[str]] = None,
) -> dict:
```

with these additions to the docstring:

```
    Reported twice. The full annotation panel yields the unsuffixed keys; the
    QC-filtered narrow panel yields the same nine aggregates, four coverage counters and
    a second marker-minus-housekeeping margin taken against PGK1 alone, every key
    suffixed `_narrow_set`. Both families are reductions over one correlation pass —
    per-gene rho is independent of the other genes in the panel — so they cost one extra
    masked mean per cohort and nothing else, and any difference between them is a
    property of the gene set alone. Only the full panel produces the per-gene and
    per-cohort dicts; the narrow family is integrative only.

    Two housekeeping controls, deliberately. `mk_rho_marker_minus_hk_narrow_set` uses the
    full housekeeping panel, of which only 6 of 15 genes clear the coverage bar the
    narrow markers had to clear, so its control set varies in composition across
    attempts. `mk_rho_marker_minus_PGK1_only_narrow_set` uses the one housekeeping gene
    inside the narrow panel: coverage-matched, but n = 1. Which is less noisy is an
    empirical question the blind-check notebook answers.

    narrow_panel : list of str, optional
        Genes for the `_narrow_set` family. Default: narrow_set_genes(). Pass [] to
        disable it (every `_narrow_set` key is then NaN / 0).
```

Panel resolution — **before:**
```python
    result: dict = {}
    full_panel = panel if panel is not None else panel_genes(include_housekeeping=True)

    shared = exp_df.columns.intersection(ref_df.columns)
    genes, missing = resolve_panel(set(shared), full_panel)

    result["mk_n_panel_genes_used"] = len(genes)
    result["mk_n_genes_null"] = len(missing)
    result["mk_panel_coverage_frac"] = (
        float(len(genes) / len(full_panel)) if full_panel else np.nan
    )
    result["mk_is_self_reference"] = bool(exp_df is ref_df)
```

**After:**
```python
    result: dict = {}
    full_panel = panel if panel is not None else panel_genes(include_housekeeping=True)
    narrow_full = narrow_set_genes() if narrow_panel is None else list(narrow_panel)
    hk_full = housekeeping_genes()

    shared = exp_df.columns.intersection(ref_df.columns)
    avail = set(shared)
    genes, missing = resolve_panel(avail, full_panel)
    # The narrow family must not depend on a --panel-groups filter, and its
    # housekeeping control must not depend on whether housekeeping genes are inside the
    # requested signatures, so both are resolved independently and unioned into the one
    # correlation pass below. With the default panel the union is a no-op: all 56 narrow
    # genes and all 15 housekeeping genes are already in the annotation table.
    narrow_genes, narrow_missing = resolve_panel(avail, narrow_full)
    hk_genes, _ = resolve_panel(avail, hk_full)
    genes_all = sorted(set(genes) | set(narrow_genes) | set(hk_genes))

    result["mk_n_panel_genes_used"] = len(genes)
    result["mk_n_genes_null"] = len(missing)
    result["mk_panel_coverage_frac"] = (
        float(len(genes) / len(full_panel)) if full_panel else np.nan
    )
    result["mk_is_self_reference"] = bool(exp_df is ref_df)
    result[f"mk_n_panel_genes_used{NARROW_SET_SUFFIX}"] = len(narrow_genes)
    result[f"mk_n_genes_null{NARROW_SET_SUFFIX}"] = len(narrow_missing)
    result[f"mk_panel_coverage_frac{NARROW_SET_SUFFIX}"] = (
        float(len(narrow_genes) / len(narrow_full)) if narrow_full else np.nan
    )
    result[f"mk_n_hk_genes_used{NARROW_SET_SUFFIX}"] = len(hk_genes)
    if not narrow_full:
        print(
            f"[{_ts()}][metrics] Group L: narrow panel is empty — every "
            f"{NARROW_SET_SUFFIX} key will be NaN. Is marker_gene_annotation.csv "
            f"missing the in_narrow_set column?",
            flush=True,
        )
```

Zero-gene fallback — **before:**
```python
    if not genes:
        for key in (
            "mk_rho_mean_all_genes",
            ...
            "mk_rho_mean_by_cohort_mean",
        ):
            result[key] = np.nan
        result["mk_rho_by_gene"] = {}
        result["mk_rho_n_cohorts_by_gene"] = {}
        result["mk_rho_by_cohort"] = {}
        result["mk_n_cohorts_used"] = 0
        result["mk_n_cohorts_skipped_small"] = 0
        return result
```

**After** (note the condition changes from `genes` to `genes_all` — a matrix that
resolves narrow genes but no panel genes is impossible with the default panel, but the
fallback must still emit both families):
```python
    if not genes_all:
        for key in _MK_AGG_KEYS:
            result[key] = np.nan
            result[f"{key}{NARROW_SET_SUFFIX}"] = np.nan
        for key in _MK_NARROW_ONLY_KEYS:
            result[f"{key}{NARROW_SET_SUFFIX}"] = np.nan
        result["mk_rho_by_gene"] = {}
        result["mk_rho_n_cohorts_by_gene"] = {}
        result["mk_rho_by_cohort"] = {}
        result["mk_n_cohorts_used"] = 0
        result["mk_n_cohorts_skipped_small"] = 0
        return result
```

Matrices and masks — **before:**
```python
    A = exp_df[genes].values.astype(float)
    B = ref_df[genes].values.astype(float)
```

**After:**
```python
    A = exp_df[genes_all].values.astype(float)
    B = ref_df[genes_all].values.astype(float)

    panel_set, narrow_set, hk_set = set(genes), set(narrow_genes), set(hk_genes)
    panel_mask = np.array([g in panel_set for g in genes_all])
    narrow_mask = np.array([g in narrow_set for g in genes_all])
    hk_mask = np.array([g in hk_set for g in genes_all])
```

Cohort loop — **before:**
```python
    rho_sums = np.zeros(len(genes))
    rho_counts = np.zeros(len(genes))
    per_cohort: dict[str, float] = {}
    detail: dict[str, dict[str, float]] = {}
    n_skipped = 0

    for level in np.unique(cohorts):
        mask = cohorts == level
        if mask.sum() < min_cohort_n:
            n_skipped += 1
            continue
        rho = _spearman_columnwise(A[mask], B[mask])
        valid = ~np.isnan(rho)
        rho_sums[valid] += rho[valid]
        rho_counts[valid] += 1
        if valid.any():
            per_cohort[str(level)] = float(np.mean(rho[valid]))
        if collect_detail:
            detail[str(level)] = {
                g: (float(v) if not np.isnan(v) else None) for g, v in zip(genes, rho)
            }
```

**After:**
```python
    rho_sums = np.zeros(len(genes_all))
    rho_counts = np.zeros(len(genes_all))
    per_cohort: dict[str, float] = {}
    per_cohort_narrow: dict[str, float] = {}
    detail: dict[str, dict[str, float]] = {}
    n_skipped = 0

    for level in np.unique(cohorts):
        mask = cohorts == level
        if mask.sum() < min_cohort_n:
            n_skipped += 1
            continue
        rho = _spearman_columnwise(A[mask], B[mask])
        valid = ~np.isnan(rho)
        rho_sums[valid] += rho[valid]
        rho_counts[valid] += 1
        # Per-cohort means are the one aggregate that cannot be recovered from
        # rho_by_gene afterwards, so both families accumulate theirs here.
        v_panel = valid & panel_mask
        if v_panel.any():
            per_cohort[str(level)] = float(np.mean(rho[v_panel]))
        v_narrow = valid & narrow_mask
        if v_narrow.any():
            per_cohort_narrow[str(level)] = float(np.mean(rho[v_narrow]))
        if collect_detail:
            # Detail stays on the requested panel only, so the marker_corr/ payload and
            # the long-format tables are unchanged by the union above.
            detail[str(level)] = {
                g: (float(v) if not np.isnan(v) else None)
                for g, v, keep in zip(genes_all, rho, panel_mask)
                if keep
            }
```

Per-gene dicts — **before:**
```python
    result["mk_rho_by_gene"] = {
        g: (float(v) if not np.isnan(v) else None) for g, v in zip(genes, rho_by_gene)
    }
    result["mk_rho_n_cohorts_by_gene"] = {g: int(c) for g, c in zip(genes, rho_counts)}
    result["mk_rho_by_cohort"] = per_cohort
```

**After** (restricted to `panel_mask`, so `marker_gene_correlations_long.csv` and
`marker_cohort_correlations_long.csv` come out byte-identical to the current run):
```python
    result["mk_rho_by_gene"] = {
        g: (float(v) if not np.isnan(v) else None)
        for g, v, keep in zip(genes_all, rho_by_gene, panel_mask)
        if keep
    }
    result["mk_rho_n_cohorts_by_gene"] = {
        g: int(c) for g, c, keep in zip(genes_all, rho_counts, panel_mask) if keep
    }
    result["mk_rho_by_cohort"] = per_cohort
```

Aggregates — **before** (the ~40 lines computing `finite`, the five percentile keys, the
`hk`/`is_hk`/`marker_vals`/`hk_vals` block and `mk_rho_mean_by_cohort_mean`):

**After:**
```python
    # Full annotation panel. hk is intersected with the panel so a --panel-groups run
    # that excludes housekeeping keeps today's behaviour exactly.
    result.update(
        _mk_rho_aggregates(
            rho_by_gene,
            all_mask=panel_mask,
            marker_mask=panel_mask & ~hk_mask,
            hk_mask=panel_mask & hk_mask,
            per_cohort=per_cohort,
            suffix="",
        )
    )
    # QC-filtered narrow panel. Primary margin: the full housekeeping control panel.
    result.update(
        _mk_rho_aggregates(
            rho_by_gene,
            all_mask=narrow_mask,
            marker_mask=narrow_mask & ~hk_mask,
            hk_mask=hk_mask,
            per_cohort=per_cohort_narrow,
            suffix=NARROW_SET_SUFFIX,
        )
    )
    # Second, coverage-matched margin for the narrow panel: the housekeeping genes that
    # are themselves inside the narrow panel — today exactly PGK1. Only 6 of the 15
    # housekeeping controls clear the all-42-pairs coverage bar the narrow markers had to
    # clear, so the full-panel control above is a variable-composition set while this one
    # is coverage-matched but n = 1. Both are reported so the noisier of the two can be
    # identified from the data rather than argued about.
    ok = ~np.isnan(rho_by_gene)
    narrow_marker_vals = rho_by_gene[(narrow_mask & ~hk_mask) & ok]
    pgk1_vals = rho_by_gene[(narrow_mask & hk_mask) & ok]
    result[f"mk_rho_mean_PGK1_only{NARROW_SET_SUFFIX}"] = (
        float(np.mean(pgk1_vals)) if pgk1_vals.size else np.nan
    )
    result[f"mk_rho_marker_minus_PGK1_only{NARROW_SET_SUFFIX}"] = (
        float(np.mean(narrow_marker_vals) - np.mean(pgk1_vals))
        if narrow_marker_vals.size and pgk1_vals.size
        else np.nan
    )
    if collect_detail:
        result["mk_gene_cohort_detail"] = detail
    return result
```

#### 4e. `compute_all_metrics()` — thread the parameter through (line 2208–2380)

Signature gains `narrow_panel: Optional[list[str]] = None` after `panel`, with the
docstring entry:

```
    narrow_panel : list of str, optional
        Gene panel for the Group L `_narrow_set` aggregates. Default:
        marker_panels.narrow_set_genes(). Pass [] to disable that family.
```

and the Group L dispatch — **before:**
```python
    _run_group(
        "L",
        compute_group_l,
        exp_df,
        ref_df,
        ann_df,
        panel,
        MIN_COHORT_N,
        collect_gene_cohort_detail,
    )
```

**After:**
```python
    _run_group(
        "L",
        compute_group_l,
        exp_df,
        ref_df,
        ann_df,
        panel,
        MIN_COHORT_N,
        collect_gene_cohort_detail,
        narrow_panel,
    )
```

Also update the module-level `panel` docstring line ("Marker gene panel for Groups L and
M") to note that the narrow family is Group L only.

---

### 5. `harmonization-metrics-calculation/run_metrics_job.py`

#### 5a. `GROUP_SENTINEL_KEYS` — multi-key sentinels (line 83–99)

**Before:**
```python
GROUP_SENTINEL_KEYS: dict[str, str] = {
    "E": "n_samples",
    ...
    "L": "mk_rho_mean_all_genes",
    "M": "xb_rank_agree",
    "N": "pv_lobo3_f1_macro_mean",
}
```

**After:**
```python
# One sentinel key per group, or a tuple when a group has gained a new metric family: a
# group counts as complete only when EVERY listed key is populated. Listing the new key
# is what makes every already-finished sidecar resume that group automatically on the
# next run — no --force-groups, and no way to end up with a half-populated group.
GROUP_SENTINEL_KEYS: dict[str, str | tuple[str, ...]] = {
    "E": "n_samples",
    ...
    "L": ("mk_rho_mean_all_genes", "mk_rho_mean_all_genes_narrow_set"),
    "M": "xb_rank_agree",
    "N": "pv_lobo3_f1_macro_mean",
}
```

#### 5b. `_groups_to_recompute()` — honour tuples (line 114–133)

**Before:**
```python
        sentinel = GROUP_SENTINEL_KEYS.get(g)
        if sentinel is None or prior.get(sentinel) is None:
            missing.add(g)
```

**After:**
```python
        sentinel = GROUP_SENTINEL_KEYS.get(g)
        if sentinel is None:
            missing.add(g)
            continue
        keys = (sentinel,) if isinstance(sentinel, str) else sentinel
        if any(prior.get(k) is None for k in keys):
            missing.add(g)
```

#### 5c. Module docstring — the resume note (line 28–39)

Add after the existing "Blind final check only" example:

```
# Add the Group L `_narrow_set` aggregates to a sidecar that already has Group L. No
# --force-groups is needed: Group L's second sentinel key is missing, so the incremental
# check schedules it on its own.
python run_metrics_job.py \
    --strat C_rnaseq_only --imp softimpute --method 04_sva --post-rm False \
    --out-json /tmp/metrics.json --out-genes-json /tmp/genes.json \
    --groups L --skip-wm True --ref-cache-dir /workspace/ref_cache
```

No CLI flag is added: the narrow panel is read from the annotation CSV, exactly as the
full panel is. `--panel-groups` continues to filter the full-panel family only, by
design (§4d).

---

### 6. `harmonization-metrics-calculation/test_mock_metrics.py`

#### 6a. Import (line 27–31)

Add `narrow_set_genes` to the `marker_panels` import and `NARROW_SET_SUFFIX`,
`_MK_AGG_KEYS`, `_MK_NARROW_ONLY_KEYS` to the `compute_batch_metrics` import.

#### 6b. New test — narrow-set family, after `test_group_l_per_gene_keys` (line ~625)

```python
def test_group_l_narrow_set() -> None:
    print("\n--- test_group_l_narrow_set ---")
    narrow = narrow_set_genes()
    _check(len(narrow) == 56, "narrow_panel_has_56_genes", f"got {len(narrow)}")
    # mk_rho_*_PGK1_only_narrow_set names this gene, so the identity behind the name is
    # asserted here as well as in build_marker_gene_annotation.py.
    hk_in_narrow = set(narrow) & set(housekeeping_genes())
    _check(
        hk_in_narrow == {"PGK1"},
        "pgk1_is_the_only_narrow_housekeeping_gene",
        f"got {sorted(hk_in_narrow)}",
    )

    # Build data whose columns are the narrow panel plus the housekeeping controls, so
    # both families resolve fully.
    genes = sorted(set(narrow) | set(housekeeping_genes()))
    exp_df, ann_df = _make_panel_data(panel=genes)
    res = compute_group_l(exp_df, exp_df, ann_df)

    for key in _MK_AGG_KEYS:
        _check(f"{key}{NARROW_SET_SUFFIX}" in res, f"narrow_key_present:{key}")
    for key in (
        "mk_n_panel_genes_used",
        "mk_n_genes_null",
        "mk_panel_coverage_frac",
    ):
        _check(f"{key}{NARROW_SET_SUFFIX}" in res, f"narrow_key_present:{key}")
    _check(f"mk_n_hk_genes_used{NARROW_SET_SUFFIX}" in res, "narrow_hk_count_present")
    for key in _MK_NARROW_ONLY_KEYS:
        _check(f"{key}{NARROW_SET_SUFFIX}" in res, f"narrow_only_key_present:{key}")

    # No dict-valued narrow keys: the family is integrative only, so nothing new can
    # reach the wide CSV as a stringified container.
    containers = [
        k
        for k, v in res.items()
        if k.endswith(NARROW_SET_SUFFIX) and isinstance(v, (dict, list))
    ]
    _check(not containers, "narrow_family_is_scalar_only", f"got {containers}")

    _check(
        res[f"mk_n_panel_genes_used{NARROW_SET_SUFFIX}"] == 56,
        "all_56_narrow_genes_resolved",
        f"got {res[f'mk_n_panel_genes_used{NARROW_SET_SUFFIX}']}",
    )
    _check(
        abs(res[f"mk_panel_coverage_frac{NARROW_SET_SUFFIX}"] - 1.0) < 1e-9,
        "narrow_coverage_frac_is_one",
    )

    # Identity reference: rho == 1 everywhere, so both families sit at 1.0.
    _check(
        abs(res[f"mk_rho_mean_all_genes{NARROW_SET_SUFFIX}"] - 1.0) < 1e-6,
        "narrow_identity_rho_is_one",
        f"got {res[f'mk_rho_mean_all_genes{NARROW_SET_SUFFIX}']}",
    )

    # The decisive property: the narrow family is a re-aggregation of the same rho
    # values, so it must equal the mean over the narrow subset of mk_rho_by_gene.
    by_gene = {g: v for g, v in res["mk_rho_by_gene"].items() if v is not None}
    sub = [v for g, v in by_gene.items() if g in set(narrow)]
    _check(
        abs(float(np.mean(sub)) - res[f"mk_rho_mean_all_genes{NARROW_SET_SUFFIX}"])
        < 1e-9,
        "narrow_mean_matches_per_gene_subset",
    )

    # The two housekeeping controls: the PGK1-only variant must equal PGK1's own rho,
    # and its margin must be the marker mean minus exactly that value.
    _check(
        abs(res[f"mk_rho_mean_PGK1_only{NARROW_SET_SUFFIX}"] - by_gene["PGK1"]) < 1e-12,
        "pgk1_only_control_equals_pgk1_rho",
    )
    _check(
        abs(
            res[f"mk_rho_marker_minus_PGK1_only{NARROW_SET_SUFFIX}"]
            - (
                res[f"mk_rho_mean_markers{NARROW_SET_SUFFIX}"]
                - res[f"mk_rho_mean_PGK1_only{NARROW_SET_SUFFIX}"]
            )
        )
        < 1e-12,
        "pgk1_only_margin_decomposes",
    )
    # Dropping PGK1 must NaN out the coverage-matched margin while leaving the
    # full-housekeeping margin intact — that asymmetry is the whole point of shipping
    # both.
    no_pgk1 = [g for g in genes if g != "PGK1"]
    res_no = compute_group_l(exp_df[no_pgk1], exp_df[no_pgk1], ann_df)
    _check(
        np.isnan(res_no[f"mk_rho_marker_minus_PGK1_only{NARROW_SET_SUFFIX}"]),
        "pgk1_only_margin_is_nan_without_pgk1",
    )
    _check(
        not np.isnan(res_no[f"mk_rho_marker_minus_hk{NARROW_SET_SUFFIX}"]),
        "full_hk_margin_survives_without_pgk1",
    )

    # Partial coverage must be counted, not silently absorbed.
    keep = genes[:20]
    part = compute_group_l(exp_df[keep], exp_df[keep], ann_df)
    _check(
        part[f"mk_n_panel_genes_used{NARROW_SET_SUFFIX}"]
        == len(set(keep) & set(narrow)),
        "narrow_partial_coverage_counted",
    )
    _check(
        part[f"mk_n_genes_null{NARROW_SET_SUFFIX}"] > 0,
        "narrow_missing_genes_counted",
    )

    # Disabling the family must leave the full-panel family untouched.
    off = compute_group_l(exp_df, exp_df, ann_df, narrow_panel=[])
    _check(
        off[f"mk_n_panel_genes_used{NARROW_SET_SUFFIX}"] == 0,
        "narrow_family_disabled_by_empty_panel",
    )
    _check(
        abs(off["mk_rho_mean_all_genes"] - res["mk_rho_mean_all_genes"]) < 1e-12,
        "full_panel_unaffected_by_narrow_family",
    )
```

`_make_panel_data()` (line 503) currently hardcodes `panel_genes(...)[:n_genes]`; it
needs an optional `panel: Optional[list[str]] = None` argument so the test can hand it an
explicit gene list. Default behaviour unchanged.

#### 6c. Extend the existing sentinel test (line 266–302 and 838–843)

```python
    # Group L gained a second sentinel with the `_narrow_set` family: a sidecar carrying
    # only the old key must schedule L for recompute, and only stop once both are there.
    prior_old_l = {"mk_rho_mean_all_genes": 0.99, "status": "ok"}
    result = _groups_to_recompute(prior_old_l, {"L"})
    _check(result == {"L"}, "L_recomputed_when_narrow_sentinel_missing", f"got {result}")

    prior_both_l = dict(prior_old_l, mk_rho_mean_all_genes_narrow_set=0.98)
    result = _groups_to_recompute(prior_both_l, {"L"})
    _check(result == set(), "L_complete_with_both_sentinels", f"got {result}")
```

#### 6d. Extend `test_lmn_in_compute_all` (line 810–817)

Add `"mk_rho_mean_all_genes_narrow_set"`, `"mk_rho_marker_minus_hk_narrow_set"` and
`"mk_rho_marker_minus_PGK1_only_narrow_set"` to the expected-key list.

#### 6e. Register the new test in `__main__` (line ~885)

Add `test_group_l_narrow_set()` after `test_group_l_missing_panel_genes()`.

---

### 7. `harmonization-metrics/create_correlation_prediction_notebook.py`

One generator, two notebooks. All edits are driven by a single variant switch, so the
full-variant notebook comes out unchanged.

#### 7a. Variant switch, right after the imports (line 22–33)

**Before:**
```python
from pathlib import Path

import nbformat as nbf

OUTPUT = Path(__file__).parent / "correlation_prediction_metrics_analysis.ipynb"

# Dated inputs. Bump DATE_TAG after a new run_metrics_concat.py, and FIG_DIR when the
# article's figure folder rolls over.
DATE_TAG = "260824"
FIG_DIR = "../figures_for_article/current_figures_tables_for_article_260819"
```

**After:**
```python
import argparse
from pathlib import Path

import nbformat as nbf

# Cell bodies are declared at import time by the md()/code() calls below, so the variant
# has to be known before them. argparse runs here rather than in main() for that reason.
_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument(
    "--narrow-set",
    action="store_true",
    help="Build the narrow-panel variant: Group L read from the mk_*_narrow_set "
    "columns and every gene-level view restricted to the 56 in_narrow_set genes. "
    "Writes correlation_prediction_metrics_analysis_narrow_set.ipynb.",
)
_ap.add_argument(
    "--date-tag",
    default="260824",
    help="Metric-table date tag the notebook reads (default: 260824). The narrow "
    "columns only exist in a snapshot produced after the Group L recompute run.",
)
_args = _ap.parse_args()

NARROW = _args.narrow_set
SFX = "_narrow_set" if NARROW else ""
OUTPUT = (
    Path(__file__).parent / f"correlation_prediction_metrics_analysis{SFX}.ipynb"
)

# Dated inputs. Bump --date-tag after a new run_metrics_concat.py, and FIG_DIR when the
# article's figure folder rolls over.
DATE_TAG = _args.date_tag
FIG_DIR = "../figures_for_article/current_figures_tables_for_article_260819"
```

#### 7b. Title markdown (line 47–68) — variant note

Append, interpolated only in the narrow variant:

```
**Narrow panel variant.** Group L here is read from the `mk_*_narrow_set` columns: the
same aggregates over the 56-gene QC-filtered subset (present in all 42 `01_raw__post0`
matrices, mean `frac_lt_1` < 0.20). The marker-versus-housekeeping margin is reported
twice — against the full housekeeping panel and against `PGK1`, the one housekeeping gene
inside the narrow subset — because only 6 of the 15 housekeeping genes clear the same
coverage bar the narrow markers had to clear. §3b decides which of the two is less noisy.
Every gene-level view is restricted to those 56 genes, taken from the same
`marker_gene_correlations_long` table — the narrow family adds no long table of its own.
Groups M and N are unchanged from the full-panel notebook and are shown here for context.
```

#### 7c. Setup cell (line ~110–140) — variant constants

Add to the constants block:

```python
# ── Variant ────────────────────────────────────────────────────────────────
NARROW      = %(narrow)s      # narrow-panel variant?
MK_SFX      = "%(sfx)s"       # suffix on every Group L column and figure name
```

and change the `save_figure` call sites to use `f"{name}{MK_SFX}"` — done once, inside
`save_figure()` itself, so no call site changes:

**Before:**
```python
def save_figure(fig, name, figures_dir=FIG_DIR):
    """Save one figure as PDF, SVG and PNG. PDF/SVG are the project defaults."""
    figures_dir = Path(figures_dir)
```

**After:**
```python
def save_figure(fig, name, figures_dir=FIG_DIR):
    """Save one figure as PDF, SVG and PNG, with the variant suffix on the filename."""
    name = f"{name}{MK_SFX}"
    figures_dir = Path(figures_dir)
```

#### 7d. Blind-check column selection (line 190–197)

**Before:**
```python
mk_cols = sorted(c for c in analysis.columns if c.startswith("mk_"))
```

**After:**
```python
# The two Group L families are separated here, so each notebook variant reports exactly
# one of them and the printed counts stay stable when the other family lands.
NARROW_TAG = "_narrow_set"
if NARROW:
    mk_cols = sorted(c for c in analysis.columns if c.startswith("mk_")
                     and c.endswith(NARROW_TAG))
else:
    mk_cols = sorted(c for c in analysis.columns if c.startswith("mk_")
                     and not c.endswith(NARROW_TAG))
```

#### 7e. Gene-set filter (line 329–350)

**Before:**
```python
GENE_MIN_FRAC = 0.9

if gene_long.empty:
    COMPLETE_GENES = []
    ...
```

**After** — the narrow variant replaces the coverage gate with the narrow list, because
the narrow genes were selected *by* a coverage criterion and re-gating them on
harmonized-attempt coverage would be circular:

```python
GENE_MIN_FRAC = 0.9

if NARROW:
    # The narrow panel is itself a coverage-plus-QC selection made on the raw
    # references, so re-gating it on harmonized-attempt coverage would be circular.
    # The gate here is only the panel membership flag.
    NARROW_GENES = sorted(
        marker_ann.loc[marker_ann["in_narrow_set"], "gene"].unique())
    assert len(NARROW_GENES) == 56, f"narrow panel changed: {len(NARROW_GENES)}"
    COMPLETE_GENES = ([] if gene_long.empty else
                      sorted(set(NARROW_GENES) & set(gene_long["gene"])))
    print(f"Narrow panel: {len(NARROW_GENES)} genes, "
          f"{len(COMPLETE_GENES)} of them present in the long table.")
elif gene_long.empty:
    COMPLETE_GENES = []
    ...
```

This cell reads `marker_ann`, which is currently loaded in the *next* cell — the marker
annotation block (line 353–361) moves above the gene-set filter block within the same
cell. Both are in one code cell already, so this is a reordering inside one string, not a
cell reshuffle.

#### 7f. `HEADLINE` (line 375–384)

**Before:**
```python
HEADLINE = [
    ("mk_rho_mean_all_genes",      "Group L\\nmean per-gene $\\\\rho$"),
    ("mk_rho_marker_minus_hk",     "Group L\\nmarker $-$ housekeeping"),
    ("xb_rank_agree",              "Group M\\ncross-batch agreement"),
    ...
```

**After** — the narrow variant gains an eighth panel for the coverage-matched margin, so
both housekeeping controls are read side by side in the same best-vs-rest figure
(`HEADLINE` is already filtered to columns that exist, so the extra entry is inert in the
full-panel variant):
```python
HEADLINE = [
    (f"mk_rho_mean_all_genes{MK_SFX}",  "Group L\\nmean per-gene $\\\\rho$"),
    (f"mk_rho_marker_minus_hk{MK_SFX}", "Group L\\nmarker $-$ housekeeping"),
    ("mk_rho_marker_minus_PGK1_only_narrow_set",
                                        "Group L\\nmarker $-$ PGK1 only"),
    ("xb_rank_agree",                   "Group M\\ncross-batch agreement"),
    ...
```

#### 7g. Coverage section §5 (line 597–610)

**Before:**
```python
if "mk_n_panel_genes_used" in df_lmn.columns:
    cov = (df_lmn.groupby(["strat", "imp"])["mk_n_panel_genes_used"]
```

**After:**
```python
_cov_col = f"mk_n_panel_genes_used{MK_SFX}"
if _cov_col in df_lmn.columns:
    cov = (df_lmn.groupby(["strat", "imp"])[_cov_col]
```

with the same substitution in the `else` branch's message and the axis label.

#### 7h. New cell — cross-check / fallback (narrow variant only)

Every narrow aggregate except `mk_rho_mean_by_cohort_mean_narrow_set` is derivable from
`marker_gene_correlations_long.csv`, because the narrow genes are a subset of the 633-gene
panel. That makes a free consistency check — and a fallback that lets the notebook run
before the recompute lands.

**Placement matters.** This cell goes at the **end of §1**, immediately after the
gene-set-filter / marker-annotation cell — the first point where `gene_long`,
`NARROW_GENES`, `HOUSEKEEPING_GENES`, `df_lmn` and `mk_cols` all exist. It must run
*before* §2's `HEADLINE` figure and before the new §3b comparison, both of which read the
margin columns; a fallback that only fires later would leave those two sections empty on
a pre-recompute snapshot.

```python
# ── Cross-check: the wide narrow columns vs the long table ─────────────────────
# The narrow family is a re-aggregation of the same per-gene rho values the long table
# already carries, so these two paths must agree to floating-point noise. If the wide
# narrow columns are absent (the Group L recompute has not run for this DATE_TAG yet),
# the long-table version stands in so the rest of the notebook still works.
if NARROW and not gene_long.empty:
    HK = set(HOUSEKEEPING_GENES)
    g = gene_long[gene_long["gene"].isin(NARROW_GENES)].dropna(subset=["rho"])
    from_long = g.groupby("run_id")["rho"].agg(
        mk_rho_mean_all_genes_narrow_set="mean",
        mk_rho_median_all_genes_narrow_set="median",
        mk_rho_min_all_genes_narrow_set="min",
    )
    from_long["mk_rho_frac_genes_above_0.9_narrow_set"] = (
        g.assign(hi=g["rho"] > 0.9).groupby("run_id")["hi"].mean())
    from_long["mk_rho_mean_markers_narrow_set"] = (
        g[~g["gene"].isin(HK)].groupby("run_id")["rho"].mean())
    # Both housekeeping controls are derivable here too: the full panel's controls are in
    # the long table (they are part of the 633-gene panel), and PGK1 is one row of it.
    from_long["mk_rho_mean_housekeeping_narrow_set"] = (
        gene_long[gene_long["gene"].isin(HK)].dropna(subset=["rho"])
                 .groupby("run_id")["rho"].mean())
    from_long["mk_rho_mean_PGK1_only_narrow_set"] = (
        gene_long[gene_long["gene"] == "PGK1"].dropna(subset=["rho"])
                 .groupby("run_id")["rho"].mean())
    from_long["mk_rho_marker_minus_hk_narrow_set"] = (
        from_long["mk_rho_mean_markers_narrow_set"]
        - from_long["mk_rho_mean_housekeeping_narrow_set"])
    from_long["mk_rho_marker_minus_PGK1_only_narrow_set"] = (
        from_long["mk_rho_mean_markers_narrow_set"]
        - from_long["mk_rho_mean_PGK1_only_narrow_set"])

    col = "mk_rho_mean_all_genes_narrow_set"
    if col in df_lmn.columns and df_lmn[col].notna().any():
        both = df_lmn[[col]].join(from_long[[col]], rsuffix="_long").dropna()
        d = (both[col] - both[f"{col}_long"]).abs()
        print(f"Wide vs long narrow mean rho: n = {len(both)}, "
              f"max |diff| = {d.max():.2e}")
        assert d.max() < 1e-6, (
            "The wide mk_*_narrow_set columns disagree with the long table. One of the "
            "two is stale — regenerate the metric tables before reading any figure.")
    else:
        print("No mk_*_narrow_set columns in this snapshot — falling back to the "
              "long-table aggregates for §2.")
        for c in from_long.columns:
            df_lmn[c] = from_long[c]
        mk_cols = sorted(set(mk_cols) | set(from_long.columns))
```

#### 7i. New section §3b — which housekeeping control is noisier (narrow variant only)

The reason both margins are computed is to find out which one is less noisy. That is a
measurement, so the notebook makes it, rather than leaving it to inspection. Inserted as
a markdown cell plus one code cell at the end of §3 — i.e. **earlier in the generated
notebook than §7h's cell, but later in this list**; the generator emits cells in the
order its `md()` / `code()` calls appear, so add §3b's calls between the §3 block and the
`# ── §4` divider, and §7h's call just before the `# ── §2 Best vs rest` divider.

Markdown:

```
### §3b — Which housekeeping control is less noisy?

`mk_rho_marker_minus_hk_narrow_set` subtracts the full housekeeping panel; only 6 of
those 15 genes clear the coverage bar the narrow markers had to clear, so its control set
changes composition between attempts. `mk_rho_marker_minus_PGK1_only_narrow_set`
subtracts `PGK1` alone: coverage-matched, but a single gene.

Three readings, all on the same rows:

1. **Dispersion within a fixed `(strat, imp)` pair.** Attempts inside one pair share a
   sample set and a gene set, so spread there is method effect plus metric noise. The
   noisier control inflates it.
2. **Dispersion of the control term itself** — `sd` of `mk_rho_mean_housekeeping_narrow_set`
   versus `mk_rho_mean_PGK1_only_narrow_set`.
3. **Discriminative power** — the best-vs-rest rank-biserial correlation of each margin.
   A noisier metric buys the same separation at a lower effect size.

A margin that wins on 1 and 3 is the one to quote in the manuscript.
```

Code:

```python
# Fig 5f — the two housekeeping controls, compared on noise and on discrimination.
PAIR = [
    ("mk_rho_marker_minus_hk_narrow_set",        "full housekeeping panel"),
    ("mk_rho_marker_minus_PGK1_only_narrow_set", "PGK1 only"),
]
PAIR = [(c, lab) for c, lab in PAIR if c in df_lmn.columns]

if NARROW and len(PAIR) == 2:
    d = df_lmn[~df_lmn["is_raw"]].copy()
    rows = []
    for col, lab in PAIR:
        s = d[col].dropna()
        # Within-pair spread: mean over (strat, imp) of the per-pair SD.
        within = (d.dropna(subset=[col]).groupby(["strat", "imp"])[col]
                   .std().mean())
        a = d.loc[d["is_best"], col].dropna()
        b = d.loc[~d["is_best"], col].dropna()
        if len(a) > 2 and len(b) > 2:
            u, p = mannwhitneyu(a, b, alternative="two-sided")
            rbc = 2 * u / (len(a) * len(b)) - 1
        else:
            p, rbc = np.nan, np.nan
        rows.append({
            "control": lab, "metric": col, "n": len(s),
            "mean": s.mean(), "sd": s.std(),
            "iqr": s.quantile(0.75) - s.quantile(0.25),
            "mad": (s - s.median()).abs().median(),
            "within_pair_sd": within,
            "best_vs_rest_rbc": rbc, "best_vs_rest_p": p,
        })
    noise_cmp = pd.DataFrame(rows)
    display(noise_cmp.round(4))
    noise_cmp.to_csv(FIG_DIR / f"T5f_hk_control_noise_comparison{MK_SFX}.csv",
                     index=False)

    quieter = noise_cmp.loc[noise_cmp["within_pair_sd"].idxmin(), "control"]
    sharper = noise_cmp.loc[noise_cmp["best_vs_rest_rbc"].abs().idxmax(), "control"]
    print(f"\nLower within-(strat, imp) SD : {quieter}")
    print(f"Larger best-vs-rest effect   : {sharper}")
    if quieter == sharper:
        print(f"=> quote the {quieter} margin in the manuscript.")
    else:
        print("=> the two readings disagree; report both margins and say so.")

    fig, axes = plt.subplots(1, 3, figsize=(8.4, 2.8))
    # A  distribution of each margin
    long = d[[c for c, _ in PAIR]].melt(var_name="metric", value_name="margin").dropna()
    long["control"] = long["metric"].map(dict((c, l) for c, l in PAIR))
    sns.violinplot(data=long, x="control", y="margin", ax=axes[0],
                   palette=[COL_BEST, COL_HK], cut=0, inner="quartile")
    axes[0].set_title("A  Margin distribution", loc="left")
    axes[0].set_xlabel(""); axes[0].tick_params(axis="x", labelrotation=15)
    # B  within-pair SD side by side
    axes[1].bar(noise_cmp["control"], noise_cmp["within_pair_sd"],
                color=[COL_BEST, COL_HK], width=0.6)
    axes[1].set_title("B  Within-(strat, imp) SD", loc="left")
    axes[1].tick_params(axis="x", labelrotation=15)
    # C  agreement between the two margins
    sub = d[[c for c, _ in PAIR]].dropna()
    axes[2].scatter(sub.iloc[:, 0], sub.iloc[:, 1], s=3, alpha=0.35, color=COL_REST)
    lim = [float(sub.min().min()), float(sub.max().max())]
    axes[2].plot(lim, lim, ls="--", lw=0.8, color="k")
    r = sub.corr(method="spearman").iloc[0, 1]
    axes[2].set_xlabel("full housekeeping"); axes[2].set_ylabel("PGK1 only")
    axes[2].set_title(f"C  Agreement, $\\rho$ = {r:.2f}", loc="left")

    fig.tight_layout()
    save_figure(fig, "fig5f_hk_control_comparison", FIG_DIR)
    plt.show()
elif NARROW:
    print("Both narrow margins are needed for the comparison — "
          f"found {[c for c, _ in PAIR]}.")
```

`display` is already used elsewhere in the notebook; `mannwhitneyu` is already imported
in the setup cell.

#### 7j. Export section §9 (line 880–917)

**Before:**
```python
SUPP_DIR = FIG_DIR / "supplementary_file_5"
```

**After:**
```python
SUPP_DIR = FIG_DIR / f"supplementary_file_5{MK_SFX}"
```

and add the narrow gene list to `exports`:

```python
if NARROW:
    exports["S5_8_narrow_panel_genes.csv"] = marker_ann.loc[
        marker_ann["in_narrow_set"],
        ["gene", "gene_group", "cell_type", "is_housekeeping"]]
    if "noise_cmp" in globals():
        exports["S5_9_hk_control_noise_comparison.csv"] = noise_cmp
```

#### 7k. Module docstring and the `main()` print

Document both invocations at the top of the file:

```
    python create_correlation_prediction_notebook.py
    python create_correlation_prediction_notebook.py --narrow-set --date-tag 260905
```

---

### 8. `harmonization-metrics/correlation_prediction_metrics_analysis_narrow_set.ipynb` (new, generated)

Produced by `python create_correlation_prediction_notebook.py --narrow-set --date-tag <tag>`.
Not hand-edited, per the directory's standing rule. The existing
`correlation_prediction_metrics_analysis.ipynb` is regenerated too, and must come out
functionally identical (the only diff is the `save_figure`/`mk_cols`/`SUPP_DIR`
plumbing, which resolves to today's behaviour when `MK_SFX == ""`).

---

### 9. Documentation

#### 9a. `harmonization-metrics-calculation/CLAUDE.md`

- **Metric groups table, Group L row** — before:
  `| L — Marker correlation | mk_rho_mean_all_genes, mk_rho_by_gene, mk_rho_marker_minus_hk, mk_n_panel_genes_used | Fast; **needs the raw reference** | Yes |`
  after: add `… plus the same aggregates over the 56-gene narrow panel, suffixed
  \`_narrow_set\`` and keep the rest.
- **Group L paragraph** ("**Group L** requires the raw reference …") — add a paragraph on
  the two families, the one-pass/two-reductions design, and the housekeeping-control
  decision.
- **`marker_gene_annotation.csv` row in the file table** — 834 rows, 633 genes, 63
  groups, 15 housekeeping; add "**56 `in_narrow_set`**" and the new column name.
- **`marker_panels.py` row** — add `narrow_set_genes()` to the listed accessors.
- **Group L paragraph** — record that the narrow family carries **two**
  marker-minus-housekeeping margins (full housekeeping panel and `PGK1` only), why
  (only 6 of 15 housekeeping genes clear the narrow coverage bar), and that
  `mk_n_hk_genes_used_narrow_set` is the audit column for the first one.
- **Key design patterns → Incremental computation** — document that a sentinel may be a
  tuple and that Group L now carries two, so the narrow family resumes without
  `--force-groups`.
- **Commands block** — add the Group L narrow recompute command (see §Verification).

#### 9b. `harmonization-metrics-calculation/README.md`

New sub-step after "Step 10f — Force-recompute a single group with different parameters":
**Step 10g — Add the Group L narrow-panel aggregates**, with the run command, the
`--skip-wm` note, the reference-cache reminder, and the "do not pass `--skip-if-exists`"
warning that the neighbouring steps already carry.

#### 9c. `harmonization-metrics/CLAUDE.md`

- Commands block: add
  `python create_correlation_prediction_notebook.py --narrow-set --date-tag <tag>`.
- File-roles table: new row for
  `correlation_prediction_metrics_analysis_narrow_set.ipynb` — noting its §3b
  housekeeping-control noise comparison (`fig5f_hk_control_comparison_narrow_set`,
  `T5f_hk_control_noise_comparison_narrow_set.csv`) — and a note on the `--narrow-set`
  flag in the generator's row.
- `metric_tables/metrics_comprehensive_260824.csv` row: "(15 `mk_`, 24 `xb_`, 38 `pv_`
  columns)" → note that snapshots after the narrow run carry **30** `mk_` columns.

#### 9d. `project_overview.md`

- §4b table, Group L row: add the narrow family sentence.
- "**Excluded from the clustermap**" paragraph: "~65 new scalar columns" → ~80; the
  `scoring_cols` = 87 and 2,234-row statements stay true and should be reaffirmed.
- "**Gene panel**" paragraph: add the narrow-set definition, the 56/193 counts, the two
  housekeeping controls, and the finding that only 6 of the 15 housekeeping genes are
  present in all 42 raw pairs (`ACTB` and `GAPDH` among the nine that are not) — which
  is why the control-set choice is measured rather than assumed.

#### 9e. Root `CLAUDE.md`

- Key-files table, `marker_gene_annotation.csv` row: append "plus the 56-gene
  `in_narrow_set` QC-filtered subset behind the Group L `_narrow_set` metrics".
- Key-files table: new row for the narrow-set blind-check notebook.
- "Next steps — Article 1": add the narrow-panel Group L recompute + notebook as a
  checklist item under the blind check.

---

## Files that do NOT need to change

| File | Why not |
|---|---|
| `run_metrics_parallel.py` | The narrow family is inside Group L and reads the panel from the CSV, so no new flag and no new forwarding. `--groups L` already reaches the worker. |
| `run_metrics_concat.py` | All 15 new keys are scalars, so they flow into `metrics_comprehensive.csv` automatically. No new nested-dict key, hence no new long table and no `_split_nested` change. `_drop_remaining_containers` has nothing to drop (asserted by a test in §6b). |
| `figures_for_article/figure_drawing_scripts/figures_helpers.py` | `_BLIND_CHECK_PREFIXES = ("mk_", …)` already excludes every `mk_*_narrow_set` column from `metric_cols`, `scoring_cols`, the clustermap and the composite score, and the existing leak assertion covers them. `load_new_metrics_data()` picks them up by prefix with no edit. |
| `create_v3_notebook.py` / `harmonization_metrics_analysis_v3.ipynb` | A–K only. Unknown prefixes get polarity 0 and are dropped from `scoring_cols`; `scoring_cols` stays at 87. |
| `create_marker_gene_deep_analysis_notebook.py` | This notebook is where the narrow set was *derived* (`COVERAGE_SCOPE="raw_all_pairs"` + the `frac_lt_1` gate). A `_narrow_set` variant of it would be circular. Optional, low-priority addition noted in the TODO: one print cell comparing its live gate output against the committed `in_narrow_set` flag, as a provenance record. Not an assertion — the notebook's gate also applies `zero_frac` and `detection_frac` thresholds, so the two sets need not match exactly. |
| `gene_panel_analysis/*` | Writes its own S3 prefixes and tables, adds no `metrics_comprehensive.csv` column, and never calls `compute_all_metrics()`. It is the *source* of the QC that defined the narrow set, not a consumer. |
| `compute_group_m` / `compute_group_n` | Out of scope (see Background). Group M keeps using the full panel via the unchanged `panel` argument. |
| `k8s/pod-metrics.yaml`, `requirements.txt` | No new dependency. |

---

## Side effects and caveats

1. **A compute run is required before the columns exist.** Recommended scope — the same
   2,323 non-Shambhala attempts as the original blind check:
   ```bash
   nohup python run_metrics_parallel.py \
       --groups L --skip-wm --only-with-metrics --skip-shambhala \
       --n-workers 20 --memory-limit-gb 8.0 --timeout-s 1800 \
       --ref-cache-dir /workspace/ref_cache \
       > /workspace/metrics_l_narrow.log 2>&1 &
   ```
   - **Do not pass `--skip-if-exists`** — every target job already has a sidecar and
     would be skipped wholesale. The second sentinel is the resume mechanism.
   - **`--force-groups` is not needed** and should not be used: the sentinel handles it,
     and forcing would also re-run jobs that are already done if the run is restarted.
   - **Pass `--skip-wm`.** Without it the worker adds Group I to the requested set
     (`if not args.skip_wm: requested_groups.add("I")`); harmless for jobs that already
     have `wm_RNA_BATCH`, but it would compute a 2–5 min WaterMelon score on any job
     that does not.
2. **The Group L reference cache is needed again** — `/workspace/ref_cache`, 42
   `(strat, imp)` pairs, ~12.8 GB. If the PVC no longer has it, the run re-downloads it.
   Groups M and N are untouched by this plan and need no reference.
3. **Runtime estimate:** Group L itself is unchanged in cost (one extra masked mean per
   cohort), so the run is dominated by downloading each harmonized matrix — roughly
   1–3 min per job, so about **2–4 h at 20 workers** for 2,323 jobs. No timeout risk at
   `--timeout-s 1800`.
4. **The long tables are re-uploaded but must not change.** `mk_rho_by_gene` and
   `mk_rho_by_cohort` stay restricted to the requested panel (§4d), and with the default
   panel the union adds nothing (all 15 housekeeping genes and all 56 narrow genes are
   already in the 633-gene table). Verify with a diff of the regenerated
   `marker_gene_correlations_long_*.csv` against `..._260826.csv` — it should be
   identical apart from row order. **If it is not, stop and investigate before touching
   the notebooks:** it would mean the union changed the panel resolution.
5. **`metrics_comprehensive.csv` gains 15 columns; `mk_` goes 15 → 30.** The doc counts
   in `harmonization-metrics/CLAUDE.md` and `project_overview.md` go stale if not
   updated (§9). `scoring_cols` stays **87** and the analysis set **2,234** rows — both
   are asserted in the notebooks, and those assertions are the guard that this stayed
   true.
6. **`marker_gene_annotation.csv` gains a column, and that file is exported as
   Supplementary File 5 sheet S5_5.** The published supplementary table will therefore
   carry `in_narrow_set`. That is desirable documentation, but it is a change to a file
   already sent to co-authors — flagging it rather than assuming.
7. **Shambhala attempts get no narrow metrics** under `--skip-shambhala` (1,512 of the
   3,835 sidecars). Consistent with the blind check's existing scope and with Shambhala's
   exclusion from Article 1. The one canonical representative
   (`shambhala_P0std_Q0std`) that the notebook renames to `20_shambhala` would show NaN
   narrow columns — drop `--skip-shambhala` if that row matters, or accept the NaN.
8. **The narrow notebook's `DATE_TAG` must point at a post-run snapshot.** Generated with
   the default `260824` it will find no narrow columns and fall back to the long-table
   aggregates (§7h) — correct numbers for eleven of the fifteen metrics, including both
   margins, but `mk_rho_mean_by_cohort_mean_narrow_set` and the three coverage counters
   will be absent. Regenerate with the real tag once the concat has run.
9. **`mk_rho_mean_housekeeping_narrow_set` duplicates `mk_rho_mean_housekeeping`** by
   construction under the default panel. Deliberate (see Background); it keeps the
   `_narrow_set` family self-contained for column selection and export. Worth one
   sentence in the manuscript methods so a reader does not read it as an independent
   measurement. `mk_rho_mean_PGK1_only_narrow_set` does **not** duplicate anything.
10. **Two margins means the manuscript has to pick one — and say why.** §3b of the narrow
    notebook decides it on within-`(strat, imp)` dispersion and best-vs-rest effect size,
    and writes `T5f_hk_control_noise_comparison_narrow_set.csv`. If the two readings
    disagree, both margins get reported and the disagreement stated; do not quietly quote
    whichever looks better. Note also that the `PGK1`-only margin is NaN in the ~2 % of
    attempts where `PGK1` does not resolve, so the comparison is pairwise-complete only
    on the intersection — the notebook drops those rows via `.dropna()` rather than
    comparing different row sets.
11. **The committed full-panel notebook has diverged from its generator — do not
    regenerate it blindly.** Found during implementation: the committed
    `correlation_prediction_metrics_analysis.ipynb` holds **40** cells while the
    generator emits 29 (32 after this change). Eight of those cells exist only in the
    committed file, including hand-added working notes ("We fit PCA on the training split,
    then refit it on the test split. That is too harsh...", "TODO: replace this heatmap with
    a clustermap annotated by gene set...", "Investigate how strongly the genes correlate
    with one another...") and small exploratory cells (`len(gl.gene.unique())`,
    a `piv = ...` heatmap draft). Regenerating overwrites them. The full-panel notebook was
    therefore **left at its committed state**: every generator edit in §7 is inert when
    `MK_SFX == ""` and the two new sections are `NARROW`-guarded, so the full-panel
    notebook loses nothing by not being regenerated. Before it is ever regenerated, those
    eight cells must be ported into the generator — that is a separate decision for
    Daniil, not part of this change.
12. **No cache to invalidate on the harmonization side.** This plan touches no filter
    strategy, so `/tmp/bench_filter_strategies.pkl` is irrelevant. But
    `load_marker_annotation()` is `lru_cache`d — an interactive session that already
    imported `marker_panels` before the CSV was regenerated will keep serving the old
    table. Restart the kernel or the worker process, never just re-run the cell.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd /Users/user890/Desktop/Follicular_lymphoma_disser/harmonization-metrics-calculation

# 1. Regenerate the panel CSV and confirm the new column
python build_marker_gene_annotation.py
#   expect: unique genes 633 | housekeeping genes 15 | narrow-set genes 56
#           housekeeping in narrow: ['PGK1']   <- the assertion behind the metric name

python -c "
import pandas as pd
df = pd.read_csv('marker_gene_annotation.csv')
print('cols:', df.columns.tolist())
print('narrow genes:', df.loc[df.in_narrow_set, 'gene'].nunique())
print('narrow rows :', int(df.in_narrow_set.sum()))
print('narrow ∩ hk :', sorted(set(df.loc[df.in_narrow_set & df.is_housekeeping, 'gene'])))
"
#   expect: 56 genes, 86 rows, ['PGK1']

# 2. Loader
python -c "
import marker_panels as mp
n = mp.narrow_set_genes()
print(len(n), n[:6])
print('subset of panel:', set(n) <= set(mp.panel_genes(include_housekeeping=True)))
"
#   expect: 56, True

# 3. Smoke tests — all assertions must pass (169 + the new ones)
python test_mock_metrics.py

# 4. One real job, Group L only (inside the pod, reference cache present)
python run_metrics_job.py \
    --strat C_rnaseq_only --imp softimpute --method 10_mnn --post-rm False \
    --groups L --skip-wm True \
    --out-json /tmp/l.json --out-genes-json /tmp/g.json \
    --ref-cache-dir /workspace/ref_cache

python -c "
import json
d = json.load(open('/tmp/l.json'))
narrow = {k: v for k, v in d.items() if k.endswith('_narrow_set')}
print(len(narrow), 'narrow keys')
for k in sorted(narrow):
    print(f'  {k:48s} {narrow[k]}')
print('full  mean rho :', d['mk_rho_mean_all_genes'])
print('narrow mean rho:', d['mk_rho_mean_all_genes_narrow_set'])
# the narrow family must be a re-aggregation of the same per-gene values
import numpy as np, pandas as pd
ann = pd.read_csv('marker_gene_annotation.csv')
nset = set(ann.loc[ann.in_narrow_set, 'gene'])
sub = [v for g, v in d['mk_rho_by_gene'].items() if g in nset and v is not None]
print('recomputed from mk_rho_by_gene:', float(np.mean(sub)))
assert abs(float(np.mean(sub)) - d['mk_rho_mean_all_genes_narrow_set']) < 1e-9
print('OK: narrow aggregate matches the per-gene subset')
# the two housekeeping controls
print('hk genes used  :', d['mk_n_hk_genes_used_narrow_set'])
print('hk control     :', d['mk_rho_mean_housekeeping_narrow_set'])
print('PGK1 control   :', d['mk_rho_mean_PGK1_only_narrow_set'])
print('margin vs hk   :', d['mk_rho_marker_minus_hk_narrow_set'])
print('margin vs PGK1 :', d['mk_rho_marker_minus_PGK1_only_narrow_set'])
assert abs(d['mk_rho_mean_PGK1_only_narrow_set'] - d['mk_rho_by_gene']['PGK1']) < 1e-12
print('OK: PGK1-only control equals PGK1 own rho')
"
#   expect: 15 narrow keys, mk_n_panel_genes_used_narrow_set == 56, both assertions pass

# 5. Resume semantics — the sentinel must schedule L, then stop
python -c "
from run_metrics_job import _groups_to_recompute, GROUP_SENTINEL_KEYS
old = {'mk_rho_mean_all_genes': 0.99, 'status': 'ok'}
new = dict(old, mk_rho_mean_all_genes_narrow_set=0.98)
print('L on old sidecar:', _groups_to_recompute(old, {'L'}))
print('L on new sidecar:', _groups_to_recompute(new, {'L'}))
print('L sentinels:', GROUP_SENTINEL_KEYS['L'])
"
#   expect: {'L'} then set()

# 6. Full run (pod) — see caveat 1 for the flags
nohup python run_metrics_parallel.py \
    --groups L --skip-wm --only-with-metrics --skip-shambhala \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 1800 \
    --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_l_narrow.log 2>&1 &

# 7. Aggregate, then check the column count and long-table stability
python run_metrics_concat.py --out-dir ../harmonization-metrics/metric_tables --date-tag 260905

python -c "
import pandas as pd
d = '../harmonization-metrics/metric_tables/'
df = pd.read_csv(d + 'metrics_comprehensive_260905.csv', low_memory=False)
mk = [c for c in df.columns if c.startswith('mk_')]
nar = [c for c in mk if c.endswith('_narrow_set')]
print('mk cols:', len(mk), '| narrow:', len(nar))
print('rows with narrow metrics:', int(df['mk_rho_mean_all_genes_narrow_set'].notna().sum()))
print(df[['mk_n_panel_genes_used_narrow_set', 'mk_n_hk_genes_used_narrow_set']].describe().T)
# first look at the question the two margins exist to answer
m = ['mk_rho_marker_minus_hk_narrow_set', 'mk_rho_marker_minus_PGK1_only_narrow_set']
ok = df[df.status == 'ok']
print(ok[m].agg(['count', 'mean', 'std']).T)
print('within-(strat,imp) SD:')
print(ok.groupby(['strat', 'imp'])[m].std().mean())
"
#   expect: 30 mk cols, 15 narrow, ~2,323 rows populated, n_panel_genes 50-56,
#           n_hk_genes 6-15 (the variable-composition control of caveat 10)

python -c "
import pandas as pd
d = '../harmonization-metrics/metric_tables/'
a = pd.read_csv(d + 'marker_gene_correlations_long_260826.csv')
b = pd.read_csv(d + 'marker_gene_correlations_long_260905.csv')
k = ['run_id', 'gene']
m = a.merge(b, on=k, suffixes=('_old', '_new'), how='outer', indicator=True)
print(m['_merge'].value_counts().to_dict())
both = m[m._merge == 'both']
print('max |rho diff|:', (both.rho_old - both.rho_new).abs().max())
"
#   expect: both == all rows, max diff 0.0 (caveat 4)

# 8. Regenerate both notebooks
cd ../harmonization-metrics
python create_correlation_prediction_notebook.py
python create_correlation_prediction_notebook.py --narrow-set --date-tag 260905
git diff --stat correlation_prediction_metrics_analysis.ipynb
#   expect: the full-panel notebook changes only in the save_figure / mk_cols /
#   SUPP_DIR plumbing cells; the narrow notebook is new

# 9. Read the answer to the housekeeping-control question out of §3b
python -c "
import pandas as pd
t = pd.read_csv('../figures_for_article/current_figures_tables_for_article_260819/'
                'T5f_hk_control_noise_comparison_narrow_set.csv')
print(t.round(4).to_string(index=False))
"
#   the control with the lower within_pair_sd and the larger |best_vs_rest_rbc| is the
#   margin to quote; if they disagree, report both (caveat 10)
```

---

## TODO

### Panel source of truth
- [x] `build_marker_gene_annotation.py` — add the `in_narrow_set` provenance paragraph to the module docstring (§1a)
- [x] `build_marker_gene_annotation.py` — add the `NARROW_SET_GENES` frozenset with its selection-criteria comment near line 60 (§1b)
- [x] `build_marker_gene_annotation.py` — emit `"in_narrow_set"` in `build()` (§1c)
- [x] `build_marker_gene_annotation.py` — add the absent-gene assertion, the `narrow ∩ housekeeping == {PGK1}` assertion that keeps the metric name honest, and both count prints to `main()` (§1d)
- [x] Run `python build_marker_gene_annotation.py`; confirm 633 genes / 15 housekeeping / 56 narrow / housekeeping-in-narrow `['PGK1']`; commit the regenerated `marker_gene_annotation.csv` (§2) — 834 rows × 11 cols, identical to the previous CSV apart from the new column; 86 narrow rows, not the 58 estimated above

### Loader
- [x] `marker_panels.py` — docstring sentence on the two gene-level flags (§3a)
- [x] `marker_panels.py` — guarded `in_narrow_set` bool cast in `load_marker_annotation()` + `Returns` update (§3b)
- [x] `marker_panels.py` — add `narrow_set_genes()` after `housekeeping_genes()` (§3c)

### Metric library
- [x] `compute_batch_metrics.py` — module docstring Group L line (§4a)
- [x] `compute_batch_metrics.py` — import `narrow_set_genes` (§4b)
- [x] `compute_batch_metrics.py` — add `NARROW_SET_SUFFIX`, `_MK_AGG_KEYS` and `_MK_NARROW_ONLY_KEYS` constants (§4b)
- [x] `compute_batch_metrics.py` — add the `_mk_rho_aggregates()` helper (§4c)
- [x] `compute_batch_metrics.py` — `compute_group_l()` signature + docstring: `narrow_panel` (§4d)
- [x] `compute_batch_metrics.py` — resolve narrow + housekeeping panels, union into `genes_all`, emit the four narrow coverage counters and the empty-panel warning (§4d)
- [x] `compute_batch_metrics.py` — zero-gene fallback emits both families via `_MK_AGG_KEYS` plus `_MK_NARROW_ONLY_KEYS` (§4d)
- [x] `compute_batch_metrics.py` — build `A`/`B` on `genes_all`; add `panel_mask` / `narrow_mask` / `hk_mask` (§4d)
- [x] `compute_batch_metrics.py` — cohort loop: accumulate `per_cohort_narrow`; restrict `detail` to `panel_mask` (§4d)
- [x] `compute_batch_metrics.py` — restrict `mk_rho_by_gene` / `mk_rho_n_cohorts_by_gene` to `panel_mask` (§4d)
- [x] `compute_batch_metrics.py` — replace the inline aggregate block with the two `_mk_rho_aggregates()` calls (§4d)
- [x] `compute_batch_metrics.py` — add the coverage-matched `mk_rho_mean_PGK1_only_narrow_set` / `mk_rho_marker_minus_PGK1_only_narrow_set` block after the narrow reduction (§4d)
- [x] `compute_batch_metrics.py` — `compute_all_metrics()`: `narrow_panel` parameter, docstring entry, and pass-through in the Group L dispatch (§4e)

### Worker
- [x] `run_metrics_job.py` — `GROUP_SENTINEL_KEYS` type widened to `str | tuple[str, ...]`; Group L gets both keys; explanatory comment (§5a)
- [x] `run_metrics_job.py` — `_groups_to_recompute()` handles tuple sentinels (§5b)
- [x] `run_metrics_job.py` — module docstring: the narrow resume example (§5c)

### Tests
- [x] `test_mock_metrics.py` — extend imports (§6a)
- [x] `test_mock_metrics.py` — `_make_panel_data()` gains an optional `panel` argument (§6b)
- [x] `test_mock_metrics.py` — add `test_group_l_narrow_set()`, including the `PGK1`-only decomposition check and the drop-`PGK1` asymmetry check (§6b)
- [x] `test_mock_metrics.py` — extend `test_incremental_groups_to_recompute()` with the two-sentinel cases (§6c)
- [x] `test_mock_metrics.py` — extend `test_lmn_in_compute_all()` expected keys (§6d)
- [x] `test_mock_metrics.py` — register the new test in `__main__` (§6e)
- [ ] Run `python test_mock_metrics.py` — every assertion passes *(requires the venv/pod: this Mac has no scipy/sklearn/umap, so the module cannot be imported here. The new `test_group_l_narrow_set`, the extended `test_group_l_missing_panel_genes` and `test_incremental_groups_to_recompute` were all run locally under a stub harness — 30 + 6 + 13 checks, all PASS)*

### Notebook generator
- [x] `create_correlation_prediction_notebook.py` — module docstring: both invocations (§7k)
- [x] `create_correlation_prediction_notebook.py` — `argparse` variant switch, `NARROW` / `SFX` / `OUTPUT` / `DATE_TAG` (§7a)
- [x] `create_correlation_prediction_notebook.py` — title markdown variant note (§7b)
- [x] `create_correlation_prediction_notebook.py` — setup cell `NARROW` / `MK_SFX` constants and suffix inside `save_figure()` (§7c)
- [x] `create_correlation_prediction_notebook.py` — split `mk_cols` by the `_narrow_set` suffix (§7d)
- [x] `create_correlation_prediction_notebook.py` — move the `marker_ann` load above the gene-set filter; add the narrow gene-set branch (§7e)
- [x] `create_correlation_prediction_notebook.py` — suffix the `HEADLINE` Group L columns and add the `PGK1`-only margin panel (§7f)
- [x] `create_correlation_prediction_notebook.py` — suffix the §5 coverage column (§7g)
- [x] `create_correlation_prediction_notebook.py` — add the wide-vs-long cross-check / fallback cell at the **end of §1** (before §2's figure and §3b), deriving both margins from the long table (§7h)
- [x] `create_correlation_prediction_notebook.py` — add §3b: the housekeeping-control noise comparison (markdown + code cell, `fig5f_hk_control_comparison`, `T5f_hk_control_noise_comparison.csv`) (§7i)
- [x] `create_correlation_prediction_notebook.py` — suffix `SUPP_DIR`; add the `S5_8_narrow_panel_genes.csv` and `S5_9_hk_control_noise_comparison.csv` exports (§7j)
- [x] Regenerate `correlation_prediction_metrics_analysis.ipynb`; confirm the diff is plumbing-only — **deliberately not applied.** Generator-to-generator diff confirmed plumbing-only (29 → 32 cells: the 3 additions are the cross-check cell and the two §3b cells), but the *committed* notebook carries 8 hand-added cells the generator does not produce, Daniil's Russian notes among them, so it was restored to its committed state instead of overwritten (caveat 11)
- [x] Generate `correlation_prediction_metrics_analysis_narrow_set.ipynb` (§8)

### Compute run
- [ ] *(requires live pod)* rsync `harmonization-metrics-calculation/` to the pod **as a whole directory** (a `*.py` glob would leave the regenerated `marker_gene_annotation.csv` behind — and that CSV *is* the change)
- [ ] *(requires live pod)* Confirm `/workspace/ref_cache` still holds the 42 reference matrices (~12.8 GB), or budget the re-download
- [ ] *(requires live pod)* Single-job check (Verification step 4) before the fan-out
- [ ] *(requires live pod)* Launch the Group L recompute with `--groups L --skip-wm --only-with-metrics --skip-shambhala`, no `--skip-if-exists`, no `--force-groups`
- [ ] *(requires live pod)* `run_metrics_concat.py --out-dir ../harmonization-metrics/metric_tables --date-tag <YYMMDD>`
- [ ] *(requires live pod)* Verify 30 `mk_` columns and ~2,323 populated rows (Verification step 7)
- [ ] *(requires live pod)* Verify the long tables are unchanged against `..._260826.csv` (caveat 4) — **stop if they differ**
- [ ] *(after the pod run)* Regenerate the narrow notebook with the real `--date-tag` — generated now against `--date-tag 260905` as a placeholder; the cross-check cell falls back to long-table aggregates until the snapshot exists
- [ ] *(after the pod run)* Run §3b and record which housekeeping control is less noisy (Verification step 9); if the two readings disagree, note that both margins must be reported

### Documentation
- [x] `harmonization-metrics-calculation/CLAUDE.md` — Group L row in the metric-groups table (§9a)
- [x] `harmonization-metrics-calculation/CLAUDE.md` — Group L paragraph: the two families, the two housekeeping controls, and the 6-of-15 coverage finding (§9a)
- [x] `harmonization-metrics-calculation/CLAUDE.md` — `marker_gene_annotation.csv` and `marker_panels.py` file-table rows (§9a)
- [x] `harmonization-metrics-calculation/CLAUDE.md` — Incremental computation pattern: tuple sentinels (§9a)
- [x] `harmonization-metrics-calculation/CLAUDE.md` — commands block: the narrow recompute command (§9a)
- [x] `harmonization-metrics-calculation/README.md` — new "Step 10g" (§9b)
- [x] `harmonization-metrics/CLAUDE.md` — commands block, file-roles rows, `mk_` column count (§9c)
- [x] `project_overview.md` — §4b Group L row, the excluded-columns count, the gene-panel paragraph (§9d)
- [x] Root `CLAUDE.md` — key-files rows and the Article 1 checklist item (§9e)
- [ ] *(Optional, low priority)* `create_marker_gene_deep_analysis_notebook.py` — one print cell comparing its live coverage+QC gate against the committed `in_narrow_set` flag, as a provenance record (not an assertion)
