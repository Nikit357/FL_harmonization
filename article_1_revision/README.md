> **Public copy.** This folder holds the code, outputs and figures of the major revision of
> Article 1 (NAR Genomics and Bioinformatics, manuscript NARGAB-2026-312): a one-way, sanitized
> copy of the authors' working folder. The manuscript, the review correspondence and a few
> per-sample rows are withheld, and cluster names are placeholders. See [`WITHHELD.md`](WITHHELD.md).

# Article 1 revision (NARGAB-2026-312)

> **Pod names** end with the pinned instance type (the project's pod-naming rule): `fl-revision`, `fl-metrics`. Commands find the pod by its stable label `app=<name without the type>`: `$POD_REV` = `$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)`; `$POD_METRICS` = `$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-metrics -o name | cut -d/ -f2)`. Resize = edit the manifest's `node.kubernetes.io/instance-type` and the name suffix together; launch with `kubectl apply -f <manifest>`.

Major revision of "Benchmarking of bulk transcriptomic harmonization tools in a multi-platform
B-cell lymphoma cohort…". Reviewer report: `reviewer_report.md`. Plan:
`article_1_revision_implementation_plan_261029.md`. Short pod command sheet: `RUNBOOK.md`.
Rules for working in this folder: `CLAUDE.md`. **This README is the full manual: what is done,
what you decide, when and how to run the pods, and what happens after them.**

## What the revision does

The composite score is removed. In its place come a reduced panel of 25 non-redundant metrics, four
scores (marker correlation, cross-batch prediction, local and global batch / diagnosis bars), a
written selection rule applied blind, confounding diagnostics and a confounding-gradient experiment
with positive and negative controls, a leave-cohort-out validation of the recommendations, and a
bridging-batch check.

---

## 1. Status (2026-11-07)

**All pod runs are done and collected on JupyterHub (2026-11-07).** r13 (gradient statistics), r22
(leave-cohort-out), r05 (robustness incl. bridging), r40 (every supplementary part filled) and r45
(124 numbers ready, 0 pending) have run; notebooks nb03 (Figure 6B, 6C/D, 6F, S14), nb04 (Figure 6
gradient panel, S17) and nb05 (S16, S18) are written and run, nb02 re-run with the rule picks.
**What you do next:** (1) G2b round 2 (`figures_svg/g2b_review_round2/`, `gates_review_261102.md`
§4.4) → Claude re-runs r04 → r05 → r22 → r40 → r45 → nb03 / nb05; (2) gate G4 — read
`gates_review_261102.md` §6.1 (results and five new G4 questions); then Claude writes r50 stage B.

The table below is the state on 2026-11-03; rows marked "waits for the pods" are now done (see the
paragraph above and `CLAUDE.md`, "Run order and status").


Gates G1, G2 and G3 were answered on 2026-11-03 (`gates_review_261102.md`, rewritten with the
answers). Q1 and Q2 were answered the same day; the rule was **frozen on 2026-11-03** and r04 has run
(→ gate G2b). The full pod runs were launched on 2026-11-03 from the Mac (RUNBOOK §6).

| Part | Status | Output |
|---|---|---|
| Phase 0 setup (frozen MD5s, baseline copies, ledger, `revision_lib`) | done | `FROZEN_MD5.txt`, `output/ledger_baseline*` |
| Confounding diagnostics (r01) | done | `output/wp1/` |
| Reduced panel (r02) | done, G1 answered: **22 metrics** (tSNE centroid dispersion removed, no coverage additions) | `output/wp2/` |
| Four scores (r03) | re-run 2026-11-03: + N2 (2-class), `identical_to_raw`, runner-up local bars, Shambhala L / N; Global-biology headline PC regression on diagnosis (Q1, fixed) | `output/wp3/` |
| η² of the four design factors on the reduced panel (r45) | done | `output/wp3/eta_squared.tsv` |
| Selection rule | final text (G2, Q1, Q2 answers applied), **frozen 2026-11-03** (MD5 in `FROZEN_MD5.txt`) | `adjudication_rule_261029.md` |
| Rule application + review (r04) | run 2026-11-03 → **gate G2b** (fronts: FF 8, FFPE 5, RNA-seq 8, multi-platform 12, microarrays 13, no batch removal (S0) 7; vs Table 3: 3 kept, 12 lost, 26 new); G2b partly answered (picks approved; vetoes after nb07) | `output/wp4/selection_review.xlsx` (+ `.md`) |
| Robustness (r05) | written + toy-tested; rule frozen, waits for the bridging metrics (pod) | — |
| Gradient designs (r10), cohort folds (r20) | done, committed | `output/wp6/designs/`, `output/wp7/` |
| Pod code: r11, r12, r19, r21, r30, `revision_dispatch.py`, `k8s/pod-revision.yaml` | done, dry-run + smoke-tested | — |
| Pilots + report for gate G3 (r14) | done; G3 answered 2026-11-03 → full runs (RUNBOOK §6) | `output/wp6/pilot/` |
| Gradient statistics (r13) | written + toy-tested, waits for the pods | `output/wp6/` |
| Leave-cohort-out evaluation (r22) | written + toy-tested, waits for the pods and G2b | `output/wp7/` |
| Figure 1E + Figure 2A (`nb01_confounding.ipynb`) | see §1.1 | `figures_svg/` |
| Figure 3, S4, S5, S6 (`nb02_reduced_panel_clustermap.ipynb`) | re-run 2026-11-03 on the 22-metric panel, missing cells black; rule marks empty until G2b | `figures_svg/` |
| New S2 = old S2–S4 merged (`nb06_merged_distributions.ipynb`) | see §1.1 | `figures_svg/` |
| Figure 6, S14 (`nb03`), gradient panel + S17 (`nb04`), S16 + S18 (`nb05`) | not written: need r04 / pod results | — |
| PCA / tSNE / UMAP of the rule's picks (`nb07_selected_approaches_embeddings.ipynb`, like Figures 4–5, S11–S17) | rewritten 2026-11-03 for G2b: all 53 front members (6 pools) as unharmonized / harmonized pairs, post-removal batches faint | `figures_svg/g2b_review/` |
| Supplementary Files 1–3 (r40) | built with everything available now; re-run fills the rest | `output/wp10/`, `build_status.tsv` |
| Numbers for the text (r45) | 63 ready, 5 pending | `output/numbers.json` |
| Manuscript, stage A tracked edits (r50) | done: terminology, 33 / 31 methods, strategy D, Figure 4F legend, composite paragraphs deleted | `Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageA_261101.docx` |
| Manuscript, stage B (new paragraphs, rewrites, S-figure renumbering) | listed in the r50 docstring (23 items); needs results | — |
| Ledger (r90), validation (r99) | done; stage A: words 16,495 → 16,032, all integrity checks PASS | `output/wp14/` |
| Response letter draft + builder (r60) | draft written, `--draft` docx built | `response_letter_draft.md`, `Revised_manuscript/*_DRAFT.docx` |
| References (r51) | 12 items for you to fix in Mendeley | `output/wp12/reference_audit.tsv` |

### 1.1 Figure notebooks

`figures_svg/PLACEMENT.md` maps every file to its figure panel. All labels come from
`revision_lib.PUBLICATION_NAMES` (plain words only).

---

## 2. What you decide now (no pod needed)

Everything is in `gates_review_261102.md` (rewritten 2026-11-03 with your answers). Open:

1. **Q1 and Q2: answered 2026-11-03** (PC regression on diagnosis kept as the Global-biology
   headline; the "returned its input" check applies to every method, 111 approaches fail).
2. (nothing else open before the freeze)
3. **"Freeze"** of `adjudication_rule_261029.md` (final text with your G2 answers). Then Claude
   runs `md5sum … >> FROZEN_MD5.txt`, `r04_apply_rule.py --review` and nb07 → gate G2b.
4. References: the 12 items of `output/wp12/reference_audit.tsv` in Mendeley (you, before G6).

---

## 3. When to run the pods: now

The pilots **do not depend on gates G1 and G2**: the pods only harmonize and compute every metric
group; the panel and the rule are applied later on JupyterHub. So start the pilots now, in parallel
with your G1 / G2 reading. The order is:

| Cycle | What | Where | Takes (estimate) | Then |
|---|---|---|---|---|
| 1a | Gradient pilot, 24 harmonizations | harmonization pod | ~1–2 h | 1b |
| 1b | Leave-cohort-out pilot, 62 harmonizations | harmonization pod | ~3–8 h (31 methods, 1,869 + 374 samples) | delete pod, 1c |
| 1c | Pilot metrics, 86 jobs | same PVC-free pod (or the metrics pod) | ~2–6 h (group D is the slow part) | delete pod, tell Claude |
| — | **Gate G3** — Claude builds `output/wp6/pilot/pilot_report.md` (r14); you approve run times, node size, the slow-method fallback, dropping group D or not | JupyterHub | — | cycle 2 |
| 2a | Full gradient, 540 harmonizations (516 to run) | PVC-free pod, 48-vCPU node | ~hours (AMDBNorm dominates) | 2b |
| 2b | Full leave-cohort-out, 1,200 harmonizations (30 methods; 1,141 to run), C → K → J → S0 | same pod | ~1–2 days | 2c |
| 2c | Metrics of both experiments + bridging-batch check (2,234 jobs) | same pod | ~1 day | delete pod, tell Claude |
| — | **Gate G4** — results | JupyterHub | — | figures, text |

**Only one pod at a time**: both pods mount the main PVC (`fl-a3-scratch-150`). The
annotation 3.0 processing pod and the h230 pod must be stopped first (their data on the PVC stay).
Exception: the harmonization pod has a PVC-free manifest, `k8s/pod-revision-nopvc.yaml` (scratch on
the node, logs saved on S3 `revision_261029/pod_logs/`), that can run while the annotation 3.0 pod
holds the PVC (plan `revision_pod_without_pvc_plan_261101.md`, RUNBOOK §4b).

---

## 4. Pod manual (everything runs on the Mac unless marked "inside the pod")

Working copy: `~/FL_harmonization`. Namespace: `${K8S_NAMESPACE}`. Copy-paste the blocks
in order. If anything looks different from the "expect" lines, stop and see §4.6.

### 4.1 One-time checks

```bash
kubectl get pods -n ${K8S_NAMESPACE}                                   # expect: a list (kubectl works)
kubectl get secret aws-credentials ssh-pubkey -n ${K8S_NAMESPACE}   # expect: both listed
kubectl get pvc fl-a3-scratch-150 -n ${K8S_NAMESPACE}        # expect: STATUS Bound
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/ | head   # expect: folders
```

A missing Secret: create it with the commands in `harmonization-scripts/k8s/CLAUDE.md` and
`harmonization-metrics-calculation/CLAUDE.md` ("Pod Operations").

### 4.2 Before every launch: fresh code and a free volume

```bash
cd ~/FL_harmonization
git pull --rebase origin main
ls article_1_revision/r11_run_gradient.py \
   article_1_revision/output/wp6/designs/designs.tsv \
   article_1_revision/output/wp7/fold_samples.tsv              # expect: all three listed

kubectl get pods -n ${K8S_NAMESPACE} | grep fl-             # expect: nothing else running
kubectl describe pvc fl-a3-scratch-150 -n ${K8S_NAMESPACE} | grep -A3 "Used By"
# another pod listed and its work finished → kubectl delete pod <that-pod> -n ${K8S_NAMESPACE}
```

### 4.3 Cycle 1a–1b: harmonization pod, the two pilots

Launch the pod (8 vCPU / 16 GiB is enough for the pilots):

```bash
kubectl apply -f article_1_revision/k8s/pod-revision.yaml -n ${K8S_NAMESPACE}
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
#   or, while the annotation 3.0 pod holds the PVC:
#   kubectl apply -f article_1_revision/k8s/pod-revision-nopvc.yaml -n ${K8S_NAMESPACE}
kubectl get pod $POD_REV -n ${K8S_NAMESPACE} -w      # wait for Running (2–10 min), Ctrl-C
# PVC-free pod: expect "log-sync -> s3://…" (logs saved on S3, RUNBOOK §4b)
kubectl logs $POD_REV -c log-sync -n ${K8S_NAMESPACE}
```

Both manifests run on the ComboBatch image `ghcr.io/nikit357/combobatch:20260830` (the ECR
image is NotFound since 2026-11-01): it is only the environment. Wait for the start-up lines
(`kubectl logs $POD_REV -c worker -n ${K8S_NAMESPACE} | grep startup` → R 4.5.3,
`Shambhala2_fast 30ac312 OK`, `ready`), then copy the revision folder, the frozen
`bench_shared.py` and the metrics code in:

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
tar -C ~/FL_harmonization -cf - \
    --exclude='article_1_revision/cache' --exclude='article_1_revision/Revised_manuscript' \
    --exclude='article_1_revision/figures_svg' --exclude='*.parquet' --exclude='.ipynb_checkpoints' \
    article_1_revision harmonization-scripts/bench_shared.py harmonization-metrics-calculation \
  | kubectl exec -i $POD_REV -c worker -n ${K8S_NAMESPACE} -- tar -xf - -C /app

# the copied bench_shared.py must be the frozen one → "…bench_shared.py: OK"
kubectl exec $POD_REV -c worker -n ${K8S_NAMESPACE} -- \
    sh -c 'cd /app/article_1_revision && grep bench_shared FROZEN_MD5.txt | md5sum -c -'
```

Start the gradient pilot:

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
kubectl exec -it $POD_REV -n ${K8S_NAMESPACE} -- bash -l
```

Inside the pod:

```bash
cd /app/article_1_revision
mkdir -p /workspace/revision
python -m pytest tests/ -q                               # expect: 87 collected, some skipped is fine
python r11_run_gradient.py --pilot --dry-run             # expect: "24 harmonization jobs planned"
python r21_run_v1.py --pilot --dry-run                   # expect: "62 harmonization jobs planned"
python r18_env_check.py 2>&1 | tee /workspace/revision/env_check.log   # ~10–15 min; "ENV CHECK: OK"
setsid nohup python r11_run_gradient.py --pilot --skip-if-exists --n-workers 4 \
    > /workspace/revision/gradient_pilot.log 2>&1 &
exit
```

Watch from the Mac (the first job downloads the raw matrix, ~2 GB, once):

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
kubectl exec $POD_REV -n ${K8S_NAMESPACE} -- tail -n 20 /workspace/revision/gradient_pilot.log
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/gradient/runs/ | wc -l
# expect: grows to 24; the log ends with "SUMMARY harmonize: 24 jobs — …"
```

A method that fails (for example ComBat with the diagnosis covariate at λ = 1) is a **result**, not
an error: the job still counts as done and the reason is in its S3 run record.

Then the leave-cohort-out pilot (strategy C, fold 1, training + test, 31 methods):

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
kubectl exec -it $POD_REV -n ${K8S_NAMESPACE} -- bash -l
cd /app/article_1_revision
setsid nohup python r21_run_v1.py --pilot --skip-if-exists --n-workers 4 \
    > /workspace/revision/v1_pilot.log 2>&1 &
exit
# watch:  kubectl exec $POD_REV -n ${K8S_NAMESPACE} -- tail -n 20 /workspace/revision/v1_pilot.log
# expect at the end: "SUMMARY harmonize: 62 jobs — …"
kubectl delete pod $POD_REV -n ${K8S_NAMESPACE}     # free the PVC
# (PVC-free pod: deletion first writes the last logs to S3 pod_logs/, up to 90 s)
```

### 4.4 Cycle 1c: pilot metrics

**PVC-free pod (decided 2026-11-01):** the metrics pilot runs in the same pod right after
`SUMMARY harmonize: 62 jobs` — `python r12_revision_metrics.py --pilot --skip-if-exists
--n-workers 8 --memory-limit-gb 3.0` (RUNBOOK §5); then delete the pod. The SSH metrics pod
below is the alternative (it needs the PVC).


```bash
kubectl apply -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
POD_METRICS=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-metrics -o name | cut -d/ -f2)
kubectl logs -f $POD_METRICS -n ${K8S_NAMESPACE}
# wait for "[startup] Metrics environment ready." (10–20 min), Ctrl-C
```

Terminal 2 (keep it open the whole time):

```bash
POD_METRICS=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-metrics -o name | cut -d/ -f2)
kubectl port-forward pod/$POD_METRICS 2222:22 -n ${K8S_NAMESPACE}
```

Terminal 1 — copy the two folders (whole folders: group L needs `marker_gene_annotation.csv`):

```bash
for d in harmonization-metrics-calculation article_1_revision; do
  rsync -avz --exclude='cache/' --exclude='Revised_manuscript/' --exclude='*.parquet' \
      --exclude='.ipynb_checkpoints/' \
      -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
      ~/FL_harmonization/$d/ root@localhost:/app/$d/
done
ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@localhost
```

Inside the pod:

```bash
cd /app/article_1_revision
mkdir -p /workspace/revision
python r12_revision_metrics.py --pilot --dry-run
# expect: "86 metric jobs planned; 86 have a harmonized matrix" (fewer if a method failed — fine)
setsid nohup python r12_revision_metrics.py --pilot --skip-if-exists \
    --n-workers 8 --memory-limit-gb 8.0 > /workspace/revision/metrics_pilot.log 2>&1 &
exit
```

`--n-workers` ≈ (vCPU of the node − 8); `nproc` inside the pod gives the vCPU. When the log ends with
`SUMMARY metrics`, delete the pod (`kubectl delete pod $POD_METRICS -n ${K8S_NAMESPACE}`)
and **tell Claude on JupyterHub: "the pilots are done"**. Claude then runs
`python r14_pilot_report.py --workers <n>` and brings you the gate G3 report:
- run time per method and the projected wall time of the full runs;
- the methods slower than 30 min on the 1,869-sample training part (decision D8 fallback: drop
  them from the full leave-cohort-out run with `--exclude-methods`);
- whether SVA / ComBat without the diagnosis covariate ran, and what the covariate arms did at λ = 1;
- the metric time per job (whether to drop the slow group D with `--groups ABCEGHIJKLN`);
- the node size for the S0 training folds (~5,700 samples).

### 4.5 Cycle 2: full runs (G3 answered 2026-11-03)

The exact commands are in **`RUNBOOK.md` §6** (one PVC-free pod on a 48-vCPU / 96-GiB node for
the harmonizations and the metrics; 6 h per run; exploBATCH dropped from leave-cohort-out).
Order: gradient (516 to run) → leave-cohort-out C → K → J → S0 (1,141 to run) → metrics gradient →
metrics leave-cohort-out → bridging check (2,234). Delete the pod and **tell Claude: "the full runs
are done"**.

### 4.6 Troubleshooting

See `RUNBOOK.md` §7 (pending pod, Multi-Attach error, missing Secret, OOM / exit 137, "waiting for
memory", `ModuleNotFoundError`, refused port-forward, wrong dry-run counts, per-job logs in
`/workspace/revision/`).

---

## 5. After the pods (Claude on JupyterHub)

After "the full runs are done":

```bash
source ~/venvs/collagen_3_11/bin/activate && cd article_1_revision
python r12_revision_metrics.py --experiment gradient --concat          # → output/wp6/gradient_metrics.parquet
python r12_revision_metrics.py --experiment leave_cohort_out --concat  # → output/wp7/v1_metrics.parquet
python r30_bridging_subset_metrics.py --concat                         # → output/wp8/bridging_biology.parquet
python r13_gradient_stats.py           # slopes vs Cramér's V, anchors, cap sensitivity, failures
python r04_apply_rule.py --review      # only after G2 (rule MD5 frozen); → gate G2b
python r22_v1_evaluate.py              # after G2b: transfer to unseen cohorts
python r05_robustness.py               # after G2b: Kendall τ, front stability (+ bridging variant)
python r40_build_supplementary.py && python r45_results_numbers.py     # → gate G4
```

Then: notebooks `nb03` (Figure 6, S14), `nb04` (gradient panel, S17), `nb05` (S16, S18); r50
stage B (new paragraphs, rewrites, S-figure renumbering) → `r90_ledger.py` (nothing grew) →
`r60_response_letter.py` (gate G5) → `r99_verify.py <tracked docx>` (gate G6).

---

## 6. Layout

| Path | Content |
|---|---|
| `revision_lib.py` | shared helpers: wrappers around the frozen code, λ designs, panel rule, four scores, rule ranking (`pareto_layers`, `rule_order`), scoring of new runs (`score_runs`), plain-word names, ledger |
| `revision_dispatch.py` | job lists + parallel subprocess runner of the pods |
| `r00`–`r05` | reanalysis: ledger, confounding, panel, four scores, rule (`r04`), robustness (`r05`) |
| `r10`–`r14` | gradient: designs, dispatcher, metrics, statistics (`r13`), pilot report (`r14`) |
| `r18` | environment check of the ComboBatch-image pod against published matrices |
| `r19`–`r22` | harmonization worker, cohort folds, leave-cohort-out dispatcher, evaluation (`r22`) |
| `r30` | bridging-batch check (metrics pod) |
| `r40`, `r45` | supplementary files, numbers for the text |
| `r50`, `r51`, `r60` | tracked manuscript edits, reference audit, response letter |
| `r90`, `r99` | ledger ("nothing grew"), full validation incl. the internal-label scan |
| `nb01`, `nb02`, `nb06` | figure notebooks (→ `figures_svg/`, map in `figures_svg/PLACEMENT.md`) |
| `adjudication_rule_261029.md` | the selection rule, final text, **frozen 2026-11-03** |
| `response_letter_draft.md` | the response letter, `{{key}}` = number from `output/numbers.json` |
| `inputs/` | read-only copies of Supplementary Files 1–3, the baseline text dump and citation-field report |
| `Revised_manuscript/` | baseline docx (read-only, git-ignored; re-create with `cp` + `chmod 444` from `figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx`), stage A tracked docx, letter draft docx |
| `output/wp1` … `output/wp14` | results; `wp6/designs/` and `wp7/folds*` are committed because the pods need them |
| `k8s/pod-revision.yaml` | harmonization pod manifest (ComboBatch image + `Shambhala2_fast`, PVC) |
| `k8s/pod-revision-nopvc.yaml` | harmonization + pilot-metrics pod without the PVC (ComboBatch image + `Shambhala2_fast`; emptyDir scratch; `log-sync` container saves the logs on S3 `pod_logs/`) |
| `tests/` | toy checks: `test_revision_lib.py` (77), `test_analysis_scripts.py` (8) |
| `cache/` | local S3 caches (git-ignored) |

## 7. Key numbers so far

| Quantity | Value | Source |
|---|---|---|
| Bias-corrected Cramér's V / AMI, batch × diagnosis, all 7,174 samples | 0.358 / 0.263 | `output/wp1/confounding_by_strategy.tsv` |
| Single-diagnosis batches | 11 of 29, 2,068 samples (28.8 %) | same |
| Multi-diagnosis batches; components of the batch–diagnosis graph | 18 (5,106 samples); 1 | `output/wp1/bridging_batches.tsv` |
| Variance partition, raw S0 (median per gene): batch / diagnosis / shared R² | 0.743 / 0.070 / 0.037 | `output/wp1/variance_partition_raw.tsv` |
| Real-data V on the 5 gradient batches (3,404 samples) | 0.398 | `output/wp6/real_data_v.json` |
| Reduced panel | 22 metrics (22 clusters at \|ρ\| ≥ 0.8 over 32 metrics; tSNE centroid dispersion excluded); 8 groups in the panel, group H through its cluster mates | `output/wp2/reduced_panel.tsv` |
| Approaches complete on the panel / on all 87 | 1,993 / 1,354 of 2,234 | `output/wp2/panel_summary.json` |
| η², reduced panel: method / strategy / imputation / post-removal | 0.333 / 0.277 / 0.010 / 0.002 (87 metrics: 0.363 / 0.256 / 0.016 / 0.002, = submitted) | `output/wp3/eta_squared.tsv` |
| Approaches that returned their input (method failures) | 111 of 2,234 (exploBATCH 49, RUV-III-PRPS 27, DWD 19, FSQN R 10, SVA 6) | `output/wp3/four_scores.parquet`, `identical_to_raw` |
| Bar headline metrics | Global batch `PCReg_RNA_BATCH`; Global diagnosis `PCReg_Diagnosis_cell_type_unified` (fixed, Q1); Local batch `kbet_acceptance_rate_RNA_BATCH`; Local diagnosis `graph_connectivity_Diagnosis_cell_type_unified` | `output/wp3/bar_headlines.tsv` |
