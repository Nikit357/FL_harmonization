"""Script to insert all §5–§11 cells into the harmonization metrics notebook."""
import os
import json

NB_PATH = os.path.expanduser("~/FL_harmonization/harmonization-metrics/harmonization_metrics_analysis.ipynb")

with open(NB_PATH) as f:
    nb = json.load(f)


def make_md(source, cell_id):
    return {"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": source}


def make_code(source, cell_id):
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


def insert_after(nb, after_id, new_cells):
    cells = nb["cells"]
    idx = next(i for i, c in enumerate(cells) if c.get("id") == after_id)
    for j, cell in enumerate(new_cells):
        cells.insert(idx + 1 + j, cell)


# ─────────────────────────────────────────────────────────────────────────────
# CITATIONS MARKDOWN (reused in §5 and §11.0)
# ─────────────────────────────────────────────────────────────────────────────
CITATIONS_SRC = """\
## Gene Set Sources and Citations

| Gene set | Source | DOI / URL |
|---|---|---|
| FL transcriptomic subtypes C1/C2/C3 (FL_2025_MARKERS) | Xochelli et al. 2025, *Leukemia* | https://doi.org/10.1038/s41375-025-02603-9 |
| legacy internal GC B-cell markers (Centroblast/Centrocyte) | unpublished internal panel | superseded by the Dybkaer et al. 2015 panels |
| FL PFS prognostic signature (FL_PROG_SIGNATURES) | Pastore et al. 2019, *J Clin Oncol* | https://doi.org/10.1200/JCO.18.01545 (PMID 29475724) |
| POD24 mutation markers | Huet et al. 2018, *Blood* | https://doi.org/10.1182/blood-2018-03-837443 |
| PROGENy pathway activating genes | Schubert et al. 2018, *Nature Communications* | https://doi.org/10.1038/s41467-017-02391-6 |
| Housekeeping genes (stability reference) | Eisenberg & Levanon 2013, *Trends Genet* | https://doi.org/10.1016/j.tig.2013.05.010 |
| kBET batch metric | Büttner et al. 2019, *Nature Methods* | https://doi.org/10.1038/s41592-018-0254-1 |
| LISI / Harmony metric | Korsunsky et al. 2019, *Nature Methods* | https://doi.org/10.1038/s41592-019-0619-0 |
| scIB benchmark + ASW/kBET weighting | Luecken et al. 2022, *Nature Methods* | https://doi.org/10.1038/s41592-021-01336-8 |
| FSQN normalization | Franks et al. 2018, *Biostatistics* | https://doi.org/10.1093/biostatistics/kxx053 |\
"""

# ─────────────────────────────────────────────────────────────────────────────
# §5 HEADER
# ─────────────────────────────────────────────────────────────────────────────
sec5_header = make_md(
    "---\n## §5 — Visual Inspection of Top Approaches\n\n"
    "Downloads harmonized expression matrices from S3 for the top-N methods and plots "
    "PCA, UMAP, and tSNE comparison grids colored by batch and biology variables.",
    "sec5-header",
)

# ─────────────────────────────────────────────────────────────────────────────
# Cell 5.0 — Canonical project palettes
# ─────────────────────────────────────────────────────────────────────────────
cell_5_0 = make_code(
    r"""# ── Canonical project palettes (from all_cohorts_assembly.ipynb) ──────────────
# These are the definitive color mappings for the entire dissertation.
# Use these for all sample-level scatter plots in §5.

lymphoma_ontogeny_palette = {
    # Normal B-cells: cold spectrum (blues, teals, greens)
    'Bone_marrow_CD19+_':  'blue',
    'Immature_':           '#08519c',
    'Naive_':              '#4292c6',
    'GC_':                 '#006d2c',
    'Centroblast_':        '#41ab5d',
    'Centrocyte_':         '#a1d99b',
    'B_cells_':            'lawngreen',
    'MZ_':                 'olive',
    'Memory_':             '#00ced1',
    'Plasmablast_':        '#5f9ea0',
    'Plasma_':             'grey',
    # Malignant types: warm spectrum (reds, oranges, purples)
    'Follicular_Lymphoma_':       '#6a0dad',
    'Follicular_Lymphoma_GCB':    '#9400d3',
    'Diffuse_Large_B_Cell_Lymphoma_ABC': '#ff4500',
    'Diffuse_Large_B_Cell_Lymphoma_GCB': '#d62728',
    'Diffuse_Large_B_Cell_Lymphoma_':    '#8b0000',
    'High_Grade_B_Cell_Lymphoma_':       '#ff00ff',
    'Burkitt_Lymphoma_':                 'orange',
}

rna_batch_palette = {
    "RNASeq_FF_Total":             "#1f77b4",
    "RNASeq_FF_PolyA":             "#17becf",
    "RNASeq_FFPE_Exome_capture":   "#9467bd",
    "RNASeq_FF_rRNADepletion":     "#000080",
    "RNASeq_FFPE_PolyA":           "#8c564b",
    "RNASeq_FF_Unknown":           "#bcbd22",
    "RNASeq_FF_Exome_capture":     "#2ca02c",
    "GPL96+97_FF_Unknown":         "#d62728",
    "GPL570_FF_Unknown":           "#ff7f0e",
    "GPL570_Unknown_Unknown":      "#ffbb78",
    "GPL570_FFPE_Unknown":         "#dbdb8d",
    "GPL96_FF_Unknown":            "#f7b6d2",
    "GPL96_FFPE_Unknown":          "#e377c2",
    "GPL6244_FF_Unknown":          "#e9967a",
    "GPL6244_FFPE_Unknown":        "#fa8072",
    "GPL13938_FFPE_Unknown":       "#800000",
    "GPL1708_FF_Unknown":          "#7f7f7f",
    "GPL14951_FFPE_Unknown":       "#c49c94",
    "GPL17077_FF_Unknown":         "#c5b0d5",
    "GPL13158_FF_Unknown":         "#ad494a",
    "GPL17586_FF_Unknown":         "#008b8b",
    "GPL17047_FF_Unknown":         "#4682b4",
    "GPL887_FFPE_Unknown":         "#b0c4de",
    "GPL10739_FF_Unknown":         "#9edae5",
    "GPL8432_FFPE_Unknown":        "#006400",
    "GPL20188_FF_Unknown":         "#556b2f",
    "GPL23541_FF_Unknown":         "#8fbc8f",
    "GPL16686_FF_Unknown":         "#333333",
    "GPL26356_FF_Unknown":         "#a0522d",
}

platform_palette = {
    "RNASeq":       "#4B0082",
    "RNAseq":       "#4B0082",
    "Kassandra":    "#6A5ACD",
    "GPL96+97":     "#FF4500",
    "GPL96+GPL97":  "#FF4500",
    "GPL570":       "#FF8C00",
    "GPL96":        "#B22222",
    "GPL6244":      "#E9967A",
    "GPL13938":     "#CD5C5C",
    "A-GEOD-19803": "#A52A2A",
    "GPL1708":      "#008080",
    "GPL14951":     "#4682B4",
    "GPL17077":     "#00CED1",
    "GPL13158":     "#1E90FF",
    "GPL17586":     "#20B2AA",
    "GPL17047":     "#5F9EA0",
    "GPL887":       "#B0C4DE",
    "GPL10739":     "#2E8B57",
    "GPL10739+GPL19251": "#3CB371",
    "GPL20188":     "#6B8E23",
    "GPL23541":     "#8FBC8F",
    "GPL8432":      "#006400",
    "GPL16686":     "#8B4513",
    "GPL26356":     "#A0522D",
    float("nan"):   "#D3D3D3",
    None:           "#D3D3D3",
}

# cohort_palette: copy verbatim from all_cohorts_assembly.ipynb (88 cohorts).
# Placeholder dict — replace with full palette before running §5.
cohort_palette: dict = {}""",
    "cell-5-0-palettes",
)

# ─────────────────────────────────────────────────────────────────────────────
# Cell 5.1 — S3 download helpers
# ─────────────────────────────────────────────────────────────────────────────
cell_5_1 = make_code(
    r"""import boto3
import io
import gzip


def load_harmonized_exp(
    strat: str,
    imp: str,
    method: str,
    post_rm: bool = False,
) -> "pd.DataFrame":
    """Download a harmonized expression matrix from S3.

    Parameters
    ----------
    strat : str
        Removal strategy key (e.g. "A_confirmed_bad").
    imp : str
        Imputation key: "strict", "knn", or "softimpute".
    method : str
        Normalization method key (e.g. "16_fsqn_r").
    post_rm : bool
        Whether to load the post-normalization outlier-removed variant.

    Returns
    -------
    pd.DataFrame
        Expression matrix, samples x genes, index = sample IDs.
    """
    s3 = boto3.client("s3")
    pm = "1" if post_rm else "0"
    key = f"{S3_PREFIX}/exp/{strat}__{imp}__{method}__post{pm}.tsv.gz"
    body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(gzip.decompress(body)), sep="\t", index_col=0)


def load_annotation(strat: str, imp: str) -> "pd.DataFrame":
    """Download the annotation file aligned to a given (strat, imp) preparation.

    Parameters
    ----------
    strat : str
        Removal strategy key.
    imp : str
        Imputation key.

    Returns
    -------
    pd.DataFrame
        Annotation DataFrame, index = sample IDs. Key columns: RNA_BATCH,
        PLATFORM_RNA, COHORT_LABEL, Major_group, Diagnosis_cell_type_unified,
        TUMOR_NORMAL.
    """
    s3 = boto3.client("s3")
    key = f"{S3_PREFIX}/prepared/{strat}__{imp}__ann.tsv.gz"
    body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(gzip.decompress(body)), sep="\t", index_col=0)


def align_exp_ann(
    exp: "pd.DataFrame",
    ann: "pd.DataFrame",
) -> "tuple[pd.DataFrame, pd.DataFrame]":
    """Align expression and annotation to their shared sample IDs.

    Alignment is done by index intersection, not positional order.

    Parameters
    ----------
    exp : pd.DataFrame
        Expression matrix (samples x genes).
    ann : pd.DataFrame
        Annotation (samples x columns).

    Returns
    -------
    tuple of (exp_aligned, ann_aligned) with matching index.
    """
    common = exp.index.intersection(ann.index)
    return exp.loc[common], ann.loc[common]""",
    "cell-5-1-s3-helpers",
)

# ─────────────────────────────────────────────────────────────────────────────
# Cell 5.2 — PCA comparison grid
# ─────────────────────────────────────────────────────────────────────────────
cell_5_2 = make_code(
    r"""from sklearn.preprocessing import StandardScaler


def compute_pca_coords(
    exp: "pd.DataFrame",
    n_components: int = 50,
) -> "tuple[np.ndarray, object]":
    """Compute PCA on a log2-scaled expression matrix.

    Data are mean-centered and unit-variance scaled before PCA.

    Parameters
    ----------
    exp : pd.DataFrame
        Expression matrix (samples x genes), log2-transformed values expected.
    n_components : int
        Number of PCs to compute.

    Returns
    -------
    coords : np.ndarray, shape (n_samples, n_components)
    pca : sklearn.decomposition.PCA
    """
    X = StandardScaler().fit_transform(exp.values)
    pca = PCA(n_components=min(n_components, min(X.shape) - 1))
    coords = pca.fit_transform(X)
    return coords, pca


def _sample_color_by_diagnosis(ann_col: "pd.Series") -> list:
    """Map Diagnosis_cell_type_unified labels to colors via prefix matching."""
    colors = []
    for label in ann_col:
        color = "#AAAAAA"
        if isinstance(label, str):
            for prefix, c in lymphoma_ontogeny_palette.items():
                if label.startswith(prefix):
                    color = c
                    break
        colors.append(color)
    return colors


# Build top_ids: list of (strat, imp, method) tuples for top-N + raw baseline
top_ids = []
for run_id, row in top_n.iterrows():
    top_ids.append((row["strat"], row["imp"], row["method"]))

raw_rows = df_ok[df_ok["method"] == "01_raw"]
if not raw_rows.empty:
    rr = raw_rows.iloc[0]
    raw_entry = (rr["strat"], rr["imp"], "01_raw")
    if raw_entry not in top_ids:
        top_ids = [raw_entry] + top_ids

n_cols = len(top_ids)
fig, axes = plt.subplots(2, n_cols, figsize=(4 * n_cols, 8))
if n_cols == 1:
    axes = axes.reshape(2, 1)

for col_i, (strat, imp, method) in enumerate(top_ids):
    try:
        exp = load_harmonized_exp(strat, imp, method)
        ann = load_annotation(strat, imp)
        exp, ann = align_exp_ann(exp, ann)
        coords, pca_obj = compute_pca_coords(exp)
        ev = pca_obj.explained_variance_ratio_

        batch_colors = ann["RNA_BATCH"].map(rna_batch_palette).fillna("#AAAAAA")
        bio_colors = _sample_color_by_diagnosis(ann["Diagnosis_cell_type_unified"])

        r2_b = df_ok.loc[df_ok["method"] == method, "r2_RNA_BATCH"]
        r2_b_val = r2_b.iloc[0] if not r2_b.empty else float("nan")

        for row_i, (c_arr, lbl) in enumerate([
            (batch_colors, "RNA_BATCH"),
            (bio_colors,   "Diagnosis"),
        ]):
            ax = axes[row_i, col_i]
            ax.scatter(coords[:, 0], coords[:, 1],
                       c=list(c_arr), s=2, alpha=0.5, rasterized=True)
            if row_i == 0:
                ax.set_title(
                    f"{method}\nr2_batch={r2_b_val:.2f}\n"
                    f"PC1={ev[0]:.1%} PC2={ev[1]:.1%}",
                    fontsize=7,
                )
            ax.set_xlabel(f"PC1 ({ev[0]:.1%})", fontsize=7)
            ax.set_ylabel(f"PC2 ({ev[1]:.1%})", fontsize=7)
            ax.tick_params(labelsize=6)
    except Exception as exc:
        print(f"WARNING: PCA skipped for {strat}/{imp}/{method}: {exc}")

axes[0, 0].set_ylabel("PC2 — colored by RNA_BATCH", fontsize=8)
axes[1, 0].set_ylabel("PC2 — colored by Diagnosis", fontsize=8)
fig.suptitle(f"PCA comparison: top-{N_TOP} methods + raw baseline", y=1.01)
fig.tight_layout()
fig.savefig(FIGURES_DIR / f"pca_grid_top{N_TOP}.svg", bbox_inches="tight")
fig.savefig(FIGURES_DIR / f"pca_grid_top{N_TOP}.png", bbox_inches="tight", dpi=200)
plt.show()""",
    "cell-5-2-pca-grid",
)

# ─────────────────────────────────────────────────────────────────────────────
# Cell 5.3 — UMAP comparison grid
# ─────────────────────────────────────────────────────────────────────────────
cell_5_3 = make_code(
    r"""def compute_umap_coords(
    exp: "pd.DataFrame",
    n_pcs: int = 50,
    n_neighbors: int = 30,
    min_dist: float = 0.3,
    random_state: int = 42,
) -> "np.ndarray":
    """Compute UMAP embedding on the top-N PCA coordinates of an expression matrix.

    UMAP is computed on PCA (not raw expression) to reduce noise and computation
    time.

    Parameters
    ----------
    exp : pd.DataFrame
        Expression matrix (samples x genes).
    n_pcs : int
        Number of PCA dimensions to use as UMAP input.
    n_neighbors : int
        UMAP neighborhood size. 30 is appropriate for ~1,000-10,000 samples.
    min_dist : float
        UMAP minimum distance. 0.3 balances local/global structure for bulk RNA-seq.
    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    np.ndarray, shape (n_samples, 2)
    """
    import umap as umap_lib
    pca_coords, _ = compute_pca_coords(exp, n_components=n_pcs)
    reducer = umap_lib.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        n_components=2,
        random_state=random_state,
    )
    return reducer.fit_transform(pca_coords)


n_cols = len(top_ids)
fig, axes = plt.subplots(2, n_cols, figsize=(4 * n_cols, 8))
if n_cols == 1:
    axes = axes.reshape(2, 1)

for col_i, (strat, imp, method) in enumerate(top_ids):
    try:
        exp = load_harmonized_exp(strat, imp, method)
        ann = load_annotation(strat, imp)
        exp, ann = align_exp_ann(exp, ann)
        coords = compute_umap_coords(exp)

        batch_colors = ann["RNA_BATCH"].map(rna_batch_palette).fillna("#AAAAAA")
        bio_colors = _sample_color_by_diagnosis(ann["Diagnosis_cell_type_unified"])

        for row_i, (c_arr, ylabel) in enumerate([
            (batch_colors, "UMAP2 — RNA_BATCH"),
            (bio_colors,   "UMAP2 — Diagnosis"),
        ]):
            ax = axes[row_i, col_i]
            ax.scatter(coords[:, 0], coords[:, 1],
                       c=list(c_arr), s=2, alpha=0.5, rasterized=True)
            if row_i == 0:
                ax.set_title(method, fontsize=8)
            ax.set_xlabel("UMAP1", fontsize=7)
            ax.set_ylabel(ylabel, fontsize=7)
            ax.tick_params(labelsize=6)
    except Exception as exc:
        print(f"WARNING: UMAP skipped for {strat}/{imp}/{method}: {exc}")

fig.suptitle(f"UMAP comparison: top-{N_TOP} methods + raw baseline", y=1.01)
fig.tight_layout()
fig.savefig(FIGURES_DIR / f"umap_grid_top{N_TOP}.svg", bbox_inches="tight")
fig.savefig(FIGURES_DIR / f"umap_grid_top{N_TOP}.png", bbox_inches="tight", dpi=200)
plt.show()""",
    "cell-5-3-umap-grid",
)

# ─────────────────────────────────────────────────────────────────────────────
# Cell 5.4 — tSNE comparison grid
# ─────────────────────────────────────────────────────────────────────────────
cell_5_4 = make_code(
    r"""from sklearn.manifold import TSNE


def compute_tsne_coords(
    exp: "pd.DataFrame",
    n_pcs: int = 50,
    perplexity: float = 30.0,
    random_state: int = 42,
) -> "np.ndarray":
    """Compute t-SNE embedding on top-N PCA coordinates of an expression matrix.

    t-SNE is computed on PCA for speed and noise reduction. Perplexity 30 is
    appropriate for ~1,000-5,000 samples.

    Parameters
    ----------
    exp : pd.DataFrame
        Expression matrix (samples x genes).
    n_pcs : int
        Number of PCA dimensions to use as t-SNE input.
    perplexity : float
        t-SNE perplexity. Rule of thumb: ~sqrt(n_samples).
    random_state : int
        Random seed.

    Returns
    -------
    np.ndarray, shape (n_samples, 2)
    """
    pca_coords, _ = compute_pca_coords(exp, n_components=n_pcs)
    tsne = TSNE(n_components=2, perplexity=perplexity, random_state=random_state)
    return tsne.fit_transform(pca_coords)


n_cols = len(top_ids)
fig, axes = plt.subplots(2, n_cols, figsize=(4 * n_cols, 8))
if n_cols == 1:
    axes = axes.reshape(2, 1)

for col_i, (strat, imp, method) in enumerate(top_ids):
    try:
        exp = load_harmonized_exp(strat, imp, method)
        ann = load_annotation(strat, imp)
        exp, ann = align_exp_ann(exp, ann)
        coords = compute_tsne_coords(exp)

        batch_colors = ann["RNA_BATCH"].map(rna_batch_palette).fillna("#AAAAAA")
        bio_colors = _sample_color_by_diagnosis(ann["Diagnosis_cell_type_unified"])

        for row_i, (c_arr, ylabel) in enumerate([
            (batch_colors, "tSNE2 — RNA_BATCH"),
            (bio_colors,   "tSNE2 — Diagnosis"),
        ]):
            ax = axes[row_i, col_i]
            ax.scatter(coords[:, 0], coords[:, 1],
                       c=list(c_arr), s=2, alpha=0.5, rasterized=True)
            if row_i == 0:
                ax.set_title(method, fontsize=8)
            ax.set_xlabel("tSNE1", fontsize=7)
            ax.set_ylabel(ylabel, fontsize=7)
            ax.tick_params(labelsize=6)
    except Exception as exc:
        print(f"WARNING: tSNE skipped for {strat}/{imp}/{method}: {exc}")

fig.suptitle(f"tSNE comparison: top-{N_TOP} methods + raw baseline", y=1.01)
fig.tight_layout()
fig.savefig(FIGURES_DIR / f"tsne_grid_top{N_TOP}.svg", bbox_inches="tight")
fig.savefig(FIGURES_DIR / f"tsne_grid_top{N_TOP}.png", bbox_inches="tight", dpi=200)
plt.show()""",
    "cell-5-4-tsne-grid",
)

# ─────────────────────────────────────────────────────────────────────────────
# Cell 5.5 — Per-batch violins + CV-vs-expression curves
# ─────────────────────────────────────────────────────────────────────────────
cell_5_5 = make_code(
    r"""# ── Part A: Expression distribution violin plots (top-5 methods) ──────────────
top_5_ids = top_ids[:5]

fig_v, axes_v = plt.subplots(len(top_5_ids), 2, figsize=(18, 4 * len(top_5_ids)))
if len(top_5_ids) == 1:
    axes_v = axes_v.reshape(1, 2)

for row_i, (strat, imp, method) in enumerate(top_5_ids):
    try:
        exp = load_harmonized_exp(strat, imp, method)
        ann = load_annotation(strat, imp)
        exp, ann = align_exp_ann(exp, ann)
        marginal = exp.mean(axis=1)

        for col_i, (group_col, pal_dict) in enumerate([
            ("RNA_BATCH",    rna_batch_palette),
            ("COHORT_LABEL", cohort_palette),
        ]):
            ax = axes_v[row_i, col_i]
            plot_data = pd.DataFrame({"expr": marginal, "group": ann[group_col]})
            group_order = sorted(plot_data["group"].dropna().unique())
            colors = [pal_dict.get(g, "#AAAAAA") for g in group_order]
            sns.violinplot(
                data=plot_data, x="group", y="expr",
                order=group_order, palette=colors,
                ax=ax, inner="box", linewidth=0.7,
            )
            ax.set_xticklabels(group_order, rotation=90, fontsize=5)
            ax.set_title(f"{method} — {group_col}", fontsize=8)
            ax.set_xlabel("")
            ax.set_ylabel("Mean expression (log2)", fontsize=7)
    except Exception as exc:
        print(f"WARNING: violin skipped for {strat}/{imp}/{method}: {exc}")

fig_v.suptitle("Per-batch expression distribution: top-5 methods", y=1.01)
fig_v.tight_layout()
fig_v.savefig(FIGURES_DIR / "violins_top5.svg", bbox_inches="tight")
fig_v.savefig(FIGURES_DIR / "violins_top5.png", bbox_inches="tight", dpi=200)
plt.show()

# ── Part B: CV-vs-mean-expression binned curves ───────────────────────────────
# CV-vs-expression binning: divide genes into 20 expression-level quantile bins,
# compute median CV per bin, plot as a curve per batch/cohort group.
# All lines in one axis per method, colored by rna_batch_palette or cohort_palette.
fig_cv, axes_cv = plt.subplots(len(top_5_ids), 2, figsize=(14, 4 * len(top_5_ids)))
if len(top_5_ids) == 1:
    axes_cv = axes_cv.reshape(1, 2)

for row_i, (strat, imp, method) in enumerate(top_5_ids):
    try:
        exp = load_harmonized_exp(strat, imp, method)
        ann = load_annotation(strat, imp)
        exp, ann = align_exp_ann(exp, ann)

        for col_i, (group_col, pal_dict) in enumerate([
            ("RNA_BATCH",    rna_batch_palette),
            ("COHORT_LABEL", cohort_palette),
        ]):
            ax = axes_cv[row_i, col_i]
            for group_name, idx in ann.groupby(group_col).groups.items():
                sub = exp.loc[exp.index.intersection(idx)]
                if sub.shape[0] < 5:
                    continue
                gene_means = sub.mean(axis=0)
                gene_cvs = sub.std(axis=0) / gene_means.replace(0, np.nan)
                bins = np.percentile(gene_means.dropna(), np.linspace(0, 100, 21))
                bin_cvs, bin_centers = [], []
                for b0, b1 in zip(bins[:-1], bins[1:]):
                    mask = (gene_means >= b0) & (gene_means < b1)
                    bin_cvs.append(gene_cvs[mask].median())
                    bin_centers.append((b0 + b1) / 2)
                ax.plot(
                    bin_centers, bin_cvs,
                    alpha=0.6, linewidth=0.8,
                    color=pal_dict.get(group_name, "#AAAAAA"),
                )
            ax.set_xlabel("Mean expression (log2)", fontsize=7)
            ax.set_ylabel("Median gene CV", fontsize=7)
            ax.set_title(f"{method} — {group_col}", fontsize=8)
            ax.tick_params(labelsize=6)
    except Exception as exc:
        print(f"WARNING: CV curve skipped for {strat}/{imp}/{method}: {exc}")

fig_cv.suptitle("CV vs mean expression: top-5 methods", y=1.01)
fig_cv.tight_layout()
fig_cv.savefig(FIGURES_DIR / "cv_vs_exp_top5.svg", bbox_inches="tight")
fig_cv.savefig(FIGURES_DIR / "cv_vs_exp_top5.png", bbox_inches="tight", dpi=200)
plt.show()""",
    "cell-5-5-violins-cv",
)

# ─────────────────────────────────────────────────────────────────────────────
# Citations markdown cell (before §5.6)
# ─────────────────────────────────────────────────────────────────────────────
cell_citations = make_md(CITATIONS_SRC, "cell-5-citations")

# ─────────────────────────────────────────────────────────────────────────────
# Cell 5.6 — FL/GC marker gene correlation + housekeeping gene stability
# ─────────────────────────────────────────────────────────────────────────────
cell_5_6 = make_code(
    r"""HOUSEKEEPING_GENES = [
    "ACTB", "GAPDH", "B2M", "HMBS", "HPRT1", "PPIA", "RPL13A",
    "RPLP0", "TBP", "YWHAZ", "UBC", "VIM", "LDHA", "PGK1", "SDHA",
]

# FL_GENES_ALL is defined in §11; use a stub if §11 hasn't run yet.
try:
    _fl_genes_for_corr = FL_GENES_ALL
except NameError:
    _fl_genes_for_corr = [
        "BCL2", "BCL6", "MKI67", "PCNA", "AICDA", "CXCR4", "CXCR5",
        "LMO2", "FN1", "CCND2", "CD83", "MME", "EZH2", "IRF4",
    ]

# ── Panel A: FL marker gene Pearson correlation heatmap (top-5 only) ──────────
fig_corr, axes_corr = plt.subplots(1, len(top_5_ids), figsize=(7 * len(top_5_ids), 6))
if len(top_5_ids) == 1:
    axes_corr = [axes_corr]

for col_i, (strat, imp, method) in enumerate(top_5_ids):
    ax = axes_corr[col_i]
    try:
        exp = load_harmonized_exp(strat, imp, method)
        ann = load_annotation(strat, imp)
        exp, ann = align_exp_ann(exp, ann)
        present = [g for g in _fl_genes_for_corr if g in exp.columns]
        if len(present) < 3:
            ax.set_title(f"{method}\n(insufficient FL genes)", fontsize=8)
            continue
        corr_mat = exp[present].corr()
        sns.heatmap(
            corr_mat, ax=ax,
            cmap="RdBu_r", center=0, vmin=-1, vmax=1,
            linewidths=0.3, linecolor="white",
            xticklabels=True, yticklabels=True,
            cbar_kws={"shrink": 0.6, "label": "Pearson r"},
        )
        ax.set_title(f"{method}\n({len(present)} FL genes)", fontsize=8)
        ax.tick_params(labelsize=6)
    except Exception as exc:
        ax.set_title(f"{method}\n(error: {exc})", fontsize=7)

fig_corr.suptitle("FL marker gene correlation (top-5 methods)", y=1.01)
fig_corr.tight_layout()
fig_corr.savefig(FIGURES_DIR / "fl_marker_corr_top5.svg", bbox_inches="tight")
fig_corr.savefig(FIGURES_DIR / "fl_marker_corr_top5.png", bbox_inches="tight", dpi=200)
plt.show()

# ── Panel B: Housekeeping gene CV (batch CV vs biology CV) ────────────────────
try:
    exp_raw_hk = load_harmonized_exp(*top_ids[0])
    ann_raw_hk = load_annotation(top_ids[0][0], top_ids[0][1])
    exp_raw_hk, ann_raw_hk = align_exp_ann(exp_raw_hk, ann_raw_hk)

    exp_top_hk = load_harmonized_exp(*top_5_ids[0])
    ann_top_hk = load_annotation(top_5_ids[0][0], top_5_ids[0][1])
    exp_top_hk, ann_top_hk = align_exp_ann(exp_top_hk, ann_top_hk)

    hk_genes = sorted(
        set(g for g in HOUSEKEEPING_GENES if g in exp_raw_hk.columns)
        & set(g for g in HOUSEKEEPING_GENES if g in exp_top_hk.columns)
    )

    records = []
    for gene in hk_genes:
        for label, exp_df, ann_df in [
            ("raw", exp_raw_hk, ann_raw_hk),
            (top_5_ids[0][2], exp_top_hk, ann_top_hk),
        ]:
            batch_means = exp_df[gene].groupby(ann_df["RNA_BATCH"]).mean()
            bio_means   = exp_df[gene].groupby(ann_df["Major_group"]).mean()
            batch_cv = batch_means.std() / batch_means.mean() if batch_means.mean() != 0 else np.nan
            bio_cv   = bio_means.std()   / bio_means.mean()   if bio_means.mean()   != 0 else np.nan
            records.append({"gene": gene, "method": label,
                             "batch_CV": batch_cv, "bio_CV": bio_cv})

    hk_df = pd.DataFrame(records)
    fig_hk, axes_hk = plt.subplots(1, 2, figsize=(12, max(4, len(hk_genes) * 0.4 + 1)))
    for ax_i, cv_col in enumerate(["batch_CV", "bio_CV"]):
        pivot = hk_df.pivot(index="gene", columns="method", values=cv_col)
        sns.heatmap(
            pivot, ax=axes_hk[ax_i],
            cmap="RdYlGn_r", annot=True, fmt=".2f",
            linewidths=0.3,
            cbar_kws={"shrink": 0.6, "label": cv_col},
        )
        axes_hk[ax_i].set_title(
            f"Housekeeping gene {cv_col}\n(green = low = good)", fontsize=9
        )
    fig_hk.suptitle("Housekeeping gene stability: raw vs top method", y=1.01)
    fig_hk.tight_layout()
    fig_hk.savefig(FIGURES_DIR / "housekeeping_cv_top5.svg", bbox_inches="tight")
    fig_hk.savefig(FIGURES_DIR / "housekeeping_cv_top5.png", bbox_inches="tight", dpi=200)
    plt.show()
except Exception as exc:
    print(f"WARNING: housekeeping CV panel skipped: {exc}")""",
    "cell-5-6-markers-hk",
)

# ─────────────────────────────────────────────────────────────────────────────
# §6 — Download Gene Lists from S3
# ─────────────────────────────────────────────────────────────────────────────
sec6_header = make_md(
    "---\n## §6 — Download Gene Lists from S3\n\n"
    "Downloads per-harmonization gene list JSON files from S3 and builds a structured "
    "dictionary for downstream overlap and GO enrichment analysis.",
    "sec6-header",
)

cell_6_1 = make_code(
    r"""def list_gene_files(s3_bucket: str, s3_prefix: str) -> list:
    """List all per-harmonization gene list JSON files on S3.

    Gene lists are stored under {s3_prefix}/genes/ as
    {strat}__{imp}__{method}__{post_rm_tag}_genes.json.

    Parameters
    ----------
    s3_bucket : str
        S3 bucket name.
    s3_prefix : str
        S3 path prefix (e.g. "FL_batch_correction").

    Returns
    -------
    list of str
        Full S3 keys of all gene list files found.
    """
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=s3_bucket, Prefix=f"{s3_prefix}/genes/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("_genes.json"):
                keys.append(obj["Key"])
    return keys


try:
    gene_keys = list_gene_files(S3_BUCKET, S3_PREFIX)
    print(f"Found {len(gene_keys)} gene list files on S3.")
except Exception as exc:
    gene_keys = []
    print(f"WARNING: could not list gene files from S3: {exc}")""",
    "cell-6-1-list-genes",
)

cell_6_2 = make_code(
    r"""def parse_gene_key(s3_key: str):
    """Parse a gene list S3 key into its (strat, imp, method, post_rm) components.

    Expected filename format:
    {strat}__{imp}__{method}__{post_tag}_genes.json
    where post_tag is "post0" (no post-removal) or "post1" (post-removal applied).

    Parameters
    ----------
    s3_key : str
        Full S3 key string.

    Returns
    -------
    tuple (strat, imp, method, post_rm) or None if the key cannot be parsed.
    """
    fname = s3_key.split("/")[-1].replace("_genes.json", "")
    parts = fname.split("__")
    if len(parts) != 4:
        return None
    strat, imp, method, pm_tag = parts
    return strat, imp, method, (pm_tag == "post1")


gene_sets: dict = {}

try:
    s3_client = boto3.client("s3")
    for key in gene_keys:
        parsed = parse_gene_key(key)
        if parsed is None:
            continue
        strat, imp, method, post_rm = parsed
        body = s3_client.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read().decode()
        gene_sets[(strat, imp, method, post_rm)] = set(json.loads(body))
    print(f"Loaded {len(gene_sets)} gene sets.")
except Exception as exc:
    print(f"WARNING: gene set download failed: {exc}")""",
    "cell-6-2-download-genes",
)

cell_6_3 = make_code(
    r"""gene_summary = []
for (strat, imp, method, post_rm), genes in gene_sets.items():
    gene_summary.append({
        "strat": strat, "imp": imp, "method": method,
        "post_rm": post_rm, "n_genes": len(genes),
    })
gene_df = pd.DataFrame(gene_summary)

if not gene_df.empty:
    print(gene_df.groupby(["strat", "imp", "post_rm"])["n_genes"].describe().to_string())
    non_angel = gene_df[gene_df["method"] != "25_angel"]
    spread = non_angel.groupby(["strat", "imp", "post_rm"])["n_genes"].std()
    print("\nGene count std across non-angel methods (expect ~0):")
    print(spread.to_string())
else:
    print("gene_df is empty — no gene sets loaded.")""",
    "cell-6-3-gene-summary",
)

cell_6_4 = make_code(
    r"""# Aggregate gene sets by (strat, imp) — union across all methods except 25_angel.
# Used in §7, §8, §10 where we ask what genes are available for a given data
# preparation step, not what a specific normalizer produces.
# 25_angel is tracked separately because it applies its own internal gene filtering
# on top of the preparation step.
gene_sets_by_strat_imp: dict = {}
gene_sets_angel: dict = {}

for (strat, imp, method, post_rm), genes in gene_sets.items():
    if not post_rm:
        key = (strat, imp)
        if method == "25_angel":
            gene_sets_angel.setdefault(key, set()).update(genes)
        else:
            gene_sets_by_strat_imp.setdefault(key, set()).update(genes)

print(f"Unique (strat, imp) pairs (non-angel): {len(gene_sets_by_strat_imp)}")
print(f"Angel gene set entries: {len(gene_sets_angel)}")
for k, v in sorted(gene_sets_by_strat_imp.items()):
    print(f"  {k}: {len(v)} genes")""",
    "cell-6-4-gene-lookups",
)

# ─────────────────────────────────────────────────────────────────────────────
# §7 — Gene Count and Overlap Analysis
# ─────────────────────────────────────────────────────────────────────────────
sec7_header = make_md(
    "---\n## §7 — Gene Count and Overlap Analysis\n\n"
    "Compares gene set sizes and Jaccard overlap across data preparation strategies to "
    "quantify how filtering harshness and imputation method affect the gene universe.",
    "sec7-header",
)

cell_7_1 = make_code(
    r"""if gene_sets_by_strat_imp:
    pairs = sorted(
        gene_sets_by_strat_imp.keys(),
        key=lambda x: (ALL_STRATS.index(x[0]) if x[0] in ALL_STRATS else 99, x[1]),
    )
    labels = [f"{s}\n{i}" for s, i in pairs]
    n_genes_list = [len(gene_sets_by_strat_imp[p]) for p in pairs]
    n_angel = [len(gene_sets_angel.get(p, set())) for p in pairs]

    fig_gc, axes_gc = plt.subplots(1, 2, figsize=(max(10, len(pairs) * 0.7 + 2), 5))

    colors_gc = [strat_pal.get(s, "#AAAAAA") for s, _ in pairs]
    axes_gc[0].bar(range(len(pairs)), n_genes_list, color=colors_gc)
    axes_gc[0].set_xticks(range(len(pairs)))
    axes_gc[0].set_xticklabels(labels, rotation=90, fontsize=7)
    axes_gc[0].set_ylabel("n_genes (all methods except angel)")
    axes_gc[0].set_title("Gene count per (strat, imp)")
    if n_genes_list:
        axes_gc[0].axhline(n_genes_list[0], color="gray", linestyle="--",
                           linewidth=0.8, label=f"Most permissive: {n_genes_list[0]}")
        axes_gc[0].legend(fontsize=7)

    baseline = n_genes_list[0] if n_genes_list else 0
    deltas = [baseline - n for n in n_genes_list]
    axes_gc[1].bar(range(len(pairs)), deltas, color=colors_gc)
    axes_gc[1].set_xticks(range(len(pairs)))
    axes_gc[1].set_xticklabels(labels, rotation=90, fontsize=7)
    axes_gc[1].set_ylabel("Genes lost vs most permissive strategy")
    axes_gc[1].set_title("Gene loss per (strat, imp)")

    fig_gc.tight_layout()
    fig_gc.savefig(FIGURES_DIR / "gene_count_by_strat_imp.svg", bbox_inches="tight")
    fig_gc.savefig(FIGURES_DIR / "gene_count_by_strat_imp.png", bbox_inches="tight", dpi=200)
    plt.show()

    if any(n > 0 for n in n_angel):
        fig_angel, ax_angel = plt.subplots(figsize=(max(8, len(pairs) * 0.7), 4))
        ax_angel.bar(range(len(pairs)), n_angel,
                     color=[strat_pal.get(s, "#AAAAAA") for s, _ in pairs])
        ax_angel.set_xticks(range(len(pairs)))
        ax_angel.set_xticklabels(labels, rotation=90, fontsize=7)
        ax_angel.set_ylabel("n_genes (25_angel internal filtering)")
        ax_angel.set_title("25_angel gene count per (strat, imp)")
        fig_angel.tight_layout()
        fig_angel.savefig(FIGURES_DIR / "gene_count_angel.svg", bbox_inches="tight")
        fig_angel.savefig(FIGURES_DIR / "gene_count_angel.png", bbox_inches="tight", dpi=200)
        plt.show()
else:
    print("gene_sets_by_strat_imp is empty — skipping gene count plot.")""",
    "cell-7-1-gene-count",
)

cell_7_2 = make_code(
    r"""def jaccard_matrix(sets: list) -> "np.ndarray":
    """Compute the pairwise Jaccard similarity matrix for a list of gene sets.

    Jaccard(A, B) = |A cap B| / |A cup B|. Returns 1 on the diagonal.

    Parameters
    ----------
    sets : list of set
        List of gene sets to compare.

    Returns
    -------
    np.ndarray, shape (n, n)
        Symmetric Jaccard matrix with values in [0, 1].
    """
    n = len(sets)
    mat = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            inter = len(sets[i] & sets[j])
            union = len(sets[i] | sets[j])
            mat[i, j] = mat[j, i] = inter / union if union > 0 else 0.0
    return mat


if len(gene_sets_by_strat_imp) >= 2:
    pairs_jac = sorted(
        gene_sets_by_strat_imp.keys(),
        key=lambda x: (ALL_STRATS.index(x[0]) if x[0] in ALL_STRATS else 99, x[1]),
    )
    jac_mat = jaccard_matrix([gene_sets_by_strat_imp[p] for p in pairs_jac])
    jac_labels = [f"{s}/{i}" for s, i in pairs_jac]

    fig_jac, ax_jac = plt.subplots(
        figsize=(max(6, len(pairs_jac) * 0.6 + 1), max(5, len(pairs_jac) * 0.6))
    )
    sns.heatmap(
        jac_mat, ax=ax_jac,
        xticklabels=jac_labels, yticklabels=jac_labels,
        cmap="YlOrRd", vmin=0, vmax=1,
        annot=(len(pairs_jac) <= 15), fmt=".2f",
        linewidths=0.3,
        cbar_kws={"shrink": 0.6, "label": "Jaccard similarity"},
    )
    ax_jac.set_xticklabels(jac_labels, rotation=45, ha="right", fontsize=7)
    ax_jac.set_yticklabels(jac_labels, rotation=0, fontsize=7)
    ax_jac.set_title("Pairwise Jaccard overlap between gene sets")
    fig_jac.tight_layout()
    fig_jac.savefig(FIGURES_DIR / "gene_jaccard_heatmap.svg", bbox_inches="tight")
    fig_jac.savefig(FIGURES_DIR / "gene_jaccard_heatmap.png", bbox_inches="tight", dpi=200)
    plt.show()
else:
    print("Need at least 2 (strat, imp) pairs for Jaccard heatmap.")""",
    "cell-7-2-jaccard",
)

cell_7_3 = make_code(
    r"""try:
    from supervenn import supervenn
    _has_supervenn = True
except ImportError:
    _has_supervenn = False
    print("WARNING: supervenn not installed — skipping set intersection plots.")

if _has_supervenn and gene_sets_by_strat_imp:
    strict_sets = {
        strat: gene_sets_by_strat_imp[(strat, "strict")]
        for strat in ALL_STRATS
        if (strat, "strict") in gene_sets_by_strat_imp
    }
    if len(strict_sets) >= 2:
        fig_sv1, ax_sv1 = plt.subplots(figsize=(12, 5))
        supervenn(
            [strict_sets[s] for s in sorted(strict_sets.keys())],
            sorted(strict_sets.keys()),
            ax=ax_sv1,
        )
        ax_sv1.set_title("Gene sets: fixed imp=strict, varying strat")
        fig_sv1.tight_layout()
        fig_sv1.savefig(FIGURES_DIR / "supervenn_strats_strict_imp.svg", bbox_inches="tight")
        fig_sv1.savefig(FIGURES_DIR / "supervenn_strats_strict_imp.png", bbox_inches="tight", dpi=200)
        plt.show()
        core = set.intersection(*strict_sets.values())
        print(f"Core genes (all strats, strict imp): {len(core)}")

    A_imp_sets = {
        imp: gene_sets_by_strat_imp[("A_confirmed_bad", imp)]
        for imp in ["strict", "knn", "softimpute"]
        if ("A_confirmed_bad", imp) in gene_sets_by_strat_imp
    }
    if len(A_imp_sets) >= 2:
        imp_order = sorted(A_imp_sets.keys())
        fig_sv2, ax_sv2 = plt.subplots(figsize=(10, 5))
        supervenn(
            [A_imp_sets[i] for i in imp_order],
            imp_order,
            ax=ax_sv2,
        )
        ax_sv2.set_title("Gene sets: fixed strat=A_confirmed_bad, varying imputation")
        fig_sv2.tight_layout()
        fig_sv2.savefig(FIGURES_DIR / "supervenn_imps_A_strat.svg", bbox_inches="tight")
        fig_sv2.savefig(FIGURES_DIR / "supervenn_imps_A_strat.png", bbox_inches="tight", dpi=200)
        plt.show()""",
    "cell-7-3-supervenn",
)

# ─────────────────────────────────────────────────────────────────────────────
# §8 — Progressive Accumulation / Depletion Curves
# ─────────────────────────────────────────────────────────────────────────────
sec8_header = make_md(
    "---\n## §8 — Progressive Accumulation / Depletion Curves\n\n"
    "Tracks gene retention from the most permissive to most aggressive data preparation "
    "strategy, revealing the biological cost of increasingly strict batch removal.",
    "sec8-header",
)

cell_8_1 = make_code(
    r"""# HARSHNESS_ORDER: ordered from permissive (most data/genes) to aggressive (least).
# Strat harshness follows ALL_STRATS index (S0=no removal to G=Affymetrix-only).
# Within each strat, softimpute recovers the most genes (strict < knn < softimpute).
HARSHNESS_ORDER = [
    ("S0_no_removal",    "strict"),
    ("S0_no_removal",    "knn"),
    ("S0_no_removal",    "softimpute"),
    ("A_confirmed_bad",  "strict"),
    ("A_confirmed_bad",  "knn"),
    ("A_confirmed_bad",  "softimpute"),
    ("B_extended_bad",   "strict"),
    ("B_extended_bad",   "knn"),
    ("B_extended_bad",   "softimpute"),
    ("C_rnaseq_only",    "strict"),
    ("C_rnaseq_only",    "knn"),
    ("C_rnaseq_only",    "softimpute"),
    ("D_malignant_only", "strict"),
    ("D_malignant_only", "knn"),
    ("D_malignant_only", "softimpute"),
    ("E1_iterative_r1",  "strict"),
    ("E1_iterative_r1",  "knn"),
    ("E1_iterative_r1",  "softimpute"),
    ("E2_iterative_r2",  "strict"),
    ("E2_iterative_r2",  "knn"),
    ("E2_iterative_r2",  "softimpute"),
    ("E3_iterative_r3",  "strict"),
    ("E3_iterative_r3",  "knn"),
    ("E3_iterative_r3",  "softimpute"),
    ("F_microarray_only","strict"),
    ("F_microarray_only","knn"),
    ("F_microarray_only","softimpute"),
    ("G_affymetrix_only","strict"),
    ("G_affymetrix_only","knn"),
    ("G_affymetrix_only","softimpute"),
]
# Filter to only include combinations that actually exist in gene_sets_by_strat_imp.
HARSHNESS_ORDER = [si for si in HARSHNESS_ORDER if si in gene_sets_by_strat_imp]

# 25_angel is tracked as a separate reference point: it applies the most aggressive
# INTERNAL gene-level filtering. On retention curves it is plotted as a horizontal
# reference line using the most permissive (S0_no_removal, strict) Angel gene set.
angel_representative_genes = gene_sets_angel.get(("S0_no_removal", "strict"), set())
if not angel_representative_genes:
    angel_representative_genes = next(iter(gene_sets_angel.values()), set())

print(f"HARSHNESS_ORDER steps available: {len(HARSHNESS_ORDER)}")
print(f"Angel gene set size (reference): {len(angel_representative_genes)}")
for si in HARSHNESS_ORDER:
    print(f"  {si}: {len(gene_sets_by_strat_imp[si])} genes")""",
    "cell-8-1-harshness-order",
)

cell_8_2 = make_code(
    r"""if len(HARSHNESS_ORDER) >= 2:
    n_genes_post0 = [len(gene_sets_by_strat_imp[si]) for si in HARSHNESS_ORDER]

    gene_sets_by_strat_imp_post1: dict = {}
    for (strat, imp, method, post_rm), genes in gene_sets.items():
        if post_rm and method != "25_angel":
            key = (strat, imp)
            gene_sets_by_strat_imp_post1.setdefault(key, set()).update(genes)
    n_genes_post1 = [len(gene_sets_by_strat_imp_post1.get(si, set())) for si in HARSHNESS_ORDER]

    cumulative: set = set()
    cum_curve = []
    for si in HARSHNESS_ORDER:
        cumulative |= gene_sets_by_strat_imp[si]
        cum_curve.append(len(cumulative))

    step_labels = [f"{s}\n{i}" for s, i in HARSHNESS_ORDER]
    x = list(range(len(HARSHNESS_ORDER)))

    fig_ret, (ax_line, ax_bar) = plt.subplots(1, 2, figsize=(14, 5))

    ax_line.plot(x, n_genes_post0, "o-", linewidth=1.5, color="#2166ac", label="post0 (n_genes)")
    if any(n > 0 for n in n_genes_post1):
        ax_line.plot(x, n_genes_post1, "s--", linewidth=1.2, color="#74add1",
                     alpha=0.8, label="post1 (n_genes)")
    ax_line.plot(x, cum_curve, "^--", linewidth=1.2, color="#d6604d", label="Cumulative union")
    if angel_representative_genes:
        ax_line.axhline(len(angel_representative_genes), color="#984ea3", linewidth=1.2,
                        linestyle=":", label=f"25_angel ({len(angel_representative_genes)})")
    ax_line.set_xticks(x)
    ax_line.set_xticklabels(step_labels, rotation=45, ha="right", fontsize=7)
    ax_line.set_ylabel("Number of genes")
    ax_line.set_title("Gene retention along harshness axis")
    ax_line.legend(fontsize=7)

    losses = [0] + [max(0, n_genes_post0[i - 1] - n_genes_post0[i])
                    for i in range(1, len(n_genes_post0))]
    bar_colors = [strat_pal.get(si[0], "#AAAAAA") for si in HARSHNESS_ORDER]
    ax_bar.bar(x, n_genes_post0, color=bar_colors, label="Retained")
    ax_bar.bar(x, losses, bottom=n_genes_post0, color="#d62728", alpha=0.7, label="Lost vs prev")
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(step_labels, rotation=45, ha="right", fontsize=7)
    ax_bar.set_ylabel("Number of genes")
    ax_bar.set_title("Genes retained vs lost per step")
    ax_bar.legend(fontsize=7)

    fig_ret.tight_layout()
    fig_ret.savefig(FIGURES_DIR / "gene_retention_curve.svg", bbox_inches="tight")
    fig_ret.savefig(FIGURES_DIR / "gene_retention_curve.png", bbox_inches="tight", dpi=200)
    plt.show()
else:
    print("Not enough harshness steps to plot retention curve.")""",
    "cell-8-2-retention-curve",
)

cell_8_3 = make_code(
    r"""if _has_supervenn:
    A_imp_sets_post0 = {
        imp: gene_sets_by_strat_imp.get(("A_confirmed_bad", imp), set())
        for imp in ["strict", "knn", "softimpute"]
    }
    A_imp_sets_post0 = {k: v for k, v in A_imp_sets_post0.items() if v}

    if len(A_imp_sets_post0) >= 2:
        imp_order = sorted(A_imp_sets_post0.keys())
        fig_sv3, ax_sv3 = plt.subplots(figsize=(10, 5))
        supervenn(
            [A_imp_sets_post0[i] for i in imp_order],
            imp_order,
            ax=ax_sv3,
        )
        ax_sv3.set_title("Gene recovery by imputation: A_confirmed_bad strategy")
        fig_sv3.tight_layout()
        fig_sv3.savefig(FIGURES_DIR / "supervenn_imputation_recovery.svg", bbox_inches="tight")
        fig_sv3.savefig(FIGURES_DIR / "supervenn_imputation_recovery.png", bbox_inches="tight", dpi=200)
        plt.show()

        if "strict" in A_imp_sets_post0:
            strict_genes = A_imp_sets_post0["strict"]
            for imp_name in ["knn", "softimpute"]:
                if imp_name in A_imp_sets_post0:
                    recovered = A_imp_sets_post0[imp_name] - strict_genes
                    print(f"{imp_name} recovered vs strict: {len(recovered)} genes")
            if "knn" in A_imp_sets_post0 and "softimpute" in A_imp_sets_post0:
                both = (
                    (A_imp_sets_post0["knn"] - strict_genes)
                    & (A_imp_sets_post0["softimpute"] - strict_genes)
                )
                print(f"Recovered by both knn AND softimpute: {len(both)} genes")
    else:
        print("Need at least 2 imputation variants of A_confirmed_bad for supervenn.")
else:
    print("supervenn not available — skipping imputation recovery supervenn.")""",
    "cell-8-3-imp-recovery",
)

# ─────────────────────────────────────────────────────────────────────────────
# §9 — GO Enrichment Analysis Setup
# ─────────────────────────────────────────────────────────────────────────────
sec9_header = make_md(
    "---\n## §9 — GO Enrichment Analysis Setup\n\n"
    "Loads the Gene Ontology DAG and human gene-GO associations. Uses a fixed background "
    "(all GO-annotated genes, not a dataset subset) to ensure fair enrichment comparison "
    "across strategies with different gene counts.",
    "sec9-header",
)

cell_9_1 = make_code(
    r"""import urllib.request
import shutil

T2T_DIR = Path("../../Retroelements/T2T_genes_article/T2T_transposons_genes/")
GO_OBO_PATH = Path("go-basic.obo")
GO_GAF_PATH = Path("goa_human.gaf")

for fname, url in [
    ("go-basic.obo",     "http://purl.obolibrary.org/obo/go/go-basic.obo"),
    ("goa_human.gaf.gz", "http://geneontology.org/gene-associations/goa_human.gaf.gz"),
]:
    dst = Path(fname.replace(".gz", ""))
    if dst.exists():
        print(f"{dst} already present ({dst.stat().st_size // 1024} KB).")
        continue
    t2t_candidate = T2T_DIR / fname.replace(".gz", "")
    if t2t_candidate.exists():
        shutil.copy(t2t_candidate, dst)
        print(f"Copied {dst} from T2T project cache.")
        continue
    gz_candidate = Path(fname)
    if gz_candidate.exists() and fname.endswith(".gz"):
        with gzip.open(gz_candidate, "rb") as fi, open(dst, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        print(f"Decompressed {dst} from existing .gz.")
        continue
    print(f"Downloading {url} ...")
    try:
        tmp = Path(fname)
        urllib.request.urlretrieve(url, tmp)
        if fname.endswith(".gz"):
            with gzip.open(tmp, "rb") as fi, open(dst, "wb") as fo:
                shutil.copyfileobj(fi, fo)
            tmp.unlink()
        print(f"Done: {dst} ({dst.stat().st_size // 1024} KB)")
    except Exception as exc:
        print(f"WARNING: could not download {fname}: {exc}")""",
    "cell-9-1-go-download",
)

cell_9_2 = make_code(
    r"""def load_go_database(obo_path: str, gaf_path: str) -> tuple:
    """Load the Gene Ontology DAG and human gene to GO term associations.

    The background gene list is fixed to ALL genes with GO annotations in the
    GAF file, not a subset of the current harmonization dataset. Using a
    dataset-specific background would introduce a bias: as more genes are
    included (less harsh filtering), the background grows, making GO terms
    harder to detect -- the opposite of the expected biological signal.
    Fixing the background to the full GO universe ensures that enrichment
    strength correctly increases when more biologically relevant genes are
    present.

    Parameters
    ----------
    obo_path : str
        Path to go-basic.obo file.
    gaf_path : str
        Path to goa_human.gaf file (not compressed).

    Returns
    -------
    godag : GODag
        Loaded GO DAG object.
    full_assoc : dict[str, set[str]]
        Mapping gene symbol to set of GO IDs.
    GO_BACKGROUND : list[str]
        Sorted list of all gene symbols present in the GAF file.
    """
    from goatools.obo_parser import GODag
    from goatools.anno.gaf_reader import GafReader

    godag = GODag(str(obo_path))
    ogaf = GafReader(str(gaf_path))
    full_assoc: dict = {}
    for ntf in ogaf.associations:
        full_assoc.setdefault(ntf.DB_Symbol, set()).add(ntf.GO_ID)
    go_background = sorted(full_assoc.keys())
    return godag, full_assoc, go_background


godag = full_assoc = GO_BACKGROUND = None
if GO_OBO_PATH.exists() and GO_GAF_PATH.exists():
    try:
        godag, full_assoc, GO_BACKGROUND = load_go_database(GO_OBO_PATH, GO_GAF_PATH)
        print(f"GO DAG loaded: {len(godag)} terms")
        print(f"Gene associations: {len(full_assoc)} symbols")
        print(f"Background size: {len(GO_BACKGROUND)} genes")
    except Exception as exc:
        print(f"WARNING: GO database load failed: {exc}")
else:
    print("GO files not found — §9-§11 GO analyses will be skipped.")""",
    "cell-9-2-go-load",
)

cell_9_3 = make_code(
    r"""def run_goatools_enrichment(
    gene_list: list,
    fdr_threshold: float = 0.05,
    namespace: "str | None" = "biological_process",
    min_study_count: int = 3,
) -> "pd.DataFrame":
    """Run GO enrichment for gene_list against the full GO-annotated human gene universe.

    Background is fixed to GO_BACKGROUND (all genes in full_assoc), not a
    dataset-specific subset. This ensures enrichment significance correctly
    increases as more relevant genes enter the study list.

    Parameters
    ----------
    gene_list : list of str
        HGNC gene symbols to test for enrichment.
    fdr_threshold : float
        FDR cutoff (Benjamini-Hochberg). Default 0.05.
    namespace : str or None
        GO namespace filter: "biological_process", "molecular_function",
        "cellular_component", or None for all.
    min_study_count : int
        Minimum number of study genes annotated to a GO term; terms with
        fewer are excluded to avoid spurious single-gene enrichments.

    Returns
    -------
    pd.DataFrame
        Enriched GO terms sorted by FDR. Columns: GO_ID, term_name,
        namespace, p_value, FDR, fold_enrichment, n_study, n_background,
        study_genes_str. Empty DataFrame if no terms pass threshold.
    """
    from goatools.go_enrichment import GOEnrichmentStudy

    if godag is None or full_assoc is None:
        return pd.DataFrame()

    goeaobj = GOEnrichmentStudy(
        GO_BACKGROUND,
        full_assoc,
        godag,
        propagate_counts=True,
        alpha=fdr_threshold,
        methods=["fdr_bh"],
    )
    results_all = goeaobj.run_study(gene_list, prt=None)
    rows = []
    for r in results_all:
        if r.p_fdr_bh >= fdr_threshold:
            continue
        if namespace is not None and r.NS != namespace:
            continue
        if r.study_count < min_study_count:
            continue
        fe = (
            (r.study_count / r.study_n) / (r.pop_count / r.pop_n)
            if r.pop_count > 0 and r.pop_n > 0
            else float("nan")
        )
        rows.append({
            "GO_ID":           r.GO,
            "term_name":       r.name,
            "namespace":       r.NS,
            "p_value":         r.p_uncorrected,
            "FDR":             r.p_fdr_bh,
            "fold_enrichment": fe,
            "n_study":         r.study_count,
            "n_background":    r.pop_count,
            "study_genes_str": ", ".join(sorted(r.study_items)),
        })
    if rows:
        return pd.DataFrame(rows).sort_values("FDR")
    return pd.DataFrame()


print("run_goatools_enrichment defined.")""",
    "cell-9-3-go-func",
)

# ─────────────────────────────────────────────────────────────────────────────
# §10 — Progressive GO Term Accumulation Curves
# ─────────────────────────────────────────────────────────────────────────────
sec10_header = make_md(
    "---\n## §10 — Progressive GO Term Accumulation Curves\n\n"
    "Quantifies how biological information (measured by unique GO term count) accumulates "
    "as more genes are retained, and identifies which filtering steps cause the largest "
    "biological information loss.",
    "sec10-header",
)

cell_10_1 = make_code(
    r"""go_study_genes_by_step: dict = {}

if full_assoc is not None and HARSHNESS_ORDER:
    for si in HARSHNESS_ORDER:
        gs = gene_sets_by_strat_imp[si]
        go_study_genes_by_step[si] = sorted(gs & set(full_assoc.keys()))
    angel_go_study = sorted(angel_representative_genes & set(full_assoc.keys()))
    print(f"Angel GO-annotated genes (reference): {len(angel_go_study)}")
    for si in HARSHNESS_ORDER:
        print(f"  {si}: {len(go_study_genes_by_step[si])} GO-annotated genes")
else:
    angel_go_study = []
    print("GO database not loaded or HARSHNESS_ORDER empty — skipping §10.")""",
    "cell-10-1-go-setup",
)

cell_10_2 = make_code(
    r"""from pathlib import Path as _Path

GO_CACHE_DIR = _Path("go_cache")
GO_CACHE_DIR.mkdir(exist_ok=True)

go_results_by_step: dict = {}
accumulation_curve = []
cumulative_terms: set = set()
go_angel = pd.DataFrame()

if go_study_genes_by_step:
    for si in HARSHNESS_ORDER:
        strat_key, imp_key = si
        cache_file = GO_CACHE_DIR / f"{strat_key}_{imp_key}.parquet"

        if cache_file.exists():
            go_df = pd.read_parquet(cache_file)
            print(f"  Loaded from cache: {si} -> {len(go_df)} terms")
        else:
            print(f"  Running GO enrichment: {si} ...", end=" ", flush=True)
            try:
                go_df = run_goatools_enrichment(
                    go_study_genes_by_step[si], namespace="biological_process"
                )
                if not go_df.empty:
                    go_df.to_parquet(cache_file, index=False)
                print(f"{len(go_df)} terms")
            except Exception as exc:
                go_df = pd.DataFrame()
                print(f"ERROR: {exc}")

        go_results_by_step[si] = go_df
        new_terms = set(go_df["GO_ID"]) - cumulative_terms if not go_df.empty else set()
        cumulative_terms |= new_terms
        accumulation_curve.append({
            "strat_imp":    str(si),
            "n_genes":      len(go_study_genes_by_step[si]),
            "n_go_terms":   len(go_df),
            "n_new_terms":  len(new_terms),
            "n_cumulative": len(cumulative_terms),
        })

    angel_cache = GO_CACHE_DIR / "angel_reference.parquet"
    if angel_cache.exists():
        go_angel = pd.read_parquet(angel_cache)
        print(f"Angel reference loaded from cache: {len(go_angel)} terms")
    elif angel_go_study:
        print("Running GO enrichment for angel reference ...", end=" ", flush=True)
        try:
            go_angel = run_goatools_enrichment(angel_go_study, namespace="biological_process")
            if not go_angel.empty:
                go_angel.to_parquet(angel_cache, index=False)
            print(f"{len(go_angel)} terms")
        except Exception as exc:
            print(f"ERROR: {exc}")

    acc_df = pd.DataFrame(accumulation_curve)
    print("\nAccumulation summary:")
    print(acc_df.to_string())
else:
    acc_df = pd.DataFrame()
    print("Skipping GO enrichment (no study gene sets available).")""",
    "cell-10-2-go-enrichment",
)

cell_10_3 = make_code(
    r"""if not acc_df.empty:
    fig_go, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))
    x = list(range(len(acc_df)))
    step_labels = acc_df["strat_imp"].tolist()

    ax1.plot(x, acc_df["n_genes"], "o-", color="#2166ac", linewidth=1.5, label="n_genes")
    ax1_r = ax1.twinx()
    ax1_r.plot(x, acc_df["n_go_terms"], "s--", color="#4dac26",
               linewidth=1.2, label="GO terms at step")
    ax1_r.plot(x, acc_df["n_cumulative"], "^--", color="#d6604d",
               linewidth=1.2, label="Cumulative unique terms")
    if not go_angel.empty:
        ax1_r.axhline(len(go_angel), color="#984ea3", linewidth=1.2, linestyle=":",
                      label=f"Angel ({len(go_angel)} terms)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(step_labels, rotation=45, ha="right", fontsize=7)
    ax1.set_ylabel("n_genes", color="#2166ac", fontsize=8)
    ax1_r.set_ylabel("GO:BP terms", fontsize=8)
    ax1.set_title("Gene count + GO term accumulation")
    lines1, lbl1 = ax1.get_legend_handles_labels()
    lines2, lbl2 = ax1_r.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lbl1 + lbl2, fontsize=6)

    bar_colors = []
    for si_str in step_labels:
        try:
            si_strat = si_str.strip("()'").split(",")[0].strip("' ")
            bar_colors.append(strat_pal.get(si_strat, "#AAAAAA"))
        except Exception:
            bar_colors.append("#AAAAAA")
    ax2.bar(x, acc_df["n_new_terms"], color=bar_colors)
    ax2.set_xticks(x)
    ax2.set_xticklabels(step_labels, rotation=45, ha="right", fontsize=7)
    ax2.set_ylabel("New unique GO:BP terms vs previous step")
    ax2.set_title("Biological information added per step")

    gene_diffs = [1] + [max(1, acc_df["n_genes"].iloc[i] - acc_df["n_genes"].iloc[i - 1])
                        for i in range(1, len(acc_df))]
    density = [nt / gd for nt, gd in zip(acc_df["n_new_terms"], gene_diffs)]
    ax3.bar(x, density, color=bar_colors)
    ax3.set_xticks(x)
    ax3.set_xticklabels(step_labels, rotation=45, ha="right", fontsize=7)
    ax3.set_ylabel("New GO terms per gene added")
    ax3.set_title("Biological information density")

    fig_go.tight_layout()
    fig_go.savefig(FIGURES_DIR / "go_accumulation_curve.svg", bbox_inches="tight")
    fig_go.savefig(FIGURES_DIR / "go_accumulation_curve.png", bbox_inches="tight", dpi=200)
    plt.show()
else:
    print("acc_df is empty — no GO accumulation curve to plot.")""",
    "cell-10-3-go-curve",
)

cell_10_4 = make_code(
    r"""if go_results_by_step and len(HARSHNESS_ORDER) >= 2:
    max_lost = 0
    max_pair = None
    for i in range(len(HARSHNESS_ORDER) - 1):
        key_p, key_s = HARSHNESS_ORDER[i], HARSHNESS_ORDER[i + 1]
        if go_results_by_step.get(key_p, pd.DataFrame()).empty:
            continue
        if go_results_by_step.get(key_s, pd.DataFrame()).empty:
            continue
        terms_p = set(go_results_by_step[key_p]["GO_ID"])
        terms_s = set(go_results_by_step[key_s]["GO_ID"])
        lost = terms_p - terms_s
        if len(lost) > max_lost:
            max_lost = len(lost)
            max_pair = (key_p, key_s, lost)

    if max_pair is not None:
        key_p, key_s, lost_ids = max_pair
        lost_df = (
            go_results_by_step[key_p]
            [go_results_by_step[key_p]["GO_ID"].isin(lost_ids)]
            .sort_values("fold_enrichment", ascending=False)
            .head(20)
        )
        print(f"Largest term loss: {key_p} -> {key_s}: {max_lost} terms lost")

        if not lost_df.empty:
            fig_lost, ax_lost = plt.subplots(
                figsize=(10, max(4, len(lost_df) * 0.35 + 1))
            )
            c_vals = [-np.log10(max(r["FDR"], 1e-30)) for _, r in lost_df.iterrows()]
            norm_c = plt.Normalize(0, max(c_vals) if c_vals else 1)
            colors_lost = [plt.cm.RdYlGn_r(norm_c(v)) for v in c_vals]
            ax_lost.barh(lost_df["term_name"], lost_df["fold_enrichment"], color=colors_lost)
            ax_lost.set_xlabel("Fold enrichment")
            ax_lost.set_title(
                f"Top GO terms lost: {key_p} -> {key_s}\n({max_lost} total terms lost)"
            )
            ax_lost.tick_params(labelsize=7)
            fig_lost.tight_layout()
            fig_lost.savefig(FIGURES_DIR / "go_lost_terms_max_pair.svg", bbox_inches="tight")
            fig_lost.savefig(FIGURES_DIR / "go_lost_terms_max_pair.png",
                             bbox_inches="tight", dpi=200)
            plt.show()
    else:
        print("No term loss detected between adjacent pairs.")
else:
    print("Insufficient GO results for term-loss analysis.")""",
    "cell-10-4-go-lost-terms",
)

cell_10_5 = make_code(
    r"""if _has_supervenn and go_results_by_step:
    A_go_sets = {}
    for imp_name in ["strict", "knn", "softimpute"]:
        si = ("A_confirmed_bad", imp_name)
        if si in go_results_by_step and not go_results_by_step[si].empty:
            A_go_sets[imp_name] = set(go_results_by_step[si]["GO_ID"])

    if len(A_go_sets) >= 2:
        imp_order_go = sorted(A_go_sets.keys())
        fig_sv_go, ax_sv_go = plt.subplots(figsize=(10, 5))
        supervenn(
            [A_go_sets[i] for i in imp_order_go],
            imp_order_go,
            ax=ax_sv_go,
        )
        ax_sv_go.set_title("GO:BP term recovery by imputation\n(A_confirmed_bad strategy)")
        fig_sv_go.tight_layout()
        fig_sv_go.savefig(FIGURES_DIR / "supervenn_go_imputation.svg", bbox_inches="tight")
        fig_sv_go.savefig(FIGURES_DIR / "supervenn_go_imputation.png",
                          bbox_inches="tight", dpi=200)
        plt.show()
    else:
        print("Need at least 2 imputation variants for GO supervenn.")
else:
    print("supervenn unavailable or no GO results — skipping imputation GO supervenn.")""",
    "cell-10-5-go-supervenn",
)

# ─────────────────────────────────────────────────────────────────────────────
# §11 — FL-Specific Gene Retention Analysis
# ─────────────────────────────────────────────────────────────────────────────
sec11_header = make_md(
    "---\n## §11 — FL-Specific Gene Retention Analysis\n\n"
    "Tracks how many FL-relevant genes (from published transcriptomic subtype, prognostic, "
    "and marker gene sets) survive each data preparation strategy, linking filtering decisions "
    "to downstream biological analysis capability.",
    "sec11-header",
)

cell_11_0 = make_md(CITATIONS_SRC, "cell-11-0-citations")

cell_11_1 = make_code(
    r"""FL_2025_MARKERS = {
    "C1_DZ_proliferative": [
        "MKI67", "TOP2A", "PCNA", "MCM2", "MCM6", "CCND2", "CDK4", "AICDA",
        "MYBL1", "CENPF", "UBE2C", "RRM2", "TYMS", "GINS2",
    ],
    "C2_LZ_anergy": [
        "BCL2", "CXCR4", "CD83", "FCER2", "CD79A", "IGHM", "IGHD",
        "IRF4", "PRDM1", "BLIMP1", "FAS",
    ],
    "C3_inflammatory": [
        "CXCL9", "CXCL10", "CXCL11", "STAT1", "IFI27", "IFI44",
        "IFIT1", "IFIT3", "ISG15", "MX1", "OAS1", "IFI16",
    ],
}

LEGACY_GC_MARKERS = {
    "Centroblast_DZ": [
        "AICDA", "MKI67", "BCL6", "CXCR4", "EZH2", "RGS13", "FOXO1",
        "LMO2", "CCNB1", "BIRC5",
    ],
    "Centrocyte_LZ": [
        "CD83", "MME", "FCER2", "BCL2", "CD40", "SELL",
        "DUSP5", "DUSP6", "NR4A1",
    ],
}

FL_PROG_SIGNATURES = {
    "FL_PFS_signature_2019": [
        "LMO2", "FN1", "CCND2", "BCL6", "CCL3", "HGAL",
        "LRMP", "MKI67", "BCL2", "CDKN2A",
    ],
    "POD24_markers": [
        "EZH2", "BCL2", "CCND3", "TNFRSF14", "KMT2D",
        "FOXO1", "CREBBP", "EP300",
    ],
}

FL_PATHWAY_GENES = {
    "BCR_signaling": ["CD79A", "CD79B", "PTPN6", "PIK3CD", "CARD11", "BCL10", "MALT1"],
    "NF_kB":         ["NFKB1", "NFKB2", "REL", "RELA", "RELB", "IKBKB", "IKBKG"],
    "PI3K_AKT":      ["PIK3CA", "PIK3CB", "PIK3CD", "AKT1", "AKT2", "AKT3", "PTEN", "MTOR"],
    "GCB_markers":   ["BCL6", "MYC", "BCL2", "MME", "CXCR4", "CXCR5"],
}

FL_GENES_ALL = sorted(set(
    sum(FL_2025_MARKERS.values(), []) +
    sum(LEGACY_GC_MARKERS.values(), []) +
    sum(FL_PROG_SIGNATURES.values(), []) +
    sum(FL_PATHWAY_GENES.values(), [])
))

fl_gene_meta = []
for cat, genes in {
    **FL_2025_MARKERS, **LEGACY_GC_MARKERS,
    **FL_PROG_SIGNATURES, **FL_PATHWAY_GENES,
}.items():
    for g in genes:
        fl_gene_meta.append({"gene": g, "category": cat})
fl_gene_df = pd.DataFrame(fl_gene_meta).drop_duplicates("gene").reset_index(drop=True)

print(f"Total FL-relevant genes: {len(FL_GENES_ALL)}")
print(fl_gene_df["category"].value_counts().to_string())


def validate_gene_aliases(gene_list: list, reference_genes: set) -> dict:
    """Check which genes from a curated list are absent from the expression matrices
    and propose HGNC alias resolution.

    Known aliases to check:
    - MME  <-> CD10  (neprilysin; HGNC primary = MME)
    - FAS  <-> CD95  <-> TNFRSF6  (HGNC primary = FAS)
    - FCER2 <-> CD23  (HGNC primary = FCER2)

    Parameters
    ----------
    gene_list : list of str
        Curated gene symbols to validate.
    reference_genes : set of str
        Union of all gene_sets values (not 25_angel) used as reference universe.

    Returns
    -------
    dict[str, str]
        Mapping absent_symbol -> suggested_replacement. Empty if all found.
    """
    KNOWN_ALIASES = {
        "CD10": "MME", "CD95": "FAS", "TNFRSF6": "FAS",
        "CD23": "FCER2", "BLIMP1": "PRDM1",
    }
    missing = {}
    for g in gene_list:
        if g not in reference_genes:
            suggestion = KNOWN_ALIASES.get(g, "")
            if not suggestion:
                for primary, aliases in [
                    ("MME",   ["CD10"]),
                    ("FAS",   ["CD95", "TNFRSF6"]),
                    ("FCER2", ["CD23"]),
                    ("PRDM1", ["BLIMP1"]),
                ]:
                    if g == primary and primary not in reference_genes:
                        suggestion = ", ".join(a for a in aliases if a in reference_genes)
            missing[g] = suggestion
    return missing


all_reference_genes = set.union(*gene_sets_by_strat_imp.values()) if gene_sets_by_strat_imp else set()
missing_aliases = validate_gene_aliases(FL_GENES_ALL, all_reference_genes)
if missing_aliases:
    print("\nFL genes absent from reference — check aliases:")
    for g, sug in missing_aliases.items():
        print(f"  {g!r} -> suggestion: {sug!r}")
else:
    print("\nAll FL genes found in reference gene universe.")""",
    "cell-11-1-fl-genes",
)

cell_11_2 = make_code(
    r"""fl_presence = pd.DataFrame(
    {
        f"{s}__{i}__{m}": [g in gene_sets[(s, i, m, False)] for g in FL_GENES_ALL]
        for (s, i, m, pr) in gene_sets
        if not pr and (s, i) in gene_sets_by_strat_imp
    },
    index=FL_GENES_ALL,
)

cat_order = list({
    **FL_2025_MARKERS, **LEGACY_GC_MARKERS,
    **FL_PROG_SIGNATURES, **FL_PATHWAY_GENES,
}.keys())
gene_to_cat = fl_gene_df.set_index("gene")["category"]
fl_presence["_cat"] = [gene_to_cat.get(g, "?") for g in FL_GENES_ALL]
fl_presence["_cat_order"] = fl_presence["_cat"].map(
    {c: i for i, c in enumerate(cat_order)}
)
fl_presence = fl_presence.sort_values(["_cat_order", "_cat"]).drop(
    columns=["_cat", "_cat_order"]
)

print(f"FL gene presence matrix: {fl_presence.shape}")
print(f"  Always present: {fl_presence.all(axis=1).sum()}")
print(f"  Sometimes absent: {(~fl_presence.all(axis=1)).sum()}")""",
    "cell-11-2-fl-presence",
)

cell_11_3 = make_code(
    r"""if not fl_presence.empty:
    def _col_score(col):
        parts = col.split("__")
        if len(parts) < 3:
            return -999.0
        s, i, m = parts[0], parts[1], parts[2]
        matches = df_ok[(df_ok.strat == s) & (df_ok.imp == i) & (df_ok.method == m)]
        return matches["composite_score"].iloc[0] if not matches.empty else -999.0

    sorted_cols = sorted(fl_presence.columns, key=_col_score, reverse=True)
    fl_pres_sorted = fl_presence[sorted_cols]

    gene_cats = fl_gene_df.set_index("gene").reindex(fl_pres_sorted.index)["category"]
    all_cats_hm = sorted(gene_cats.dropna().unique())
    cat_pal = dict(zip(all_cats_hm, sns.color_palette("tab10", n_colors=len(all_cats_hm))))
    cat_colors = gene_cats.map(cat_pal).fillna("#CCCCCC")

    fig_hm, ax_hm = plt.subplots(
        figsize=(max(10, len(sorted_cols) * 0.25), max(6, len(FL_GENES_ALL) * 0.22))
    )
    cmap_binary = sns.diverging_palette(10, 130, as_cmap=True)
    sns.heatmap(
        fl_pres_sorted.astype(int), ax=ax_hm,
        cmap=cmap_binary, vmin=0, vmax=1,
        xticklabels=False, yticklabels=True,
        linewidths=0,
        cbar_kws={"shrink": 0.3, "label": "Gene present (1) / absent (0)"},
    )
    if len(sorted_cols) > 10:
        ax_hm.axvline(10, color="black", linewidth=1.2, linestyle="--")

    for yi, gene in enumerate(fl_pres_sorted.index):
        ax_hm.add_patch(
            plt.Rectangle(
                (-0.5, yi), 0.5, 1,
                color=cat_colors.get(gene, "#CCCCCC"),
                transform=ax_hm.transData, clip_on=False,
            )
        )

    ax_hm.set_title("FL gene retention heatmap (sorted by composite_score)")
    ax_hm.tick_params(axis="y", labelsize=6)

    patches_cat = [mpatches.Patch(color=c, label=l) for l, c in cat_pal.items()]
    ax_hm.legend(handles=patches_cat, loc="upper left",
                 bbox_to_anchor=(1.01, 1), fontsize=7, title="Gene category")

    fig_hm.tight_layout()
    fig_hm.savefig(FIGURES_DIR / "fl_retention_heatmap.svg", bbox_inches="tight")
    fig_hm.savefig(FIGURES_DIR / "fl_retention_heatmap.png", bbox_inches="tight", dpi=200)
    plt.show()
else:
    print("fl_presence is empty — skipping retention heatmap.")""",
    "cell-11-3-fl-heatmap",
)

cell_11_4 = make_code(
    r"""if HARSHNESS_ORDER and gene_sets_by_strat_imp:
    all_fl_categories = list({
        **FL_2025_MARKERS, **LEGACY_GC_MARKERS,
        **FL_PROG_SIGNATURES, **FL_PATHWAY_GENES,
    }.keys())

    # ── Figure A: per-category subplots ──────────────────────────────────────
    n_cats = len(all_fl_categories)
    fig_a, axes_a = plt.subplots(
        2, math.ceil(n_cats / 2),
        figsize=(max(12, n_cats * 1.5), 8),
        sharey=True,
    )
    axes_a_flat = axes_a.flatten()
    x = list(range(len(HARSHNESS_ORDER)))
    step_labels = [f"{s}\n{i}" for s, i in HARSHNESS_ORDER]

    for ax_i, cat in enumerate(all_fl_categories):
        ax = axes_a_flat[ax_i]
        cat_genes = [
            g for g in fl_gene_df[fl_gene_df["category"] == cat]["gene"].tolist()
            if g in all_reference_genes
        ]
        fractions = [
            len(set(cat_genes) & gene_sets_by_strat_imp[si]) / max(len(cat_genes), 1)
            for si in HARSHNESS_ORDER
        ]
        ax.plot(x, fractions, "o-", linewidth=1.5, markersize=4)
        ax.axhline(0.9, color="gray", linestyle="--", linewidth=0.7)
        if angel_representative_genes and cat_genes:
            frac_angel = (
                len(set(cat_genes) & angel_representative_genes) / max(len(cat_genes), 1)
            )
            ax.axhline(frac_angel, color="#984ea3", linewidth=0.8, linestyle=":", alpha=0.7)
        ax.set_title(cat, fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(step_labels, rotation=45, ha="right", fontsize=5)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Fraction retained", fontsize=7)

    for ax_hidden in axes_a_flat[n_cats:]:
        ax_hidden.set_visible(False)

    fig_a.suptitle("FL gene retention by category along harshness axis", y=1.01)
    fig_a.tight_layout()
    fig_a.savefig(FIGURES_DIR / "fl_retention_curves_per_cat.svg", bbox_inches="tight")
    fig_a.savefig(FIGURES_DIR / "fl_retention_curves_per_cat.png", bbox_inches="tight", dpi=200)
    plt.show()

    # ── Figure B: overall + per-category thin lines ───────────────────────────
    fig_b, ax_b = plt.subplots(figsize=(max(10, len(HARSHNESS_ORDER) * 0.5), 5))

    for cat in all_fl_categories:
        cat_genes = [
            g for g in fl_gene_df[fl_gene_df["category"] == cat]["gene"].tolist()
            if g in all_reference_genes
        ]
        fracs = [
            len(set(cat_genes) & gene_sets_by_strat_imp[si]) / max(len(cat_genes), 1)
            for si in HARSHNESS_ORDER
        ]
        ax_b.plot(x, fracs, linewidth=0.8, alpha=0.4)

    overall_fracs = [
        len(set(FL_GENES_ALL) & gene_sets_by_strat_imp[si]) / max(len(FL_GENES_ALL), 1)
        for si in HARSHNESS_ORDER
    ]
    ax_b.plot(x, overall_fracs, "o-", linewidth=2.5, color="black",
              label="All FL genes", zorder=5)

    if angel_representative_genes:
        angel_frac = (
            len(set(FL_GENES_ALL) & angel_representative_genes) / max(len(FL_GENES_ALL), 1)
        )
        ax_b.scatter(
            [len(HARSHNESS_ORDER)], [angel_frac],
            color="#984ea3", marker="D", s=60, zorder=6,
            label=f"Angel ({angel_frac:.2f})",
        )

    ax_b.axhline(0.9, color="gray", linestyle="--", linewidth=0.8, label="90% threshold")
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(step_labels, rotation=45, ha="right", fontsize=7)
    ax_b.set_ylabel("Fraction of FL genes retained")
    ax_b.set_ylim(0, 1.05)
    ax_b.set_title("Overall FL gene retention + per-category curves")
    ax_b.legend(fontsize=7)

    fig_b.tight_layout()
    fig_b.savefig(FIGURES_DIR / "fl_retention_curves_overall.svg", bbox_inches="tight")
    fig_b.savefig(FIGURES_DIR / "fl_retention_curves_overall.png", bbox_inches="tight", dpi=200)
    plt.show()
else:
    print("HARSHNESS_ORDER or gene_sets_by_strat_imp empty — skipping FL retention curves.")""",
    "cell-11-4-fl-curves",
)

cell_11_5 = make_code(
    r"""if full_assoc is not None and FL_GENES_ALL:
    fl_genes_in_go = [g for g in FL_GENES_ALL if g in full_assoc]
    print(f"FL genes with GO annotations: {len(fl_genes_in_go)} / {len(FL_GENES_ALL)}")

    go_fl_all = run_goatools_enrichment(fl_genes_in_go, namespace="biological_process")

    if HARSHNESS_ORDER:
        most_aggressive = HARSHNESS_ORDER[-1]
        fl_at_risk = [g for g in fl_genes_in_go
                      if g not in gene_sets_by_strat_imp.get(most_aggressive, set())]
        print(f"FL genes at-risk (absent in {most_aggressive}): {len(fl_at_risk)}")
        go_fl_risk = run_goatools_enrichment(fl_at_risk, namespace="biological_process")
    else:
        most_aggressive = None
        go_fl_risk = pd.DataFrame()

    def _dot_plot(go_df, ax, title):
        if go_df.empty:
            ax.text(0.5, 0.5, "No significant terms", ha="center", transform=ax.transAxes)
            ax.set_title(title)
            return
        top20 = go_df.head(20)
        sizes = (top20["n_study"] / top20["n_study"].max() * 200).clip(lower=20)
        c_vals = -np.log10(top20["FDR"].clip(lower=1e-30))
        sc = ax.scatter(
            top20["fold_enrichment"], top20["term_name"],
            s=sizes, c=c_vals, cmap="YlOrRd", alpha=0.85,
        )
        plt.colorbar(sc, ax=ax, label="-log10(FDR)", shrink=0.6)
        ax.set_xlabel("Fold enrichment")
        ax.set_title(title)
        ax.tick_params(labelsize=7)

    n_rows = max(5, min(20, max(len(go_fl_all), len(go_fl_risk))))
    fig_dot, axes_dot = plt.subplots(1, 2, figsize=(18, n_rows * 0.4 + 2))
    _dot_plot(go_fl_all,  axes_dot[0], "GO enrichment: all FL genes")
    _dot_plot(go_fl_risk, axes_dot[1],
              f"GO enrichment: FL genes at-risk\n({most_aggressive})")
    fig_dot.tight_layout()
    fig_dot.savefig(FIGURES_DIR / "fl_go_dot_plots.svg", bbox_inches="tight")
    fig_dot.savefig(FIGURES_DIR / "fl_go_dot_plots.png", bbox_inches="tight", dpi=200)
    plt.show()
else:
    print("GO database not loaded or FL_GENES_ALL empty — skipping FL GO enrichment.")""",
    "cell-11-5-fl-go",
)

cell_11_6 = make_code(
    r"""if HARSHNESS_ORDER and full_assoc is not None:
    fl_go_results_by_step: dict = {}
    fl_cumulative_terms: set = set()
    fl_acc_curve = []

    for si in HARSHNESS_ORDER:
        strat_key, imp_key = si
        cache_file = GO_CACHE_DIR / f"fl_{strat_key}_{imp_key}.parquet"
        gs = gene_sets_by_strat_imp[si]
        fl_study = [g for g in FL_GENES_ALL if g in gs and g in full_assoc]

        if cache_file.exists():
            fl_go_df = pd.read_parquet(cache_file)
        else:
            try:
                fl_go_df = run_goatools_enrichment(fl_study, namespace="biological_process")
                if not fl_go_df.empty:
                    fl_go_df.to_parquet(cache_file, index=False)
            except Exception as exc:
                fl_go_df = pd.DataFrame()
                print(f"WARNING: FL GO enrichment failed for {si}: {exc}")

        fl_go_results_by_step[si] = fl_go_df
        new_terms = set(fl_go_df["GO_ID"]) - fl_cumulative_terms if not fl_go_df.empty else set()
        fl_cumulative_terms |= new_terms
        fl_acc_curve.append({
            "strat_imp":    str(si),
            "n_fl_genes":   len(fl_study),
            "n_go_terms":   len(fl_go_df),
            "n_new_terms":  len(new_terms),
            "n_cumulative": len(fl_cumulative_terms),
        })

    fl_acc_df = pd.DataFrame(fl_acc_curve)
    x = list(range(len(HARSHNESS_ORDER)))
    step_labels = [f"{s}\n{i}" for s, i in HARSHNESS_ORDER]

    fig_fl_go, ax_fl = plt.subplots(figsize=(max(10, len(HARSHNESS_ORDER) * 0.5), 5))
    ax_fl.plot(x, fl_acc_df["n_fl_genes"], "o-", color="#2166ac",
               linewidth=1.5, label="FL genes in dataset")
    ax_fl2 = ax_fl.twinx()
    ax_fl2.plot(x, fl_acc_df["n_go_terms"], "s--", color="#4dac26",
                linewidth=1.2, label="FL GO terms at step")
    ax_fl2.plot(x, fl_acc_df["n_cumulative"], "^--", color="#d6604d",
                linewidth=1.2, label="Cumulative FL GO terms")

    ax_fl.set_xticks(x)
    ax_fl.set_xticklabels(step_labels, rotation=45, ha="right", fontsize=7)
    ax_fl.set_ylabel("n_FL_genes", color="#2166ac", fontsize=8)
    ax_fl2.set_ylabel("GO:BP terms", fontsize=8)
    ax_fl.set_title("FL-specific GO term accumulation along harshness axis")
    lines1, lbl1 = ax_fl.get_legend_handles_labels()
    lines2, lbl2 = ax_fl2.get_legend_handles_labels()
    ax_fl.legend(lines1 + lines2, lbl1 + lbl2, fontsize=7)

    fig_fl_go.tight_layout()
    fig_fl_go.savefig(FIGURES_DIR / "fl_go_accumulation.svg", bbox_inches="tight")
    fig_fl_go.savefig(FIGURES_DIR / "fl_go_accumulation.png", bbox_inches="tight", dpi=200)
    plt.show()
else:
    print("HARSHNESS_ORDER or GO database not available — skipping FL GO accumulation curve.")""",
    "cell-11-6-fl-go-curve",
)

cell_11_7 = make_code(
    r"""if gene_sets_by_strat_imp and HARSHNESS_ORDER:
    rec_rows = []
    for run_id, row in df_ok.iterrows():
        strat, imp, method = row["strat"], row["imp"], row["method"]
        si = (strat, imp)
        gs = gene_sets_by_strat_imp.get(si, set())
        n_fl_retained = len(set(FL_GENES_ALL) & gs)
        frac_fl = n_fl_retained / max(len(FL_GENES_ALL), 1)

        all_cats_ok = True
        cat_retentions = {}
        for cat, cat_genes in {
            **FL_2025_MARKERS, **LEGACY_GC_MARKERS,
            **FL_PROG_SIGNATURES, **FL_PATHWAY_GENES,
        }.items():
            present = [g for g in cat_genes if g in all_reference_genes]
            frac_cat = len(set(present) & gs) / max(len(present), 1) if present else 1.0
            cat_retentions[f"fl_ret_{cat}"] = round(frac_cat, 3)
            if frac_cat < 0.9:
                all_cats_ok = False

        rec_rows.append({
            "run_id":                run_id,
            "strat":                 strat,
            "imp":                   imp,
            "method":                method,
            "composite_score":       row.get("composite_score", np.nan),
            "score_batch_mixing":    row.get("score_batch_mixing", np.nan),
            "score_bio_preservation":row.get("score_bio_preservation", np.nan),
            "r2_RNA_BATCH":          row.get("r2_RNA_BATCH", np.nan),
            "r2_Diagnosis_cell_type_unified": row.get("r2_Diagnosis_cell_type_unified", np.nan),
            "n_genes":               len(gs),
            "n_fl_genes_retained":   n_fl_retained,
            "frac_fl_genes":         round(frac_fl, 3),
            "all_fl_categories_90pct": all_cats_ok,
            **cat_retentions,
        })

    rec_table = (
        pd.DataFrame(rec_rows)
        .set_index("run_id")
        .sort_values("composite_score", ascending=False)
    )

    display_cols_rec = [
        "strat", "imp", "method", "composite_score",
        "score_batch_mixing", "score_bio_preservation",
        "r2_RNA_BATCH", "r2_Diagnosis_cell_type_unified",
        "n_genes", "n_fl_genes_retained", "frac_fl_genes",
        "all_fl_categories_90pct",
    ]
    print("Top 20 recommendations:")
    print(rec_table[display_cols_rec].head(20).to_string())

    style_cols = ["composite_score", "frac_fl_genes",
                  "r2_RNA_BATCH", "r2_Diagnosis_cell_type_unified"]
    styled = (
        rec_table[display_cols_rec].head(30).style
        .background_gradient(subset=["composite_score"], cmap="RdYlGn")
        .background_gradient(subset=["frac_fl_genes"], cmap="RdYlGn")
        .background_gradient(subset=["r2_RNA_BATCH"], cmap="RdYlGn_r")
        .format({c: "{:.3f}" for c in style_cols})
    )
    display(styled)

    rec_table.to_csv("recommendation_table.csv")
    print("\nSaved: recommendation_table.csv")

    try:
        import boto3 as _boto3
        _s3 = _boto3.client("s3")
        _s3.upload_file("recommendation_table.csv", S3_BUCKET,
                        f"{S3_PREFIX}/recommendation_table.csv")
        print(f"Uploaded to s3://{S3_BUCKET}/{S3_PREFIX}/recommendation_table.csv")
    except Exception as exc:
        print(f"WARNING: S3 upload failed: {exc}")
else:
    print("No data available for recommendation table.")""",
    "cell-11-7-recommendation",
)

# ─────────────────────────────────────────────────────────────────────────────
# Assemble all new cells in order
# ─────────────────────────────────────────────────────────────────────────────
new_cells = [
    # §5
    sec5_header, cell_5_0, cell_5_1, cell_5_2, cell_5_3, cell_5_4,
    cell_5_5, cell_citations, cell_5_6,
    # §6
    sec6_header, cell_6_1, cell_6_2, cell_6_3, cell_6_4,
    # §7
    sec7_header, cell_7_1, cell_7_2, cell_7_3,
    # §8
    sec8_header, cell_8_1, cell_8_2, cell_8_3,
    # §9
    sec9_header, cell_9_1, cell_9_2, cell_9_3,
    # §10
    sec10_header, cell_10_1, cell_10_2, cell_10_3, cell_10_4, cell_10_5,
    # §11
    sec11_header, cell_11_0, cell_11_1, cell_11_2, cell_11_3,
    cell_11_4, cell_11_5, cell_11_6, cell_11_7,
]

insert_after(nb, "cell-4-7-pareto", new_cells)

print(f"Total cells after insertion: {len(nb['cells'])}")
print(f"Added {len(new_cells)} cells")

with open(NB_PATH, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook saved successfully.")
