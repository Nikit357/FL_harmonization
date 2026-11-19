"""
r01_confounding_diagnostics.py — how strongly diagnosis is tied to batch (plan WP1).

Reanalysis only; no harmonization. Answers Reviewer 1, comment 1 (layers 1–3).

Inputs
------
- prepared S3 annotations `FL_batch_correction/prepared/{strategy}__strict__ann.tsv.gz`
  for the 14 strategies (cached in cache/annotations/)
- raw S0 matrix `FL_batch_correction/exp/S0_no_removal__strict__01_raw__post0.tsv.gz`
  (all 7,174 samples, strict = genes without NA, log2; cached in cache/)

Outputs (output/wp1/)
---------------------
- confounding_by_strategy.tsv   14 rows: bias-corrected Cramér's V (Bergsma 2013) and AMI
                                for RNA_BATCH × Diagnosis, RNA_BATCH × major group,
                                COHORT_LABEL × Diagnosis, PLATFORM_RNA × Diagnosis; χ² and
                                Monte-Carlo Fisher–Freeman–Halton p-values (10^4
                                simulations, seed 42); single-diagnosis batches (number,
                                samples, share); mean normalized per-batch diagnosis entropy
- batch_diagnosis_entropy.tsv   per strategy × batch: n, diagnoses, normalized entropy
- bipartite_edges.tsv           S0 batch × diagnosis edges with sample counts
- bridging_batches.tsv          S0 batches with ≥ 2 diagnoses (multi-diagnosis batches) and
                                the connected component of every batch
- variance_partition_raw.tsv    R² of batch, diagnosis and both (and the shared part
                                R²(batch) + R²(dx) − R²(batch + dx)) per gene (median, IQR)
                                and on the top 10 PCs (variance-weighted)
- variance_partition_per_gene.parquet   the per-gene values behind the summary

Filters: none. "Diagnosis" = Diagnosis_cell_type_unified (15 levels); "major group" =
DLBCL / FL / Normal B / BL / HGBCL from Major_group (Normal B = Normal_B_cells, B_cells,
Kassandra); samples without a major group (122 in S0) are dropped for that pair only.

Usage
-----
python r01_confounding_diagnostics.py [--n-sim 10000]
"""

from __future__ import annotations

import argparse
import math

import networkx as nx
import numpy as np
import pandas as pd
from scipy.special import gammaln
from scipy.stats import chi2_contingency

import revision_lib as rl

OUT_DIR = rl.OUTPUT_DIR / "wp1"
ANN_CACHE_DIR = rl.CACHE_DIR / "annotations"
RAW_S0_KEY = f"{rl.S3_PREFIX}/exp/S0_no_removal__strict__01_raw__post0.tsv.gz"
RAW_S0_CACHE = rl.CACHE_DIR / "S0_no_removal__strict__01_raw__post0.tsv.gz"
SEED = 42
N_TOP_PCS = 10

PAIRS: dict[str, tuple[str, str]] = {
    "batch_x_diagnosis": (rl.BATCH_COL, rl.BIO_COL),
    "batch_x_major_group": (rl.BATCH_COL, "major_group"),
    "cohort_x_diagnosis": (rl.COHORT_COL, rl.BIO_COL),
    "platform_x_diagnosis": (rl.PLATFORM_COL, rl.BIO_COL),
}


def load_strategy_annotation(strategy: str) -> pd.DataFrame:
    """Prepared strict annotation of one strategy (cached), with a major_group column."""
    ANN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = ANN_CACHE_DIR / f"{strategy}__strict__ann.tsv.gz"
    if not path.exists():
        rl.s3_client().download_file(  # type: ignore[attr-defined]
            rl.S3_BUCKET,
            f"{rl.S3_PREFIX}/prepared/{strategy}__strict__ann.tsv.gz",
            str(path),
        )
    ann = pd.read_csv(path, sep="\t", index_col=0, low_memory=False)
    ann["major_group"] = rl.major_group(ann, n_classes=5)
    return ann


def table_log_probability(table: np.ndarray) -> float:
    """Log probability of a contingency table under fixed margins (FFH statistic)."""
    n_total = table.sum()
    return float(
        gammaln(table.sum(axis=1) + 1).sum()
        + gammaln(table.sum(axis=0) + 1).sum()
        - gammaln(n_total + 1)
        - gammaln(table + 1).sum()
    )


def ffh_monte_carlo_pvalue(
    codes_a: np.ndarray, codes_b: np.ndarray, n_sim: int
) -> float:
    """
    Monte-Carlo Fisher–Freeman–Halton p-value: share of label permutations (margins
    fixed) whose table is at most as probable as the observed one; (k + 1) / (n + 1).
    """
    n_a, n_b = codes_a.max() + 1, codes_b.max() + 1
    observed = np.bincount(codes_a * n_b + codes_b, minlength=n_a * n_b).reshape(
        n_a, n_b
    )
    observed_logp = table_log_probability(observed)
    rng = np.random.default_rng(SEED)
    as_extreme = 0
    for _ in range(n_sim):
        shuffled = rng.permutation(codes_b)
        table = np.bincount(codes_a * n_b + shuffled, minlength=n_a * n_b).reshape(
            n_a, n_b
        )
        as_extreme += table_log_probability(table) <= observed_logp + 1e-9
    return (as_extreme + 1) / (n_sim + 1)


def pair_statistics(ann: pd.DataFrame, col_a: str, col_b: str, n_sim: int) -> dict:
    """V, AMI, χ² p and FFH p of one annotation pair."""
    frame = ann[[col_a, col_b]].dropna()
    codes_a = pd.factorize(frame[col_a])[0]
    codes_b = pd.factorize(frame[col_b])[0]
    if codes_a.max() < 1 or codes_b.max() < 1:
        return {"V": np.nan, "AMI": np.nan, "chi2_p": np.nan, "ffh_p": np.nan}
    table = pd.crosstab(frame[col_a], frame[col_b]).to_numpy()
    return {
        "V": rl.cramers_v(frame[col_a], frame[col_b]),
        "AMI": rl.adjusted_mutual_info(frame[col_a], frame[col_b]),
        "chi2_p": float(chi2_contingency(table, correction=False)[1]),
        "ffh_p": ffh_monte_carlo_pvalue(codes_a, codes_b, n_sim),
    }


def normalized_entropy(counts: pd.Series) -> float:
    """Shannon entropy of a count vector divided by log(number of levels present)."""
    p = counts[counts > 0] / counts.sum()
    return float(-(p * np.log(p)).sum() / math.log(len(p))) if len(p) > 1 else 0.0


def batch_entropy_table(ann: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Per-batch size, number of diagnoses and normalized diagnosis entropy."""
    rows = []
    for batch, group in ann.groupby(rl.BATCH_COL):
        counts = group[rl.BIO_COL].value_counts()
        rows.append(
            {
                "strategy": strategy,
                "RNA_BATCH": batch,
                "n_samples": len(group),
                "n_diagnoses": int((counts > 0).sum()),
                "normalized_entropy": normalized_entropy(counts),
            }
        )
    return pd.DataFrame(rows)


def strategy_row(ann: pd.DataFrame, strategy: str, n_sim: int) -> dict:
    """All confounding statistics of one strategy."""
    row: dict = {
        "strategy": strategy,
        "n_samples": len(ann),
        "n_batches": ann[rl.BATCH_COL].nunique(),
    }
    for name, (col_a, col_b) in PAIRS.items():
        for key, value in pair_statistics(ann, col_a, col_b, n_sim).items():
            row[f"{key}_{name}"] = value
    single = rl.single_diagnosis_batches(ann)
    in_single = ann[rl.BATCH_COL].isin(single)
    entropy = batch_entropy_table(ann, strategy)
    row.update(
        {
            "n_single_dx_batches": len(single),
            "n_samples_single_dx_batches": int(in_single.sum()),
            "pct_samples_single_dx_batches": 100.0 * in_single.mean(),
            "mean_normalized_batch_entropy": entropy["normalized_entropy"].mean(),
            "single_dx_batches": ";".join(single),
        }
    )
    return row


def bipartite_tables(ann: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Batch × diagnosis edges and per-batch component / bridging flag (S0)."""
    edges = (
        ann.groupby([rl.BATCH_COL, rl.BIO_COL]).size().rename("n_samples").reset_index()
    )
    graph = nx.Graph()
    for _, edge in edges.iterrows():
        graph.add_edge(("batch", edge[rl.BATCH_COL]), ("dx", edge[rl.BIO_COL]))
    component_of = {
        node: index
        for index, nodes in enumerate(nx.connected_components(graph), start=1)
        for node in nodes
    }
    batches = (
        edges.groupby(rl.BATCH_COL)
        .agg(
            n_samples=("n_samples", "sum"),
            n_diagnoses=(rl.BIO_COL, "nunique"),
            diagnoses=(rl.BIO_COL, lambda s: ";".join(sorted(s))),
        )
        .reset_index()
    )
    batches["bridging_batch"] = batches["n_diagnoses"] >= 2
    batches["component"] = [component_of[("batch", b)] for b in batches[rl.BATCH_COL]]
    batches["n_components_in_graph"] = nx.number_connected_components(graph)
    return edges, batches.sort_values(["bridging_batch", "n_samples"], ascending=False)


def r2_per_gene(y: np.ndarray, design: np.ndarray) -> np.ndarray:
    """R² of an OLS fit of every column of y on the design (intercept included)."""
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ coef
    total = ((y - y.mean(axis=0)) ** 2).sum(axis=0)
    return 1.0 - (residual**2).sum(axis=0) / np.where(total > 0, total, np.nan)


def variance_partition(
    exp_df: pd.DataFrame, ann: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """R² of batch, diagnosis and both, per gene and on the top 10 PCs."""
    ann = ann.loc[exp_df.index]
    batch = pd.get_dummies(ann[rl.BATCH_COL], drop_first=True, dtype=float)
    dx = pd.get_dummies(ann[rl.BIO_COL], drop_first=True, dtype=float)
    intercept = np.ones((len(ann), 1))
    designs = {
        "batch": np.hstack([intercept, batch.to_numpy()]),
        "diagnosis": np.hstack([intercept, dx.to_numpy()]),
        "batch_plus_diagnosis": np.hstack([intercept, batch.to_numpy(), dx.to_numpy()]),
    }
    values = exp_df.to_numpy(dtype=float)
    per_gene = pd.DataFrame(
        {name: r2_per_gene(values, design) for name, design in designs.items()},
        index=exp_df.columns,
    )
    per_gene["shared"] = (
        per_gene["batch"] + per_gene["diagnosis"] - per_gene["batch_plus_diagnosis"]
    )
    centred = values - values.mean(axis=0)
    u, s, _ = np.linalg.svd(centred, full_matrices=False)
    pcs = u[:, :N_TOP_PCS] * s[:N_TOP_PCS]
    weights = s[:N_TOP_PCS] ** 2 / (s**2).sum()
    pc_r2 = {name: r2_per_gene(pcs, design) for name, design in designs.items()}
    rows = []
    for name in ["batch", "diagnosis", "batch_plus_diagnosis", "shared"]:
        gene_values = per_gene[name]
        if name == "shared":
            pc_values = (
                pc_r2["batch"] + pc_r2["diagnosis"] - pc_r2["batch_plus_diagnosis"]
            )
        else:
            pc_values = pc_r2[name]
        rows.append(
            {
                "term": name,
                "gene_median_R2": gene_values.median(),
                "gene_q25_R2": gene_values.quantile(0.25),
                "gene_q75_R2": gene_values.quantile(0.75),
                "top10_PC_weighted_R2": float(
                    (pc_values * weights).sum() / weights.sum()
                ),
                "PC1_R2": float(pc_values[0]),
                "n_genes": len(gene_values),
                "n_samples": len(ann),
            }
        )
    return pd.DataFrame(rows), per_gene


def main() -> None:
    """Run every WP1 diagnostic and write the tables."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--n-sim", type=int, default=10_000)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows, entropy_tables = [], []
    for strategy in rl.ALL_STRATEGIES:
        ann = load_strategy_annotation(strategy)
        rows.append(strategy_row(ann, strategy, args.n_sim))
        entropy_tables.append(batch_entropy_table(ann, strategy))
        print(
            f"{strategy}: n={len(ann)}  V(batch × dx)="
            f"{rows[-1]['V_batch_x_diagnosis']:.3f}",
            flush=True,
        )
    pd.DataFrame(rows).to_csv(
        OUT_DIR / "confounding_by_strategy.tsv", sep="\t", index=False
    )
    pd.concat(entropy_tables).to_csv(
        OUT_DIR / "batch_diagnosis_entropy.tsv", sep="\t", index=False
    )

    ann_s0 = load_strategy_annotation("S0_no_removal")
    edges, batches = bipartite_tables(ann_s0)
    edges.to_csv(OUT_DIR / "bipartite_edges.tsv", sep="\t", index=False)
    batches.to_csv(OUT_DIR / "bridging_batches.tsv", sep="\t", index=False)
    print(
        f"bridging batches: {int(batches.bridging_batch.sum())} "
        f"({int(batches.loc[batches.bridging_batch, 'n_samples'].sum())} samples); "
        f"components: {int(batches.n_components_in_graph.iloc[0])}"
    )

    if not RAW_S0_CACHE.exists():
        rl.s3_client().download_file(  # type: ignore[attr-defined]
            rl.S3_BUCKET, RAW_S0_KEY, str(RAW_S0_CACHE)
        )
    raw = pd.read_csv(RAW_S0_CACHE, sep="\t", index_col=0)
    summary, per_gene = variance_partition(raw, ann_s0)
    summary.to_csv(OUT_DIR / "variance_partition_raw.tsv", sep="\t", index=False)
    per_gene.to_parquet(OUT_DIR / "variance_partition_per_gene.parquet")
    print(summary.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
