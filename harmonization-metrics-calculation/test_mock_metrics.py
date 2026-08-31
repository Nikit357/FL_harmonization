"""
test_mock_metrics.py — Smoke tests for compute_batch_metrics.

Creates synthetic expression/annotation data, runs compute_all_metrics,
and asserts key correctness properties.

Usage
-----
python test_mock_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from compute_batch_metrics import (
    XB_MAX_SAMPLES,
    compute_all_metrics,
    compute_group_i,
    compute_group_j,
    compute_group_k,
    compute_group_l,
    compute_group_m,
    compute_group_n,
)
from marker_panels import housekeeping_genes, panel_genes
from run_metrics_job import GROUP_SENTINEL_KEYS, _groups_to_recompute

RNG = np.random.default_rng(42)


def _make_data(
    n_samples: int = 80,
    n_genes: int = 200,
    n_batches: int = 3,
    n_cohorts: int = 2,
    n_diag: int = 2,
    batch_effect_strength: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Synthetic dataset for smoke testing.

    Parameters
    ----------
    batch_effect_strength
        0.0 = random assignment (no batch effect),
        >0.0 = genes drawn from different distributions per batch.
    """
    sample_ids = [f"S{i:04d}" for i in range(n_samples)]
    gene_ids = [f"GENE{j:04d}" for j in range(n_genes)]

    batches = [f"batch_{b}" for b in range(n_batches)]
    cohorts = [f"cohort_{c}" for c in range(n_cohorts)]
    diagnoses = [f"DX_{d}" for d in range(n_diag)]
    platforms = ["RNASeq", "Microarray"]
    rna_sources = ["FF", "FFPE"]

    batch_labels = RNG.choice(batches, n_samples)
    cohort_labels = RNG.choice(cohorts, n_samples)
    diag_labels = RNG.choice(diagnoses, n_samples)
    platform_labels = RNG.choice(platforms, n_samples)
    source_labels = RNG.choice(rna_sources, n_samples)
    tumor_normal = RNG.choice(["Tumor", "Normal"], n_samples)

    if batch_effect_strength > 0:
        base = RNG.normal(0, 1, (n_samples, n_genes))
        # Per-gene per-batch random offsets so batch effect spans multiple PCs
        batch_offsets = RNG.normal(0, batch_effect_strength, (n_batches, n_genes))
        for b_idx, batch in enumerate(batches):
            mask = batch_labels == batch
            base[mask] += batch_offsets[b_idx]
        exp_values = base
    else:
        exp_values = RNG.normal(0, 1, (n_samples, n_genes))

    exp_df = pd.DataFrame(exp_values, index=sample_ids, columns=gene_ids)
    ann_df = pd.DataFrame(
        {
            "RNA_BATCH": batch_labels,
            "PLATFORM_RNA": platform_labels,
            "RNASEQ_SOURCE": source_labels,
            "COHORT_LABEL": cohort_labels,
            "Major_group": diag_labels,
            "Diagnosis_cell_type_unified": diag_labels,
            "TUMOR_NORMAL": tumor_normal,
        },
        index=sample_ids,
    )
    return exp_df, ann_df


PASS = 0
FAIL = 0


def _check(condition: bool, name: str, msg: str = "") -> None:
    global PASS, FAIL
    if condition:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}  {msg}")
        FAIL += 1


def test_all_keys_present() -> None:
    print("\n--- test_all_keys_present ---")
    exp_df, ann_df = _make_data()
    result = compute_all_metrics(exp_df, ann_df, skip_slow=True)

    expected_keys = [
        # E1
        "n_samples",
        "n_genes",
        # E2
        "n_batches",
        "n_cohorts",
        "n_samples_per_batch_min",
        "n_samples_per_batch_max",
        # E3
        "zero_fraction_global",
        "fraction_genes_below_1",
        "below_1_fraction_by_batch_max",
        "below_1_fraction_by_batch_min",
        # E4
        "exp_min",
        "exp_max",
        "exp_median",
        "exp_std",
        "exp_p01",
        "exp_p99",
        "per_batch_median_cv",
        "n_cohorts_bimodal",
        "fraction_cohorts_bimodal",
        # A1
        "r2_RNA_BATCH",
        "r2_Major_group",
        # A2
        "r2_pc1_RNA_BATCH",
        # A3
        "pcr_RNA_BATCH",
        "pcr_Major_group",
        # A4
        "dsc_RNA_BATCH",
        "dsc_pvalue_RNA_BATCH",
        # B1
        "kbet_acceptance_rate_RNA_BATCH",
        # B2
        "ilisi_mean_RNA_BATCH",
        "ilisi_norm_RNA_BATCH",
        # B3
        "clisi_mean_Major_group",
        # B4
        "asw_batch_RNA_BATCH",
        "asw_batch_norm_RNA_BATCH",
        # B5
        "asw_bio_Major_group",
        "asw_bio_norm_Major_group",
        # B6
        "cms_mean_RNA_BATCH",
        # C1
        "umap_centroid_disp_RNA_BATCH",
        # C2 UMAP
        "umap_entropy_mean_RNA_BATCH",
        "umap_entropy_norm_RNA_BATCH",
        # C3
        "tsne_centroid_disp_RNA_BATCH",
        # C2 tSNE
        "tsne_entropy_mean_RNA_BATCH",
        # D1
        "ks_mean_D_RNA_BATCH",
        "ks_frac_sig_RNA_BATCH",
        # D2
        "ks_cohort_within_batch_mean_D",
        # D3
        "per_gene_batch_mean_cv_RNA_BATCH",
        "per_gene_batch_mean_cv_COHORT_LABEL",
        "per_gene_batch_mean_cv_PLATFORM_RNA",
        # G
        "graph_connectivity_Major_group",
        # H
        "avg_intra_dist_RNA_BATCH",
        "avg_inter_dist_RNA_BATCH",
        "dist_ratio_RNA_BATCH",
    ]
    for k in expected_keys:
        _check(k in result, f"key_present:{k}")


def test_random_batch_low_r2() -> None:
    print("\n--- test_random_batch_low_r2 ---")
    exp_df, ann_df = _make_data(n_samples=80, batch_effect_strength=0.0)
    result = compute_all_metrics(exp_df, ann_df, skip_slow=True)
    r2 = result.get("r2_RNA_BATCH")
    _check(r2 is not None and r2 < 0.30, "r2_RNA_BATCH<0.30_for_random", f"got {r2}")


def test_strong_batch_high_r2() -> None:
    print("\n--- test_strong_batch_high_r2 ---")
    # 10 batches → batch effect spans up to 9 PCs; per-gene offsets make it high-rank
    exp_df, ann_df = _make_data(n_samples=200, n_batches=10, batch_effect_strength=5.0)
    result = compute_all_metrics(exp_df, ann_df, skip_slow=True)
    r2 = result.get("r2_RNA_BATCH")
    _check(
        r2 is not None and r2 > 0.5, "r2_RNA_BATCH>0.50_for_strong_batch", f"got {r2}"
    )


def test_group_failure_isolation() -> None:
    """A patched failure in one group must not prevent other groups from running."""
    print("\n--- test_group_failure_isolation ---")
    import compute_batch_metrics as _mod

    original = _mod.compute_group_a

    def _bad_group_a(*_args: object, **_kw: object) -> dict:
        raise RuntimeError("Simulated group A failure")

    _mod.compute_group_a = _bad_group_a  # type: ignore[assignment]
    try:
        exp_df, ann_df = _make_data()
        result = compute_all_metrics(exp_df, ann_df, skip_slow=True)
        _check("error_A" in result, "error_A_recorded_on_failure")
        _check("n_samples" in result, "group_E_ran_despite_A_failure")
        _check(
            "graph_connectivity_Major_group" in result, "group_G_ran_despite_A_failure"
        )
    finally:
        _mod.compute_group_a = original  # type: ignore[assignment]


def test_degenerate_single_batch() -> None:
    """When only one batch is present, batch metrics should return None/nan, not crash."""
    print("\n--- test_degenerate_single_batch ---")
    exp_df, ann_df = _make_data()
    ann_df["RNA_BATCH"] = "single_batch"
    result = compute_all_metrics(exp_df, ann_df, skip_slow=True)
    r2 = result.get("r2_RNA_BATCH")
    _check(
        r2 is None or (isinstance(r2, float) and __import__("math").isnan(r2)),
        "r2_RNA_BATCH_nan_for_single_batch",
        f"got {r2}",
    )
    _check("n_samples" in result, "descriptive_stats_present_despite_degenerate_batch")


def _make_pca(
    exp_df: pd.DataFrame, n_components: int = 20
) -> tuple[np.ndarray, np.ndarray]:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    X = StandardScaler().fit_transform(exp_df.values.astype(float))
    pca = PCA(
        n_components=min(n_components, X.shape[0] - 1, X.shape[1]), random_state=42
    )
    coords = pca.fit_transform(X)
    return coords, pca.explained_variance_


def test_incremental_groups_to_recompute() -> None:
    print("\n--- test_incremental_groups_to_recompute ---")
    prior_with_e = {"n_samples": 100, "status": "ok"}
    prior_with_e_and_j = {"n_samples": 100, "pct_var_pc1": 45.0, "status": "ok"}

    result = _groups_to_recompute(prior_with_e, {"E", "J"})
    _check(result == {"J"}, "only_J_missing_when_E_present", f"got {result}")

    result = _groups_to_recompute(prior_with_e_and_j, {"E", "J"})
    _check(result == set(), "empty_when_both_present", f"got {result}")

    result = _groups_to_recompute(None, {"E", "J", "K"})
    _check(result == {"E", "J", "K"}, "all_returned_when_no_prior", f"got {result}")

    prior_null_val = {"n_samples": None, "status": "ok"}
    result = _groups_to_recompute(prior_null_val, {"E"})
    _check("E" in result, "recompute_when_sentinel_is_None", f"got {result}")

    # --force-groups: bypasses the sentinel check for named groups only.
    result = _groups_to_recompute(prior_with_e_and_j, {"E", "J"}, force_groups={"J"})
    _check(result == {"J"}, "force_groups_recomputes_present_sentinel", f"got {result}")

    result = _groups_to_recompute(prior_with_e_and_j, {"E", "J"}, force_groups=set())
    _check(result == set(), "empty_force_groups_is_a_no_op", f"got {result}")

    result = _groups_to_recompute(prior_with_e_and_j, {"E"}, force_groups={"J"})
    _check(
        "J" not in result,
        "force_groups_has_no_effect_outside_requested_groups",
        f"got {result}",
    )

    _check("E" in GROUP_SENTINEL_KEYS, "sentinel_E_defined")
    _check("J" in GROUP_SENTINEL_KEYS, "sentinel_J_defined")
    _check("K" in GROUP_SENTINEL_KEYS, "sentinel_K_defined")
    _check("I" in GROUP_SENTINEL_KEYS, "sentinel_I_defined")


def test_group_j_pc_variance() -> None:
    print("\n--- test_group_j_pc_variance ---")
    exp_df, _ = _make_data(n_samples=60, n_genes=100)
    pca_coords, eigenvalues = _make_pca(exp_df, n_components=20)

    result = compute_group_j(pca_coords, eigenvalues)

    _check("pct_var_pc1" in result, "key_pct_var_pc1_present")
    _check("pct_var_cum_top10" in result, "key_pct_var_cum_top10_present")

    pct_vals = [result[f"pct_var_pc{i}"] for i in range(1, 11)]
    _check(all(v is not None for v in pct_vals), "all_pc_values_not_none")

    ordered = all(pct_vals[i] >= pct_vals[i + 1] for i in range(len(pct_vals) - 1))
    _check(ordered, "pc_variance_descending_order", f"values={pct_vals[:5]}")

    cum_from_sum = round(sum(pct_vals), 6)
    cum_stored = round(float(result["pct_var_cum_top10"]), 6)
    _check(
        abs(cum_from_sum - cum_stored) < 0.01,
        "cum_top10_equals_sum",
        f"{cum_from_sum} vs {cum_stored}",
    )

    _check(float(result["pct_var_cum_top10"]) <= 100.0 + 1e-6, "cum_top10_le_100")


def test_group_k_dropna_metrics() -> None:
    print("\n--- test_group_k_dropna_metrics ---")
    exp_df, ann_df = _make_data(n_samples=50, n_genes=80)

    result_clean = compute_group_k(exp_df, ann_df)
    _check(result_clean["pct_genes_noNA"] == 100.0, "clean_pct_genes_noNA_100")
    _check(result_clean["pct_samples_noNA"] == 100.0, "clean_pct_samples_noNA_100")
    _check(result_clean["n_genes_allNA"] == 0, "clean_n_genes_allNA_0")
    _check(result_clean["n_samples_allNA"] == 0, "clean_n_samples_allNA_0")
    _check(result_clean["n_na_cells"] == 0, "clean_n_na_cells_0")

    exp_one_gene_na = exp_df.copy()
    exp_one_gene_na.iloc[:, 0] = float("nan")
    result_gene_na = compute_group_k(exp_one_gene_na, ann_df)
    _check(
        result_gene_na["n_genes_allNA"] == 1,
        "one_gene_all_na_detected",
        f"got {result_gene_na['n_genes_allNA']}",
    )
    _check(
        result_gene_na["pct_genes_noNA"] < 100.0,
        "pct_genes_noNA_drops_when_gene_all_na",
    )

    exp_one_sample_na = exp_df.copy()
    exp_one_sample_na.iloc[0, :] = float("nan")
    result_sample_na = compute_group_k(exp_one_sample_na, ann_df)
    _check(
        result_sample_na["n_samples_allNA"] == 1,
        "one_sample_all_na_detected",
        f"got {result_sample_na['n_samples_allNA']}",
    )
    _check(
        result_sample_na["pct_samples_noNA"] < 100.0,
        "pct_samples_noNA_drops_when_sample_all_na",
    )

    n_s, n_g = exp_df.shape
    na_count = n_s * n_g // 10
    flat_idx = RNG.choice(n_s * n_g, na_count, replace=False)
    rows, cols = flat_idx // n_g, flat_idx % n_g
    arr_partial = exp_df.to_numpy().copy()
    arr_partial[rows, cols] = float("nan")
    exp_partial_na = pd.DataFrame(
        arr_partial, index=exp_df.index, columns=exp_df.columns
    )
    result_partial = compute_group_k(exp_partial_na, ann_df)
    _check(
        abs(result_partial["n_na_cells"] - na_count) <= 2,
        "n_na_cells_correct_for_partial_na",
        f"expected ~{na_count}, got {result_partial['n_na_cells']}",
    )


def test_group_i_wm_score() -> None:
    print("\n--- test_group_i_wm_score ---")
    n_per_class = 50
    n_genes = 150

    # Well-separated: two classes with very different gene expression
    exp_sep = pd.DataFrame(
        np.vstack(
            [
                RNG.normal(5, 0.5, (n_per_class, n_genes)),
                RNG.normal(-5, 0.5, (n_per_class, n_genes)),
            ]
        ),
        columns=[f"G{i}" for i in range(n_genes)],
    )
    ann_sep = pd.DataFrame(
        {
            "RNA_BATCH": ["batch_A"] * n_per_class + ["batch_B"] * n_per_class,
            "PLATFORM_RNA": ["RNASeq"] * (2 * n_per_class),
            "RNASEQ_SOURCE": ["FF"] * (2 * n_per_class),
            "COHORT_LABEL": ["C1"] * (2 * n_per_class),
            "Major_group": ["class_0"] * n_per_class + ["class_1"] * n_per_class,
            "Diagnosis_cell_type_unified": ["class_0"] * n_per_class
            + ["class_1"] * n_per_class,
            "TUMOR_NORMAL": ["Tumor"] * n_per_class + ["Normal"] * n_per_class,
        },
        index=exp_sep.index,
    )

    pca_sep, _ = _make_pca(exp_sep, n_components=10)
    result_sep = compute_group_i(
        exp_sep, ann_sep, pca_sep, n_permutations=50, max_samples=500
    )

    wm_bio = result_sep.get("wm_Major_group")
    _check(
        wm_bio is not None and float(wm_bio) > 0.3,
        "wm_bio_high_for_separated",
        f"got {wm_bio}",
    )

    # Random data: WM should be near 0 for random labels
    exp_rand, ann_rand = _make_data(n_samples=80, n_genes=80, batch_effect_strength=0.0)
    pca_rand, _ = _make_pca(exp_rand, n_components=10)
    result_rand = compute_group_i(
        exp_rand, ann_rand, pca_rand, n_permutations=50, max_samples=500
    )

    wm_batch_rand = result_rand.get("wm_RNA_BATCH")
    _check(
        wm_batch_rand is not None and float(wm_batch_rand) < 0.15,
        "wm_batch_near_zero_for_random",
        f"got {wm_batch_rand}",
    )

    # Subsampling: N > max_samples should set wm_subsampled=True
    exp_large, ann_large = _make_data(n_samples=120, n_genes=50)
    pca_large, _ = _make_pca(exp_large, n_components=10)
    result_large = compute_group_i(
        exp_large, ann_large, pca_large, n_permutations=20, max_samples=100
    )
    _check(
        result_large.get("wm_subsampled") is True,
        "wm_subsampled_True_when_N_exceeds_limit",
    )
    _check("wm_RNA_BATCH" in result_large, "wm_RNA_BATCH_present_after_subsampling")

    # Ratio metric: bio WM > batch WM should give ratio > 0
    ratio = result_sep.get("wm_ratio_bio_batch")
    _check(ratio is not None, "wm_ratio_bio_batch_present")

    # Keys present
    for col in [
        "RNA_BATCH",
        "PLATFORM_RNA",
        "RNASEQ_SOURCE",
        "COHORT_LABEL",
        "Major_group",
        "Diagnosis_cell_type_unified",
        "TUMOR_NORMAL",
    ]:
        _check(f"wm_{col}" in result_sep, f"key_wm_{col}_present")
    _check("wm_mean_batch" in result_sep, "key_wm_mean_batch_present")
    _check("wm_mean_bio" in result_sep, "key_wm_mean_bio_present")


def test_new_keys_in_compute_all() -> None:
    print("\n--- test_new_keys_in_compute_all ---")
    exp_df, ann_df = _make_data(n_samples=60, n_genes=80)
    result = compute_all_metrics(exp_df, ann_df, skip_slow=True)

    for k in ["pct_var_pc1", "pct_var_pc10", "pct_var_cum_top10"]:
        _check(k in result, f"key_in_compute_all:{k}")
    for k in [
        "n_genes_noNA",
        "pct_genes_noNA",
        "n_samples_noNA",
        "pct_samples_noNA",
        "n_genes_allNA",
        "n_samples_allNA",
        "n_na_cells",
        "pct_na_cells",
    ]:
        _check(k in result, f"key_in_compute_all:{k}")
    _check("wm_RNA_BATCH" in result, "wm_in_default_compute_all")

    result_no_wm = compute_all_metrics(
        exp_df,
        ann_df,
        skip_slow=True,
        groups={"E", "J", "K", "A", "B", "C", "G", "H", "D"},
    )
    _check("wm_RNA_BATCH" not in result_no_wm, "wm_absent_when_I_excluded_from_groups")


# ── Groups L / M / N — blind final check ─────────────────────────────────────


def _make_panel_data(
    n_per_batch: int = 60,
    n_batches: int = 4,
    n_genes: int = 80,
    bio_strength: float = 1.5,
    batch_strength: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Synthetic data whose gene names come from the real marker panel.

    Groups L and M intersect the panel with the matrix columns, so the columns must
    be real marker symbols or the panel resolves to nothing.
    """
    genes = panel_genes(include_housekeeping=True)[:n_genes]
    n = n_per_batch * n_batches
    idx = [f"S{i:04d}" for i in range(n)]

    bio = np.array(["FL", "DLBCL"] * (n // 2))[:n]
    bio_full = np.where(
        bio == "FL", "Follicular_Lymphoma", "Diffuse_Large_B_Cell_Lymphoma"
    )
    bio_axis = RNG.normal(0, 1, len(genes))
    X = RNG.normal(0, 0.4, (n, len(genes)))
    X += np.where(bio == "FL", 1, -1)[:, None] * bio_axis[None, :] * bio_strength

    batch_labels = np.repeat([f"b{b}" for b in range(n_batches)], n_per_batch)
    if batch_strength > 0:
        offsets = RNG.normal(0, batch_strength, (n_batches, len(genes)))
        for b in range(n_batches):
            X[batch_labels == f"b{b}"] += offsets[b]

    exp_df = pd.DataFrame(X, index=idx, columns=genes)
    ann_df = pd.DataFrame(
        {
            "RNA_BATCH": batch_labels,
            "COHORT_LABEL": batch_labels,
            "PLATFORM_RNA": "RNASeq",
            "RNASEQ_SOURCE": "FF",
            "Major_group": bio_full,
            "Diagnosis_cell_type_unified": bio_full,
            "TUMOR_NORMAL": "Tumor",
        },
        index=idx,
    )
    return exp_df, ann_df


def test_group_l_correlation_preservation() -> None:
    print("\n--- test_group_l_correlation_preservation ---")
    exp_df, ann_df = _make_panel_data()

    identity = compute_group_l(exp_df, exp_df, ann_df)
    rho = identity.get("mk_rho_mean_all_genes")
    _check(rho is not None and abs(rho - 1.0) < 1e-9, "identity_rho_is_1", f"got {rho}")
    _check(identity.get("mk_is_self_reference") is True, "self_reference_flagged")
    _check(identity.get("mk_n_panel_genes_used", 0) > 0, "panel_genes_resolved")

    # A per-batch constant added to each gene leaves within-cohort ranks untouched.
    # This is the documented ceiling of Group L, asserted so it cannot regress silently.
    shifted = exp_df.copy()
    for b in ann_df["RNA_BATCH"].unique():
        mask = (ann_df["RNA_BATCH"] == b).values
        shifted.loc[mask] = shifted.loc[mask].values + RNG.normal(
            0, 3.0, exp_df.shape[1]
        )
    shift_res = compute_group_l(shifted, exp_df, ann_df)
    rho_shift = shift_res.get("mk_rho_mean_all_genes")
    _check(
        rho_shift is not None and rho_shift > 0.999,
        "per_batch_shift_preserves_rho",
        f"got {rho_shift}",
    )

    # Permuting samples inside a cohort must destroy the correlation.
    shuffled = exp_df.copy()
    for b in ann_df["COHORT_LABEL"].unique():
        mask = (ann_df["COHORT_LABEL"] == b).values
        block = shuffled.loc[mask].values.copy()
        RNG.shuffle(block)
        shuffled.loc[mask] = block
    shuf_res = compute_group_l(shuffled, exp_df, ann_df)
    rho_shuf = shuf_res.get("mk_rho_mean_all_genes")
    _check(
        rho_shuf is not None and abs(rho_shuf) < 0.30,
        "shuffle_destroys_rho",
        f"got {rho_shuf}",
    )


def test_group_l_per_gene_keys() -> None:
    print("\n--- test_group_l_per_gene_keys ---")
    exp_df, ann_df = _make_panel_data(n_genes=40)
    res = compute_group_l(exp_df, exp_df, ann_df)

    by_gene = res.get("mk_rho_by_gene")
    _check(isinstance(by_gene, dict), "mk_rho_by_gene_is_dict")
    _check(
        len(by_gene) == res["mk_n_panel_genes_used"],
        "one_entry_per_resolved_gene",
        f"{len(by_gene)} vs {res['mk_n_panel_genes_used']}",
    )
    _check(all(g in exp_df.columns for g in by_gene), "gene_keys_are_matrix_columns")
    counts = res.get("mk_rho_n_cohorts_by_gene")
    _check(
        isinstance(counts, dict) and set(counts) == set(by_gene),
        "cohort_counts_match_gene_keys",
    )
    _check(isinstance(res.get("mk_rho_by_cohort"), dict), "mk_rho_by_cohort_is_dict")

    hk_present = set(by_gene) & set(housekeeping_genes())
    _check(
        bool(hk_present)
        == (
            res.get("mk_rho_mean_housekeeping") is not None
            and not np.isnan(res["mk_rho_mean_housekeeping"])
        ),
        "housekeeping_mean_present_iff_hk_genes_resolved",
    )

    detail = compute_group_l(exp_df, exp_df, ann_df, collect_detail=True)
    _check("mk_gene_cohort_detail" in detail, "detail_present_when_requested")
    _check("mk_gene_cohort_detail" not in res, "detail_absent_by_default")


def test_group_l_missing_panel_genes() -> None:
    print("\n--- test_group_l_missing_panel_genes ---")
    exp_df, ann_df = _make_panel_data(n_genes=40)
    keep = list(exp_df.columns[:3])
    res = compute_group_l(exp_df[keep], exp_df[keep], ann_df)
    _check(
        res["mk_n_panel_genes_used"] == 3,
        "three_genes_used",
        f"got {res['mk_n_panel_genes_used']}",
    )
    _check(res["mk_n_genes_null"] > 0, "missing_genes_counted")
    _check(0.0 < res["mk_panel_coverage_frac"] < 1.0, "coverage_frac_between_0_and_1")

    empty = compute_group_l(
        pd.DataFrame(index=exp_df.index, columns=["NOT_A_GENE"], data=0.0),
        pd.DataFrame(index=exp_df.index, columns=["NOT_A_GENE"], data=0.0),
        ann_df,
    )
    _check(empty["mk_n_panel_genes_used"] == 0, "zero_genes_handled")
    _check("mk_rho_mean_all_genes" in empty, "keys_present_even_with_zero_genes")


def test_group_m_rank_agreement() -> None:
    print("\n--- test_group_m_rank_agreement ---")
    clean_df, ann_df = _make_panel_data(batch_strength=0.0)
    batchy_df, _ = _make_panel_data(batch_strength=3.0)

    clean = compute_group_m(clean_df, ann_df)
    batchy = compute_group_m(batchy_df, ann_df)

    _check(clean.get("xb_rank_agree") is not None, "xb_rank_agree_present")
    _check(
        "ref" not in str(compute_group_m.__code__.co_varnames),
        "group_m_takes_no_reference",
    )
    _check(
        clean["xb_rank_agree_ratio"] > batchy["xb_rank_agree_ratio"],
        "batch_effect_lowers_biology_margin",
        f"clean {clean['xb_rank_agree_ratio']:.3f} vs batchy {batchy['xb_rank_agree_ratio']:.3f}",
    )
    _check(
        clean["xb_n_pairs_same_bio"] > 0 and clean["xb_n_pairs_diff_bio"] > 0,
        "both_pair_populations_nonempty",
    )
    _check(
        isinstance(clean.get("xb_rank_agree_by_diagnosis"), dict),
        "by_diagnosis_is_dict",
    )

    # Collapsing every sample onto one profile inflates agreement but not the margin.
    collapsed = clean_df.copy()
    collapsed.loc[:, :] = clean_df.mean(axis=0).values + RNG.normal(
        0, 0.01, clean_df.shape
    )
    coll = compute_group_m(collapsed, ann_df)
    _check(
        abs(coll["xb_rank_agree_ratio"]) < abs(clean["xb_rank_agree_ratio"]),
        "overcorrection_flattens_margin",
        f"collapsed {coll['xb_rank_agree_ratio']:.3f} vs clean {clean['xb_rank_agree_ratio']:.3f}",
    )


def test_group_m_subsampling() -> None:
    print("\n--- test_group_m_subsampling ---")
    exp_df, ann_df = _make_panel_data(n_per_batch=30, n_batches=4, n_genes=30)
    res = compute_group_m(exp_df, ann_df, max_samples=50)
    _check(res.get("xb_subsampled") is True, "xb_subsampled_True_when_N_exceeds_limit")
    _check(
        res["xb_n_samples_used"] <= 50 + 4,
        "subsample_respects_limit",
        f"got {res['xb_n_samples_used']}",
    )
    _check(
        res.get("xb_rank_agree") is not None, "metric_still_computed_after_subsampling"
    )

    res_full = compute_group_m(exp_df, ann_df, max_samples=XB_MAX_SAMPLES)
    _check(res_full.get("xb_subsampled") is False, "not_subsampled_below_limit")


def test_group_n_prediction() -> None:
    print("\n--- test_group_n_prediction ---")
    exp_df, ann_df = _make_panel_data(bio_strength=2.0)
    res = compute_group_n(exp_df, ann_df, n_perm=10)

    f1 = res.get("pv_lobo3_f1_macro_mean")
    _check(
        res["pv_lobo3_n_folds"] > 0, "folds_created", f"got {res['pv_lobo3_n_folds']}"
    )
    _check(f1 is not None and f1 > 0.8, "separable_classes_high_f1", f"got {f1}")
    _check(res.get("pv_lobo2_f1_macro_mean") is not None, "two_class_target_computed")
    _check(res.get("pv_n_perm") == 10, "n_perm_recorded")

    # Two classes are present here, so a collapsed permuted macro-F1 sits near 0.5.
    # The test is that it falls to chance and stays far below the observed score.
    perm = res.get("pv_lobo3_f1_macro_perm_mean")
    _check(
        perm is not None and perm < 0.6 and (f1 - perm) > 0.3,
        "permutation_collapses_f1",
        f"observed {f1:.3f}, permuted {perm:.3f}",
    )
    _check(res.get("pv_lobo3_f1_macro_delta", 0) > 0, "delta_positive")
    _check(
        0.0 < res.get("pv_lobo3_f1_perm_pvalue", -1) <= 1.0, "pvalue_in_unit_interval"
    )
    _check(
        isinstance(res.get("pv_lobo3_folds"), dict) and res["pv_lobo3_folds"],
        "per_fold_detail_present",
    )


def test_group_n_no_imputation() -> None:
    print("\n--- test_group_n_no_imputation ---")
    exp_df, ann_df = _make_panel_data(bio_strength=2.0)
    with_na = exp_df.copy()
    with_na.iloc[:, 0] = np.nan  # one all-NA gene  → dropped as a gene
    with_na.iloc[5, :] = np.nan  # one all-NA sample → dropped as a sample
    with_na.iloc[7, 3] = np.nan  # scattered NA cell → its gene is dropped
    res = compute_group_n(with_na, ann_df, n_perm=2)

    _check(
        res.get("pv_n_genes_dropped_na", 0) >= 1,
        "na_genes_dropped_and_counted",
        f"got {res.get('pv_n_genes_dropped_na')}",
    )
    _check(
        res.get("pv_n_samples_dropped_na", 0) >= 1,
        "na_samples_dropped_and_counted",
        f"got {res.get('pv_n_samples_dropped_na')}",
    )
    _check(res.get("pv_lobo3_n_folds", 0) > 0, "still_runs_after_dropping_na")


def test_group_n_single_class_fold() -> None:
    print("\n--- test_group_n_single_class_fold ---")
    exp_df, ann_df = _make_panel_data(bio_strength=2.0)
    # Make one whole batch DLBCL-only: it must count toward F1 but not toward AUC.
    single = (ann_df["RNA_BATCH"] == "b0").values
    ann_df.loc[single, "Major_group"] = "Diffuse_Large_B_Cell_Lymphoma"
    ann_df.loc[single, "Diagnosis_cell_type_unified"] = "Diffuse_Large_B_Cell_Lymphoma"

    res = compute_group_n(exp_df, ann_df, n_perm=2)
    _check(
        res["pv_lobo3_n_folds"] > res["pv_lobo3_n_folds_multiclass"],
        "single_class_fold_counted_for_f1_not_auc",
        f"{res['pv_lobo3_n_folds']} folds, {res['pv_lobo3_n_folds_multiclass']} multiclass",
    )
    fold_b0 = res["pv_lobo3_folds"].get("b0")
    _check(fold_b0 is not None and fold_b0["n_classes"] == 1, "b0_is_single_class")
    _check(
        fold_b0 is not None and fold_b0["auc"] is None, "single_class_fold_auc_is_none"
    )
    _check(
        fold_b0 is not None and fold_b0["f1_macro"] is not None,
        "single_class_fold_has_f1",
    )


def test_group_n_degenerate_single_batch() -> None:
    print("\n--- test_group_n_degenerate_single_batch ---")
    exp_df, ann_df = _make_panel_data()
    ann_df["RNA_BATCH"] = "only_batch"
    res = compute_group_n(exp_df, ann_df, n_perm=2)
    _check(
        res.get("pv_lobo3_n_folds") == 0,
        "no_folds_for_single_batch",
        f"got {res.get('pv_lobo3_n_folds')}",
    )
    _check("pv_lobo3_f1_macro_mean" in res, "keys_present_for_degenerate_input")


def test_lmn_in_compute_all() -> None:
    print("\n--- test_lmn_in_compute_all ---")
    exp_df, ann_df = _make_panel_data(n_per_batch=40, n_batches=3, n_genes=40)
    result = compute_all_metrics(
        exp_df,
        ann_df,
        skip_slow=True,
        groups={"L", "M", "N"},
        ref_df=exp_df,
        n_perm=2,
    )
    for k in [
        "mk_rho_mean_all_genes",
        "xb_rank_agree",
        "xb_rank_agree_ratio",
        "pv_lobo3_f1_macro_mean",
        "pv_lobo2_f1_macro_mean",
    ]:
        _check(k in result, f"key_in_compute_all:{k}")

    # A missing reference must disable Group L only.
    no_ref = compute_all_metrics(
        exp_df,
        ann_df,
        skip_slow=True,
        groups={"L", "M", "N"},
        ref_df=None,
        n_perm=2,
    )
    _check("error_L" in no_ref, "error_L_when_reference_absent")
    _check("mk_rho_mean_all_genes" not in no_ref, "group_L_skipped_without_reference")
    _check("xb_rank_agree" in no_ref, "group_M_runs_without_reference")
    _check("pv_lobo3_f1_macro_mean" in no_ref, "group_N_runs_without_reference")

    for g in ("L", "M", "N"):
        _check(g in GROUP_SENTINEL_KEYS, f"sentinel_{g}_defined")
    missing = _groups_to_recompute(
        {"n_samples": 1, "r2_RNA_BATCH": 0.5, "status": "ok"}, {"E", "A", "L", "M", "N"}
    )
    _check(
        missing == {"L", "M", "N"},
        "only_LMN_recomputed_for_completed_AK_job",
        f"got {missing}",
    )


def test_group_failure_isolation_lmn() -> None:
    """A failure in Group L must not stop M or N."""
    print("\n--- test_group_failure_isolation_lmn ---")
    import compute_batch_metrics as _mod

    original = _mod.compute_group_l

    def _bad_group_l(*_args: object, **_kw: object) -> dict:
        raise RuntimeError("Simulated group L failure")

    _mod.compute_group_l = _bad_group_l  # type: ignore[assignment]
    try:
        exp_df, ann_df = _make_panel_data(n_per_batch=40, n_batches=3, n_genes=40)
        result = compute_all_metrics(
            exp_df,
            ann_df,
            skip_slow=True,
            groups={"L", "M", "N"},
            ref_df=exp_df,
            n_perm=2,
        )
        _check("error_L" in result, "error_L_recorded_on_failure")
        _check("xb_rank_agree" in result, "group_M_ran_despite_L_failure")
        _check("pv_lobo3_f1_macro_mean" in result, "group_N_ran_despite_L_failure")
    finally:
        _mod.compute_group_l = original  # type: ignore[assignment]


def main() -> None:
    test_all_keys_present()
    test_random_batch_low_r2()
    test_strong_batch_high_r2()
    test_group_failure_isolation()
    test_degenerate_single_batch()
    test_incremental_groups_to_recompute()
    test_group_j_pc_variance()
    test_group_k_dropna_metrics()
    test_group_i_wm_score()
    test_new_keys_in_compute_all()
    test_group_l_correlation_preservation()
    test_group_l_per_gene_keys()
    test_group_l_missing_panel_genes()
    test_group_m_rank_agreement()
    test_group_m_subsampling()
    test_group_n_prediction()
    test_group_n_no_imputation()
    test_group_n_single_class_fold()
    test_group_n_degenerate_single_batch()
    test_lmn_in_compute_all()
    test_group_failure_isolation_lmn()

    print(f"\n{'='*50}")
    print(f"Results: {PASS} passed, {FAIL} failed.")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
