# Stage-B text drafts (manuscript paragraphs written before stage B is applied)

**Superseded 2026-11-07 (gate G4.7, "read and correct").** D-1 and D-2 were corrected and
shortened into the final stage-B text in `r50_stage_b_text.py` (D-1 → REWRITES[118], second
paragraph; D-2 → INSERT_AFTER[65], last sentences, and REWRITES[118], first paragraph).
Corrections: "as in the first analysis" removed (no comparison with the submitted version);
round-1 counts are 17 accepted / 36 rejected once the two members decided on 2026-11-07 are
included; the two multi-platform leaves are merged ("RNA-seq + microarrays"). This file is
kept as the history of the drafts.

Working file. Each draft names the r50 `STAGE_B_TODO` item it feeds. Drafts use plain words
only (no internal labels, plan §1.1); numbers in `{{…}}` come from `numbers.json` (r45) at
stage B. Nothing here is in the manuscript until `r50 --stage B` writes it as tracked changes,
and the word ledger (r90) must still pass.

---

## D-1. Visual check of the rule's picks (STAGE_B_TODO 11 and 18; Daniil, G2b 2026-11-04)

Source: `output/wp4/visual_check.tsv` (one row per front member: decision + reason),
`output/wp4/vetoes.tsv`, `output/wp4/selection_after_visual_check.tsv`, plots
`figures_svg/g2b_review/` (round 1) and `figures_svg/g2b_review_round2/` (round 2).
Request (Daniil): describe in the main text **why** each approach was rejected.

Draft (Results, after the paragraph on the selection rule; ≈ 260 words, to be shortened so
that the ledger does not grow):

> We then inspected every approach selected by the rule on PCA, UMAP and tSNE plots, next to the
> unharmonized data of the same strategy and imputation, and asked one question: do batches of
> the same biology mix? This check could only remove an approach, never add one.
> In the FF-only scenario, most selected approaches did not differ from the unharmonized data on
> tSNE: batches stayed separate. Only Angel with SoftImpute separated FL, DLBCL and normal B
> cells into three distinct clouds on PCA. In the FFPE-only scenario, only SVA with SoftImpute
> mixed batches of the same biology on all three plots; the other approaches either left such
> batches apart or mixed batches of different biology. In the RNA-seq-only scenario, the
> Shambhala-2 approaches with outlier-batch removal were rejected because the removal step
> deleted the whole FFPE exome-capture batch, almost half of the RNA-seq samples, so FF and
> FFPE samples could no longer be mixed; ComBat-seq (both implementations) did not mix FF and
> FFPE samples on tSNE. SVA mixed FF and FFPE samples, as in the first analysis. In the
> multi-platform scenario, FSQN R and FSMVN on malignant samples only brought the two large
> DLBCL batches (RNA-seq FF poly-A and the Illumina FFPE array GPL14951) together with the
> smaller batches on tSNE and UMAP. ComBat on malignant samples only and M-ComBat after removal
> of rare batches placed FL, DLBCL and normal B cells as separate groups of batches on PCA, with
> batches of the same biology closer to each other than to batches of another biology; the
> other selected approaches showed neither batch mixing nor biology separation. Among
> microarray-only approaches only Angel (extended Affymetrix set, SoftImpute, outlier-batch
> removal) brought DLBCL batches partly together on UMAP.
> Without any sample removal, Angel only moderately improved batch mixing: batches of the same
> biology overlapped on PCA and lay close on UMAP, but remained separate groups on tSNE; ComBat
> did not differ from the unharmonized data on any plot.

Round 2 and closing sentences (Daniil, G2b 2026-11-07; add to the draft above, shortened with it):

> Removing a rejected approach lets approaches it had dominated enter the front; we inspected
> these once in the same way and did not refill the front again. In the RNA-seq-only scenario
> all new entrants (VST, rank normalization, qsmooth, TMM and the unharmonized data, each with
> outlier-batch removal) failed for the same reason as Shambhala-2: the removal step deleted the
> FFPE exome-capture batch, 939 of 2,243 RNA-seq samples. ComBat without imputation brought
> samples of the same diagnosis together and separated batches on PCA, and moderately on tSNE.
> In the FF-only scenario the other Angel variants also placed batches of the same biology
> together; ComBat and M-ComBat showed no visible correction. On malignant samples only, ComBat
> without imputation and without outlier-batch removal separated FL from DLBCL on PCA only (a
> marginal result); all other new entrants, in every scenario, left batches apart without any
> grouping by biology. Without sample removal, M-ComBat did not bring batches of the same
> biology together.

Numbers for the text: round 1 16 accepted / 35 rejected; round 2 5 accepted / 23 rejected; the two
uncommented members 1 / 1; final selection 22 approaches (`output/wp4/selection_after_visual_check.tsv`).
Multi-platform approaches → leaf "RNA-seq + Illumina microarrays" (provisional,
`output/wp4/leaf_assignment.tsv`); the leaf "RNA-seq + various microarrays" has no accepted approach.

## D-2. Method failures (Methods; Daniil, G4 review 2026-11-07: "honestly state that some methods failed with a simple description of the error")

Sources: `output/wp3/four_scores.parquet` (`identical_to_raw`), `output/wp9/nb04_gradient_failures.tsv`,
`output/wp7/v1_fold_results.tsv`, `output/wp6/pilot/pilot_report.md`. Counts go through `r45`.

> Some methods failed. In 111 of the 2,234 approaches the method returned its input unchanged
> (identical principal-component regression and silhouette values to the unharmonized data):
> exploBATCH in 49, RUV-III-PRPS in 27, DWD in 19, FSQN R in 10 and SVA in 6 approaches. These
> approaches were treated as failures and could not be selected. In the new experiments, ComBat
> with the diagnosis as covariate stopped with an error whenever every batch held a single
> diagnosis, because the covariate then equals the batch and the design matrix is singular (all
> runs at the highest confounding level and on the single-diagnosis batches; limma failed in the
> same way on some leave-cohort-out test cohorts). AMDBNorm exceeded the 6-hour limit on the
> largest inputs, and exploBATCH could not be run in the leave-cohort-out experiment because its
> required R package is no longer available. Failed runs are listed in Supplementary File 3.
