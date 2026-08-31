#!/usr/bin/env python
"""Recompute every statistic quoted in `Harmonization_metrics_extended.docx`.

This is the evidence behind `apply_extended_metrics_edits_v2_260802.py`. Run it to
reproduce, or to re-derive after the metric snapshot changes:

    source ~/venvs/collagen_3_11/bin/activate
    python recompute_extended_metrics_260802.py            # everything
    python recompute_extended_metrics_260802.py pcreg lisi # selected sections

Analysis set
------------
`figures_helpers.load_metrics_data()` on `metrics_comprehensive_260609.csv`, which is the
function and the file the article's figure notebook uses. It yields exactly the article's
2,234 approaches: status == ok, one canonical Shambhala representative
(`shambhala_P0std_Q0std` renamed `20_shambhala`), and `n_samples_allNA < 5% x 5,444`, which
drops `34_arsyn` and `38_harman` and leaves 31 methods over 14 strategies.

Not metrics_comprehensive_260527.csv
------------------------------------
That snapshot cannot reproduce the article. Merged against the deposited Supplementary
File 3 on (strat, imp, method, post_rm) it shares 1,822 rows and agrees on **0 of 66**
numeric columns; `n_samples` and `n_genes` differ by up to 850 and 1,309, so it was computed
on a different set of prepared matrices. It also predates strategies I, J and K. The same
merge against 260609 agrees on **79 of 79** columns. `check_snapshots()` below re-runs that
comparison.

Conventions
-----------
* MAD is the plain (unscaled) median absolute deviation, matching the manuscript.
* Per-method and per-strategy summaries in heat-map paragraphs are **means over runs**,
  matching the figures, which average across imputations and post-removal variants.
* "Best" is the 15 clustermap-selected approaches (`TOP_IDS`, post_rm = False).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import figures_helpers as fh  # noqa: E402

METRIC_TABLES = HERE.parent.parent / "harmonization-metrics" / "metric_tables"
METRICS_CSV = METRIC_TABLES / "metrics_comprehensive_260609.csv"
SUPP_FILE_3 = HERE.parent / "current_figures_tables_for_article_260802" / "Supplementary File 3.csv.gz"

# The 15 clustermap best approaches, copied verbatim from
# Finally_assembled_figures_for_article.ipynb cell 2.
TOP_IDS = [
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

# Method harshness tiers, copied verbatim from the same notebook, cell 4.
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

STRAT_SHORT = {
    "S0_no_removal": "S0", "A_confirmed_bad": "A", "B_extended_bad": "B",
    "C_rnaseq_only": "C", "D_malignant_only": "D", "E1_iterative_r1": "E1",
    "E2_iterative_r2": "E2", "E3_iterative_r3": "E3", "F_microarray_only": "F",
    "G_affymetrix_only": "G", "H_affymetrix_extended": "H",
    "I_rare_batches_removed": "I", "J_ff_only": "J", "K_ffpe_only": "K",
}

PC_VAR = [f"pct_var_pc{i}" for i in range(1, 11)]
PC_R2 = [f"r2_pc{i}_RNA_BATCH" for i in range(1, 11)]


def mad(x) -> float:
    """Plain (unscaled) median absolute deviation."""
    x = pd.Series(x).dropna()
    return float(np.median(np.abs(x - np.median(x)))) if len(x) else np.nan


def ci95(x) -> float:
    """Half-width of the normal-approximation 95% confidence interval of the mean."""
    x = pd.Series(x).dropna()
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def load():
    """Return (df_ok, df_normed, scoring_cols, col_meta) for the 2,234-approach set."""
    df_ok, df_normed, scoring_cols, col_meta = fh.load_metrics_data(METRICS_CSV)
    fh.build_best_vs_rest(df_ok, TOP_IDS)  # sets df_ok["is_best"]
    df_ok["harshness_level"] = df_ok["method"].map(HARSHNESS_LEVEL_MAP)
    df_ok["strat_short"] = df_ok["strat"].map(STRAT_SHORT)
    df_ok["composite"] = df_normed[scoring_cols].mean(axis=1)
    assert len(df_ok) == 2234, f"analysis set is {len(df_ok)} rows, expected 2,234"
    assert int(df_ok["is_best"].sum()) == 15
    assert len(scoring_cols) == 87
    return df_ok, df_normed, scoring_cols, col_meta


def by_group(df_ok, cols, key="method", agg="mean"):
    """Per-group summary with the 15 best approaches added as an extra group, `Best`."""
    best = df_ok[df_ok["is_best"]].assign(_g="Best")
    stacked = pd.concat([df_ok.assign(_g=df_ok[key]), best])
    return stacked.groupby("_g")[cols].agg(agg)


# ── sections ──────────────────────────────────────────────────────────────────

def check_snapshots():
    """Show that Supplementary File 3 matches the 260609 snapshot and not the 260527 one."""
    key = ["strat", "imp", "method", "post_rm"]
    sf3 = pd.read_csv(SUPP_FILE_3, low_memory=False)
    sf3["post_rm"] = sf3["post_rm"].astype(str)
    for name in ("metrics_comprehensive_260609.csv", "metrics_comprehensive_260527.csv"):
        other = pd.read_csv(METRIC_TABLES / name, low_memory=False)
        other["post_rm"] = other["post_rm"].astype(str)
        merged = sf3.merge(other, on=key, suffixes=("_s", "_d"))
        shared = [
            c for c in sf3.columns
            if c in other.columns and c not in key
            and pd.api.types.is_numeric_dtype(sf3[c])
        ]
        agree = total = 0
        for c in shared:
            a, b = merged[c + "_s"], merged[c + "_d"]
            both = a.notna() & b.notna()
            if both.sum() < 10:
                continue
            total += 1
            agree += int(np.allclose(a[both], b[both], rtol=1e-6, atol=1e-9))
        print(f"  Supp. File 3 vs {name}: {len(merged)} shared rows, "
              f"{agree}/{total} numeric columns agree")


def pcreg(df_ok, **_):
    batch, bio = "pcr_RNA_BATCH", "pcr_Diagnosis_cell_type_unified"
    best = df_ok[df_ok["is_best"]]
    rest = df_ok[~df_ok["is_best"]]

    d = df_ok[[batch, bio]].dropna()
    r, p = stats.spearmanr(d[batch], d[bio])
    boot = stats.bootstrap(
        (d[batch].values, d[bio].values),
        lambda a, b: stats.spearmanr(a, b).statistic,
        paired=True, n_resamples=2000, random_state=42, method="percentile",
    )
    print(f"  batch~biology Spearman r = {r:.4f}, p = {p:.3g}, n = {len(d)}, "
          f"95% CI {boot.confidence_interval.low:.4f} to {boot.confidence_interval.high:.4f}")
    for col, lab in ((batch, "batch"), (bio, "biology")):
        mw = stats.mannwhitneyu(best[col].dropna(), rest[col].dropna(),
                                alternative="two-sided").pvalue
        print(f"  best {lab}: median {best[col].median():.4f} MAD {mad(best[col]):.4f} | "
              f"rest median {rest[col].median():.4f} | Mann-Whitney p = {mw:.3g}")

    raw = df_ok[(df_ok.strat == "S0_no_removal") & (df_ok.method == "01_raw")
                & (df_ok.imp == "strict") & (~df_ok.post_rm)]
    print(f"  S0/01_raw/strict/post0: PCReg {raw[batch].iloc[0]:.6f}, "
          f"{raw.n_samples.iloc[0]} samples, {raw.n_genes.iloc[0]} genes")

    per_method = df_ok.groupby("method")[batch].agg(["min", "median", "mean", "count"])
    print("  methods with median PCReg >= 0.999:")
    print(per_method[per_method["median"] >= 0.999].round(4).to_string(header=True))
    print(f"  methods with mean PCReg batch > biology: "
          f"{int((df_ok.groupby('method')[batch].mean() > df_ok.groupby('method')[bio].mean()).sum())}"
          f" of {df_ok.method.nunique()}")

    combat = df_ok[df_ok.method.isin(["05_combat", "29_combat_ref"])
                   & df_ok.strat_short.isin(["A", "B", "I", "J", "E1", "E2", "E3"])]
    others = df_ok[~df_ok.method.isin(["05_combat", "29_combat_ref"])
                   & df_ok.strat_short.isin(["A", "B", "I", "J", "E1", "E2", "E3"])]
    print(f"  combat+combat_ref on A,B,I,J,E1-E3: median biology PCReg {combat[bio].median():.4f} "
          f"(range {combat[bio].min():.4f}-{combat[bio].max():.4f}) vs {others[bio].median():.4f}")

    print("  strategy medians (batch, biology):")
    print(df_ok.groupby("strat_short")[[batch, bio]].median().round(4).to_string())
    print("  n_diagnosis_groups per strategy (min, max):")
    print(df_ok.groupby("strat_short")["n_diagnosis_groups"].agg(["min", "max"]).to_string())

    imp = df_ok.pivot_table(index="method", columns="imp", values=batch, aggfunc="mean")
    imp["order"] = df_ok.groupby("method")[batch].mean()
    lowest11 = imp.sort_values("order").head(11)
    delta = (lowest11.softimpute - lowest11.knn) * 100
    print(f"  11 lowest-PCReg methods: strict {lowest11.strict.mean():.4f}, "
          f"knn {lowest11.knn.mean():.4f}, softimpute {lowest11.softimpute.mean():.4f}; "
          f"softimpute - knn = {delta.min():.1f} to {delta.max():.1f} pp (mean {delta.mean():.1f})")

    for s in ("C", "G", "H", "K", "F"):
        v = df_ok[df_ok.strat_short == s].groupby("method")[batch].mean()
        print(f"  strategy {s}: method-mean floor {v.min():.4f} ({v.idxmin()})")
    print("  16_fsqn_r mean PCReg per strategy:")
    print(df_ok[df_ok.method == "16_fsqn_r"].groupby("strat_short")[batch].mean().round(4).to_string())

    post = df_ok.pivot_table(index="method", columns="post_rm", values=batch, aggfunc="mean")
    post.columns = ["post0", "post1"]
    post["delta"] = post.post1 - post.post0
    print(f"  post-removal raises mean PCReg for {int((post.delta > 0).sum())} of {len(post)} "
          f"methods; median |shift| {post.delta.abs().median():.4f}")
    print(post.reindex(post.delta.abs().sort_values(ascending=False).index).head(3).round(4).to_string())
    print("  methods where post-removal lowers it:")
    print(post[post.delta < 0].round(4).to_string())


def pc_profile(df_ok, **_):
    var = by_group(df_ok, PC_VAR)
    r2 = by_group(df_ok, PC_R2)
    order = by_group(df_ok, ["pcr_RNA_BATCH"]).squeeze()
    table = pd.DataFrame({
        "PC1_var": var.pct_var_pc1, "PC2_var": var.pct_var_pc2,
        "PC1_r2": r2.r2_pc1_RNA_BATCH, "PC2_r2": r2.r2_pc2_RNA_BATCH,
        "meanPCReg": order,
    }).sort_values("PC1_var")
    print(table.round(4).to_string())

    per_method_r2 = df_ok.groupby("method")[PC_R2].mean()
    top5 = df_ok.groupby("method")["pcr_RNA_BATCH"].mean().nlargest(5).index
    worst = per_method_r2.loc[top5].stack().idxmax()
    print(f"  top-5 PCReg methods {list(top5)}: max mean R2 over all 10 PCs = "
          f"{per_method_r2.loc[top5].max().max():.6f} at {worst}")
    lower = per_method_r2[PC_R2[0]] < per_method_r2[PC_R2[1:]].max(axis=1)
    print(f"  methods with PC1 R2 below the max of PC2-PC10: {int(lower.sum())} of {len(per_method_r2)}")

    per_strat_r2 = by_group(df_ok, PC_R2, key="strat_short")
    low = per_strat_r2[PC_R2[0]] < per_strat_r2[PC_R2[1]]
    strategies_only = [i for i in per_strat_r2.index if i != "Best"]
    print(f"  strategies with PC1 R2 below PC2 R2: "
          f"{int(low.loc[strategies_only].sum())} of {len(strategies_only)}")
    print(by_group(df_ok, ["pct_var_pc1"] + PC_R2[:2], key="strat_short")
          .sort_values("pct_var_pc1").round(4).to_string())


def lisi(df_ok, **_):
    il, cl = "ilisi_mean_RNA_BATCH", "clisi_mean_Diagnosis_cell_type_unified"
    best, rest = df_ok[df_ok["is_best"]], df_ok[~df_ok["is_best"]]
    for col, lab in ((il, "iLISI batch"), (cl, "cLISI biology")):
        mw = stats.mannwhitneyu(best[col].dropna(), rest[col].dropna(),
                                alternative="two-sided").pvalue
        print(f"  {lab}: best median {best[col].median():.4f} MAD {mad(best[col]):.4f}, "
              f"all median {df_ok[col].median():.4f} MAD {mad(df_ok[col]):.4f}, "
              f"Mann-Whitney p = {mw:.3g}")
    per_method = df_ok.groupby("method")[il].agg(["median", mad]).sort_values("median")
    print(f"  best method {per_method.index[-1]} {per_method.iloc[-1].to_dict()}")
    print(f"  worst method {per_method.index[0]} {per_method.iloc[0].to_dict()}")
    print("  cLISI biology per strategy:")
    print(df_ok.groupby("strat_short")[cl].median().sort_values().round(4).to_string())

    d = df_ok[[il, cl]].dropna()
    r, p = stats.spearmanr(d[il], d[cl])
    print(f"  iLISI~cLISI Spearman r = {r:.4f}, p = {p:.3g}, n = {len(d)}")
    from statsmodels.stats.multitest import multipletests
    rows = []
    for st, sub in df_ok.groupby("strat_short"):
        dd = sub[[il, cl]].dropna()
        rr, pp = stats.spearmanr(dd[il], dd[cl])
        rows.append((st, rr, pp))
    per_strat = pd.DataFrame(rows, columns=["strat", "r", "p"])
    per_strat["fdr"] = multipletests(per_strat.p, method="fdr_bh")[1]
    sig = per_strat[per_strat.fdr < 0.05]
    print(f"  significant in {len(sig)} of {len(per_strat)} strategies "
          f"(not: {sorted(set(per_strat.strat) - set(sig.strat))}); "
          f"r {sig.r.min():.3f}-{sig.r.max():.3f}, median {sig.r.median():.3f}")

    ent, disp = "tsne_entropy_norm_RNA_BATCH", "tsne_centroid_disp_RNA_BATCH"
    e = df_ok.groupby("method")[ent].agg(["median", mad]).sort_values("median")
    print(f"  tSNE entropy best {e.index[-1]} {e.iloc[-1].round(5).to_dict()}, "
          f"worst {e.index[0]} {e.iloc[0].round(5).to_dict()}")
    print("  tSNE entropy per strategy:")
    print(df_ok.groupby("strat_short")[ent].median().sort_values(ascending=False).round(4).to_string())
    dm = by_group(df_ok, [disp]).squeeze().sort_values()
    print(f"  tSNE centroid dispersion by method: {dm.iloc[0]:.4f} ({dm.index[0]}) to "
          f"{dm.iloc[-1]:.4f} ({dm.index[-1]})")


def kbet(df_ok, **_):
    k, kp = "kbet_acceptance_rate_RNA_BATCH", "kbet_acceptance_rate_PLATFORM_RNA"
    best = df_ok[df_ok["is_best"]]
    print(f"  all approaches: {(df_ok[k] < 0.01).mean() * 100:.1f}% below 0.01, "
          f"{(df_ok[k] < 0.10).mean() * 100:.1f}% below 0.10")
    print(f"  best approaches above 0.10: {int((best[k] > 0.10).sum())} of 15 "
          f"({sorted(best.loc[best[k] > 0.10, 'method'].unique())})")
    mnn = best[best.method == "10_mnn"]
    print(f"  MNN best: iLISI {mnn.ilisi_mean_RNA_BATCH.min():.3f}-"
          f"{mnn.ilisi_mean_RNA_BATCH.max():.3f}, kBET {mnn[k].min():.4f}-{mnn[k].max():.4f}")
    c_high = df_ok[(df_ok.strat_short == "C") & (df_ok[k] > 0.6)]
    print(f"  C strategy with kBET > 0.6: {len(c_high)} approaches from "
          f"{c_high.method.nunique()} methods, kBET {c_high[k].min():.3f}-{c_high[k].max():.3f}, "
          f"iLISI {c_high.ilisi_mean_RNA_BATCH.min():.3f}-{c_high.ilisi_mean_RNA_BATCH.max():.3f}")

    per_method = df_ok.groupby("method")[[k, kp]].mean().sort_values(k, ascending=False)
    base = per_method.loc["01_raw", k]
    print(f"  01_raw mean kBET {base:.4f}; above it: "
          f"{int((per_method[k] > base).sum())}, below: {int((per_method[k] < base).sum())}")
    print(per_method.head(9).round(4).to_string())
    print(f"  kBET PLATFORM_RNA defined for {int(per_method[kp].notna().sum())} methods, "
          f"above 0.1 for {int((per_method[kp] > 0.1).sum())}; below: "
          f"{sorted(per_method.index[per_method[kp] <= 0.1])}")
    print(f"  Best group mean kBET {best[k].mean():.4f}")
    print("  strategy means:")
    print(df_ok.groupby("strat_short")[k].mean().sort_values(ascending=False).round(4).to_string())

    saturated = df_ok[df_ok.pcr_RNA_BATCH > 0.9999]
    print(f"  approaches with PCReg > 0.9999: {len(saturated)} from "
          f"{sorted(saturated.method.unique())}; {(saturated[k] < 0.1).mean() * 100:.1f}% "
          f"have kBET < 0.1")
    print("  approaches above kBET 0.1, per method:")
    print(df_ok[df_ok[k] > 0.1].groupby("method").size().sort_values(ascending=False).head(4).to_string())


def structural(df_ok, **_):
    best = df_ok[df_ok["is_best"]]
    within, between = "ks_cohort_within_batch_mean_D", "ks_mean_D_RNA_BATCH"
    print(f"  KS within-batch D: best median {best[within].median():.4f} "
          f"MAD {mad(best[within]):.4f}")
    c = df_ok[df_ok.strat_short == "C"]
    print(f"  C strategy: within {c[within].median():.4f} (MAD {mad(c[within]):.4f}), "
          f"between {c[between].median():.4f} (MAD {mad(c[between]):.4f})")

    frac = "ks_frac_sig_RNA_BATCH"
    per_method = df_ok.groupby("method")[frac].mean().sort_values()
    print(f"  KS fraction significant: 01_raw {per_method['01_raw']:.4f}, "
          f"below it {int((per_method < per_method['01_raw']).sum())} of {len(per_method)}; "
          f"below 0.7: {int((per_method < 0.7).sum())} "
          f"({per_method.index[0]} {per_method.iloc[0]:.3f} to "
          f"{per_method[per_method < 0.7].index[-1]} {per_method[per_method < 0.7].iloc[-1]:.3f}); "
          f"Best group {best[frac].mean():.4f}")
    print(df_ok.groupby("strat_short")[frac].mean().sort_values().round(4).head(4).to_string())

    na = df_ok.groupby("method")[["pct_samples_noNA", "pct_genes_noNA"]].mean()
    clean = (na.pct_samples_noNA > 99.9999) & (na.pct_genes_noNA > 99.9999)
    print(f"  methods with no missing value at all: {int(clean.sum())}")
    lost = (100 - na).round(4)
    lost.columns = ["samples_withNA_%", "genes_withNA_%"]
    print(lost[~clean].sort_values("samples_withNA_%").to_string())
    hz = df_ok[df_ok.method == "21_harmonizr"].groupby("strat_short")["pct_genes_noNA"].mean()
    print(f"  21_harmonizr loses every gene in {int((hz < 0.001).sum())} of {len(hz)} strategies")

    exp_cols = ["exp_min", "exp_median", "exp_p99", "exp_max", "exp_std"]
    per_method_exp = df_ok.groupby("method")[exp_cols].mean().sort_values("exp_max",
                                                                         ascending=False)
    print(per_method_exp.round(3).to_string())
    print(f"  methods with mean minimum below zero: "
          f"{int((per_method_exp.exp_min < 0).sum())} of {len(per_method_exp)}")
    print("  the 15 best approaches:")
    print(best[["method", "imp", "strat_short", "exp_min", "exp_median", "exp_max"]]
          .sort_values(["method", "strat_short"]).round(3).to_string(index=False))

    conn = ["graph_connectivity_Diagnosis_cell_type_unified", "graph_connectivity_PLATFORM_RNA"]
    print(f"  best graph connectivity: PLATFORM {best[conn[1]].min():.4f}-{best[conn[1]].max():.4f}, "
          f"Diagnosis {best[conn[0]].min():.4f}-{best[conn[0]].max():.4f}")
    print(df_ok.groupby("strat_short")[conn].mean().sort_values(conn[0]).round(3).to_string())

    ratio = ["dist_ratio_RNA_BATCH", "dist_ratio_Diagnosis_cell_type_unified"]
    print(f"  best distance ratio RNA_BATCH {best[ratio[0]].min():.3f}-{best[ratio[0]].max():.3f} "
          f"(median {best[ratio[0]].median():.3f}); all median {df_ok[ratio[0]].median():.3f}")
    print(df_ok.groupby("method")[ratio].mean().sort_values(ratio[0]).round(3).head(5).to_string())
    print(df_ok.groupby("strat_short")[ratio].mean().sort_values(ratio[1]).round(3).to_string())

    wm = ["wm_RNA_BATCH", "wm_Diagnosis_cell_type_unified", "wm_mean_batch", "wm_mean_bio"]
    print(df_ok.groupby("strat_short")[wm].mean().sort_values("wm_mean_batch").round(3).to_string())
    for s in ("C", "G"):
        sub = df_ok[df_ok.strat_short == s]
        print(f"  {s}: wm_mean_batch 5th-95th percentile "
              f"{sub.wm_mean_batch.quantile(.05):.3f}-{sub.wm_mean_batch.quantile(.95):.3f}")

    dsc = "dsc_RNA_BATCH"
    print(f"  DSC RNA_BATCH overall median {df_ok[dsc].median():.4f}; "
          f"best approaches below it: {int((best[dsc] < df_ok[dsc].median()).sum())} of 15")
    print(best[["method", "strat_short", dsc]].sort_values(dsc).round(4).to_string(index=False))

    asw = "asw_batch_RNA_BATCH"
    print("  ASW RNA_BATCH per strategy (lower = better batch mixing):")
    print(df_ok.groupby("strat_short")[asw].mean().sort_values().round(4).to_string())
    print("  best methods by ASW:")
    print(df_ok.groupby("method")[asw].mean().sort_values().head(3).round(4).to_string())
    g = df_ok[df_ok.strat_short == "G"]
    print(f"  G strategy: ASW {g[asw].quantile(.05):.3f}-{g[asw].quantile(.95):.3f}, "
          f"PCReg {g.pcr_RNA_BATCH.quantile(.05):.3f}-{g.pcr_RNA_BATCH.quantile(.95):.3f}")
    harmony = df_ok[(df_ok.method == "11_harmony") & df_ok.strat_short.isin(["J", "K"])]
    disp = "tsne_centroid_disp_RNA_BATCH"
    print(f"  11_harmony in J/K: tSNE centroid dispersion "
          f"{harmony[disp].min():.3f}-{harmony[disp].max():.3f}; "
          f"J-wide median {df_ok[df_ok.strat_short == 'J'][disp].median():.3f}, "
          f"K-wide {df_ok[df_ok.strat_short == 'K'][disp].median():.3f}")
    g_post = df_ok[df_ok.strat_short == "G"]
    print(f"  G strategy PCReg median: post0 {g_post[~g_post.post_rm].pcr_RNA_BATCH.median():.3f}, "
          f"post1 {g_post[g_post.post_rm].pcr_RNA_BATCH.median():.3f}")


def harshness(df_ok, **_):
    panels = [
        ("A", "pcr_RNA_BATCH", True),
        ("B", "pcr_Diagnosis_cell_type_unified", False),
        ("C", "tsne_entropy_norm_RNA_BATCH", True),
        ("D", "ilisi_mean_RNA_BATCH", True),
        ("E", "clisi_mean_Diagnosis_cell_type_unified", False),
        ("F", "ks_frac_sig_RNA_BATCH", False),
    ]
    for panel, col, higher_is_better in panels:
        t = df_ok.pivot_table(index="strat_short", columns="harshness_level",
                              values=col, aggfunc="mean")
        best_lvl = t.idxmax(axis=1) if higher_is_better else t.idxmin(axis=1)
        worst_lvl = t.idxmin(axis=1) if higher_is_better else t.idxmax(axis=1)
        print(f"  panel {panel} ({col}, {'higher' if higher_is_better else 'lower'} better): "
              f"best {best_lvl.value_counts().to_dict()}, worst {worst_lvl.value_counts().to_dict()}")


def composite(df_ok, df_normed=None, scoring_cols=None, col_meta=None, **_):
    best = df_ok[df_ok["is_best"]]
    comp = df_ok["composite"]
    print(f"  composite: mean {comp.mean():.4f}, median {comp.median():.4f}, "
          f"range {comp.min():.4f}-{comp.max():.4f}; Best group {best.composite.mean():.4f}")
    print(by_group(df_ok, ["composite"], key="strat_short")
          .sort_values("composite", ascending=False).round(4).to_string())
    print(by_group(df_ok, ["composite"]).sort_values("composite", ascending=False)
          .head(8).round(4).to_string())
    print(f"  above 0.6: {int((comp > 0.6).sum())} of {len(comp)} "
          f"({(comp > 0.6).mean() * 100:.1f}%); best approaches among them "
          f"{int((best.composite > 0.6).sum())} of 15")

    meta = col_meta.loc[scoring_cols]

    def contribution(by, index_key):
        """Share of the composite supplied by each subset of the scoring columns.

        Each subset's mean score is weighted by its share of the 87 columns, so the
        contributions sum exactly to the composite.
        """
        frames = {}
        for name, cols in meta.groupby(by).groups.items():
            cols = list(cols)
            per_row = df_normed.loc[df_ok.index, cols].mean(axis=1) * len(cols) / len(scoring_cols)
            frames[name] = per_row.groupby(index_key).mean()
        return pd.DataFrame(frames)

    for by in ("metric_type", "group"):
        print(f"  contribution by {by}:")
        for key, label in ((df_ok["strat_short"], "strategy"), (df_ok["method"], "method")):
            table = contribution(by, key)
            best_row = contribution(by, pd.Series("Best", index=df_ok.index)).loc["Best"]
            table.loc["Best"] = best_row
            table["total"] = table.sum(axis=1)
            table = table.sort_values("total", ascending=False)
            print(f"    -- by {label} --")
            print(table.round(4).to_string())
            spread = (table.drop(columns="total").max() - table.drop(columns="total").min())
            print(f"    spread across {label}s: {spread.round(4).to_dict()}")

    bio_cols = {"Major_group", "Diagnosis_cell_type_unified", "TUMOR_NORMAL"}
    kind = np.where(meta.annot_col.isin(bio_cols), "biology",
                    np.where(meta.annot_col == "global/all", "global", "batch"))
    meta_kind = meta.assign(kind=kind)
    print(f"  scoring columns by kind: "
          f"{meta_kind.kind.value_counts().to_dict()} of {len(scoring_cols)}")
    frames = {}
    for name, cols in meta_kind.groupby("kind").groups.items():
        cols = list(cols)
        per_row = df_normed.loc[df_ok.index, cols].mean(axis=1) * len(cols) / len(scoring_cols)
        frames[name] = per_row.groupby(df_ok["strat_short"]).mean()
    kinds = pd.DataFrame(frames)
    kinds["total"] = kinds.sum(axis=1)
    print(kinds.sort_values("total", ascending=False).round(4).to_string())
    share = kinds.drop(columns="total").div(kinds.total, axis=0) * 100
    print("  share of the composite (%):")
    print(share.round(1).agg(["min", "max"]).to_string())


SECTIONS = {
    "snapshots": lambda **kw: check_snapshots(),
    "pcreg": pcreg,
    "pc_profile": pc_profile,
    "lisi": lisi,
    "kbet": kbet,
    "structural": structural,
    "harshness": harshness,
    "composite": composite,
}


def main(argv):
    wanted = argv[1:] or list(SECTIONS)
    unknown = [s for s in wanted if s not in SECTIONS]
    if unknown:
        raise SystemExit(f"unknown section(s) {unknown}; choose from {list(SECTIONS)}")
    df_ok, df_normed, scoring_cols, col_meta = load()
    for name in wanted:
        print(f"\n{'=' * 78}\n{name}\n{'=' * 78}")
        SECTIONS[name](df_ok=df_ok, df_normed=df_normed,
                       scoring_cols=scoring_cols, col_meta=col_meta)


if __name__ == "__main__":
    main(sys.argv)
