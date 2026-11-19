> **Public copy.** This folder holds the code, outputs and figures of the major revision of
> Article 1 (NAR Genomics and Bioinformatics, manuscript NARGAB-2026-312): a one-way, sanitized
> copy of the authors' working folder. The manuscript, the review correspondence and a few
> per-sample rows are withheld, and cluster names are placeholders. See [`WITHHELD.md`](WITHHELD.md).

# CLAUDE.md — article_1_revision/ (NARGAB-2026-312 major revision of Article 1)

Operating manual of this folder. Plan: `article_1_revision_implementation_plan_261029.md` (read §0
glossary, §1.1 naming rule, §4 frozen rule, §13 gates before editing anything here). Pod steps:
`RUNBOOK.md`. Human summary and status: `README.md`.

## Hard rules

1. **Frozen baseline (plan §4).** Never edit `bench_shared.py`, the benchmark job / dispatcher
   scripts, `compute_batch_metrics.py`, `run_metrics_*.py`, the `harmonization-metrics/*.ipynb`
   notebooks, the two figure notebooks of `figures_for_article/`, the submitted docx
   `FL_harmonization_article_NAR_260912.docx` or `supplementary_260824/**`. Their MD5s are in
   `FROZEN_MD5.txt`; check with `md5sum -c FROZEN_MD5.txt --quiet` (run from this folder).
   Variants live in `revision_lib.py` as wrappers (e.g. `sva_nocov` hands the frozen
   `normalize_sva` a one-level column).
2. **Blindness of the selection rule.** `r04_apply_rule.py` refuses to run until the MD5 of
   `adjudication_rule_261029.md` is in `FROZEN_MD5.txt` (gate G2). Do not compute or look at
   rule picks (Pareto fronts after the gates) before that. An amendment after G2b is a new file
   `adjudication_rule_261029_v2.md`, never an edit of version 1.
3. **Plain-word names (plan §1.1).** No internal label (WP, D, G, C codes, `_nocov`, `L11`, `V1`,
   `post0`, script names, snake_case columns) in any publication document. Every label of a
   figure / supplementary table comes from `revision_lib.PUBLICATION_NAMES`,
   `METHOD_DISPLAY_NAMES`, `STRATEGY_DISPLAY_NAMES`.
   **Exception (Daniil, 2026-11-08):** the 14 strategy codes (S0, A, B, C, D, E1–E3, F–K) are
   publication notation: figures / tables show "code · name" (`STRATEGY_DISPLAY_NAMES`, S0 =
   "No removal"), the text gives "name (code)" at the first Methods / Results mention, then the
   code (`STRATEGY_CODES`). r99 no longer scans for S0.
4. **Nothing grows.** Lines, figures and tables (main + supplementary) may go down, never up:
   `r00_baseline_ledger.py` wrote the reference (`output/ledger_baseline_totals.json`: 6 figures,
   3 tables, 19 supplementary figures, 3 supplementary files, 16,495 words); `r90_ledger.py`
   checks the revision.
5. **Numbers in the text** are read from `output/**` by `r45_results_numbers.py`, never typed.
6. **Daniil decides at the gates** (G1 panel, G2 rule, G2b picks, G3 pilots, G4 results, G5
   letter, G6 manuscript). Do not proceed past a gate without his answer.

## Data sources (read only through these)

| What | Where | Loader |
|---|---|---|
| 87 published metrics, 2,407 approaches (analysis set = `pct_samples_allNA < 5` → 2,234) | `inputs/Supplementary File 3.csv.gz` | `rl.load_supp_file_3()` |
| Metric polarity / group / type | `inputs/Supplementary File 2.xlsx`, sheet `Metric_polarity` | `rl.load_metric_polarity()` |
| L (`mk_rho_mean_all_genes_narrow_set`) and N (`pv_lobo3_f1_macro_mean`, perm mean / SD / p, n_perm = 100) | `harmonization-metrics/metric_tables/metrics_comprehensive_260905.csv` — L / N ONLY | `rl.load_ln_columns()` |
| 7,174-sample annotation | S3 `prepared/S0_no_removal__softimpute__ann.tsv.gz` (cached in `cache/`) | `rl.load_s0_annotation()` |
| Raw S0 matrix (strict, 3,447 genes) | S3 `exp/S0_no_removal__strict__01_raw__post0.tsv.gz` | `r01`, `r12` |

`metrics_comprehensive_260527.csv` is unusable (memory). The 84 `20_shambhala` approaches take L / N
from the blind-check rows `shambhala_P0std_Q0std` (same matrices; 84 L, 83 N; G2 2026-11-03). Never impute.
The table also holds the 2-class N (`pv_lobo2_f1_*`), used by gate N for strategy D.

## Run order and status (2026-11-07)

| Step | Script | Where | Status |
|---|---|---|---|
| Ledger baseline | `r00_baseline_ledger.py` | JupyterHub | done |
| WP1 confounding | `r01_confounding_diagnostics.py` (~18 min: 10⁴ FFH simulations × 4 pairs × 14 strategies) | JupyterHub | done |
| WP2 panel | `r02_reduced_panel.py` (`--check`) | JupyterHub | done; G1 answered 2026-11-03 → 22 metrics |
| WP3 four scores | `r03_four_scores.py` | JupyterHub | re-run 2026-11-03 (N2, identical_to_raw, runner-up bars, Shambhala L / N); Q1 answered |
| WP4 rule | `adjudication_rule_261029.md` → freeze → `r04_apply_rule.py [--review]` | JupyterHub / Mac | frozen 2026-11-03 (MD5 17d4fe01); G2b **closed 2026-11-07** after round 2 (`VISUAL_CHECK_CLOSED`): 22 approaches in `selection_after_visual_check.tsv`, late entrants in `not_added_check_closed.tsv`, leaves in `leaf_assignment.tsv` |
| WP6 designs | `r10_build_gradient_designs.py` | JupyterHub | done (45 designs, committed) |
| WP7 folds | `r20_build_cohort_folds.py` (~10 min) | JupyterHub | done (committed) |
| Env check | `r18_env_check.py` (4 frozen methods + Shambhala vs published matrices) | revision pod, before the pilots | done 2026-11-01: OK (2 identical, 3 equivalent) |
| Pilots | `r11_run_gradient.py --pilot`, `r21_run_v1.py --pilot` (worker `r19_harmonize_one.py`) | harmonization pod | done 2026-11-01/02: 24 / 24, 62 / 62 (61 ok + AMDBNorm timeout) |
| Pilot metrics | `r12_revision_metrics.py --pilot` | same PVC-free pod (decided 2026-11-01) | done 2026-11-02: 82 / 82 ok; pod deleted → **gate G3** |
| Full runs | r11, r21, r12, `r30_bridging_subset_metrics.py` | one PVC-free pod, 48-vCPU node (RUNBOOK §6) | done 2026-11-06 (pod logs on S3 `pod_logs/fl-revision_261105_1155/`) |
| Collect | `r12 … --concat`, `r30 --concat` | JupyterHub | done 2026-11-07 (gradient 534 / 540 ok, leave-cohort-out 1,072 / 1,202, bridging 2,234) |
| WP12 references | `r51_reference_audit.py` | JupyterHub | done: 12 items for Daniil (Mendeley) |
| Pilot report (G3) | `r14_pilot_report.py [--workers n]` | JupyterHub | run 2026-11-02 → `output/wp6/pilot/`; G3 questions in `gates_review_261102.md` §5 (r14 omits timed-out runs from the slow list) |
| WP6 stats | `r13_gradient_stats.py` | JupyterHub | run 2026-11-07; + Spearman / BH-FDR columns and `gradient_ranks.tsv` (G4 review) |
| WP7 evaluation | `r22_v1_evaluate.py` | JupyterHub | run 2026-11-07 (round-1 vetoes) |
| WP5 robustness | `r05_robustness.py` | JupyterHub | re-run 2026-11-07 after G2b closed (column `selected_after_visual_check`) |
| WP10 supplementary | `r40_build_supplementary.py` | JupyterHub | run 2026-11-07: every part filled |
| Numbers | `r45_results_numbers.py` | JupyterHub | run 2026-11-08: 652 keys after the figure review (gt keys dropped, S18 test keys added), 0 pending; also `output/wp3/eta_squared.tsv` |
| Figures | `nb01`–`nb06`, `nb08` (Figures 4–5) | JupyterHub | nb01 / nb02 / nb06 2026-11-01 (nb02 re-run 2026-11-07 with the rule picks); nb03 / nb04 / nb05 written + run 2026-11-07 → `figures_svg/` (+ `PLACEMENT.md`); nb03–nb05 re-run 2026-11-07 with article palettes (`method_pal` hex in §0c) + S16a bars, S17d–f; 2026-11-08 every figure notebook re-run after the figure review (page-size panels, S18 statistics, palette / name fixes) |
| WP11 manuscript | `r50_manuscript_tracked_edits.py` (`--stage A` / `--stage B`; stage-B text in `r50_stage_b_text.py`) | JupyterHub | stage A 2026-11-01; stage B 2026-11-07; **re-run 2026-11-08** with the 14-arm gradient and again after the figure review (Pareto definition + DOI, S18 statistics, D1 names, "decrease"): `Revised_manuscript/…_tracked_stageB_261108.docx` (108 edits, r90 PASS, r99 0 FAIL) |
| WP14 checks | `r90_ledger.py [docx]`, `r99_verify.py <docx>` | JupyterHub | done; stage A passes except Supp Fig 19 (renumbering is stage B) |
| Figma check | `r97_figma_check.py` (font sizes in Figma px, plot area vs slot / frame) → `output/wp14/figma_check.tsv` | JupyterHub | run 2026-11-09: 33 / 33 pass (S18b merged into S18a) |
| Review package | `r46_review_figure_pdfs.py --tag YYMMDD` then `r47_build_review_package.py --tag YYMMDD` → `Revised_manuscript/review_package_<tag>/` | JupyterHub | 261109 built: tracked + clean docx, letter draft, Tables 1–3, figure PDFs, Supplementary Files |
| Figure consistency | `r98_figure_consistency.py` (palette dicts of nb01–nb08 vs canonical copies, SVG text rules) → `output/wp14/figure_consistency.tsv` | JupyterHub | run 2026-11-08: 14 findings left (Figure 3 / S5 metric code names; nb07 review-only palette) |
| Final-selection embeddings | nb07 `REVIEW_ROUND = "final"` (cache only) → `review_extras/final_selection_embeddings/` | JupyterHub | run 2026-11-08 |
| WP13 letter | `response_letter_draft.md` → `r60_response_letter.py [--draft]` | JupyterHub | draft built; final mode refuses while numbers are pending |

Stage B written 2026-11-07 (G4 answered, `gates_review_261102.md` §9). Angel / M-ComBat gradient
arms collected 2026-11-08 (630 runs, 619 ok) → r13, nb04 (14 arms), nb03, r40, r45, r50 stage B
→ `Revised_manuscript/…_stageB_261108.docx`; review package `Revised_manuscript/review_package_261108/`
(figure PDFs by `r46_review_figure_pdfs.py`) + digest `gates_review_261102.md` §10. Fourth review (2026-11-08, §11): strategy codes "code · name" (S0 = No removal), Q1 b, Q2 a
(r13 `end_lambda`), Figures 4–5 rebuilt by `nb08_figures_4_5.ipynb` (B1), alt text in the supplementary
PDF (B3), S5 = 87-metric clustermap with the 22 starred (nb02) → stage B 261108 re-run. Waiting: Daniil's
single Word-comment pass (§11.5), Figma assembly, G5, G6.
`nb07_selected_approaches_embeddings.ipynb` (G2b plots): every front member of the six r04 pools as unharmonized | harmonized pairs; post-removal batches faint (the post0 matrix is embedded, since post-removal only drops whole batches). Embeddings cached in `cache/nb07/` (`…__post0.pkl`, kept lists `…__post1_kept.txt`); 4 parallel jobs.

## Skills / gotchas learned here

- **Shambhala naming.** `20_shambhala` of Supplementary File 3 is stored on S3 and in the
  blind-check table as `shambhala_P0std_Q0std` (published metrics identical on all 84).
  `rl.load_ln_columns` maps it (`LMN_METHOD_ALIASES`); read matrices with
  `rl.main_benchmark_matrix_key()`, never by formatting the key with `20_shambhala`.
- **Visual check closed (2026-11-07).** r04 `VISUAL_CHECK_CLOSED = True`: no further nb07 rounds; the selection is the accepted members only. Round-1 decision copies: `output/wp4/*_round1_261104.tsv`.
- **Vetoes never touch version 1.** r04 writes the blind front to `selection_by_rule.tsv` and the front
  without the vetoed approaches to `selection_after_visual_check.tsv`. A vetoed member lets the
  approaches it dominated enter (`visual_check == "not reviewed"`) → nb07 `REVIEW_ROUND = 2`;
  G2b decisions live in `output/wp4/visual_check.tsv` (vetoed rows copied to `vetoes.tsv`).
  RNA-seq-only post-removal can delete the whole FFPE exome-capture batch (939 / 2,243): check
  `output/wp9/nb07_removed_batches*.tsv` before trusting any C post-removal front member.
- **Method failures = "identical to raw".** `rl.flag_identical_to_raw` (PC regression + ASW on
  batch / diagnosis equal to the 01_raw row at 6 decimals): 111 of 2,234 (exploBATCH 49,
  RUV-III-PRPS 27, DWD 19, FSQN R 10, SVA 6). UMAP / tSNE metrics differ between runs of one
  matrix and kBET / % NA agree by chance, so they are not used for identity.
- **Gate N for D uses N2** (`pv_lobo2_f1_*`, DLBCL vs FL), `rl.TWO_CLASS_N_STRATEGIES`.
- Dropping a cluster mate can move a bar medoid (G1: Global biology PCReg → wm_mean_bio);
  r03 `HEADLINE_OVERRIDES` pins a headline and logs it.
- A timed-out harmonization writes a "timeout" run record on S3 (`Job.timeout_record_key`);
  `--skip-if-exists` then never restarts it. Default `--timeout-s` 21,600 (G3).

- Pod name (rule the project's pod-naming rule, from the next launch): `fl-revision`,
  label `app=fl-revision`; commands use `POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)`.
  The pod launched 2026-11-05 still has the old name and no label.
- Revision pods run on `ghcr.io/nikit357/combobatch:20260830` (ECR `fl-batch-correction` is
  NotFound since 2026-11-01): environment only, the frozen code is copied in (RUNBOOK §3);
  `environment/` (pip freeze, R packages, image + Shambhala commit) is on S3 under `pod_logs/`.
  Pilots: worker 14 vCPU / 24 GiB (c6a.4xlarge). Full runs (G3): 44 vCPU / 80 GiB pinned to a
  c6a.12xlarge (`node.kubernetes.io/instance-type: c6a.12xlarge`).
- `20_shambhala` in the revision = `rl.shambhala_fast` = `Nikit357/Shambhala2_fast` @ `30ac312`,
  P0std / Q0std, seed 42, k 5, 16 workers — the implementation behind the published
  `shambhala_P0std_Q0std`. The frozen `bench_shared` entry (R `BorisovNM/Shambhala2`) never
  produced a published number and is not used. Needs `SHAMBHALA_FAST_DIR` (set in the manifests).
  CuBlock clusters genes, so Shambhala output depends on the input gene set, not only on the
  sample: compare with a published matrix only on the S0 input (r18 does; with C's genes r = 0.993).

- Harmonization pod without the PVC: `k8s/pod-revision-nopvc.yaml` (emptyDir at `/workspace`, so
  `default_log_dir()` and every path stay the same). Results are on S3; the `log-sync` container
  mirrors `/workspace/revision` (without `cache/`) to S3 `revision_261029/pod_logs/<pod>_<start
  UTC>/` every 60 s and on deletion; read pod logs from there. Two containers → `-c worker`.

- `python -m pytest tests/ -q` — 87 toy checks (79 library + 8 post-pod analysis; 2 skip without local data); ~1 min.
- New runs (gradient, leave-cohort-out) are scored with `rl.score_runs(metrics,
  rl.bar_scaling_reference())`: the four bars are min-max scaled on the **main-benchmark range**
  (2,234 approaches), so 0 / 1 mean the same in every experiment (values may leave [0, 1]).
- `rl.rule_order` = full ranking in rule order (candidates first, Pareto layer, scaled Local
  batch); r22 reuses `r04.apply_gates` by passing the subset id as `strat`.
- Real-data V (batch × 3-class major group, bias-corrected) on the 5 gradient batches = 0.398
  (3,404 samples); r13 places the data there.
- The η² formula of the submitted Figure 6B (mean one-way η² over the metrics) reproduces the
  submitted 0.3629 / 0.2564 / 0.0155 / 0.0020 exactly on the 87 metrics (r45).
- Supplementary File 1 is per cohort (88 rows), not per sample.
- r99's label scan strips the letter draft's leading HTML comment and the `{{key}}` placeholders;
  scripts / plan codes may appear there but never in the letter body.
- The PCReg columns of Supplementary File 3 have polarity +1 for RNA_BATCH and −1 for Diagnosis
  (they are 1 − R²-type scores); always take polarity from `Metric_polarity`, never assume.

- `python -m pytest tests/test_revision_lib.py -q` — 77 toy checks (pure Python; pods need
  `pip install -q pytest`).
- The bias-corrected Cramér's V of the whole cohort (batch × 15-level diagnosis) is **0.358**; the
  plan's 0.363 is the uncorrected value. AMI 0.263 matches. Normal B = 899 samples (733 Normal_B_cells +
  141 Kassandra + 25 B_cells), not 889.
- Gradient V (cap 150, replicate 1): 0, 0.014, 0.169, 0.287, 0.388, 0.490, 0.592, 0.690, 0.799,
  0.896, 0.998 (plan: 0.010 at λ = 0.1 and 0.897 at λ = 0.9 — rounding of the largest-remainder
  tie order). Draws are nested along λ within a replicate (one permutation per cell and seed).
- Frozen metric groups skip every column absent from the annotation (`_row_mask` → None): pass
  `ann[[Diagnosis_cell_type_unified]]` to get Diagnosis metrics without kBET (r30).
- The benchmark image has no pyarrow guarantee in the metrics pod: pod-side caches are pickles.
- Smoke test 2026-10-31 (one 405-sample design, R-free arms, scratch prefix): preparation → harmonization → metrics → batch-free fold changes all work; the metric JSON has 304 keys, no group errors. **Group D (KS tests) took 1,197 s single-threaded on the busy JupyterHub** (all other groups < 40 s): for 1,780 jobs that is the dominant cost — the pilot measures it on the pod; `r12 --groups ABCEGHIJKLN` drops D if G3 decides so (D metrics are only members, not headlines, of the global batch bar).
- The compute code emits `pcr_<col>`; Supplementary File 3 calls it `PCReg_<col>`, and `pct_*_allNA` are derived from counts. `revision_lib.add_published_names` adds both, so revision tables use the published names.
- `REVISION_S3_PREFIX` env var points every script at a scratch prefix (smoke tests only):
  `FL_batch_correction/revision_261029_smoketest/`.
- **Gradient L is 1 by construction** for no harmonization, limma and FSMVN (L = within-cohort ρ vs
  the unharmonized data; per-batch shifts keep ranks), so r13 reports "not fitted" there; MNN L ≈ 0.
- **Chosen method failing on a leave-cohort-out test fold** (ComBat with covariate / limma:
  singular design when diagnosis = batch in the test cohorts) gives NaN rank / hit in
  `v1_fold_results.tsv`; readers must treat the hit columns as numeric-or-NaN (r45 counts NaN as no
  hit; the random-method row holds expected shares such as 0.033, not booleans).
- r13 merges the design table into the metrics: sample counts arrive as `n_samples_x` (metrics,
  NaN on failures) and `n_samples_y` (design).
- Figure notebooks nb03–nb05 were generated once with a scratch `nbformat` script (not in the repo);
  edit the `.ipynb` directly from now on.
- Leave-cohort-out folds: in C (RNA-seq only) and K (FFPE only) two test folds are one large
  single-batch, single-diagnosis cohort each (C: 553, 567; K: 553, 810 samples) — no grouping can
  avoid it; batch metrics and gate N are "not evaluable" on those folds (plan caveat C4).
- **Merge pitfall (2026-11-03).** A "keep remote" merge restored the JupyterHub rule text (header
  "FROZEN", MD5 17d4fe01) but the Mac's `FROZEN_MD5.txt` line (b192bb, older "not frozen" header;
  same rule body) — `md5sum -c FROZEN_MD5.txt` then fails and r04 refuses. It also overwrote a
  saved-but-uncommitted `gates_review_261102.md` (Daniil's G2b comment survived only in
  `.ipynb_checkpoints/`). After any merge here: run `md5sum -c FROZEN_MD5.txt --quiet` and diff the
  review files against their checkpoints.

- **No comparison with the submitted version (Daniil, G4 2026-11-07).** No "submitted tree" role
  (r22), no "submitted version" mark (Figure 3), no "(submitted)" label (6B), no kept / lost / new
  concordance in publication outputs; r45 no longer writes `rule_vs_visual__*`. Internal review
  files may keep the comparison.
- **Stage B mechanics.** `r50 --stage B` reads the newest `*_tracked_stageA_*.docx`; texts in
  `r50_stage_b_text.py` with `{{key}}` / `{{key:fmt}}` / `{{key:q}}` (FDR, "< 0.001") from
  numbers.json; a rewritten paragraph that holds stage-A insertions gets them deleted as
  w:ins/w:del ("inserted, then deleted") — `nar_review_tools.py validate` was patched to read
  that correctly on Reject All. Replacement spans may cross proofErr / bookmark marks, never a
  citation. Supplementary Figure renumbering runs right to left at exact offsets.
- **Arms that fail at λ = 1** (ComBat, M-ComBat with the covariate) have NaN `mean_at_lambda1`, so
  `changes_with_confounding` is always False for them in r13 even with a strong Spearman ρ (§10.5 Q2).
  nb04 asserts `len(gradient_scores) == 45 × n_arms` (no hard-coded 540).
- **Statistical annotations.** Comparison boxplots carry pairwise Mann–Whitney + BH FDR stars
  (≤ 4 boxes bars, > 4 boxes p-value heatmap; notebook_writing skill §10); helpers inline in nb05.

- **Figure review 2026-11-08** (plan `figure_review_corrections_plan_261108.md`, digest
  `gates_review_261102.md` §12.4). The agreement with batch-free fold changes (`gt_*`) is computed
  by r12 but **not analysed** (r13 `SCORES`, 12 scores; not in Supplementary Files 2–3 or the
  figures). In publications the combined axes are "Batch mixing (global + local mean)" /
  "Diagnosis retention (global + local mean)" (D1; `PUBLICATION_NAMES`), and the leave-cohort-out
  loss is **"decrease"**, never "regret" (internal column / key names keep `regret`).
- **Random baselines are distributions** (Daniil's figure rule): leave-cohort-out random rank
  uniform on 1…n (exact p = rank / n; Monte Carlo of the summed ranks), hits Poisson-binomial
  (exact p), decreases = every test run (Mann–Whitney + Monte Carlo); BH-FDR per panel; bar plots
  always with error bars. nb05 `MONTE_CARLO_DRAWS = 100_000`, seed 261108.
- **Page size (D2):** Figma file `t8bFgusleBEwB9ht7rORCH`, node 761-28 (frame "Figure 4") =
  753 × 1150 px = 180 × 275 mm. nb03–nb05 copy `PANEL_SLOTS_MM` (= `PLACEMENT.md` column
  "slot (mm)") and draw at true size, `GLOBAL_FONT_SIZE = 7`, `SMALL_FONT_SIZE = 6`. A page-level
  Figma metadata read is too large for the connector; read single frames. The Figma OAuth flow
  expires between turns: paste the callback URL right after authorizing.
- **New citations are written as "(DOI: …)"**, checked on Crossref; Daniil inserts them in
  Mendeley (Pareto front: DOI 10.1109/4235.996017).
- **Palettes are literal copies.** nb02 used to build `method_pal` over the 31 analysed methods
  (shifts exploBATCH to ARSyN's colour); nb08 used tab20 platform colours. Both now copy the
  canonical dicts (nb04 §0c, nb06 §0c); r98 checks it.
- r46 resolves a panel by its exact file name first, so `figS2_merged_distributions_all_cohorts`
  (review only, D3) never enters the S2 slot.
- Agent calls (reviewer, brainstorm) are refused in auto mode because the context-mode hook
  rewrites agent prompts; run them outside auto mode or inline.

- **Figma units (2026-11-09).** Figma imports SVG pt × 4/3 as px; Daniil's frame (node 1607-116664)
  is 756 × 1159 px = 180 × 275 mm. Every figure notebook carries the same "Figma units" cell: text
  7.5 pt (= 10 px in Figma), `save_figure(fig, stem, slot_mm)` sets all fonts, fits the plot area
  (no legends / colour bars) to the slot, logs to `output/wp14/figma_fit/<nb>.tsv`. Draw legends that
  depend on the final size (stacked fig legends, adjustText labels) **after** `fit_to_slot`.
  Square scatters need `ax.set_box_aspect(1)` + nb08 `pack_columns`. `batch_display_name()` drops
  the microarray "Unknown". No LibreOffice on JupyterHub: no PDF render of the docx here.
