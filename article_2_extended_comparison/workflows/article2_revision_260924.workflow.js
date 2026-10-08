export const meta = {
  name: 'article2-revision-260924',
  description: 'Revision round 1 of the F1000 Article 2 draft: apply Daniil\'s review, rewrite the unreviewed half, rebuild figures, deliver as tracked changes',
  phases: [
    { title: 'Reconcile', detail: 'Census 344/334/87, citation invariants 46/4, Markdown master from Daniil\'s .docx' },
    { title: 'Evidence',  detail: 'E1 index, every missing test and correlation, main and supplementary tables, citation proposals' },
    { title: 'Figures',   detail: 'E2, E3, E5, B6 panels at the reference frame, text overlays for Figma' },
    { title: 'Draft',     detail: 'Three writers on disjoint paragraph ranges; statistics queue drained by re-entering Evidence' },
    { title: 'Review',    detail: 'Principles gate, density pass, overlap and style gates, citation proposals re-resolved' },
    { title: 'Deliver',   detail: 'Renumber by first citation, tracked-changes .docx, workbooks, run report' },
  ],
}

// Plan of record: article_2_extended_comparison/f1000_article2_revision_plan_260924.md.
//
// This script is the revision round's workflow as it was actually executed on 2026-09-25,
// written down so it can be rerun. The first run was driven interactively, phase by phase,
// with Daniil approving each gate; every agent brief it used is on disk in RUN_DIR and the
// prompts below point at those briefs instead of restating them, so a rerun follows the same
// instructions. The 260919 workflow (article2_f1000.workflow.js) is left untouched so the
// run that produced the first draft stays reproducible.
//
// Deterministic steps are scripts, not agents; the agents below only write prose or review.
//   Phase 0  workflow_runs/260924_run1/phase0_map_registry_to_snapshot.py, tools/docx2md.py
//   Phase 1  analysis/article2_generalizability.py, analysis/build_numbers_json.py
//   Phase 2  figures/article2_figures_260925.py, tools/split_figure_text_260925.py
//   Phase 3  workflow_runs/260924_run1/phase3_paragraph_index.py, tools/assemble_draft_260925.py
//   Phase 4  tools/check_principles.py, tools/audit_numbers.py, tools/check_overlap.py,
//            tools/check_style.py --budgets revision_260925
//   Phase 5  tools/renumber_260925.py, tools/build_tracked_revision_260924.py,
//            analysis/build_supplementary_workbooks.py
// Figma placement (Phase 2, Phase 5 renaming) needs an authenticated session and is not
// done by this script.

const REPO = (args && args.repo) || '<repo>'
const A2 = `${REPO}/article_2_extended_comparison`
const RUN_DIR = (args && args.runDir) || 'workflow_runs/260924_run1'
const PHASES = (args && args.phases) || ['reconcile', 'evidence', 'figures', 'draft', 'review', 'deliver']
const wants = p => PHASES.indexOf(p) !== -1
const MAX_ROUNDS = 2          // revision rounds per gate (plan W, inherited)
const MAX_REENTRIES = 3       // statistics-queue re-entries; they do not count as rounds (W2b)
const VENV = 'source ~/venvs/collagen_3_11/bin/activate'

// ---------------------------------------------------------------- rules

// Rules 1-3, 5-10 are inherited from article2_f1000.workflow.js. Rule 4 ("the source is v2")
// and its rule 12 ("Word edits are plain") are replaced: the base is now Daniil's edited
// copy and the deliverable is a tracked-changes .docx. Rules 11-19 are plan §W3 verbatim.
const HARD_RULES = `
BINDING RULES -- these override any instinct to be helpful or complete:
1. PROVENANCE. No number without a table, a column and a filter.
2. NEVER INVENT. No link, reference, DOI, PMID, statistic, author or URL you did not read.
   Unknown values are written literally as [TO CONFIRM: what is missing].
3. CROSS-CHECK. Numbers are re-derived by audit_numbers.py; citations by another agent.
5. NO PLAGIARISM OF ARTICLE 1. check_overlap.py runs against FL_harmonization_article_NAR_260912.docx.
6. COMPARE CATEGORIES AGAINST EACH OTHER on the full analysis set; the clustermap group is one
   isolated named group.
7. THE ANALYSIS SET IS 2,234 ROWS, 31 methods; shambhala_P0std_Q0std IS 20_shambhala.
7b. LOBO: report the full cut and the multiclass-only cut side by side.
9. LANGUAGE. No "rather than", no "X, not Y", no proofless adjective. American spelling.
10. ARTIFACTS. Write to disk BEFORE returning, incrementally, with a ## Status block at the top.
11. THE BASE IS DANIIL'S EDITED COPY (FL_metric_classes_F1000_260917_edited_Daniil.docx). His
    wording wins; you extend it. The exception is the defects in §F of the principles document.
12. THE PRINCIPLES DOCUMENT IS BINDING ON PARAGRAPHS 78-148 (its §G checklist).
13. NUMBERS ARE THREE SIGNIFICANT FIGURES; the evidence file carries the rounded spellings.
14. DO NOT TOUCH A CITATION: 46 Mendeley content controls and [38] x2, [50,51], [52] are
    invariants; carry every ⟦CIT:…⟧ token verbatim, in order, in its paragraph.
15. AT MOST THREE NUMERIC VALUES AND ONE TEST RESULT PER SENTENCE; beyond that, a table.
16. NEVER WRITE AROUND A MISSING NUMBER: queue it in 10_stat_requests_<writer>.json and write
    [STAT: <id>]; the phase re-opens and the number is computed.
17. HARMONIZATION_METRICS_EXTENDED_260920_V3.DOCX MAY BE REUSED FREELY (Daniil's own document).
18. THE DELIVERABLE IS A TRACKED-CHANGES .DOCX against Daniil's edited copy: Accept All gives the
    revised article, rejecting Claude's revisions restores his copy.
19. AT MOST FIVE TABLES IN THE MAIN TEXT.
`

const BRIEF = `${A2}/${RUN_DIR}/03_brief_common.md`

// ---------------------------------------------------------------- schemas

const RESULT_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string' },
    artifacts_written: { type: 'array', items: { type: 'string' } },
    open_stat_requests: { type: 'array', items: { type: 'string' } },
    notes: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'artifacts_written'],
}

const GATE_SCHEMA = {
  type: 'object',
  properties: {
    gate: { type: 'number' },
    verdict: { type: 'string' },
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          agent: { type: 'string' }, defect: { type: 'string' }, required_fix: { type: 'string' },
        },
        required: ['agent', 'defect', 'required_fix'],
      },
    },
    open_items: { type: 'array', items: { type: 'string' } },
  },
  required: ['gate', 'verdict', 'defects'],
}

// ---------------------------------------------------------------- prompts

const common = extra => `Working directory: ${A2}. Python: ${VENV}. Run folder: ${RUN_DIR}.
Plan of record: f1000_article2_revision_plan_260924.md (read §B, §C, §W3 and the TODO).
${HARD_RULES}
${extra}`

const defectBlock = d => (d && d.length)
  ? `\nTHE TEAM LEAD REJECTED YOUR PREVIOUS ARTIFACT. Fix exactly these defects:\n${JSON.stringify(d, null, 2)}\n`
  : ''

function codeAnalystPrompt(defects, requests) {
  return common(`You are the CODE-ANALYST. ${requests ? `RE-ENTRY: serve these open statistics
requests from the writers, appending the tests to A2_T10 (or a new A2_T* table where a test is
not the right form) and the values to 01_numbers.json; mark each request resolved with its
value, and say plainly when a result contradicts the claim that requested it:
${JSON.stringify(requests, null, 2)}` : `Produce the Phase 1 evidence: the E1 index, every
missing test (Mann-Whitney two-sided raw p, Kruskal-Wallis, Fisher, Spearman), baselines and
named dispersions, the main tables A2_T9/A2_T13/A2_T3/A2_T2b and the supplementary catalogues,
each registered in TABLE_REGISTRY with its tier. Run: python analysis/article2_generalizability.py
&& python analysis/build_numbers_json.py. Write 13_phase1_evidence_report.md.`}
${defectBlock(defects)}`)
}

function literatureScoutPrompt(defects) {
  return common(`You are the LITERATURE-SCOUT. Resolve the C20 (statistical methods and Python
packages of the Methods) and C37 (class-count dependence of local metrics) references as a
PROPOSAL LIST in ${RUN_DIR}/11_citations_to_insert.md: identifier, supporting passage, target
sentence, verdict. Nothing is written into the manuscript. tools/fetch_literature.py resolves
PMIDs and DOIs. ${defectBlock(defects)}`)
}

function figureAnalystPrompt(defects) {
  return common(`You are the FIGURE-ANALYST. Build the E2, E3, E5 and B6 figures and re-lay the
panels C50 names, each inside the reference frame 637:93145 (756 x 1159 px, 2 px = 1 pt), grids
not strips, no overlapping labels, p written as p = 1.4 × 10⁻⁹, every panel lettered. Run:
python figures/article2_figures_260925.py && python tools/split_figure_text_260925.py, look at
every figures/panels_260925/*.png, then write 07_panels.{json,md}
(workflow_runs/260924_run1/phase2_panel_inventory.py). ${defectBlock(defects)}`)
}

function writerPrompt(role, range, defects) {
  return common(`You are the ${role}. Your binding brief is ${BRIEF}: read it first and follow
it exactly (inputs, figure tokens, table slate, sheet names, block format). Your range: ${range}.
Revise from ${RUN_DIR}/00_paragraph_index.md, never from manuscript/*.md. Write your blocks to
your own draft file and your statistics requests to your own 10_stat_requests_*.json.
${defectBlock(defects)}`)
}

function referenceVerifierPrompt(defects) {
  return common(`You are the REFERENCE-VERIFIER. You edit nothing in the manuscript. (1) Re-resolve
every proposal of ${RUN_DIR}/11_citations_to_insert.md from the registry and, where reachable,
the full text; verdict CONFIRMED / CONFIRMED WITH CORRECTION / NOT CONFIRMED. (2) Audit the
citation invariants in ${RUN_DIR}/03_revision_edits.json against the base .docx (46 fields,
same order, numeric brackets present) and report any citation left on a claim that changed.
Write ${RUN_DIR}/18_references_verified.md. ${defectBlock(defects)}`)
}

function styleEditorPrompt(defects) {
  return common(`You are the STYLE-EDITOR. Run python tools/check_principles.py
manuscript/FL_metric_classes_F1000_260925.md. For every sentence over the rule-15 ceiling, split
it or route its surplus numbers to a named main table or Supplementary File sheet, editing the
draft blocks (03a/03b/08), never the assembled manuscript. Enforce the five-table cap. Rebuild
with python tools/assemble_draft_260925.py and iterate until check_principles and audit_numbers
pass. Write ${RUN_DIR}/17_style_editor_report.md. ${defectBlock(defects)}`)
}

function teamleadPrompt(gate, payload) {
  return common(`You are the TEAM LEAD at gate ${gate}. Judge the artifacts against the plan's
gate questions (W1) and HARD_RULES. Run every deterministic check yourself; do not accept an
agent's claim that a gate passed. Return defects addressed to a named agent, or verdict
"accept". Payload: ${JSON.stringify(payload).slice(0, 20000)}`)
}

// ---------------------------------------------------------------- gate loop

async function gateLoop(gate, phaseName, payload, revise) {
  let verdict = null
  for (let round = 1; round <= MAX_ROUNDS; round++) {
    verdict = await agent(teamleadPrompt(gate, payload),
      { label: `teamlead:gate${gate}:r${round}`, phase: phaseName, schema: GATE_SCHEMA })
    if (!verdict || verdict.verdict === 'accept' || !verdict.defects.length) break
    payload = await revise(verdict.defects, payload)
  }
  return verdict
}

const defectsFor = (defects, who) => (defects || []).filter(d => d.agent === who)

// ---------------------------------------------------------------- run

log(`Article 2 revision round 1 — phases: ${PHASES.join(', ')} | run folder: ${RUN_DIR}`)
const out = { phases: PHASES, runDir: RUN_DIR }

if (wants('reconcile')) {
  phase('Reconcile')
  out.reconcile = await agent(common(`You are the CODE-ANALYST, Phase 0. Confirm the 344 / 334 / 87
census against figures_for_article/supplementary_260824/Supplementary File 2.xlsx (sheet
Metric_polarity); record the citation invariants of the base .docx (46 Mendeley content
controls, 4 numeric brackets); regenerate the Markdown master with python tools/docx2md.py
manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx manuscript/FL_metric_classes_F1000_260924.md
and verify every non-empty paragraph of the .docx survives it; run
${RUN_DIR}/phase0_map_registry_to_snapshot.py. Write ${RUN_DIR}/09_metric_census.md.`),
    { label: 'code-analyst:reconcile', phase: 'Reconcile', schema: RESULT_SCHEMA })
}

if (wants('evidence')) {
  phase('Evidence')
  const pair = await parallel([
    () => agent(codeAnalystPrompt(null, null), { label: 'code-analyst', phase: 'Evidence', schema: RESULT_SCHEMA }),
    () => agent(literatureScoutPrompt(null), { label: 'literature-scout', phase: 'Evidence', schema: RESULT_SCHEMA }),
  ])
  out.evidence = pair
  out.gate1 = await gateLoop(1, 'Evidence', { evidence: pair }, async (defects, prev) => {
    const redone = await parallel([
      () => defectsFor(defects, 'code-analyst').length
        ? agent(codeAnalystPrompt(defectsFor(defects, 'code-analyst'), null), { label: 'code-analyst:revise', phase: 'Evidence', schema: RESULT_SCHEMA })
        : Promise.resolve(prev.evidence[0]),
      () => defectsFor(defects, 'literature-scout').length
        ? agent(literatureScoutPrompt(defectsFor(defects, 'literature-scout')), { label: 'literature-scout:revise', phase: 'Evidence', schema: RESULT_SCHEMA })
        : Promise.resolve(prev.evidence[1]),
    ])
    return { evidence: redone }
  })
}

if (wants('figures')) {
  phase('Figures')
  out.figures = await agent(figureAnalystPrompt(null), { label: 'figure-analyst', phase: 'Figures', schema: RESULT_SCHEMA })
  out.gate2 = await gateLoop(2, 'Figures', { figures: out.figures }, async defects => ({
    figures: await agent(figureAnalystPrompt(defectsFor(defects, 'figure-analyst')), { label: 'figure-analyst:revise', phase: 'Figures', schema: RESULT_SCHEMA }),
  }))
}

const WRITERS = [
  ['writer-reviewed', 'P0-P76 without the legend paragraphs P37, P41, P44 -> 03a_draft_reviewed.md'],
  ['writer-unreviewed', 'P78-P148 and P161-P177 without P130, P138 -> 03b_draft_unreviewed.md'],
  ['legend-writer', 'every figure legend (P37, P41, P44, P77, P130, P138) and P149-P160, plus new legends -> 08_legends.md'],
]

if (wants('draft')) {
  phase('Draft')
  out.draft = await parallel(WRITERS.map(([role, range]) => () =>
    agent(writerPrompt(role, range, null), { label: role, phase: 'Draft', schema: RESULT_SCHEMA })))
  // W2b: a writer's open statistics request re-opens Evidence; the draft resumes after it.
  for (let k = 1; k <= MAX_REENTRIES; k++) {
    const open = out.draft.flatMap(w => (w && w.open_stat_requests) || [])
    if (!open.length) break
    log(`Statistics queue: ${open.length} open request(s) — re-entering Evidence (${k}/${MAX_REENTRIES}).`)
    await agent(codeAnalystPrompt(null, open), { label: `code-analyst:reentry${k}`, phase: 'Draft', schema: RESULT_SCHEMA })
    out.draft = await parallel(WRITERS.map(([role, range]) => () =>
      agent(writerPrompt(role, range, [{ agent: role, defect: 'statistics requests resolved',
        required_fix: `replace every [STAT: …] marker in your draft with the value recorded in your 10_stat_requests file; rewrite any claim the resolution contradicts` }]),
      { label: `${role}:reentry${k}`, phase: 'Draft', schema: RESULT_SCHEMA })))
  }
  out.gate3 = await gateLoop(3, 'Draft', { draft: out.draft }, async (defects, prev) => ({
    draft: await parallel(WRITERS.map(([role, range]) => () => defectsFor(defects, role).length
      ? agent(writerPrompt(role, range, defectsFor(defects, role)), { label: `${role}:revise`, phase: 'Draft', schema: RESULT_SCHEMA })
      : Promise.resolve(null))),
  }))
}

if (wants('review')) {
  phase('Review')
  out.review = await parallel([
    () => agent(styleEditorPrompt(null), { label: 'style-editor', phase: 'Review', schema: RESULT_SCHEMA }),
    () => agent(referenceVerifierPrompt(null), { label: 'reference-verifier', phase: 'Review', schema: RESULT_SCHEMA }),
  ])
  out.gate4 = await gateLoop(4, 'Review', { review: out.review }, async (defects, prev) => ({
    review: await parallel([
      () => defectsFor(defects, 'style-editor').length
        ? agent(styleEditorPrompt(defectsFor(defects, 'style-editor')), { label: 'style-editor:revise', phase: 'Review', schema: RESULT_SCHEMA })
        : Promise.resolve(prev.review[0]),
      () => defectsFor(defects, 'reference-verifier').length
        ? agent(referenceVerifierPrompt(defectsFor(defects, 'reference-verifier')), { label: 'reference-verifier:revise', phase: 'Review', schema: RESULT_SCHEMA })
        : Promise.resolve(prev.review[1]),
    ]),
  }))
}

if (wants('deliver')) {
  phase('Deliver')
  out.deliver = await agent(common(`You are the TEAM LEAD, Phase 5. Run in order and require
each to exit 0: python tools/assemble_draft_260925.py; python tools/renumber_260925.py;
python tools/build_tracked_revision_260924.py; python analysis/build_supplementary_workbooks.py;
then every Phase 4 gate on the final manuscript. Report the renumbering map (21_renumber_map.md),
the build report (22_docx_build_report.md), the Figma frames still to rename (by node id,
longest name first), and write ${RUN_DIR}/RUN_REPORT.md with the provenance table and open items.`),
    { label: 'teamlead:deliver', phase: 'Deliver', schema: RESULT_SCHEMA })
}

return out
