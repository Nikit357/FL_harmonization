"""r46 — review-draft PDFs: revised main-figure panels and Supplementary Figures S1-S18 (new
numbering, submitted pages reused for unchanged figures) → Revised_manuscript/review_package_<tag>/.
Run: python r46_review_figure_pdfs.py [--tag YYMMDD] (from article_1_revision/; default tag = today).
Daniil assembles the final pages.

Alt text (Daniil 2026-11-08, gates_review §9.4 B3 option b): every supplementary figure gets one
alt-text line on its title page in the PDF (SUPP_ALT_TEXT); the manuscript carries none for the
supplementary figures."""
import argparse
import datetime as dt
import io
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pypdf import PdfReader, PdfWriter

REV = Path(__file__).resolve().parents[1]
FIG = REV / "figures_svg"
OLD = REV.parent / "figures_for_article/supplementary_260824/Supplementary Figures S1-S19.pdf"
_parser = argparse.ArgumentParser(description="review-draft figure PDFs")
_parser.add_argument("--tag", default=dt.date.today().strftime("%y%m%d"), help="date tag YYMMDD")
TAG = _parser.parse_args().tag
OUT = REV / f"Revised_manuscript/review_package_{TAG}"
OUT.mkdir(parents=True, exist_ok=True)
old_reader = PdfReader(str(OLD))

def old_page(n):  # submitted S<n> is page n-1
    return ("submitted", n - 1)

MAIN = [
    ("Figure 1E (new): batch × diagnosis confounding", ["fig1E_confounding"]),
    ("Figure 2A (re-render, plain-word labels)", ["fig2A_strategy_sankey"]),
    ("Figure 3 (rebuilt on the 22-metric panel; 22 recommended approaches marked)", ["fig3_reduced_panel_clustermap"]),
    ("Figure 4 (rebuilt): unharmonized data and the single-sample-type recommendations, A–D", [f"fig4{c}_" for c in "ABCD"] + ["fig4_legend"]),
    ("Figure 5 (rebuilt): the RNA-seq + microarrays recommendations, A–C", [f"fig5{c}_" for c in "ABC"] + ["fig5_legend"]),
    ("Figure 6B: η² of the design factors", ["fig6B_eta_squared"]),
    ("Figure 6C/D: four scores of the recommended approaches", ["fig6CD_four_scores"]),
    ("Figure 6 gradient panel (new)", ["fig6_gradient_panel"]),
    ("Figure 6F: decision tree", ["fig6F_decision_tree"]),
]
SUPP = [
    ("Supplementary Figure 1 (unchanged; submitted S1)", [old_page(1)]),
    ("Supplementary Figure 2 (merges submitted S2–S4)", ["figS2_merged_distributions"]),
    ("Supplementary Figure 3 (unchanged; submitted S5)", [old_page(5)]),
    ("Supplementary Figure 4 (rebuilt; submitted S6)", ["figS4_metric_availability"]),
    ("Supplementary Figure 5 (rebuilt on the 87 metrics with the 22 panel metrics marked; submitted S7)", ["figS5_metric_correlation_clusters"]),
    ("Supplementary Figure 6 (rebuilt; submitted S9)", ["figS6_approach_correlation"]),
] + [
    (f"Supplementary Figure {new} (unchanged; submitted S{old})", [old_page(old)])
    for new, old in zip(range(7, 14), range(11, 18))
] + [
    ("Supplementary Figure 14 (gates; replaces submitted S18)", ["figS14a_marker_correlation_gate", "figS14b_prediction_gate", "figS14c_label_leakage"]),
    ("Supplementary Figure 15 (unchanged; submitted S19)", [old_page(19)]),
    ("Supplementary Figure 16 (new): robustness of the selection", ["figS16a_robustness_tau", "figS16b_front_stability"]),
    ("Supplementary Figure 17 (new): confounding gradient, A–F (two pages: A–C, D–F)", [f"figS17{c}" for c in "abcdef"]),
    ("Supplementary Figure 18 (new): leave-cohort-out validation", ["figS18a_v1_rank_on_test", "figS18b_v1_regret"]),
]


# One alt-text line per supplementary figure (new numbering), plain words.
SUPP_ALT_TEXT = {
    1: "Bar plots of sample counts per cohort coloured by diagnosis and by batch, and a PCA plot "
       "of a first FSQN R normalization coloured by batch, with an arrow at the batches removed in strategy A.",
    2: "Grid of density curves of log2 gene expression for 30 representative cohorts, without "
       "imputation, with KNN and with softImpute imputation.",
    3: "Clustermap of Jaccard indices between the gene sets of every strategy and imputation combination.",
    4: "Heat map of the share of approaches with every metric defined, per strategy and imputation, "
       "for the reduced panel and for all 87 scoring metrics.",
    5: "Clustermap of Spearman correlations between the 87 scoring metrics, with colour bars for "
       "the 22 panel metrics (also starred), metric group, score bar, annotation column and type.",
    6: "Clustermap of Spearman correlations between harmonization approaches on the reduced panel, "
       "annotated by strategy, method and imputation.",
    7: "PCA, UMAP and tSNE plots of MNN-harmonized data in strategies S0, H and D and of the "
       "unharmonized S0 data, coloured by batch and by diagnosis.",
    8: "PCA, UMAP and tSNE plots of SVA-harmonized strategy C data with KNN, softImpute and no "
       "imputation and of the unharmonized data, coloured by batch and by diagnosis.",
    9: "PCA, UMAP and tSNE plots of FSQN R-harmonized strategy C data with three imputation "
       "settings and of the unharmonized data, coloured by batch and by diagnosis.",
    10: "PCA, UMAP and tSNE plots of MNN- and FSQN R-harmonized strategy J data and of the "
        "unharmonized data, coloured by batch and by diagnosis.",
    11: "PCA, UMAP and tSNE plots of SVA-harmonized strategy K data with three imputation settings "
        "and of the unharmonized data, coloured by batch and by diagnosis.",
    12: "PCA, UMAP and tSNE plots of FSMVN-harmonized strategy S0 data with three imputation "
        "settings and of the unharmonized data, coloured by batch and by diagnosis.",
    13: "PCA, UMAP and tSNE plots of AMDBNorm-harmonized data in strategies K, S0 and J, coloured "
        "by batch and by diagnosis.",
    14: "Box plots by method of marker correlation and of the change in cross-batch prediction, "
        "with threshold lines, and line plots of SVA and ComBat with and without the diagnosis "
        "covariate along the confounding gradient.",
    15: "PCA and tSNE plots of unharmonized and harmonized data coloured by diagnosis, with DLBCL "
        "split into ABC and GCB cell-of-origin subtypes.",
    16: "Bar plots with error bars of ranking agreement between the selection rule and seven "
        "variants, and a bar plot of how often each recommended approach stays on the front.",
    17: "Line plots of every method's six scores against the confounding level with replicate "
        "bands, a forest plot of the slopes, a scatter plot of the 14 strategies in their "
        "colours, scatter plots of batch mixing against diagnosis retention, rank trajectories "
        "under the selection rule and the scores of the recommended methods.",
    18: "Bar plots of the test-cohort rank of the method chosen on training cohorts against a "
        "random method with error bars and the top-1 and top-3 counts in the panel titles, "
        "rate, and bar plots of the decrease against the best approach with significance stars.",
}

def title_page(text):
    number = text.split()[2] if text.startswith("Supplementary Figure ") else None
    alt_text = SUPP_ALT_TEXT.get(int(number)) if number and number.isdigit() else None
    fig = plt.figure(figsize=(11.69, 1.2 if alt_text is None else 1.9))
    fig.text(0.02, 0.75 if alt_text else 0.5, text, fontsize=16, va="center", weight="bold")
    if alt_text:
        import textwrap
        fig.text(0.02, 0.38, "Alt text: " + textwrap.fill(alt_text, 130), fontsize=10.5,
                 va="center", style="italic")
    buf = io.BytesIO(); fig.savefig(buf, format="pdf"); plt.close(fig)
    return PdfReader(buf).pages[0]

def resolve(stem):
    if isinstance(stem, tuple):
        return [old_reader.pages[stem[1]]], f"submitted page {stem[1] + 1}"
    # exact file first: "figS2_merged_distributions" must not pick up the review-only
    # "figS2_merged_distributions_all_cohorts" (D3, Daniil decides); prefixes such as
    # "figS17a" resolve through the glob
    hits = [FIG / f"{stem}.pdf"] if (FIG / f"{stem}.pdf").exists() else sorted(FIG.glob(stem + "*.pdf"))
    assert hits, stem
    return [PdfReader(str(h)).pages[0] for h in hits], ", ".join(h.name for h in hits)

def build(entries, name):
    writer = PdfWriter(); index = []
    for title, stems in entries:
        start = len(writer.pages)
        writer.add_page(title_page(title))
        for stem in stems:
            pages, src = resolve(stem)
            for p in pages: writer.add_page(p)
            index.append((title, src))
        writer.add_outline_item(title, start)
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    path = OUT / name
    with open(path, "wb") as fh: writer.write(fh)
    print(path.name, len(writer.pages), "pages", round(path.stat().st_size / 1e6, 1), "MB")
    return index

idx = build(MAIN, f"Revised main-figure panels (review draft) {TAG}.pdf")
idx += build(SUPP, f"Supplementary Figures S1-S18 (review draft) {TAG}.pdf")
with open(OUT / "figure_sources.tsv", "w") as fh:
    fh.write("figure\tsource files\n")
    for t, s in idx: fh.write(f"{t}\t{s}\n")
