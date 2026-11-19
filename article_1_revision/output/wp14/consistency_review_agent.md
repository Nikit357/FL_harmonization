# Figure consistency review (plan `figure_review_corrections_plan_261108.md`, item 14b) — 2026-11-08

**How it was made.** The plan asked for one general-purpose reviewer agent. The agent call was
refused twice by the auto-mode check (a context-mode plugin hook rewrites every agent prompt, so
auto mode cannot review it), so the review was done inline by Claude on the same inputs: the
review PDFs of 2026-11-08, the panel PNGs in `figures_svg/`, `figures_svg/PLACEMENT.md` and the
deterministic audit `output/wp14/figure_consistency.tsv` (r98). To run it as an independent agent,
switch the context-mode hook off or approve the agent call outside auto mode.

**Summary.** After the per-notebook fixes the palettes agree across all publication figures
(r98: no colour mismatch left). The review found two palette bugs, both fixed and re-run: nb02
built `method_pal` over the 31 analysed methods instead of the 33 of the frozen recipe, so
exploBATCH had ARSyN's colour in Figure 3 and S6; nb08 coloured platforms with tab20 instead of
`platform_palette`. Three naming inconsistencies were fixed: diagnosis names, batch IDs and the
name of the S0 pool. Two mechanical points remain open (6 and 7 below), both waiting for Daniil's names. Three content points
are listed for Daniil's decision (D5).

| # | figures / panels | inconsistency | evidence | proposed fix | kind | status |
|---|---|---|---|---|---|---|
| 1 | Figure 3, S6 vs every other figure | exploBATCH coloured `#e7b02f` (ARSyN's colour) | r98 + recomputing nb02's `build_method_palette` over the 31 analysed methods: 1 of 31 colours differs from nb04 §0c | literal copy of `method_pal` in nb02 | mechanical | **fixed**, nb02 re-run |
| 2 | Figures 4–5 vs S2 | platform colours from tab20 in Figures 4–5, article `platform_palette` in S2 | r98: "palette built by code, nb08" | literal copy of `platform_palette` (nb06) in nb08 | mechanical | **fixed**, nb08 re-run (nb07 review PDFs keep tab20: review-only) |
| 3 | Figure 1E vs Figures 4–5 | diagnoses named "Diffuse large B-cell lymphoma", "Germinal centre B cells", "Marginal zone B cells" in 1E but "Diffuse Large B Cell Lymphoma", "GC", "MZ" in the 4–5 legends | panel PNGs | nb01 `DIAGNOSIS_PLAIN_NAMES` copied into nb08 | mechanical | **fixed**, nb08 re-run |
| 4 | Figure 1E vs Figures 4–5 | batch IDs with underscores in 1E ("GPL570_FF_Unknown") and with spaces in 4–5 ("GPL570 FF Unknown") | panel PNGs | spaces in 1E | mechanical | **fixed**, nb01 re-run |
| 5 | Figure 6C/D vs S16 | the S0 pool named "No batch removal (information only)" (6C/D) and "No sample removal" (S16), while Figure 4A and S18 say "S0 · No removal" | panel PNGs | "S0 · No removal" everywhere | mechanical | **fixed**, nb03 / nb05 re-run |
| 6 | Figure 3, S5 | metric names are identifiers (`wm_ratio_bio_batch`, `pct_na_cells`, `ks_cohort_within_batch_frac_sig`, …) | r98: 13 snake_case hits | plain metric names; they are the published metric identifiers of Supplementary Files 2–3, so a rename needs a name table (not in `PUBLICATION_NAMES`) | mechanical, but needs Daniil's word on the names | open |
| 7 | 6C/D column "Global batch removal" next to the axis "Batch mixing (global + local mean)" | the global bar still says "removal" (D1 covered the combined axes only) | 6C/D, S17a, S17f, Supplementary Files 2–3 | rename the bar "Global batch mixing"? | mechanical (name) | open, question to Daniil |
| 8 | Figures 4–5 vs Figure 6C/D, S14b | prediction named "prediction F1" (4–5 titles), "Cross-batch prediction" (6C/D), "Cross-batch diagnosis prediction (macro-F1)" (S14, S17) | panel titles | "cross-batch prediction (macro-F1)" in the 4–5 titles | mechanical | **fixed**, nb08 re-run |
| 9 | S17e vs S18a | rank 1 drawn at the top in S17e (inverted axis), as the shortest bar in S18a | panel PNGs | keep both: S18a is a bar plot (bars start at 0) and its y label says "lower bar = better" | content (plot type) | listed, no change |
| 10 | "No harmonization" (S17, S18 legends) vs "Unharmonized" (Figures 4–5, 6C/D legend) | two names for the 01_raw data | legends | acceptable: "No harmonization" names the arm in a list of methods, "unharmonized data" names the matrix; say so in the legends | mechanical | listed |
| 11 | S18a | the grey random bar is drawn in every fold although it depends only on the fold's number of methods | S18a | one band per scenario instead of a bar per fold | content | for Daniil (D5) |
