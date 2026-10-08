"""Metric-class cross-election analysis for Article 2 (F1000Research).

Every number quoted in Results sections 6-8 is produced here. Run standalone to
reproduce the tables; import `load_analysis_set`, `elect`, `generalizability_index`
from the notebook generators so the notebooks and the manuscript cannot diverge.

    source ~/venvs/collagen_3_11/bin/activate
    cd article_2_extended_comparison
    python analysis/article2_generalizability.py --date-tag 260905 --out-dir tables/

Polarity for the Article 1 metric classes is taken from
`figures_for_article/figure_drawing_scripts/figures_helpers.py`, the module Article 1's
own figures use. Re-deriving it here would create a second answer to "is a high kBET
good", and the two would drift. Polarity for groups L, M and N is declared below,
because figures_helpers deliberately excludes them (they are the blind check, kept out
of the clustermap and the composite score).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import (binomtest, chisquare, fisher_exact, hypergeom, kruskal,
                         mannwhitneyu, spearmanr, wilcoxon)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

METRICS_CSV = "../harmonization-metrics/metric_tables/metrics_comprehensive_{tag}.csv"
SUPP_FILE_3 = "../figures_for_article/supplementary_260824/Supplementary File 3.csv.gz"
FOLDS_CSV = "../harmonization-metrics/metric_tables/prediction_folds_long_260826.csv"
# Article 1's metric registry, the authority for the 344 / 334 / 87 census (plan §B5).
SUPP_FILE_2 = "../figures_for_article/supplementary_260824/Supplementary File 2.xlsx"

KEY = ["strat", "imp", "method", "post_rm"]

RHO_GATE = 0.75   # Group L: necessary, not sufficient (Daniil, 2026-09-18)

# The metric snapshots store Shambhala as 18 P/Q variants; Article 1 kept one
# canonical representative and renamed it. These are the SAME method.
SHAMBHALA_CANONICAL = "shambhala_P0std_Q0std"   # == 20_shambhala

N_APPROACHES = 2234
N_METHODS = 31

# The 15 approaches Article 1's clustermap elected, as (method, imp, strat) at
# post_rm = False. Copied from correlation_prediction_metrics_analysis.ipynb cell 8,
# which took them from harmonization_metrics_analysis_v3.ipynb.
CLUSTERMAP_BEST = [
    ("10_mnn", "strict", "S0_no_removal"),
    ("10_mnn", "strict", "H_affymetrix_extended"),
    ("10_mnn", "strict", "D_malignant_only"),
    ("04_sva", "knn", "C_rnaseq_only"),
    ("04_sva", "softimpute", "C_rnaseq_only"),
    ("16_fsqn_r", "knn", "C_rnaseq_only"),
    ("16_fsqn_r", "softimpute", "C_rnaseq_only"),
    ("16_fsqn_r", "strict", "C_rnaseq_only"),
    ("10_mnn", "strict", "J_ff_only"),
    ("16_fsqn_r", "strict", "J_ff_only"),
    ("04_sva", "knn", "K_ffpe_only"),
    ("04_sva", "strict", "K_ffpe_only"),
    ("04_sva", "softimpute", "K_ffpe_only"),
    ("13_fsmvn", "strict", "S0_no_removal"),
    ("33_amdbnorm", "strict", "S0_no_removal"),
]

CONFOUNDED_STRATS = ("A_confirmed_bad", "B_extended_bad")

# Method-level harshness, from Finally_assembled_figures_for_article.ipynb cell 4.
# This is HARSHNESS_LEVEL_MAP (methods), NOT HARSHNESS_MAP (strategies), and it is a
# different quantity from the disputed composite ordering of plan §9.6.
HARSHNESS_LEVEL_MAP = {
    "01_raw": "low", "02_median_scaling": "low", "03_limma": "low", "04_sva": "low",
    "05_combat": "medium", "06_combat_seq": "medium", "07_pycombat": "medium",
    "08_inmoose_combatseq": "medium", "09_ruv": "medium", "10_mnn": "medium",
    "11_harmony": "medium", "12_scanorama": "medium", "13_fsmvn": "medium",
    "14_qsmooth": "high", "15_fsqn_py": "high", "16_fsqn_r": "high",
    "17_quantile": "high", "18_rank": "high", "19_tdm": "high", "20_shambhala": "high",
    "21_harmonizr": "medium", "22_tmm": "low", "23_vst": "low", "24_peer_k10": "medium",
    "25_angel": "high", "26_xpn": "high", "27_dwd": "medium", "28_npn": "high",
    "29_combat_ref": "medium", "30_recombat": "medium", "31_ruv3prps": "medium",
    "32_deepmnn": "medium", "33_amdbnorm": "high", "34_arsyn": "medium",
    "35_dasc": "medium", "36_explobatch": "medium", "37_fabatch": "medium",
    "38_harman": "medium", "39_procrustes": "high",
}

# Metric classes, expressed as the column prefixes of Article 1's own group letters
# (figures_helpers._GROUP_MAP). A class is a set of letters so the mapping from
# "what a reader calls a metric class" to "which columns" is written out once.
METRIC_CLASS_PREFIXES = {
    "global": ("r2_", "pcr_", "dsc_", "pct_var_pc", "pct_var_cum"),
    "local": ("kbet_", "ilisi_", "clisi_", "asw_batch", "asw_bio", "cms_", "graph_"),
    "distributional": ("ks_", "per_gene_batch"),
    "structural": ("umap_", "tsne_", "avg_intra_", "avg_inter_", "dist_ratio_", "wm_"),
    "L": ("mk_",),
    "M": ("xb_",),
    "N": ("pv_",),
}

# Polarity for groups L, M and N. figures_helpers excludes these prefixes on purpose,
# so the blind-check metrics never reach Article 1's composite score; the article still
# needs to know which direction is better.
LMN_POLARITY_RULES = [
    ("mk_rho_", +1), ("mk_panel_coverage_frac", +1),
    ("xb_rank_disagree", -1), ("xb_rank_agree", +1),
    ("pv_lobo2_f1_perm_pvalue", -1), ("pv_lobo3_f1_perm_pvalue", -1),
    ("pv_lobo2_auc", +1), ("pv_lobo3_auc", +1),
    ("pv_lobo2_f1_macro_mean", +1), ("pv_lobo3_f1_macro_mean", +1),
    ("pv_lobo2_f1_macro_median", +1), ("pv_lobo3_f1_macro_median", +1),
    ("pv_lobo2_f1_macro_min", +1), ("pv_lobo3_f1_macro_min", +1),
    ("pv_lobo2_f1_weighted_mean", +1), ("pv_lobo3_f1_weighted_mean", +1),
    ("pv_lobo2_mcc_mean", +1), ("pv_lobo3_mcc_mean", +1),
    ("pv_lobo2_bal_acc_mean", +1), ("pv_lobo3_bal_acc_mean", +1),
    ("pv_lobo2_f1_per_class", +1), ("pv_lobo3_f1_per_class", +1),
]

# Columns the generalizability index is built from, in the order plan §4.1 lists them.
# Revision 260924 (C16, plan E1): the 2-class component is macro F1, not macro AUC. The
# six components are averaged as rank percentiles, so they must measure the same thing;
# mixing an F1 with an AUC was the objection.
INDEX_COLUMNS = [
    "pv_lobo3_f1_macro_mean",   # prediction, 3-class, all folds
    "f1_mc_mean",               # prediction over multiclass folds only
    "pv_lobo2_f1_macro_mean",   # prediction, 2-class
    "mk_rho_mean_markers",      # biology preserved, Group L
    "xb_margin_delta",          # Group M gain over the raw baseline
    "f1_mc_min",                # worst true multiclass fold
]
# The definition the 260917 tables and the current manuscript text were built with. Kept so
# `--stamp 260917` still reproduces those tables exactly instead of overwriting them.
INDEX_COLUMNS_260917 = [
    "pv_lobo3_f1_macro_mean", "f1_mc_mean", "pv_lobo2_auc_macro_mean",
    "mk_rho_mean_markers", "xb_margin_delta", "f1_mc_min",
]
LEGACY_STAMP = "260917"

MIN_MC_FOLDS = 5    # below this the LOBO metric describes fold structure, not an approach


# ── polarity and scaling ──────────────────────────────────────────────────────

def article1_polarity(columns: list[str]) -> dict[str, int]:
    """Polarity for the Article 1 metric columns, from figures_helpers.

    Imported rather than reimplemented: figures_helpers is what produced Article 1's
    clustermap and composite score, so importing it is the only way the two papers can
    be guaranteed to agree on which direction of a metric is better.
    """
    sys.path.insert(0, str(REPO / "figures_for_article" / "figure_drawing_scripts"))
    import figures_helpers as fh

    return fh._build_polarity(list(columns))


def lmn_polarity(column: str) -> int:
    for prefix, sign in LMN_POLARITY_RULES:
        if column.startswith(prefix):
            return sign
    return 0


def rank_percentile(s: pd.Series, polarity: int) -> pd.Series:
    """Percentile rank in [0, 1], oriented so that 1 is always better.

    Rank rather than min-max because the columns have incompatible scales and Group L
    saturates at 1.0 by construction for any monotone per-gene transform.
    """
    if polarity == 0:
        return pd.Series(np.nan, index=s.index)
    return (s * polarity).rank(pct=True, na_option="keep")


# ── loading ───────────────────────────────────────────────────────────────────

def _canonicalize_shambhala(d: pd.DataFrame) -> pd.DataFrame:
    """Drop the 17 non-canonical P/Q variants and rename the representative.

    Must run before any filter or count, in every table that carries a method column --
    the metric snapshot AND prediction_folds_long.csv, which has the same 18 variants
    and zero rows named `20_shambhala`.
    """
    d = d[~d.method.str.startswith("shambhala_") | (d.method == SHAMBHALA_CANONICAL)].copy()
    d.loc[d.method == SHAMBHALA_CANONICAL, "method"] = "20_shambhala"
    return d


def load_analysis_set(supp3_path, metrics_path, pcreg_as_pcr: bool = True) -> pd.DataFrame:
    """Article 1's canonical 2,234-approach set, with L/M/N attached.

    Supplementary File 3 supplies the 87 Article 1 scoring metrics and the membership
    criterion; the metric snapshot supplies groups L, M and N, which Supplementary
    File 3 does not carry. Only the L/M/N columns are taken from the snapshot, so the
    two tables cannot disagree about a metric they both contain.

    The Shambhala rename happens FIRST, before any filter or count. Skipping it
    silently drops 84 approaches and yields 2,150 -- verified 2026-09-18 that the two
    names carry identical values on 78 of 79 shared numeric columns (the exception is
    compute_time_s, wall-clock, not a metric).

    Asserts len == 2234 and method.nunique() == 31; fails loudly if a snapshot changes
    underneath the manuscript.
    """
    supp3 = pd.read_csv(supp3_path)
    snap = _canonicalize_shambhala(pd.read_csv(metrics_path, low_memory=False))

    lmn_cols = [c for c in snap.columns if c.startswith(("mk_", "xb_", "pv_"))]
    canon = supp3[supp3.pct_samples_allNA < 5].copy()
    # Supplementary File 3 spells the seven PCReg columns `PCReg_<col>`; the snapshot,
    # METRIC_CLASS_PREFIXES and Article 1's polarity map all spell them `pcr_<col>`.
    # Left unrenamed they match no class prefix and carry polarity 0, so the global
    # class silently shrank to the 4 DSC columns (found 2026-09-25, plan Phase 3). The
    # values are identical (max |difference| 0). `pcreg_as_pcr=False` reproduces 260917.
    if pcreg_as_pcr:
        canon = canon.rename(columns={c: "pcr_" + c[len("PCReg_"):]
                                      for c in canon.columns if c.startswith("PCReg_")})
    df = canon.merge(snap[KEY + lmn_cols], on=KEY, how="left", validate="one_to_one")

    assert len(df) == N_APPROACHES, f"analysis set is {len(df)}, expected {N_APPROACHES}"
    assert df.method.nunique() == N_METHODS, f"{df.method.nunique()} methods, expected {N_METHODS}"
    assert (df.method == "20_shambhala").sum() == 84, "the Shambhala rename did not happen"
    assert not df.method.str.startswith("shambhala_").any(), "raw P/Q variant names leaked"

    df["run_id"] = (df.strat + "__" + df.imp + "__" + df.method
                    + "__post" + df.post_rm.astype(int).astype(str))
    df["harshness_level"] = df.method.map(HARSHNESS_LEVEL_MAP)
    best = set(CLUSTERMAP_BEST)
    df["is_clustermap_best"] = [
        (m, i, s) in best and not p
        for m, i, s, p in zip(df.method, df.imp, df.strat, df.post_rm)
    ]
    df["is_confirmed_bad"] = df.strat.isin(CONFOUNDED_STRATS)
    df["is_raw"] = df.method == "01_raw"
    return df.set_index("run_id", drop=False)


def shambhala_identity(supp3_path, metrics_path) -> pd.DataFrame:
    """Column-by-column check that `shambhala_P0std_Q0std` == `20_shambhala`.

    The rename is an assertion about the data, so it is published as a table rather
    than asked to be believed: one row per shared numeric column, with both medians and
    the maximum absolute difference over the 84 matched approaches.
    """
    supp3 = pd.read_csv(supp3_path)
    snap = pd.read_csv(metrics_path, low_memory=False)
    a = supp3[supp3.method == "20_shambhala"].set_index(["strat", "imp", "post_rm"])
    b = snap[snap.method == SHAMBHALA_CANONICAL].set_index(["strat", "imp", "post_rm"])
    shared_keys = a.index.intersection(b.index)
    a, b = a.loc[shared_keys], b.loc[shared_keys]

    rows = []
    for c in sorted(set(a.select_dtypes("number").columns)
                    & set(b.select_dtypes("number").columns)):
        d = (a[c] - b[c]).abs()
        rows.append({
            "column": c,
            "n_matched_keys": len(shared_keys),
            "median_20_shambhala": a[c].median(),
            "median_P0std_Q0std": b[c].median(),
            "max_abs_diff": d.max(),
            "identical": bool(d.fillna(0).max() < 1e-9),
        })
    out = pd.DataFrame(rows)
    n_same = int(out.identical.sum())
    print(f"  A2_T0: {len(shared_keys)} keys matched, "
          f"{n_same}/{len(out)} numeric columns identical "
          f"(differing: {out.loc[~out.identical, 'column'].tolist()})")
    return out


# ── derived metrics ───────────────────────────────────────────────────────────

def add_raw_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """Join the `01_raw` / post_rm=False baseline on (strat, imp).

    Adds `{metric}_raw` and `{metric}_delta` for every L/M/N column, matching
    create_correlation_prediction_notebook.py lines 358-376. The baseline is per
    (strat, imp) because a strategy changes which samples exist, so an approach can
    only be compared against the unharmonized matrix it was actually built from.
    """
    # `mk_is_self_reference` and `xb_subsampled` are flags. pandas calls a bool column
    # numeric, and subtracting one flag from another raises rather than returning
    # nonsense, which is how this was found.
    lmn = [c for c in df.columns
           if c.startswith(("mk_", "xb_", "pv_"))
           and pd.api.types.is_numeric_dtype(df[c])
           and not pd.api.types.is_bool_dtype(df[c])]
    base = (df[(df.method == "01_raw") & (~df.post_rm)]
            .set_index(["strat", "imp"])[lmn]
            .rename(columns={c: f"{c}_raw" for c in lmn}))
    out = df.join(base, on=["strat", "imp"])
    for c in lmn:
        out[f"{c}_delta"] = out[c] - out[f"{c}_raw"]

    # The Group M margin: how much better the panel's cross-batch rank structure agrees
    # for samples of the same biology than for samples of different biology.
    out["xb_margin"] = out["xb_rank_agree"] - out["xb_rank_disagree_diffbio"]
    out["xb_margin_raw"] = out["xb_rank_agree_raw"] - out["xb_rank_disagree_diffbio_raw"]
    out["xb_margin_delta"] = out["xb_margin"] - out["xb_margin_raw"]
    return out


def add_fold_metrics(df: pd.DataFrame, folds_path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-batch LOBO detail from prediction_folds_long.csv.

    Adds, per run_id, TWO cuts of the same fold population -- neither replaces the
    other, and every table in the manuscript shows both (Daniil, 2026-09-18):

        full : pv_lobo3_f1_macro_mean as published, over ALL folds
        mc   : f1_mc_mean, f1_mc_min, n_mc   -- folds with n_classes >= 2

    A single-class fold is an honest test: a classifier trained on every batch but one,
    asked to label a DLBCL-only batch, can still get it wrong. It is NOT excluded and
    NOT treated as a metric defect. The two cuts are reported side by side because they
    answer different questions -- `full` asks how the approach does on the batch
    population as it actually is, `mc` asks how it separates classes when it is asked
    to.

    Returns the frame and the fold-composition census used by the a2_p6 panel.
    """
    folds = pd.read_csv(folds_path)
    # The folds table carries the same 18 Shambhala P/Q variants as the metric snapshot
    # and zero rows named `20_shambhala`. Without this the 84 Shambhala approaches would
    # silently get no fold metrics at all.
    folds["method"] = folds.run_id.str.split("__").str[2]
    folds = _canonicalize_shambhala(folds)
    folds["run_id"] = (folds.run_id.str.split("__").str[0] + "__"
                       + folds.run_id.str.split("__").str[1] + "__"
                       + folds.method + "__"
                       + folds.run_id.str.split("__").str[3])

    # Restrict to the analysis set before any census. The fold table carries 3,738
    # run_ids over 50 method names -- every Shambhala P/Q variant, and approaches that
    # fail the pct_samples_allNA criterion. A composition quoted over all of them
    # describes a population the article never analyses. Of the 53,737 unrestricted
    # 3-class folds, 32,746 survive this line and 20,991 do not: 20,343 belong to the
    # 17 NON-canonical Shambhala P/Q variants and 648 to 34_arsyn and 38_harman, whose
    # pct_samples_allNA is 74.2% or worse. The canonical shambhala_P0std_Q0std is kept,
    # as 20_shambhala, and contributes 1,200 folds -- counting it with the discarded
    # variants gives 21,543, which is wrong and exceeds the 20,991 actually excluded.
    folds = folds[folds.run_id.isin(df.index)]
    three = folds[folds.target == "3class"]
    mc = three[three.n_classes >= 2]
    agg = mc.groupby("run_id")["f1_macro"].agg(f1_mc_mean="mean", f1_mc_min="min",
                                               n_mc="size")
    agg["auc_mc_mean"] = mc.groupby("run_id")["auc"].mean()
    n_all = three.groupby("run_id")["f1_macro"].size().rename("n_folds_total")
    agg = agg.join(n_all)
    agg["frac_singleclass"] = 1 - agg.n_mc / agg.n_folds_total

    two = folds[folds.target == "2class"]
    agg["n_mc_2class"] = two[two.n_classes >= 2].groupby("run_id").size()

    out = df.join(agg, how="left")
    # An approach whose folds all carry one class produces no rows in the multiclass
    # aggregate, so the join leaves n_mc missing. That reads as "not measured" when it
    # means "measured, and the answer is none" -- the G_affymetrix_only post-removal
    # rows that report F1 = 1.000 on zero multiclass folds are exactly this case.
    has_folds = out.index.isin(three.run_id.unique())
    out.loc[has_folds & out.n_mc.isna(), ["n_mc", "n_mc_2class"]] = 0
    out["is_degenerate_folds"] = out.n_mc.fillna(0) < MIN_MC_FOLDS
    out["is_prediction_best"] = False   # filled by main() once elect() has run

    comp = (three.groupby(["batch", "n_classes"])
            .agg(n_folds=("f1_macro", "size"),
                 median_f1=("f1_macro", "median"),
                 median_auc=("auc", "median"),
                 median_n_samples=("n", "median"))
            .reset_index())

    # A median of per-batch medians is not the median over folds, and the manuscript
    # quotes the latter. Carry it in the table itself, as rows keyed __ALL__, so the
    # cited table contains the cited number.
    overall = (three.groupby("n_classes")
               .agg(n_folds=("f1_macro", "size"),
                    median_f1=("f1_macro", "median"),
                    median_auc=("auc", "median"),
                    median_n_samples=("n", "median"))
               .reset_index())
    overall.insert(0, "batch", "__ALL__")
    comp = pd.concat([comp, overall], ignore_index=True)

    tot = three.groupby("n_classes")["f1_macro"].agg(["size", "median"])
    print(f"  folds: {len(three):,} 3-class folds; "
          + ", ".join(f"{int(k)}-class {int(v['size']):,} (median F1 {v['median']:.3f})"
                      for k, v in tot.iterrows()))
    return out, comp


def agreement_specific(df: pd.DataFrame) -> pd.DataFrame:
    """Approaches that raise same-biology agreement and lower different-biology agreement.

    Daniil's criterion, applied to the raw-subtracted columns: `xb_rank_agree_delta > 0`
    AND `xb_rank_disagree_diffbio_delta < 0`. The unsubtracted margin is carried in the
    same table so both forms are reported, as he asked.
    """
    d = df[~df.is_raw]
    sel = d[(d.xb_rank_agree_delta > 0) & (d.xb_rank_disagree_diffbio_delta < 0)]
    cols = ["strat", "imp", "method", "post_rm", "harshness_level",
            "xb_rank_agree", "xb_rank_disagree_diffbio", "xb_margin",
            "xb_rank_agree_delta", "xb_rank_disagree_diffbio_delta", "xb_margin_delta",
            "mk_rho_mean_markers", "pv_lobo3_f1_macro_mean", "f1_mc_mean", "n_mc"]
    out = sel[cols].sort_values("xb_margin_delta", ascending=False)
    print(f"  agreement-specific: {len(out)} of {len(d)} non-raw approaches "
          f"({len(out) / len(d) * 100:.1f}%)")
    return out


def generalizability_index(df: pd.DataFrame,
                           columns: list[str] | None = None) -> pd.Series:
    """Rank-percentile mean of the six columns of plan §4.1, each polarity-adjusted.

    Rank-percentile, not min-max: the columns have incompatible scales and Group L
    saturates at 1.0 by construction for monotone methods. `columns` defaults to the
    current definition, `INDEX_COLUMNS`; pass `INDEX_COLUMNS_260917` for the old one.
    """
    parts = {}
    for c in (columns or INDEX_COLUMNS):
        pol = lmn_polarity(c) or +1     # f1_mc_* and xb_margin_delta are derived names
        parts[f"pct_{c}"] = rank_percentile(df[c], pol)
    comp = pd.DataFrame(parts, index=df.index)
    return comp.mean(axis=1, skipna=True).rename("generalizability_index")


# ── election ──────────────────────────────────────────────────────────────────

def class_columns(df: pd.DataFrame, metric_class: str) -> list[str]:
    """The columns of one metric class that carry a direction and actually vary."""
    prefixes = METRIC_CLASS_PREFIXES[metric_class]
    cols = [c for c in df.columns
            if c.startswith(prefixes)
            and not c.endswith(("_raw", "_delta"))
            and pd.api.types.is_numeric_dtype(df[c])
            and not pd.api.types.is_bool_dtype(df[c])
            and df[c].notna().any()
            and df[c].nunique(dropna=True) > 1]
    if metric_class in ("L", "M", "N"):
        return [c for c in cols if lmn_polarity(c) != 0]
    pol = article1_polarity(cols)
    return [c for c in cols if pol.get(c, 0) != 0]


def class_score(df: pd.DataFrame, metric_class: str) -> pd.Series:
    """One composite per approach for one metric class: mean rank-percentile."""
    cols = class_columns(df, metric_class)
    if metric_class in ("L", "M", "N"):
        pol = {c: lmn_polarity(c) for c in cols}
    else:
        pol = article1_polarity(cols)
    scaled = pd.DataFrame({c: rank_percentile(df[c], pol[c]) for c in cols}, index=df.index)
    return scaled.mean(axis=1, skipna=True)


def elect(df: pd.DataFrame, metric_class: str, top_frac: float = 0.05) -> set:
    """The approaches a single metric class elects: top `top_frac` by its own composite.

    The named group `clustermap_best` is not a composite at all -- it is Article 1's
    own 15-approach selection, carried through so the cross-election matrix can ask
    how much the classes agree with the choice that was actually published.
    """
    if metric_class == "clustermap_best":
        return set(df.index[df.is_clustermap_best])
    if metric_class == "composite":
        score = pd.concat(
            [class_score(df, c) for c in
             ("global", "local", "distributional", "structural")], axis=1).mean(axis=1)
    else:
        score = class_score(df, metric_class)
    k = max(1, int(round(len(df) * top_frac)))
    return set(score.nlargest(k).index)


ELECTION_CLASSES = ["global", "local", "distributional", "structural", "composite",
                    "L", "M", "N", "clustermap_best"]


def cross_election_matrix(df: pd.DataFrame, top_frac: float = 0.05) -> tuple[pd.DataFrame, dict]:
    """Jaccard overlap between the elected sets of every pair of metric classes."""
    sets = {c: elect(df, c, top_frac) for c in ELECTION_CLASSES}
    m = pd.DataFrame(index=ELECTION_CLASSES, columns=ELECTION_CLASSES, dtype=float)
    for a in ELECTION_CLASSES:
        for b in ELECTION_CLASSES:
            u = len(sets[a] | sets[b])
            m.loc[a, b] = len(sets[a] & sets[b]) / u if u else np.nan
    return m, sets


def method_census_by_class(df: pd.DataFrame, sets: dict) -> pd.DataFrame:
    """Which methods each class elects, counted."""
    rows = []
    for cls, ids in sets.items():
        sub = df.loc[sorted(ids)]
        for method, n in sub.method.value_counts().items():
            rows.append({"metric_class": cls, "method": method, "n_elected": int(n),
                         "n_class_total": len(ids)})
    return pd.DataFrame(rows).sort_values(["metric_class", "n_elected"],
                                          ascending=[True, False])


def harshness_by_lmn(df: pd.DataFrame) -> pd.DataFrame:
    """The §1.5e tier table: medians per harshness tier plus Kruskal-Wallis across tiers."""
    cols = ["mk_rho_mean_markers", "mk_rho_marker_minus_hk", "xb_rank_agree",
            "xb_margin", "pv_lobo3_f1_macro_mean", "f1_mc_mean", "pv_lobo2_auc_macro_mean"]
    tiers = ["low", "medium", "high"]
    rows = []
    for c in cols:
        groups = [df.loc[df.harshness_level == t, c].dropna() for t in tiers]
        H, p = kruskal(*groups)
        row = {"metric": c, "kruskal_H": H, "kruskal_p": p}
        for t, g in zip(tiers, groups):
            row[f"median_{t}"] = g.median()
            row[f"n_{t}"] = len(g)
        rows.append(row)
    return pd.DataFrame(rows)


def per_batch_folds(df: pd.DataFrame, folds_path, sets: dict) -> pd.DataFrame:
    """Per-batch F1/AUC for the prediction best approaches and the clustermap best group.

    `n_classes` travels with every row so a reader can rebuild either fold cut from the
    table instead of taking the summary on trust.
    """
    folds = pd.read_csv(folds_path)
    folds["method"] = folds.run_id.str.split("__").str[2]
    folds = _canonicalize_shambhala(folds)
    parts = folds.run_id.str.split("__")
    folds["run_id"] = parts.str[0] + "__" + parts.str[1] + "__" + folds.method + "__" + parts.str[3]

    folds = folds[folds.run_id.isin(df.index)]
    wanted = sets["N"] | set(df.index[df.is_clustermap_best])
    out = folds[folds.run_id.isin(wanted)].copy()
    out["group"] = np.where(out.run_id.isin(sets["N"]), "prediction_best", "clustermap_best")
    both = sets["N"] & set(df.index[df.is_clustermap_best])
    out.loc[out.run_id.isin(both), "group"] = "both"
    return out.sort_values(["group", "run_id", "target", "batch"])


# ── revision 260924: the statistics the review demands ────────────────────────
#
# Plan `f1000_article2_revision_plan_260924.md`, Phase 1. Every table written below is
# registered in TABLE_REGISTRY with its tier, so the five-main-table budget of HARD_RULE
# 19 can be checked by reading one CSV instead of trusting the writer.

COMBAT_FAMILY = ("05_combat", "06_combat_seq", "08_inmoose_combatseq", "29_combat_ref")
TIERS = ("low", "medium", "high")
ELIGIBLE_MIN_MC_FOLDS = 5  # the "eligible" filter the LOBO text uses: 1,527 approaches

# The LOBO columns: F1 on both fold cuts and AUC, for LOBO3 and LOBO2. C47 asks for both
# fold cuts of both targets in one table; the multiclass-only 2-class F1 (f1_mc2_*) is
# new in 260924. AUC has ONE cut only: it is undefined on a single-class fold (every such
# fold carries auc = NaN), so pv_lobo*_auc_macro_mean is already a multiclass-only mean
# and auc_mc_mean / auc_mc2_mean reproduce it. They stay in A2_T1 as the proof of that.
LOBO_COLUMNS = [
    "pv_lobo3_f1_macro_mean", "f1_mc_mean", "pv_lobo3_auc_macro_mean",
    "pv_lobo2_f1_macro_mean", "f1_mc2_mean", "pv_lobo2_auc_macro_mean",
]

# Rows of main-text Table 1 (C44, C45; plan E3, E4): (column, class, label, fold cut).
TABLE1_METRICS = [
    ("mk_rho_mean_markers", "L", "Mean within-cohort marker correlation", "-"),
    ("mk_rho_marker_minus_hk", "L", "Marker minus housekeeping correlation", "-"),
    ("xb_rank_agree", "M", "Same-biology cross-batch agreement", "-"),
    ("xb_rank_disagree_diffbio", "M", "Different-biology cross-batch agreement", "-"),
    ("xb_margin", "M", "Same- minus different-biology margin", "-"),
    ("pv_lobo3_f1_macro_mean", "N", "LOBO3 macro F1", "all folds"),
    ("f1_mc_mean", "N", "LOBO3 macro F1", "multiclass folds"),
    ("pv_lobo3_auc_macro_mean", "N", "LOBO3 macro AUC", "multiclass folds (only)"),
    ("pv_lobo2_f1_macro_mean", "N", "LOBO2 macro F1", "all folds"),
    ("f1_mc2_mean", "N", "LOBO2 macro F1", "multiclass folds"),
    ("pv_lobo2_auc_macro_mean", "N", "LOBO2 macro AUC", "multiclass folds (only)"),
]

# name -> (tier, main-text table number or "", what it holds). The main tier holds at
# most five tables and none longer than 15 rows (plan §C2); A2_T2 itself is 2,234 rows,
# so its main-text form is the top-15 cut A2_T2b.
TABLE_REGISTRY = {
    "A2_T0_shambhala_identity": ("supplementary", "", "Shambhala two-names identity"),
    "A2_T1_analysis_set_census": ("supplementary", "", "the 2,234 approaches, L/M/N"),
    "A2_T2_generalizability_ranking": ("supplementary", "", "E1 index, all approaches"),
    "A2_T2b_generalizability_top_eligible": ("main", "4", "E1 index, top 15 eligible"),
    "A2_T3_cross_election_matrix": ("main", "3", "Jaccard matrix of elected sets"),
    "A2_T3b_cross_election_pairs": ("supplementary", "", "pairs: counts, sizes, p"),
    "A2_T3c_threshold_sensitivity": ("supplementary", "", "overlaps at 2.5/5/10%"),
    "A2_T4_method_census_by_class": ("supplementary", "", "methods per elected set"),
    "A2_T5_per_batch_folds": ("supplementary", "", "per-batch LOBO folds"),
    "A2_T6_agreement_specific": ("supplementary", "", "the 61 approaches"),
    "A2_T7_harshness_by_lmn": ("supplementary", "", "superseded by A2_T9/A2_T9b"),
    "A2_T8_fold_composition": ("supplementary", "", "fold census by class count"),
    "A2_T9_harshness_table1": ("main", "1", "L/M/N by harshness tier"),
    "A2_T9b_harshness_full": ("supplementary", "", "every L/M/N column by tier"),
    "A2_T10_paired_tests": ("supplementary", "", "every test the text relies on"),
    "A2_T11_scatter_correlations": ("supplementary", "", "Spearman per scatter claim"),
    "A2_T12_metric_census": ("supplementary", "", "344-metric registry map"),
    "A2_T13_lobo_summary": ("main", "2", "LOBO, both cuts, both targets"),
    "A2_T14_dispersion": ("supplementary", "", "composite contribution spreads"),
    "A2_T15_class_percentile_scores": ("supplementary", "", "C15: class score per approach"),
    "A2_T16_pca_component_means": ("supplementary", "", "sfig_pca group means (SR-R01)"),
}

# Registry names that the snapshot spells differently (plan §B5, Phase 0 census).
BOOLEAN_FLAGS = {"wm_subsampled", "mk_is_self_reference", "xb_subsampled"}
PERCENT_DERIVED = {
    "pct_samples_allNA": ("n_samples_allNA", "n_samples"),
    "pct_genes_allNA": ("n_genes_allNA", "n_genes"),
}


def mad(x) -> float:
    """Plain (unscaled) median absolute deviation, the convention of both articles."""
    x = pd.Series(x).dropna()
    return float(np.median(np.abs(x - np.median(x)))) if len(x) else np.nan


def mannwhitney(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    """Two-sided Mann-Whitney U for a paired-median claim in the text.

    Returns
    -------
    tuple[float, float]
        The U statistic of `a` and the raw two-sided p-value. No multiple-testing
        correction is applied: Daniil's C25 asks for raw p-values so each claim
        can be read against its own comparison.
    """
    res = mannwhitneyu(pd.Series(a).dropna(), pd.Series(b).dropna(),
                       alternative="two-sided")
    return float(res.statistic), float(res.pvalue)


def load_restricted_folds(df: pd.DataFrame, folds_path) -> pd.DataFrame:
    """prediction_folds_long.csv with the Shambhala rename, cut to the analysis set.

    The same three steps add_fold_metrics() and per_batch_folds() apply; repeated here
    so the two verified 260917 code paths stay untouched.
    """
    folds = pd.read_csv(folds_path)
    folds["method"] = folds.run_id.str.split("__").str[2]
    folds = _canonicalize_shambhala(folds)
    parts = folds.run_id.str.split("__")
    folds["run_id"] = (parts.str[0] + "__" + parts.str[1] + "__" + folds.method
                       + "__" + parts.str[3])
    return folds[folds.run_id.isin(df.index)]


def add_twoclass_fold_metrics(df: pd.DataFrame, folds: pd.DataFrame) -> pd.DataFrame:
    """The multiclass-only cut of the 2-class target: f1_mc2_mean/min, auc_mc2_mean.

    The 2-class target (FL against DLBCL) has single-class held-out batches too; C47
    asks for both cuts of both targets, and until 260924 only the 3-class cut existed.
    """
    two = folds[(folds.target == "2class") & (folds.n_classes >= 2)]
    agg = two.groupby("run_id").agg(f1_mc2_mean=("f1_macro", "mean"),
                                    f1_mc2_min=("f1_macro", "min"),
                                    auc_mc2_mean=("auc", "mean"))
    return df.join(agg, how="left")


def attach_snapshot_columns(df: pd.DataFrame, metrics_path) -> pd.DataFrame:
    """The analysis set plus every numeric snapshot column Supplementary File 3 omits.

    Supplementary File 3 carries raw values identical to the snapshot on all 78 shared
    metric columns (checked 2026-09-25), but lacks pcr_*, r2_pc*, pct_var_*, exp_*,
    ilisi_mean_* and the tSNE/UMAP means that the text quotes. The result is used ONLY
    for the statistics tables: class_columns() selects by prefix, so letting r2_pc* or
    pct_var_pc* into the election frame would silently change the global class.
    """
    snap = _canonicalize_shambhala(pd.read_csv(metrics_path, low_memory=False))
    snap["run_id"] = (snap.strat + "__" + snap.imp + "__" + snap.method
                      + "__post" + snap.post_rm.astype(int).astype(str))
    snap = snap.set_index("run_id")
    extra = [c for c in snap.columns
             if c not in df.columns
             and pd.api.types.is_numeric_dtype(snap[c])
             and not pd.api.types.is_bool_dtype(snap[c])]
    return df.join(snap[extra], how="left")


def attach_composite(full: pd.DataFrame, metrics_path):
    """Add Article 1's equally weighted composite of the 87 scoring metrics.

    Computed by figures_helpers.load_metrics_data(), the function Article 1's own
    Supplementary Figures 9 and 10 use, so the two articles share one composite.

    Returns
    -------
    tuple
        (full with `composite_score`, normalized scores, scoring columns, col_meta).
    """
    sys.path.insert(0, str(REPO / "figures_for_article" / "figure_drawing_scripts"))
    import figures_helpers as fh

    _, normed, scoring, meta = fh.load_metrics_data(metrics_path)
    # load_metrics_data() builds run_id BEFORE it renames the Shambhala representative,
    # so its index still says shambhala_P0std_Q0std; without this the 84 Shambhala
    # approaches get no composite.
    normed.index = normed.index.str.replace(SHAMBHALA_CANONICAL, "20_shambhala")
    composite = normed[scoring].mean(axis=1).reindex(full.index)
    assert composite.notna().all(), "composite missing for some analysis-set approaches"
    return full.assign(composite_score=composite), normed, scoring, meta


# ── test-row builders: one schema for every test in A2_T10 ────────────────────

T10_COLUMNS = [
    "claim_id", "section", "claim", "test", "metric", "group_a", "group_b",
    "n_a", "n_b", "median_a", "median_b", "mad_a", "mad_b", "mean_a", "mean_b",
    "median_all", "mean_all", "count_a", "count_b", "prop_a", "prop_b", "prop_all",
    "top_group", "top_group_median", "bottom_group", "bottom_group_median",
    "top_group_by_mean", "bottom_group_by_mean",
    "range_of_group_medians", "range_of_group_means",
    "statistic", "p_value", "effect_size", "effect_name",
    "quoted", "quoted_reproduced", "tier", "destination",
]


def _mw(cid, section, claim, col, values, mask_a, mask_b, label_a, label_b,
        quoted="", within=None):
    """Mann-Whitney row: group A against group B on one column, within a population."""
    pop = values.index if within is None else values.index[within]
    v = values.loc[pop]
    a, b = v[mask_a.loc[pop]].dropna(), v[mask_b.loc[pop]].dropna()
    assert len(a) and len(b), f"{cid}: empty group ({len(a)}, {len(b)})"
    u, p = mannwhitney(a, b)
    return {"claim_id": cid, "section": section, "claim": claim, "test": "Mann-Whitney U",
            "metric": col, "group_a": label_a, "group_b": label_b,
            "n_a": len(a), "n_b": len(b), "median_a": a.median(), "median_b": b.median(),
            "mad_a": mad(a), "mad_b": mad(b), "mean_a": a.mean(), "mean_b": b.mean(),
            "median_all": v.median(), "mean_all": v.mean(),
            "statistic": u, "p_value": p, "effect_size": 2 * u / (len(a) * len(b)) - 1,
            "effect_name": "rank-biserial r (A over B)", "quoted": quoted}


def _kw(cid, section, claim, col, values, groups, quoted="", within=None):
    """Kruskal-Wallis row across every level of `groups`, with the named dispersion."""
    d = pd.DataFrame({"v": values, "g": groups})
    if within is not None:
        d = d[within]
    d = d.dropna()
    samples = [x.v for _, x in d.groupby("g")]
    h, p = kruskal(*samples)
    k, n = len(samples), len(d)
    med, mean = d.groupby("g").v.median(), d.groupby("g").v.mean()
    return {"claim_id": cid, "section": section, "claim": claim,
            "test": "Kruskal-Wallis H", "metric": col, "group_a": f"{k} groups",
            "n_a": n, "median_all": d.v.median(), "mean_all": d.v.mean(),
            "top_group": med.idxmax(), "top_group_median": med.max(),
            "bottom_group": med.idxmin(), "bottom_group_median": med.min(),
            "top_group_by_mean": mean.idxmax(), "bottom_group_by_mean": mean.idxmin(),
            "range_of_group_medians": med.max() - med.min(),
            "range_of_group_means": mean.max() - mean.min(),
            "statistic": h, "p_value": p, "effect_size": (h - k + 1) / (n - k),
            "effect_name": "epsilon-squared", "quoted": quoted}


def _fisher(cid, section, claim, metric, hit, mask_a, mask_b, label_a, label_b,
            quoted=""):
    """Fisher exact row: is the share of `hit` in group A different from group B?"""
    ka, na = int(hit[mask_a].sum()), int(mask_a.sum())
    kb, nb = int(hit[mask_b].sum()), int(mask_b.sum())
    odds, p = fisher_exact([[ka, na - ka], [kb, nb - kb]])
    return {"claim_id": cid, "section": section, "claim": claim,
            "test": "Fisher exact (two-sided)", "metric": metric,
            "group_a": label_a, "group_b": label_b, "n_a": na, "n_b": nb,
            "count_a": ka, "count_b": kb, "prop_a": ka / na, "prop_b": kb / nb,
            "prop_all": hit.mean(), "statistic": odds, "p_value": p,
            "effect_name": "odds ratio", "quoted": quoted}


def _wsr(cid, section, claim, metric, diffs, label, quoted=""):
    """Wilcoxon signed-rank row on paired (or baseline-subtracted) differences vs 0."""
    d = pd.Series(diffs).dropna()
    w, p = wilcoxon(d)
    return {"claim_id": cid, "section": section, "claim": claim,
            "test": "Wilcoxon signed-rank (two-sided)", "metric": metric,
            "group_a": label, "group_b": "0", "n_a": len(d), "median_a": d.median(),
            "mean_a": d.mean(), "statistic": w, "p_value": p,
            "effect_name": "median of the differences", "effect_size": d.median(),
            "quoted": quoted}


def _paired_diff(full, col, factor, level_a, level_b, keys, within=None):
    """level_a minus level_b of `factor`, matched on `keys` (for signed-rank tests)."""
    d = full if within is None else full[within]
    wide = d[d[factor].isin([level_a, level_b])].pivot_table(
        index=keys, columns=factor, values=col, aggfunc="first")
    return (wide[level_a] - wide[level_b]).dropna()


def _quoted_reproduced(row: dict) -> str:
    """How many of the quoted numbers a computed field reproduces at the quoted precision.

    Written as `k/n`. It is a finding-aid for the writers, not a gate: a quoted number
    can be a method mean where the row reports medians, and that shows as a miss here.
    """
    quoted = re.findall(r"-?\d+(?:\.\d+)?", str(row.get("quoted", "")))
    if not quoted:
        return ""
    fields = ["median_a", "median_b", "mad_a", "mad_b", "mean_a", "mean_b",
              "median_all", "mean_all", "top_group_median", "bottom_group_median",
              "range_of_group_medians", "range_of_group_means", "effect_size"]
    cands = [row[f] for f in fields if pd.notna(row.get(f, np.nan))]
    cands += [row[f] * 100 for f in ("prop_a", "prop_b", "prop_all")
              if pd.notna(row.get(f, np.nan))]
    cands += [row[f] for f in ("count_a", "count_b", "n_a", "n_b")
              if pd.notna(row.get(f, np.nan))]
    hits = 0
    for q in quoted:
        dp = len(q.split(".")[1]) if "." in q else 0
        hits += any(abs(round(float(c), dp) - float(q)) < 1e-9 for c in cands)
    return f"{hits}/{len(quoted)}"


# ── A2_T10: every test the text relies on ─────────────────────────────────────

def paired_tests(full: pd.DataFrame, folds: pd.DataFrame, sets: dict) -> pd.DataFrame:
    """One row per statistical test behind a comparison the manuscript makes.

    Each block is labelled with the Results sub-section and quotes the numbers the
    current text gives, so the Phase 3 writers can see at a glance whether the claim
    reproduces and which p-value belongs beside it. Two-group comparisons are
    Mann-Whitney U (C21, C25, C40); three or more groups are Kruskal-Wallis H; shares
    are Fisher exact; baseline-subtracted and matched-pair shifts are Wilcoxon
    signed-rank. All p-values are raw and two-sided.
    """
    F = full
    cm, meth, strat, imp = F.is_clustermap_best, F.method, F.strat, F.imp
    everyone = pd.Series(True, index=F.index)
    rows = []

    sec = "R1 metric classes capture non-overlapping components"
    rows += [
        _mw("T10-001", sec, "clustermap group vs rest, batch PCReg", "pcr_RNA_BATCH",
            F.pcr_RNA_BATCH, cm, ~cm, "clustermap_best", "rest", "0.871 0.626"),
        _mw("T10-002", sec, "clustermap group vs rest, biology PCReg (C25)",
            "pcr_Diagnosis_cell_type_unified", F.pcr_Diagnosis_cell_type_unified,
            cm, ~cm, "clustermap_best", "rest", "0.820 0.063 0.802"),
        _mw("T10-003", sec, "05_combat + 29_combat_ref vs other methods, biology PCReg, "
            "strategies A, B, I, J, E1-E3", "pcr_Diagnosis_cell_type_unified",
            F.pcr_Diagnosis_cell_type_unified, meth.isin(["05_combat", "29_combat_ref"]),
            ~meth.isin(["05_combat", "29_combat_ref"]), "05_combat+29_combat_ref",
            "other methods", "0.568 0.778",
            within=strat.isin(["A_confirmed_bad", "B_extended_bad",
                               "I_rare_batches_removed", "J_ff_only", "E1_iterative_r1",
                               "E2_iterative_r2", "E3_iterative_r3"])),
        _mw("T10-004", sec, "14_qsmooth vs rest, batch PCReg", "pcr_RNA_BATCH",
            F.pcr_RNA_BATCH, meth == "14_qsmooth", meth != "14_qsmooth", "14_qsmooth",
            "rest", "0.208 0.098"),
    ]
    for cid, s, q in [("T10-005", "D_malignant_only", "0.939"),
                      ("T10-006", "K_ffpe_only", "0.925"),
                      ("T10-007", "S0_no_removal", "0.883")]:
        rows.append(_mw(cid, sec, f"{s} vs other strategies, biology PCReg",
                        "pcr_Diagnosis_cell_type_unified",
                        F.pcr_Diagnosis_cell_type_unified, strat == s, strat != s, s,
                        "other strategies", q))
    rows += [
        _mw("T10-008", sec, "C_rnaseq_only vs other strategies, batch PCReg",
            "pcr_RNA_BATCH", F.pcr_RNA_BATCH, strat == "C_rnaseq_only",
            strat != "C_rnaseq_only", "C_rnaseq_only", "other strategies", "0.872"),
        _kw("T10-009", sec, "batch PCReg differs across methods (method above "
            "strategy)", "pcr_RNA_BATCH", F.pcr_RNA_BATCH, meth),
        _kw("T10-010", sec, "batch PCReg differs across strategies", "pcr_RNA_BATCH",
            F.pcr_RNA_BATCH, strat),
        _mw("T10-011", sec, "10_mnn vs rest, batch iLISI", "ilisi_mean_RNA_BATCH",
            F.ilisi_mean_RNA_BATCH, meth == "10_mnn", meth != "10_mnn", "10_mnn",
            "rest", "1.72 0.209 1.16"),
        _mw("T10-012", sec, "14_qsmooth vs rest, batch iLISI", "ilisi_mean_RNA_BATCH",
            F.ilisi_mean_RNA_BATCH, meth == "14_qsmooth", meth != "14_qsmooth",
            "14_qsmooth", "rest", "1.07 0.032"),
        _mw("T10-013", sec, "10_mnn vs 14_qsmooth, batch tSNE entropy",
            "tsne_entropy_norm_RNA_BATCH", F.tsne_entropy_norm_RNA_BATCH,
            meth == "10_mnn", meth == "14_qsmooth", "10_mnn", "14_qsmooth",
            "0.179 0.025 0.0178 0.0086"),
        _mw("T10-014", sec, "clustermap group vs rest, within-batch KS D",
            "ks_cohort_within_batch_mean_D", F.ks_cohort_within_batch_mean_D, cm, ~cm,
            "clustermap_best", "rest", "0.445 0.041"),
        _mw("T10-015", sec, "clustermap group vs rest, between-batch KS D",
            "ks_mean_D_RNA_BATCH", F.ks_mean_D_RNA_BATCH, cm, ~cm, "clustermap_best",
            "rest"),
        _mw("T10-016", sec, "C_rnaseq_only vs other strategies, within-batch KS D",
            "ks_cohort_within_batch_mean_D", F.ks_cohort_within_batch_mean_D,
            strat == "C_rnaseq_only", strat != "C_rnaseq_only", "C_rnaseq_only",
            "other strategies", "0.439 0.015"),
        _mw("T10-017", sec, "C_rnaseq_only vs other strategies, between-batch KS D",
            "ks_mean_D_RNA_BATCH", F.ks_mean_D_RNA_BATCH, strat == "C_rnaseq_only",
            strat != "C_rnaseq_only", "C_rnaseq_only", "other strategies",
            "0.332 0.052"),
    ]

    sec = "R2 global variance-based metrics saturate"
    saturated = F.pcr_RNA_BATCH > 0.9999
    rows += [
        _fisher("T10-020", sec, "kBET < 0.1 among PCReg-saturated approaches vs the "
                "rest (C28 baseline in prop_all)", "kbet_acceptance_rate_RNA_BATCH < 0.1",
                F.kbet_acceptance_rate_RNA_BATCH < 0.1, saturated, ~saturated,
                "pcr_RNA_BATCH > 0.9999", "rest", "198 98.5"),
        _mw("T10-021", sec, "clustermap group vs rest, batch DSC", "dsc_RNA_BATCH",
            F.dsc_RNA_BATCH, cm, ~cm, "clustermap_best", "rest", "0.962"),
    ]
    for cid, s, q in [("T10-022", "G_affymetrix_only", "0.165"),
                      ("T10-023", "K_ffpe_only", "0.078")]:
        rows.append(_mw(cid, sec, f"{s} vs other strategies, batch ASW",
                        "asw_batch_RNA_BATCH", F.asw_batch_RNA_BATCH, strat == s,
                        strat != s, s, "other strategies", q))
    for cid, m, q in [("T10-024", "02_median_scaling", "-0.286"),
                      ("T10-025", "33_amdbnorm", "-0.276")]:
        rows.append(_mw(cid, sec, f"{m} vs rest, batch ASW", "asw_batch_RNA_BATCH",
                        F.asw_batch_RNA_BATCH, meth == m, meth != m, m, "rest", q))
    low11 = F.groupby("method").pcr_RNA_BATCH.mean().nsmallest(11).index
    in_low11 = meth.isin(low11)
    keys = ["strat", "method", "post_rm"]
    rows += [
        _mw("T10-026", sec, "softimpute vs KNN, batch PCReg, the 11 lowest-PCReg "
            "methods", "pcr_RNA_BATCH", F.pcr_RNA_BATCH, imp == "softimpute",
            imp == "knn", "softimpute", "knn", "", within=in_low11),
        _wsr("T10-027", sec, "softimpute minus KNN, matched on strategy, method and "
             "post-removal, the 11 lowest-PCReg methods", "pcr_RNA_BATCH",
             _paired_diff(F, "pcr_RNA_BATCH", "imp", "softimpute", "knn", keys,
                          in_low11), "softimpute - knn"),
        _mw("T10-028", sec, "strict vs KNN, batch PCReg, the 11 lowest-PCReg methods",
            "pcr_RNA_BATCH", F.pcr_RNA_BATCH, imp == "strict", imp == "knn",
            "strict", "knn", "0.370 0.390", within=in_low11),
        _wsr("T10-029", sec, "strict minus KNN, matched, the 11 lowest-PCReg methods",
             "pcr_RNA_BATCH",
             _paired_diff(F, "pcr_RNA_BATCH", "imp", "strict", "knn", keys, in_low11),
             "strict - knn"),
        _mw("T10-030", sec, "post-removal vs none, batch PCReg", "pcr_RNA_BATCH",
            F.pcr_RNA_BATCH, F.post_rm.astype(bool), ~F.post_rm.astype(bool),
            "post_rm", "no post_rm"),
        _wsr("T10-031", sec, "post-removal minus none, matched on strategy, imputation "
             "and method", "pcr_RNA_BATCH",
             _paired_diff(F.assign(post=F.post_rm.astype(int)), "pcr_RNA_BATCH",
                          "post", 1, 0, ["strat", "imp", "method"]),
             "post1 - post0", "0.030"),
    ]
    fsqn = meth == "16_fsqn_r"
    for cid, s, q in [("T10-032", "K_ffpe_only", "0.83 0.08"),
                      ("T10-033", "F_microarray_only", "0.83 0.30")]:
        rows.append(_mw(cid, sec, f"16_fsqn_r under S0_no_removal vs {s}, batch PCReg",
                        "pcr_RNA_BATCH", F.pcr_RNA_BATCH, strat == "S0_no_removal",
                        strat == s, "S0_no_removal", s, q, within=fsqn))

    sec = "R3 batch variance redistributed across components"
    rows += [
        _mw("T10-040", sec, "C_rnaseq_only vs other strategies, PC1 variance",
            "pct_var_pc1", F.pct_var_pc1, strat == "C_rnaseq_only",
            strat != "C_rnaseq_only", "C_rnaseq_only", "other strategies", "30.4"),
        _mw("T10-041", sec, "clustermap group vs rest, PC1 variance", "pct_var_pc1",
            F.pct_var_pc1, cm, ~cm, "clustermap_best", "rest", "37.9"),
        _mw("T10-042", sec, "G_affymetrix_only vs other strategies, PC1 variance",
            "pct_var_pc1", F.pct_var_pc1, strat == "G_affymetrix_only",
            strat != "G_affymetrix_only", "G_affymetrix_only", "other strategies",
            "66.0"),
    ]
    by_strat = F.groupby("strat")[["r2_pc1_RNA_BATCH", "r2_pc2_RNA_BATCH"]].mean()
    k_lower = int((by_strat.r2_pc1_RNA_BATCH < by_strat.r2_pc2_RNA_BATCH).sum())
    bt = binomtest(k_lower, len(by_strat), 0.5)
    rows.append({"claim_id": "T10-043", "section": sec,
                 "claim": "strategies with a lower mean batch R2 on PC1 than on PC2",
                 "test": "binomial sign test (two-sided)",
                 "metric": "r2_pc1_RNA_BATCH < r2_pc2_RNA_BATCH, strategy means",
                 "n_a": len(by_strat), "count_a": k_lower,
                 "prop_a": k_lower / len(by_strat), "statistic": k_lower,
                 "p_value": bt.pvalue, "effect_name": "count", "quoted": "10 14"})

    sec = "R4 local neighborhood metrics"
    rows.append(_fisher("T10-050", sec, "clustermap group vs rest, kBET above 0.10",
                        "kbet_acceptance_rate_RNA_BATCH > 0.10",
                        F.kbet_acceptance_rate_RNA_BATCH > 0.10, cm, ~cm,
                        "clustermap_best", "rest", "5 15"))
    raw = meth == "01_raw"
    for i, m in enumerate(sorted(set(meth) - {"01_raw"}), 1):
        rows.append(_mw(f"T10-051-{i:02d}", sec, f"{m} vs 01_raw, batch kBET",
                        "kbet_acceptance_rate_RNA_BATCH",
                        F.kbet_acceptance_rate_RNA_BATCH, meth == m, raw, m, "01_raw",
                        "0.027"))
    for cid, s, q in [("T10-052", "D_malignant_only", "1.10"),
                      ("T10-053", "K_ffpe_only", "1.07"),
                      ("T10-054", "J_ff_only", "1.62")]:
        rows.append(_mw(cid, sec, f"{s} vs other strategies, biology cLISI",
                        "clisi_mean_Diagnosis_cell_type_unified",
                        F.clisi_mean_Diagnosis_cell_type_unified, strat == s,
                        strat != s, s, "other strategies", q))
    for cid, s, q in [("T10-055", "K_ffpe_only", "0.646"),
                      ("T10-056", "D_malignant_only", "0.727")]:
        rows.append(_mw(cid, sec, f"{s} vs other strategies, biology graph "
                        "connectivity", "graph_connectivity_Diagnosis_cell_type_unified",
                        F.graph_connectivity_Diagnosis_cell_type_unified, strat == s,
                        strat != s, s, "other strategies", q))

    sec = "R5 distributional convergence and harshness"
    for i, m in enumerate(sorted(set(meth) - {"01_raw"}), 1):
        rows.append(_mw(f"T10-060-{i:02d}", sec, f"{m} vs 01_raw, KS fraction "
                        "significant", "ks_frac_sig_RNA_BATCH", F.ks_frac_sig_RNA_BATCH,
                        meth == m, raw, m, "01_raw", "0.948"))
    rows += [
        _mw("T10-061", sec, "clustermap group vs rest, KS fraction significant",
            "ks_frac_sig_RNA_BATCH", F.ks_frac_sig_RNA_BATCH, cm, ~cm,
            "clustermap_best", "rest", "0.560"),
        _mw("T10-062", sec, "clustermap group vs rest, batch distance ratio",
            "dist_ratio_RNA_BATCH", F.dist_ratio_RNA_BATCH, cm, ~cm,
            "clustermap_best", "rest", "0.914 0.757"),
    ]
    for i, c in enumerate(["wm_mean_bio", "wm_mean_batch",
                           "wm_Diagnosis_cell_type_unified", "wm_RNA_BATCH"], 1):
        rows.append(_mw(f"T10-063-{i}", sec, "clustermap group vs rest, Watermelon "
                        "score (C40)", c, F[c], cm, ~cm, "clustermap_best", "rest"))
    # "Low harshness is highest under 11 of 14 strategies" is a within-strategy claim
    # read off the tier MEANS of Supplementary Figure 8 (the counts reproduce from means,
    # not medians). Each strategy gets its own Kruskal-Wallis row, and one binomial row
    # asks whether the claimed tier leads in more strategies than the 1-in-3 of chance.
    harsh_claims = [
        ("pcr_RNA_BATCH", "low tier highest batch PCReg", "top", "low", "11 14"),
        ("ilisi_mean_RNA_BATCH", "low tier highest batch iLISI", "top", "low", "10 14"),
        ("tsne_entropy_norm_RNA_BATCH", "high tier lowest tSNE entropy", "bottom",
         "high", "12 14"),
        ("ks_frac_sig_RNA_BATCH", "high tier lowest KS fraction", "bottom", "high",
         "13 14"),
    ]
    for j, (c, claim, end, tier, q) in enumerate(harsh_claims, 1):
        per = [_kw(f"T10-064-{j}-{i:02d}", sec, f"{claim}, within {s}", c, F[c],
                   F.harshness_level, within=strat == s)
               for i, s in enumerate(sorted(set(strat)), 1)]
        rows += per
        k = sum(r[f"{end}_group_by_mean"] == tier for r in per)
        bt = binomtest(k, len(per), 1 / 3)
        rows.append({"claim_id": f"T10-064-{j}-all", "section": sec,
                     "claim": f"{claim}: strategies in which the {tier} tier is the "
                              f"{end} tier by mean", "test": "binomial (two-sided), "
                              "chance 1/3", "metric": c, "n_a": len(per), "count_a": k,
                     "prop_a": k / len(per), "statistic": k, "p_value": bt.pvalue,
                     "effect_name": "count", "quoted": q})
    top_tail = F.composite_score > 0.6
    rows += [
        _mw("T10-065", sec, "clustermap group vs rest, composite score",
            "composite_score", F.composite_score, cm, ~cm, "clustermap_best", "rest",
            "0.602"),
        _mw("T10-066", sec, "C_rnaseq_only vs other strategies, composite score",
            "composite_score", F.composite_score, strat == "C_rnaseq_only",
            strat != "C_rnaseq_only", "C_rnaseq_only", "other strategies", "0.578"),
        _fisher("T10-067", sec, "clustermap share of the composite tail above 0.6",
                "composite_score > 0.6", top_tail, cm, ~cm, "clustermap_best", "rest",
                "9 150 6.7"),
        _kw("T10-068", sec, "composite score across harshness tiers (no ordering)",
            "composite_score", F.composite_score, F.harshness_level),
    ]
    n = 0
    for c, cls, label, cut in TABLE1_METRICS:
        for a, b in (("low", "medium"), ("low", "high"), ("medium", "high")):
            n += 1
            rows.append(_mw(f"T10-069-{n:02d}", sec, f"{label} ({cut}), {a} vs {b} "
                            "harshness", c, F[c], F.harshness_level == a,
                            F.harshness_level == b, a, b))

    sec = "R6 marker preservation and cross-batch rank structure"
    for i, m in enumerate(["10_mnn", "12_scanorama"], 1):
        rows += [
            _mw(f"T10-070-{i}a", sec, f"{m} vs rest, marker correlation",
                "mk_rho_mean_markers", F.mk_rho_mean_markers, meth == m, meth != m, m,
                "rest", "-0.0007 -0.0082"),
            _mw(f"T10-070-{i}b", sec, f"{m} vs rest, margin", "xb_margin", F.xb_margin,
                meth == m, meth != m, m, "rest", "0.0000"),
            _mw(f"T10-070-{i}c", sec, f"{m} vs rest, margin change against baseline",
                "xb_margin_delta", F.xb_margin_delta, meth == m, meth != m, m, "rest",
                "-0.0489"),
        ]
    gate = (F.mk_rho_mean_markers > RHO_GATE) & (F.xb_margin > 0)
    rows += [
        _fisher("T10-071", sec, "01_raw passes the joint L/M gate more often than the "
                "rest", "joint gate", gate, raw, ~raw, "01_raw", "rest", "80 84 75.5"),
        _fisher("T10-072", sec, "K_ffpe_only passes the joint gate less often",
                "joint gate", gate, strat == "K_ffpe_only", strat != "K_ffpe_only",
                "K_ffpe_only", "other strategies", "76 164"),
    ]
    for cid, col, grp, lab, q in [
            ("T10-073", "mk_rho_mean_markers", strat, "strategies", "0.0647"),
            ("T10-074", "mk_rho_mean_markers", imp, "imputations", "0.0243"),
            ("T10-075", "mk_rho_mean_markers", meth, "methods", ""),
            ("T10-076", "xb_margin", strat, "strategies", "0.0667"),
            ("T10-077", "xb_margin", imp, "imputations", ""),
            ("T10-078", "xb_margin", meth, "methods", "0.1263")]:
        rows.append(_kw(cid, sec, f"{col} across {lab}", col, F[col], grp, q))
    for i, s in enumerate(sorted(set(strat)), 1):
        q = {"K_ffpe_only": "0.0180", "C_rnaseq_only": "0.0077"}.get(s, "")
        rows.append(_wsr(f"T10-079-{i:02d}", sec, f"margin gain over the unharmonized "
                         f"baseline, {s}, non-raw approaches", "xb_margin_delta",
                         F.xb_margin_delta[(strat == s) & ~raw], s, q))
    spec = pd.Series(F.index.isin(agreement_specific(F).index), index=F.index)
    nonraw = ~raw
    for fac, lab in ((strat, "strategy"), (imp, "imputation"), (meth, "method")):
        for i, lvl in enumerate(sorted(set(fac[spec])), 1):
            rows.append(_fisher(f"T10-080-{lab}-{i:02d}", sec, f"agreement-specific "
                                f"share, {lab} {lvl} vs the other non-raw approaches",
                                "agreement-specific", spec[nonraw],
                                (fac == lvl)[nonraw], (fac != lvl)[nonraw], lvl,
                                f"other {lab}s"))
    sham = meth == "20_shambhala"
    rows += [
        _mw("T10-081", sec, "20_shambhala vs rest, marker correlation",
            "mk_rho_mean_markers", F.mk_rho_mean_markers, sham, ~sham, "20_shambhala",
            "rest", "0.840"),
        _mw("T10-082", sec, "20_shambhala vs rest, margin", "xb_margin", F.xb_margin,
            sham, ~sham, "20_shambhala", "rest", "0.0048"),
    ]

    sec = "R7 cross-batch prediction"
    three = folds[folds.target == "3class"]
    fold_f1 = three.f1_macro.reset_index(drop=True)
    ncls = three.n_classes.reset_index(drop=True)
    rows += [
        _mw("T10-090", sec, "single-class vs multiclass held-out folds, macro F1",
            "f1_macro (fold level, 3-class target)", fold_f1, ncls == 1, ncls >= 2,
            "single-class folds", "multiclass folds", "0.903 0.7334"),
        _mw("T10-091", sec, "two-class vs three-class held-out folds, macro F1",
            "f1_macro (fold level, 3-class target)", fold_f1, ncls == 2, ncls == 3,
            "two-class folds", "three-class folds", "0.629 0.804"),
    ]
    combat = meth.isin(COMBAT_FAMILY)
    for i, c in enumerate(["pv_lobo3_f1_macro_mean", "f1_mc_mean", "f1_mc_min",
                           "pv_lobo2_f1_macro_mean"], 1):
        rows.append(_mw(f"T10-092-{i}", sec, "ComBat family (4 implementations) vs "
                        "the other methods", c, F[c], combat, ~combat, "ComBat family",
                        "other methods"))
    for cid, col, grp, lab, q in [
            ("T10-093", "pv_lobo3_f1_macro_mean", meth, "methods", ""),
            ("T10-094", "f1_mc_mean", meth, "methods", ""),
            ("T10-095", "pv_lobo3_f1_macro_mean", strat, "strategies", "0.763 0.561"),
            ("T10-096", "f1_mc_mean", strat, "strategies", "0.724 0.462"),
            ("T10-097", "pv_lobo3_f1_macro_mean", imp, "imputations", "0.013"),
            ("T10-098", "f1_mc_mean", imp, "imputations", "0.050")]:
        rows.append(_kw(cid, sec, f"{col} across {lab}", col, F[col], grp, q))
    post = F.post_rm.astype(bool)
    rows += [
        _mw("T10-099", sec, "post-removal vs none, full-cut LOBO3 F1",
            "pv_lobo3_f1_macro_mean", F.pv_lobo3_f1_macro_mean, post, ~post, "post_rm",
            "no post_rm", "0.719 0.692"),
        _mw("T10-100", sec, "post-removal vs none, multiclass-only LOBO3 F1",
            "f1_mc_mean", F.f1_mc_mean, post, ~post, "post_rm", "no post_rm",
            "0.681 0.669"),
    ]
    elected_n = pd.Series(F.index.isin(sets["N"]), index=F.index)
    obs = F[elected_n].imp.value_counts().reindex(sorted(set(imp))).fillna(0)
    expected = imp.value_counts(normalize=True).reindex(obs.index) * obs.sum()
    chi2, p_chi = chisquare(obs, expected)
    rows.append({"claim_id": "T10-101", "section": sec,
                 "claim": "imputation composition of the class N elected set vs the "
                          "analysis set", "test": "chi-square goodness of fit",
                 "metric": "imp", "group_a": "class N elected",
                 "group_b": "analysis-set shares", "n_a": int(obs.sum()),
                 "statistic": chi2, "p_value": p_chi, "effect_name": "chi-square",
                 "quoted": "50 33 29"})
    k_post = int((elected_n & post).sum())
    bt = binomtest(k_post, int(elected_n.sum()), float(post.mean()))
    rows.append({"claim_id": "T10-102", "section": sec,
                 "claim": "post-removal share of the class N elected set vs the analysis "
                          "set", "test": "binomial (two-sided)", "metric": "post_rm",
                 "group_a": "class N elected", "n_a": int(elected_n.sum()),
                 "count_a": k_post, "prop_a": k_post / int(elected_n.sum()),
                 "prop_all": float(post.mean()), "statistic": k_post,
                 "p_value": bt.pvalue, "effect_name": "count", "quoted": "63 49"})
    rows += [
        _fisher("T10-103", sec, "K_ffpe_only share of the class N elected set",
                "class N elected", elected_n, strat == "K_ffpe_only",
                strat != "K_ffpe_only", "K_ffpe_only", "other strategies", "0"),
        _fisher("T10-104", sec, "A_confirmed_bad share of the class N elected set",
                "class N elected", elected_n, strat == "A_confirmed_bad",
                strat != "A_confirmed_bad", "A_confirmed_bad", "other strategies",
                "15"),
        _mw("T10-105", sec, "20_shambhala vs rest, full-cut LOBO3 F1",
            "pv_lobo3_f1_macro_mean", F.pv_lobo3_f1_macro_mean, sham, ~sham,
            "20_shambhala", "rest", "0.7453"),
        _mw("T10-106", sec, "20_shambhala vs rest, multiclass-only LOBO3 F1",
            "f1_mc_mean", F.f1_mc_mean, sham, ~sham, "20_shambhala", "rest", "0.7002"),
        _mw("T10-107", sec, "clustermap group vs rest, generalizability index (E1)",
            "generalizability_index", F.generalizability_index, cm, ~cm,
            "clustermap_best", "rest"),
        _mw("T10-108", sec, "13_fsmvn vs rest, full-cut LOBO3 F1",
            "pv_lobo3_f1_macro_mean", F.pv_lobo3_f1_macro_mean, meth == "13_fsmvn",
            meth != "13_fsmvn", "13_fsmvn", "rest", "0.537"),
        _mw("T10-109", sec, "13_fsmvn vs rest, multiclass-only LOBO3 F1", "f1_mc_mean",
            F.f1_mc_mean, meth == "13_fsmvn", meth != "13_fsmvn", "13_fsmvn", "rest",
            "0.624"),
    ]

    # Phase 3 re-entry (10_stat_requests_unreviewed.json, SR-U04).
    rows.append(_mw("T10-110", sec, "clustermap group vs rest, full-cut LOBO3 F1 (SR-U04)",
                    "pv_lobo3_f1_macro_mean", F.pv_lobo3_f1_macro_mean, cm, ~cm,
                    "clustermap_best", "rest", "0.629 0.709"))
    rows += reentry_tests_reviewed(F)
    out = pd.DataFrame(rows).reindex(columns=T10_COLUMNS)
    out["quoted_reproduced"] = [_quoted_reproduced(r) for r in out.to_dict("records")]
    out["tier"], out["destination"] = "supplementary", "A2_T10"
    print(f"  A2_T10: {len(out)} tests; {int((out.p_value < 0.05).sum())} at p < 0.05")
    return out


def reentry_tests_reviewed(F: pd.DataFrame) -> list[dict]:
    """Phase 3 re-entry: the tests of 10_stat_requests_reviewed.json (SR-R02 to SR-R11).

    Appended to A2_T10 as rows T10-2xx, so the catalogue stays one table.
    """
    sec = "Phase 3 re-entry (writer-reviewed)"
    strat, meth, cm = F.strat, F.method, F.is_clustermap_best
    rows = []
    for i, s in enumerate(sorted(set(strat)), 1):  # SR-R02
        rows.append(_wsr(f"T10-201-{i:02d}", sec, f"post-removal minus none, batch "
                         f"PCReg, matched, within {s} (SR-R02)", "pcr_RNA_BATCH",
                         _paired_diff(F.assign(post=F.post_rm.astype(int)),
                                      "pcr_RNA_BATCH", "post", 1, 0, ["imp", "method"],
                                      strat == s), s))
    rows += [
        _kw("T10-202", sec, "batch PCReg across imputations (SR-R03)", "pcr_RNA_BATCH",
            F.pcr_RNA_BATCH, F.imp),
        _kw("T10-203", sec, "batch PCReg across post-removal settings (SR-R03)",
            "pcr_RNA_BATCH", F.pcr_RNA_BATCH, F.post_rm.astype(str)),
        _kw("T10-204", sec, "batch kBET across strategies (SR-R04)",
            "kbet_acceptance_rate_RNA_BATCH", F.kbet_acceptance_rate_RNA_BATCH, strat),
        _mw("T10-205", sec, "C_rnaseq_only vs other strategies, batch kBET (SR-R04)",
            "kbet_acceptance_rate_RNA_BATCH", F.kbet_acceptance_rate_RNA_BATCH,
            strat == "C_rnaseq_only", strat != "C_rnaseq_only", "C_rnaseq_only",
            "other strategies"),
        _kw("T10-206", sec, "KS fraction significant across strategies (SR-R05)",
            "ks_frac_sig_RNA_BATCH", F.ks_frac_sig_RNA_BATCH, strat),
        _mw("T10-207", sec, "S0_no_removal vs other strategies, KS fraction (SR-R05)",
            "ks_frac_sig_RNA_BATCH", F.ks_frac_sig_RNA_BATCH, strat == "S0_no_removal",
            strat != "S0_no_removal", "S0_no_removal", "other strategies"),
        _kw("T10-208", sec, "biology distance ratio across strategies (SR-R06)",
            "dist_ratio_Diagnosis_cell_type_unified",
            F.dist_ratio_Diagnosis_cell_type_unified, strat),
    ]
    top = F.groupby("strat").dist_ratio_Diagnosis_cell_type_unified.mean().idxmax()
    rows.append(_mw("T10-209", sec, f"{top} vs other strategies, biology distance ratio "
                    "(SR-R06)", "dist_ratio_Diagnosis_cell_type_unified",
                    F.dist_ratio_Diagnosis_cell_type_unified, strat == top, strat != top,
                    top, "other strategies"))
    g = strat == "G_affymetrix_only"
    rows += [
        _mw("T10-210", sec, "G_affymetrix_only vs other strategies, maximum expression "
            "(SR-R07)", "exp_max", F.exp_max, g, ~g, "G_affymetrix_only",
            "other strategies"),
        _mw("T10-211", sec, "G_affymetrix_only vs other strategies, expression SD "
            "(SR-R07)", "exp_std", F.exp_std, g, ~g, "G_affymetrix_only",
            "other strategies"),
        _kw("T10-212", sec, "median expression across strategies (SR-R07)", "exp_median",
            F.exp_median, strat),
    ]
    for j, (c, end, tier, lab) in enumerate(
            [("pcr_Diagnosis_cell_type_unified", "bottom", "low", "SR-R08"),
             ("clisi_mean_Diagnosis_cell_type_unified", "top", "low", "SR-R09")], 1):
        per = [_kw(f"T10-213-{j}-{i:02d}", sec, f"{c} by harshness, within {s} ({lab})",
                   c, F[c], F.harshness_level, within=strat == s)
               for i, s in enumerate(sorted(set(strat)), 1)]
        rows += per
        k = sum(r[f"{end}_group_by_mean"] == tier for r in per)
        rows.append({"claim_id": f"T10-213-{j}-all", "section": sec,
                     "claim": f"strategies in which the {tier} tier is the {end} tier by "
                              f"mean, {c} ({lab})", "test": "binomial (two-sided), "
                              "chance 1/3", "metric": c, "n_a": len(per), "count_a": k,
                     "prop_a": k / len(per), "statistic": k,
                     "p_value": binomtest(k, len(per), 1 / 3).pvalue,
                     "effect_name": "count"})
    for i, s in enumerate(("J_ff_only", "K_ffpe_only"), 1):  # SR-R10
        rows.append(_mw(f"T10-214-{i}", sec, f"11_harmony vs other methods within {s}, "
                        "tSNE centroid dispersion (SR-R10)", "tsne_centroid_disp_RNA_BATCH",
                        F.tsne_centroid_disp_RNA_BATCH, meth == "11_harmony",
                        meth != "11_harmony", "11_harmony", "other methods",
                        within=strat == s))
    gate = (F.mk_rho_mean_markers > RHO_GATE) & (F.xb_margin > 0) & ~F.is_raw
    rows.append(_kw("T10-216", sec, "same-biology agreement gain over the baseline across "
                    "harshness tiers, gate-passing non-raw approaches (fig_markers_lm F)",
                    "xb_rank_agree_delta", F.xb_rank_agree_delta, F.harshness_level,
                    within=gate))
    for i, t in enumerate(("low", "medium", "high"), 1):
        rows.append(_fisher(f"T10-217-{i}", sec, f"share losing more than 0.1 of "
                            f"same-biology agreement, {t} tier vs the other tiers, "
                            "gate-passing non-raw", "xb_rank_agree_delta < -0.1",
                            (F.xb_rank_agree_delta < -0.1)[gate],
                            (F.harshness_level == t)[gate], (F.harshness_level != t)[gate],
                            t, "other tiers"))
    for i, c in enumerate(("ilisi_mean_RNA_BATCH",
                           "clisi_mean_Diagnosis_cell_type_unified"), 1):  # SR-R11
        rows.append(_mw(f"T10-215-{i}", sec, f"clustermap group vs rest, {c} (SR-R11)", c,
                        F[c], cm, ~cm, "clustermap_best", "rest"))
    return rows


def pca_component_means(full: pd.DataFrame) -> pd.DataFrame:
    """SR-R01: mean % variance and RNA_BATCH R² on PC1-PC10, per group (sfig_pca).

    Groups are every method, every strategy, the clustermap-selected group, and the
    unharmonized 01_raw approaches under no removal, so the per-component values the
    text quotes resolve to one row each.
    """
    cols = ([f"pct_var_pc{i}" for i in range(1, 11)]
            + [f"r2_pc{i}_RNA_BATCH" for i in range(1, 11)] + ["pcr_RNA_BATCH"])
    parts = [full.groupby("method")[cols].mean().assign(kind="method"),
             full.groupby("strat")[cols].mean().assign(kind="strategy"),
             full[full.is_clustermap_best][cols].mean().to_frame("clustermap best").T
             .assign(kind="group"),
             full[full.is_raw & (full.strat == "S0_no_removal")][cols].mean()
             .to_frame("01_raw, S0_no_removal").T.assign(kind="group")]
    out = pd.concat(parts).rename_axis("group").reset_index()
    out["tier"], out["destination"] = "supplementary", "A2_T16"
    return out


# ── A2_T11: Spearman rho and p for every scatter claim (C31, C48) ─────────────

# (panel as the legends describe it, x column, y column). The column behind each axis is
# read from the legend wording, so `panel` is a pointer for the writer, not a proof.
SCATTER_PANELS = [
    ("Figure 1A/1B", "pcr_RNA_BATCH", "pcr_Diagnosis_cell_type_unified"),
    ("Figure 2A/2B", "ilisi_mean_RNA_BATCH", "clisi_mean_Diagnosis_cell_type_unified"),
    ("Figure 3A/3B", "ks_cohort_within_batch_mean_D", "ks_mean_D_RNA_BATCH"),
    ("Supplementary Figure 2D/2E", "r2_pc1_RNA_BATCH", "pcr_RNA_BATCH"),
    ("Supplementary Figure 3A", "pcr_RNA_BATCH", "pcr_PLATFORM_RNA"),
    ("Supplementary Figure 3B", "pcr_RNA_BATCH", "pcr_COHORT_LABEL"),
    ("Supplementary Figure 3C", "pcr_RNA_BATCH", "dsc_RNA_BATCH"),
    ("Supplementary Figure 3D", "dsc_RNA_BATCH", "dsc_PLATFORM_RNA"),
    ("Supplementary Figure 3E", "dsc_RNA_BATCH", "dsc_COHORT_LABEL"),
    ("Supplementary Figure 3F-3H", "pcr_RNA_BATCH", "tsne_centroid_disp_RNA_BATCH"),
    ("Supplementary Figure 3I/3J", "pcr_RNA_BATCH", "asw_batch_RNA_BATCH"),
    ("Supplementary Figure 5A/5B", "kbet_acceptance_rate_RNA_BATCH",
     "ilisi_mean_RNA_BATCH"),
    ("Supplementary Figure 5E/5F", "ilisi_mean_RNA_BATCH",
     "tsne_entropy_norm_RNA_BATCH"),
    ("Supplementary Figure 5G/5H", "tsne_centroid_disp_RNA_BATCH",
     "tsne_entropy_norm_RNA_BATCH"),
    ("Supplementary Figure 5I/5J", "tsne_entropy_norm_RNA_BATCH",
     "umap_entropy_norm_RNA_BATCH"),
    ("Supplementary Figure 5K/5L", "tsne_centroid_disp_RNA_BATCH",
     "umap_centroid_disp_RNA_BATCH"),
    ("Supplementary Figure 6A/6B", "pcr_RNA_BATCH", "ilisi_mean_RNA_BATCH"),
    ("Supplementary Figure 6C/6D", "pcr_Diagnosis_cell_type_unified",
     "clisi_mean_Diagnosis_cell_type_unified"),
    ("Supplementary Figure 6E/6F", "pcr_RNA_BATCH", "kbet_acceptance_rate_RNA_BATCH"),
    ("Supplementary Figure 7C/7D", "graph_connectivity_PLATFORM_RNA",
     "graph_connectivity_Diagnosis_cell_type_unified"),
    ("Supplementary Figure 7E/7F", "dist_ratio_RNA_BATCH",
     "dist_ratio_Diagnosis_cell_type_unified"),
    ("Supplementary Figure 7G/7H", "wm_RNA_BATCH", "wm_Diagnosis_cell_type_unified"),
    ("Supplementary Figure 7I/7J", "wm_mean_batch", "wm_mean_bio"),
    ("Figure 4C", "mk_rho_mean_markers", "xb_margin"),
    ("Figure 4E", "xb_rank_agree_delta", "xb_rank_disagree_diffbio_delta"),
    ("Figure 5D", "pv_lobo3_f1_macro_mean", "generalizability_index"),
    ("Results, LOBO fold cuts", "pv_lobo3_f1_macro_mean", "f1_mc_mean"),
]

# The C48 scatter set: every pair among these L/M/N columns.
LMN_SCATTER_COLUMNS = [
    "mk_rho_mean_markers", "mk_rho_marker_minus_hk", "xb_rank_agree",
    "xb_rank_disagree_diffbio", "xb_margin", "xb_margin_delta",
    "pv_lobo3_f1_macro_mean", "f1_mc_mean", "pv_lobo3_auc_macro_mean",
    "pv_lobo2_f1_macro_mean", "pv_lobo2_auc_macro_mean",
]


def _spearman_row(sid, panel, x, y, subset, xs, ys):
    d = pd.DataFrame({"x": xs, "y": ys}).dropna()
    res = spearmanr(d.x, d.y)
    return {"scatter_id": sid, "panel": panel, "x": x, "y": y, "subset": subset,
            "n": len(d), "spearman_rho": float(res.statistic),
            "p_value": float(res.pvalue)}


def scatter_correlations(full: pd.DataFrame) -> pd.DataFrame:
    """Spearman rho, raw two-sided p and n for every scatterplot the text reads a trend
    from (C31), the per-strategy cut of Figure 2A that the text summarizes, and every
    pair of the C48 L/M/N set."""
    F = full
    rows = []
    for i, (panel, x, y) in enumerate(SCATTER_PANELS, 1):
        rows.append(_spearman_row(f"T11-{i:03d}", panel, x, y, "all approaches",
                                  F[x], F[y]))
    x, y = "ilisi_mean_RNA_BATCH", "clisi_mean_Diagnosis_cell_type_unified"
    for i, s in enumerate(sorted(set(F.strat)), 1):
        m = F.strat == s
        rows.append(_spearman_row(f"T11-S{i:02d}", "Figure 2A/2B, per strategy", x, y,
                                  s, F.loc[m, x], F.loc[m, y]))
    m3 = F.n_mc >= 3
    rows.append(_spearman_row("T11-M01", "Results, LOBO fold cuts",
                              "pv_lobo3_f1_macro_mean", "f1_mc_mean",
                              "n_mc >= 3", F.loc[m3, "pv_lobo3_f1_macro_mean"],
                              F.loc[m3, "f1_mc_mean"]))
    n = 0
    cols = LMN_SCATTER_COLUMNS
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            n += 1
            rows.append(_spearman_row(f"T11-L{n:02d}", "C48 L/M/N scatter (new)", a, b,
                                      "all approaches", F[a], F[b]))
    out = pd.DataFrame(rows)
    out["tier"], out["destination"] = "supplementary", "A2_T11"
    print(f"  A2_T11: {len(out)} Spearman correlations")
    return out


# ── A2_T9 / A2_T9b: harshness tiers (C44, C45, C46) ───────────────────────────

def _tier_row(df: pd.DataFrame, col: str) -> dict:
    groups = {t: df.loc[df.harshness_level == t, col].dropna() for t in TIERS}
    h, p = kruskal(*groups.values())
    n = sum(len(g) for g in groups.values())
    row = {"metric": col, "kruskal_H": h, "kruskal_p": p,
           "epsilon_sq": (h - 2) / (n - 3)}
    for t, g in groups.items():
        row |= {f"n_{t}": len(g), f"mean_{t}": g.mean(), f"median_{t}": g.median(),
                f"mad_{t}": mad(g)}
    for a, b in (("low", "medium"), ("low", "high"), ("medium", "high")):
        row[f"mw_p_{a}_{b}"] = mannwhitney(groups[a], groups[b])[1]
    medians = {t: row[f"median_{t}"] for t in TIERS}
    row["highest_tier_by_median"] = max(medians, key=medians.get)
    row["lowest_tier_by_median"] = min(medians, key=medians.get)
    return row


def harshness_table1(df: pd.DataFrame) -> pd.DataFrame:
    """Main-text Table 1: the L/M/N metrics of TABLE1_METRICS by method harshness tier.

    Means (C45 asks for means) and medians per tier, Kruskal-Wallis H and its raw p,
    and the three pairwise Mann-Whitney p-values. The per-tier n values that C46 moves
    out of the text live here and in A2_T9b.
    """
    rows = []
    for col, cls, label, cut in TABLE1_METRICS:
        rows.append({"metric_class": cls, "label": label, "fold_cut": cut}
                    | _tier_row(df, col))
    out = pd.DataFrame(rows)
    out["tier"], out["destination"] = "main", "Table 1"
    return out


def harshness_full(df: pd.DataFrame) -> pd.DataFrame:
    """Every numeric L/M/N column by harshness tier, including the permutation null.

    The `_raw` baselines are left out: they are per (strategy, imputation), not per
    method, so a tier comparison of them compares strategies rather than methods.
    """
    cols = [c for c in df.columns
            if c.startswith(("mk_", "xb_", "pv_", "f1_mc", "auc_mc"))
            and not c.endswith("_raw")
            and pd.api.types.is_numeric_dtype(df[c])
            and not pd.api.types.is_bool_dtype(df[c])
            and df[c].nunique(dropna=True) > 1]
    out = pd.DataFrame([_tier_row(df, c) for c in cols])
    out["tier"], out["destination"] = "supplementary", "A2_T9b"
    return out


# ── A2_T13: the LOBO summary, both targets, both cuts (C47) ───────────────────

def lobo_summary(df: pd.DataFrame, sets: dict) -> pd.DataFrame:
    """Main-text Table 2: named groups as medians, then the leading single approaches.

    Groups carry medians over their approaches; approach rows carry the values. Every
    row has all eight LOBO_COLUMNS, so the two fold cuts and the two targets always sit
    side by side, which is what C47 asks for in place of the superseded paragraph.
    """
    value_cols = LOBO_COLUMNS + ["f1_mc_min", "n_mc", "mk_rho_mean_markers",
                                 "generalizability_index"]
    eligible = (~df.is_confirmed_bad) & (df.n_mc >= ELIGIBLE_MIN_MC_FOLDS)
    groups = {
        "all approaches": pd.Series(True, index=df.index),
        "eligible (non-confounded, >= 5 multiclass folds)": eligible,
        "clustermap_best": df.is_clustermap_best,
        "class N elected": df.index.isin(sets["N"]),
        "class L elected": df.index.isin(sets["L"]),
        "class M elected": df.index.isin(sets["M"]),
        "ComBat family (05, 06, 08, 29)": df.method.isin(COMBAT_FAMILY),
        "20_shambhala": df.method == "20_shambhala",
    }
    rows = []
    for label, mask in groups.items():
        sub = df[np.asarray(mask)]
        rows.append({"row_type": "group (median)", "label": label,
                     "n_approaches": len(sub)} | sub[value_cols].median().to_dict())
    # One leader per strategy, as the manuscript's leading-approach table does: the top
    # four overall are three F_microarray_only variants of the same ComBat-Seq result.
    leaders = (df[eligible].sort_values("pv_lobo3_f1_macro_mean", ascending=False)
               .groupby("strat").head(1).head(4))
    index_leader = df[eligible].nlargest(1, "generalizability_index")
    confounded = df[(df.strat == "A_confirmed_bad") & (df.imp == "strict")
                    & (df.method == "29_combat_ref") & df.post_rm.astype(bool)]
    picks = [("best eligible of its strategy by full-cut LOBO3 F1", leaders),
             ("index leader among eligible (E1)", index_leader),
             ("batch-confounded, not recommended", confounded)]
    seen = set()
    for label, sub in picks:
        for rid, r in sub.iterrows():
            if rid in seen:
                continue
            seen.add(rid)
            rows.append({"row_type": "approach", "label": f"{label}: {rid}",
                         "n_approaches": 1} | r[value_cols].to_dict())
    out = pd.DataFrame(rows)
    out["tier"], out["destination"] = "main", "Table 2"
    return out


# ── A2_T3b: the election pairs with counts, sizes and a chance baseline ────────

def cross_election_pairs(sets: dict, n_total: int) -> pd.DataFrame:
    """Every pair of elected sets: both sizes, intersection, union, Jaccard, and the
    hypergeometric chance expectation with two one-sided p-values.

    The chance baseline answers "is 1 shared approach few?": two random draws of 112
    from 2,234 share 5.6 on average.
    """
    rows = []
    names = ELECTION_CLASSES
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            na, nb = len(sets[a]), len(sets[b])
            k = len(sets[a] & sets[b])
            rows.append({"set_a": a, "set_b": b, "n_a": na, "n_b": nb,
                         "n_intersection": k, "n_union": len(sets[a] | sets[b]),
                         "jaccard": k / len(sets[a] | sets[b]),
                         "expected_intersection": na * nb / n_total,
                         "p_more_than_chance": hypergeom.sf(k - 1, n_total, na, nb),
                         "p_less_than_chance": hypergeom.cdf(k, n_total, na, nb)})
    out = pd.DataFrame(rows)
    out["tier"], out["destination"] = "supplementary", "A2_T3b"
    return out


def threshold_sensitivity(df: pd.DataFrame, fracs=(0.025, 0.05, 0.10)) -> pd.DataFrame:
    """Every elected-set pair's overlap at three election thresholds (SR-U03).

    Answers whether the 5% threshold decides the ordering of the overlaps: one row per
    pair and threshold, with the Jaccard index, its rank among the 36 pairs at that
    threshold, and the Spearman rho of that threshold's 36 Jaccard values against 5%.
    """
    rows = []
    for frac in fracs:
        _, sets = cross_election_matrix(df, frac)
        names = ELECTION_CLASSES
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                u = len(sets[a] | sets[b])
                rows.append({"top_frac": frac, "set_size": len(sets["global"]),
                             "set_a": a, "set_b": b,
                             "n_intersection": len(sets[a] & sets[b]),
                             "jaccard": len(sets[a] & sets[b]) / u})
    out = pd.DataFrame(rows)
    out["rank_in_threshold"] = out.groupby("top_frac").jaccard.rank(ascending=False,
                                                                  method="min")
    ref = out[out.top_frac == 0.05].set_index(["set_a", "set_b"]).jaccard
    for frac in fracs:
        cur = out[out.top_frac == frac].set_index(["set_a", "set_b"]).jaccard
        res = spearmanr(ref, cur.reindex(ref.index))
        out.loc[out.top_frac == frac, "spearman_vs_5pct"] = res.statistic
        out.loc[out.top_frac == frac, "spearman_p_vs_5pct"] = res.pvalue
    out["tier"], out["destination"] = "supplementary", "A2_T3c"
    return out


# ── A2_T12: the metric registry mapped onto the snapshot (plan §B5, 2e) ────────

def _registry_route(name: str, snapshot_columns: set) -> tuple[str, str]:
    """How one registry metric is recovered from the snapshot (Phase 0 logic)."""
    if name in BOOLEAN_FLAGS:
        return "boolean_flag", name
    if name in snapshot_columns:
        return "direct", name
    if name.startswith("PCReg_") and "pcr_" + name[len("PCReg_"):] in snapshot_columns:
        return "rename", "pcr_" + name[len("PCReg_"):]
    if name in PERCENT_DERIVED:
        num, den = PERCENT_DERIVED[name]
        return "derived_percent", f"100 * {num} / {den}"
    for suffix in ("_raw", "_delta"):
        base = name[: -len(suffix)]
        if name.endswith(suffix) and base in snapshot_columns:
            return "derived_baseline", f"{base} vs 01_raw baseline"
    return "absent", ""


def _article2_class(column: str) -> str:
    """The Article 2 metric class of a snapshot column, by METRIC_CLASS_PREFIXES."""
    for cls, prefixes in METRIC_CLASS_PREFIXES.items():
        if column.startswith(prefixes):
            return cls
    return "unassigned"


def registry_snapshot_map(metrics_path) -> pd.DataFrame:
    """All 344 registry metrics with their snapshot column, route and Article 2 class.

    The C48 clustermap annotates metrics by type, group and class; type and group come
    from the registry, class from METRIC_CLASS_PREFIXES applied to the snapshot name.
    """
    reg = pd.read_excel(SUPP_FILE_2, sheet_name="Metric_polarity")
    snapshot_columns = set(pd.read_csv(metrics_path, nrows=0).columns)
    routes = reg["Metric"].map(lambda m: _registry_route(m, snapshot_columns))
    reg["is_metadata"] = reg["Metric group"].astype(str) == "Metadata"
    reg["route"] = np.where(reg.is_metadata, "metadata", routes.str[0])
    reg["snapshot_source"] = routes.str[1]
    reg["recoverable"] = ~reg.route.isin(["absent", "metadata"])
    reg["article2_class"] = [_article2_class(s.split(" ")[0]) if r else ""
                             for s, r in zip(reg.snapshot_source, reg.recoverable)]
    reg["is_scoring"] = reg.Polarity != 0
    out = reg[["Metric", "Polarity", "is_scoring", "Metric group", "Metric type",
               "is_metadata", "route", "snapshot_source", "recoverable",
               "article2_class"]].copy()
    n_meta = int(out.is_metadata.sum())
    print(f"  A2_T12: {len(out)} registry metrics, {len(out) - n_meta} non-metadata, "
          f"{int(out.is_scoring.sum())} scoring, {int(out.recoverable.sum())} "
          f"recoverable from the snapshot")
    out["tier"], out["destination"] = "supplementary", "A2_T12"
    return out


# ── A2_T14: dispersion of the composite contributions (C42, C43) ──────────────

def composite_dispersion(full, normed, scoring, meta) -> pd.DataFrame:
    """Contribution of each metric type, group and annotation kind to the composite,
    and how much it varies across strategies and across methods.

    A contribution is the subset's mean normalized score weighted by its share of the
    87 columns, so contributions sum to the composite (the recompute script's
    definition). The variation is reported three ways, each named, because C42 asks
    which one the text means: the range of group means with the clustermap group
    included as one more group (the definition behind the published spreads), the same
    range without it, and the standard deviation of the group means.
    """
    m = meta.loc[scoring].copy()
    bio = {"Major_group", "Diagnosis_cell_type_unified", "TUMOR_NORMAL"}
    m["kind"] = np.where(m.annot_col.isin(bio), "biology",
                         np.where(m.annot_col == "global/all", "global", "batch"))
    x = normed.loc[full.index, scoring]
    cm = full.is_clustermap_best
    rows = []
    for by in ("metric_type", "group", "kind"):
        for name, cols in m.groupby(by).groups.items():
            cols = list(cols)
            contrib = x[cols].mean(axis=1) * len(cols) / len(scoring)
            for across, key in (("strategies", full.strat), ("methods", full.method)):
                g = contrib.groupby(key).mean()
                with_best = pd.concat([g, pd.Series({"Best": contrib[cm].mean()})])
                rows.append({"by": by, "subset": name, "n_columns": len(cols),
                             "across": across, "n_groups": len(g),
                             "contribution_all": contrib.mean(),
                             "contribution_clustermap": contrib[cm].mean(),
                             "range_with_clustermap_group": with_best.max()
                             - with_best.min(),
                             "range_without_clustermap_group": g.max() - g.min(),
                             "sd_of_group_means": g.std(ddof=1)})
    out = pd.DataFrame(rows)
    out["tier"], out["destination"] = "supplementary", "A2_T14"
    return out


# ── A2_T15: the class score of every approach (C15) ───────────────────────────

def class_percentile_scores(df: pd.DataFrame, sets: dict) -> pd.DataFrame:
    """Per approach, the mean rank percentile of each metric class and its election.

    The score elect() ranks on, written out so the average percentiles the Methods
    refer to (C15) can be read for any approach: one column per class, the composite
    as the mean of the four Article 1 classes, the number of metrics behind each class,
    and one flag per class for membership in its top-5% elected set.
    """
    classes = ["global", "local", "distributional", "structural", "L", "M", "N"]
    scores = pd.DataFrame({f"score_{c}": class_score(df, c) for c in classes})
    scores["score_composite"] = scores[[f"score_{c}" for c in classes[:4]]].mean(axis=1)
    for c in classes + ["composite"]:
        scores[f"elected_{c}"] = scores.index.isin(sets[c])
    out = df[["run_id", "strat", "imp", "method", "post_rm"]].join(scores)
    counts = {c: len(class_columns(df, c)) for c in classes}
    print(f"  A2_T15: class scores for {len(out)} approaches; metrics per class {counts}")
    out["tier"], out["destination"] = "supplementary", "A2_T15"
    return out


# ── rank churn of the E1 index change ─────────────────────────────────────────

def index_rank_churn(new: pd.DataFrame, old_path: Path) -> tuple[dict, pd.DataFrame]:
    """How far the E1 index moves every approach, against the 260917 ranking.

    Both tables are ordered by the index, so a rank is its 1-based position. The
    summary answers plan decision 4: whether the top approaches change identity.
    """
    old = pd.read_csv(old_path).set_index("run_id")
    new = new.set_index("run_id")
    rank = lambda t: t.generalizability_index.rank(ascending=False, method="min")
    eligible = lambda t: (~t.is_confirmed_bad) & (t.n_mc >= ELIGIBLE_MIN_MC_FOLDS)
    per = pd.DataFrame({"index_260917": old.generalizability_index,
                        "index_260924": new.generalizability_index,
                        "rank_260917": rank(old), "rank_260924": rank(new)})
    per["rank_change"] = per.rank_260917 - per.rank_260924
    elig = new.index[eligible(new)]
    rank_e = lambda t: t.loc[elig].generalizability_index.rank(ascending=False,
                                                               method="min")
    per["eligible_rank_260917"] = rank_e(old)
    per["eligible_rank_260924"] = rank_e(new)
    top = lambda t, k, ids=None: set((t if ids is None else t.loc[ids])
                                     .generalizability_index.nlargest(k).index)
    cmb = new.index[new.is_clustermap_best]
    summary = {
        "spearman_index_260917_vs_260924": float(
            spearmanr(per.index_260917, per.index_260924, nan_policy="omit").statistic),
        "median_abs_rank_change": float(per.rank_change.abs().median()),
        "max_abs_rank_change": float(per.rank_change.abs().max()),
        "top15_overlap_all": len(top(old, 15) & top(new, 15)),
        "top40_overlap_all": len(top(old, 40) & top(new, 40)),
        "top15_overlap_eligible": len(top(old, 15, elig) & top(new, 15, elig)),
        "eligible_leader_260917": old.loc[elig].generalizability_index.idxmax(),
        "eligible_leader_260924": new.loc[elig].generalizability_index.idxmax(),
        "eligible_leader_index_260924": float(
            new.loc[elig].generalizability_index.max()),
        "clustermap_rank_range_260917": [int(rank(old)[cmb].min()),
                                         int(rank(old)[cmb].max())],
        "clustermap_rank_range_260924": [int(rank(new)[cmb].min()),
                                         int(rank(new)[cmb].max())],
        "top15_all_are_affy_post1_zero_mc_260924": bool(
            new.loc[list(top(new, 15))].eval(
                "strat == 'G_affymetrix_only' and post_rm and n_mc == 0").all()),
    }
    return summary, per.sort_values("rank_260924").reset_index()


# ── driver ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date-tag", default="260905")
    ap.add_argument("--out-dir", default="tables/")
    ap.add_argument("--stamp", default="260924",
                    help="date stamp in the output filenames; 260917 reproduces the "
                         "pre-revision tables (AUC index component, no new tables)")
    ap.add_argument("--top-frac", type=float, default=0.05)
    ap.add_argument("--run-dir", default="workflow_runs/260924_run1",
                    help="where the E1 rank-churn report is written")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = METRICS_CSV.format(tag=args.date_tag)
    legacy = args.stamp == LEGACY_STAMP
    index_columns = INDEX_COLUMNS_260917 if legacy else INDEX_COLUMNS

    print(f"article2_generalizability · snapshot {args.date_tag}")
    df = load_analysis_set(SUPP_FILE_3, metrics_path, pcreg_as_pcr=not legacy)
    print(f"  global class: {len(class_columns(df, 'global'))} metrics")
    print(f"  analysis set: {len(df)} rows | {df.method.nunique()} methods | "
          f"{df.strat.nunique()} strategies | {df.imp.nunique()} imputations")

    t0 = shambhala_identity(SUPP_FILE_3, metrics_path)
    df = add_raw_deltas(df)
    df, fold_comp = add_fold_metrics(df, FOLDS_CSV)
    if not legacy:
        folds = load_restricted_folds(df, FOLDS_CSV)
        df = add_twoclass_fold_metrics(df, folds)
    df["generalizability_index"] = generalizability_index(df, index_columns)

    matrix, sets = cross_election_matrix(df, args.top_frac)
    df["is_prediction_best"] = df.index.isin(sets["N"])

    gate = (df.mk_rho_mean_markers > RHO_GATE) & (df.xb_margin > 0)
    print(f"  joint L/M gate (rho > {RHO_GATE} and margin > 0): {int(gate.sum())} of {len(df)}")

    rho = spearmanr(df.pv_lobo3_f1_macro_mean, df.f1_mc_mean, nan_policy="omit")
    sub = df[df.n_mc >= 3]
    rho3 = spearmanr(sub.pv_lobo3_f1_macro_mean, sub.f1_mc_mean, nan_policy="omit")
    print(f"  Spearman(full F1, multiclass-only F1) = {rho.statistic:.3f} "
          f"over all {int(df.f1_mc_mean.notna().sum())} approaches carrying both; "
          f"{rho3.statistic:.3f} over the {len(sub)} with >= 3 multiclass folds")

    flags = ["run_id", "strat", "imp", "method", "post_rm", "harshness_level",
             "is_clustermap_best", "is_prediction_best", "is_confirmed_bad",
             "is_degenerate_folds", "is_raw", "n_mc", "n_folds_total",
             "frac_singleclass", "generalizability_index"]
    lmn = [c for c in df.columns if c.startswith(("mk_", "xb_", "pv_", "f1_mc", "auc_mc"))]

    ranking_cols = flags + index_columns + [f"pct_{c}" for c in index_columns]
    ranking = df.copy()
    for c in index_columns:
        ranking[f"pct_{c}"] = rank_percentile(df[c], lmn_polarity(c) or +1)
    ranking = (ranking[[c for c in ranking_cols if c in ranking.columns]]
               .sort_values("generalizability_index", ascending=False))

    stamp = args.stamp
    writes = {
        f"A2_T0_shambhala_identity_{stamp}.csv": t0,
        f"A2_T1_analysis_set_census_{stamp}.csv": df[flags + lmn],
        f"A2_T2_generalizability_ranking_{stamp}.csv": ranking,
        f"A2_T3_cross_election_matrix_{stamp}.csv": matrix,
        f"A2_T4_method_census_by_class_{stamp}.csv": method_census_by_class(df, sets),
        f"A2_T5_per_batch_folds_{stamp}.csv": per_batch_folds(df, FOLDS_CSV, sets),
        f"A2_T6_agreement_specific_{stamp}.csv": agreement_specific(df),
        f"A2_T7_harshness_by_lmn_{stamp}.csv": harshness_by_lmn(df),
        f"A2_T8_fold_composition_{stamp}.csv": fold_comp,
    }
    if not legacy:
        full = attach_snapshot_columns(df, metrics_path)
        full, normed, scoring, meta = attach_composite(full, metrics_path)
        eligible = (~ranking.is_confirmed_bad) & (ranking.n_mc >= ELIGIBLE_MIN_MC_FOLDS)
        writes |= {
            f"A2_T2b_generalizability_top_eligible_{stamp}.csv": ranking[eligible].head(15),
            f"A2_T3b_cross_election_pairs_{stamp}.csv": cross_election_pairs(sets, len(df)),
            f"A2_T9_harshness_table1_{stamp}.csv": harshness_table1(df),
            f"A2_T9b_harshness_full_{stamp}.csv": harshness_full(df),
            f"A2_T10_paired_tests_{stamp}.csv": paired_tests(full, folds, sets),
            f"A2_T11_scatter_correlations_{stamp}.csv": scatter_correlations(full),
            f"A2_T12_metric_census_{stamp}.csv": registry_snapshot_map(metrics_path),
            f"A2_T13_lobo_summary_{stamp}.csv": lobo_summary(df, sets),
            f"A2_T14_dispersion_{stamp}.csv": composite_dispersion(full, normed, scoring,
                                                                   meta),
            f"A2_T3c_threshold_sensitivity_{stamp}.csv": threshold_sensitivity(df),
            f"A2_T16_pca_component_means_{stamp}.csv": pca_component_means(full),
            f"A2_T15_class_percentile_scores_{stamp}.csv": class_percentile_scores(
                df, sets),
        }
    for name, table in writes.items():
        path = out_dir / name
        table.to_csv(path, index=name.startswith("A2_T3_"))
        print(f"  wrote {path}  ({len(table):,} rows x {table.shape[1]} cols)")
    if legacy:
        return 0

    # The tier registry makes the five-main-table budget of HARD_RULE 19 checkable.
    registry = pd.DataFrame(
        [{"table": key, "file": f"{key}_{stamp}.csv", "tier": tier,
          "main_table_number": number, "content": content,
          "rows": len(writes[f"{key}_{stamp}.csv"])}
         for key, (tier, number, content) in TABLE_REGISTRY.items()])
    n_main = int((registry.tier == "main").sum())
    assert n_main <= 5, f"{n_main} main-text tables; the budget is 5"
    too_long = registry[(registry.tier == "main") & (registry.rows > 15)]
    assert too_long.empty, f"main tables over 15 rows: {too_long.table.tolist()}"
    registry.to_csv(out_dir / f"A2_table_registry_{stamp}.csv", index=False)
    print(f"  wrote A2_table_registry_{stamp}.csv  ({n_main} main-text tables)")

    old = out_dir / f"A2_T2_generalizability_ranking_{LEGACY_STAMP}.csv"
    summary, churn = index_rank_churn(ranking, old)
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    churn.to_csv(run_dir / "12_index_rank_churn.csv", index=False)
    (run_dir / "12_index_rank_churn.json").write_text(json.dumps(summary, indent=2))
    print(f"  E1 rank churn: {json.dumps(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
