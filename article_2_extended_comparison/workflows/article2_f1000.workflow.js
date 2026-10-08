export const meta = {
  name: 'article2-f1000',
  description: 'Research, compute, draft and adversarially review the F1000Research metric-class article',
  phases: [
    { title: 'Evidence',  detail: 'Numbers recomputed from the analysis set; citation landscape with live PMIDs' },
    { title: 'Draft',     detail: 'Full manuscript to the F1000 section shape' },
    { title: 'Review',    detail: 'PMID verification from full text, style gate, verbatim-overlap gate' },
    { title: 'Delivery',  detail: 'Team lead assembly, provenance table, open items' },
  ],
}

// ---------------------------------------------------------------- configuration
//
// REPO defaults to the JupyterHub pod, which is where the metric tables large enough to
// matter actually live (gene_qc_long is 122 MB and has never been on the Mac). Pass
// args.repo to run the same script from the Mac checkout.
const REPO = (args && args.repo) || '<repo>'
const A2 = `${REPO}/article_2_extended_comparison`

// Daniil's instruction in §6.1: name the run folder for the date it actually ran.
const RUN_DIR = (args && args.runDir) || 'workflow_runs/260919_run1'

// §6.4: the run is split in two halves. Run A is ['evidence','draft'], Run B is
// ['review','delivery'] with resumeFromRunId pointing at Run A.
const PHASES = (args && args.phases) || ['evidence', 'draft', 'review', 'delivery']
const wants = p => PHASES.indexOf(p) !== -1

// Phases 2 and 3 of the TODO were implemented directly, so 01_numbers and 02_literature
// already exist under workflow_runs/260917_phase{2,3}/. 'reuse' makes the two Evidence
// agents verify and carry those files into RUN_DIR; 'recompute' makes them redo the work
// from the tables. Recomputing costs a full notebook execution and changes nothing that
// has not already been verified, so reuse is the default.
const EVIDENCE_MODE = (args && args.evidenceMode) || 'reuse'

const PHASE2_DIR = 'workflow_runs/260917_phase2'
const PHASE3_DIR = 'workflow_runs/260917_phase3'

// Two revision rounds per gate, then the defect becomes an open item for Daniil (§6.2).
const MAX_ROUNDS = 2

// ---------------------------------------------------------------- shared prompt blocks

const HARD_RULES = `
BINDING RULES -- these override any instinct to be helpful or complete:
1. PROVENANCE. No number without a table, a column and a filter. No citation without a PMID you
   resolved yourself from the full text. If you cannot quote it, you cannot use it.
2. NEVER INVENT. You are STRICTLY PROHIBITED from inventing any link, reference, article, DOI,
   PMID, accession, statistic, author, affiliation or URL. Unknown values are written literally
   as [TO CONFIRM: what is missing]. A fabricated reference aborts the run.
3. CROSS-CHECK. Every agent's citations are re-resolved by another agent. Every agent's numbers
   are re-derived by audit_numbers.py. Nothing is trusted because an agent asserted it.
4. THE SOURCE DOCUMENT IS v2. Harmonization_metrics_extended_260802_v2.docx. The _260802.docx
   (v1) pass is superseded and four of its corrections are wrong.
5. NO PLAGIARISM OF ARTICLE 1. FL_harmonization_article_NAR_260912.docx is a bioRxiv preprint by
   the same authors. Cite it by its DOI 10.64898/2026.09.15.751825, sparingly. Never write [PREPRINT-1]. Reuse no sentence, no Methods paragraph,
   no distinctive phrase. Facts it established are cited, not re-derived. Methods is SHORTER
   than Article 1's and has four to six subsections.
6. THE COMPARISON IS NOT ARTICLE 1'S. Compare strategies, imputations and methods against each
   other on the full analysis set, with the clustermap best approaches as one isolated named
   group. Do not run or restate a best-versus-rest test.
7. THE ANALYSIS SET IS 2,234 ROWS: Article 1's canonical set, pct_samples_allNA < 5, 31 methods.
   \`shambhala_P0std_Q0std\` in the metric snapshots IS \`20_shambhala\` -- rename it on load, before
   any filter, and drop the other 17 P/Q variants. Skipping the rename gives 2,150 and silently
   loses 84 approaches. If your filter returns anything but 2,234 you have a bug -- do not adjust
   the definition to match your code.
7b. LOBO FOLDS: report BOTH the full metric (all folds) and the multiclass-only metric (folds with
   >= 2 classes), side by side, in every table. A single-class fold is an honest test, not a
   defect: a classifier trained on every batch but one can still mislabel a DLBCL-only batch.
   Never drop single-class folds and never present one cut without the other.
8. FIGMA IS UNTOUCHED BY THIS WORKFLOW. Assembly happens in an interactive session.
9. LANGUAGE. No "rather than". No "X, not Y" antithesis. No proofless adjective: justify
   "comprehensive", "novel", "robust" in the adjacent clause or delete them.
10. ARTIFACTS. Write to disk BEFORE returning, incrementally, with a ## Status block at the top.
    Markdown always, JSON when structured. Both files carry the same content. Write a partial
    artifact after each sub-deliverable and append to it; a half-finished file on disk is worth
    more than a complete one that died in context. Never hold everything until the end.
11. PHASE SELECTION AND RESUME. This run executes only these phases: ${PHASES.join(', ')}.
    Artifacts from earlier phases are already on disk in the run folder -- read them, do not
    recreate them. If your own artifact is already there, read its ## Status block first and
    continue from where it stopped instead of starting over.
12. WORD EDITS ARE PLAIN. Daniil's instruction of 2026-09-19: every edit to a .docx is a plain
    edit, NOT a tracked change. Do not use word-rewrite, nar-review or any other suggestion-mode
    helper on these files, and do not emit w:ins or w:del. Edit the run text in place with
    python-docx and save. After any edit to the manuscript markdown, bring
    manuscript/FL_metric_classes_F1000_260917.docx back into agreement with it in the same pass,
    so the two never diverge -- the .docx is the main state and Daniil comments in it.
`

const FABRICATION = `
YOU ARE STRICTLY PROHIBITED from inventing or creating any non-existent link, reference, article,
DOI, PMID, accession, statistic, author, affiliation or URL. If you cannot open it and quote it,
you cannot cite it. Unknown values are written literally as [TO CONFIRM: what is missing]. A
fabricated reference aborts the workflow; it is not a defect to be corrected in review.
`

const ARTIFACT_DISCIPLINE = `
ARTIFACT DISCIPLINE:
  - Write to disk BEFORE returning, never after.
  - Markdown always, JSON when the output is structured; both files carry the same content,
    generated from the same object.
  - Every artifact opens with a "## Status" block: what is complete, what is in progress, what is
    not started.
  - The file names below are fixed so a resumed run finds them without searching. Do not rename.
`

const PROJECT_PATHS = `
WHERE THINGS ARE:
  Plan (read it, it is the specification):  ${A2}/f1000_article2_plan_260917.md
  Source document v2:  ${A2}/manuscript_versions/Harmonization_metrics_extended_260802_v2.docx
  Article 1 (do not reuse its prose):
      ${REPO}/figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx
  Tables Article 2 quotes from:  ${A2}/tables/A2_T0..A2_T8_*_260917.csv
  Panels (18, PDF+SVG+PNG):      ${A2}/figures/panels_260917/
  Recipe artwork (12 SVGs):      ${A2}/figures/recipe_assets_260917/
  Gates:                         ${A2}/tools/{check_style,audit_numbers,check_overlap,docx2md}.py
  Manuscript output folder:      ${A2}/manuscript/
  This run's artifacts:          ${A2}/${RUN_DIR}/
  Python environment:            source ~/venvs/collagen_3_11/bin/activate
`

// ---------------------------------------------------------------- schemas

const NUMBERS_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string' },
    analysis_set: {
      type: 'object',
      properties: {
        n_rows: { type: 'number' },
        n_methods: { type: 'number' },
        n_strategies: { type: 'number' },
        n_imputations: { type: 'number' },
        snapshot: { type: 'string' },
      },
      required: ['n_rows', 'n_methods', 'n_strategies', 'n_imputations', 'snapshot'],
    },
    numbers: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          key: { type: 'string' },
          value: { type: 'string' },
          table: { type: 'string' },
          column: { type: 'string' },
          filter: { type: 'string' },
          claim: { type: 'string' },
        },
        required: ['key', 'value', 'table', 'column', 'filter'],
      },
    },
    discrepancies: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          key: { type: 'string' },
          source_document_value: { type: 'string' },
          recomputed_value: { type: 'string' },
          source_document_filter: { type: 'string' },
          recomputed_filter: { type: 'string' },
          which_wins: { type: 'string' },
        },
        required: ['key', 'source_document_value', 'recomputed_value', 'which_wins'],
      },
    },
    panels: { type: 'array', items: { type: 'string' } },
    open_to_confirm: { type: 'array', items: { type: 'string' } },
    artifacts_written: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'analysis_set', 'numbers', 'discrepancies', 'artifacts_written'],
}

const LITERATURE_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string' },
    gap_statement: { type: 'string' },
    references: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          pmid: { type: 'string' },
          doi: { type: 'string' },
          title: { type: 'string' },
          year: { type: 'string' },
          journal: { type: 'string' },
          theme: { type: 'string' },
          supports_claim: { type: 'string' },
          quote: { type: 'string' },
          quote_section: { type: 'string' },
          full_text_read: { type: 'boolean' },
        },
        required: ['pmid', 'title', 'year', 'journal', 'supports_claim', 'quote', 'full_text_read'],
      },
    },
    themes_covered: { type: 'array', items: { type: 'string' } },
    could_not_open: { type: 'array', items: { type: 'string' } },
    artifacts_written: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'gap_statement', 'references', 'themes_covered', 'artifacts_written'],
}

const REFERENCE_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string' },
    checked: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          pmid: { type: 'string' },
          cited_at: { type: 'string' },
          exists: { type: 'boolean' },
          ids_correct: { type: 'boolean' },
          supports_sentence: { type: 'boolean' },
          supporting_passage: { type: 'string' },
          passage_section: { type: 'string' },
          verdict: { type: 'string' },
        },
        required: ['pmid', 'cited_at', 'exists', 'ids_correct', 'supports_sentence', 'verdict'],
      },
    },
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          pmid: { type: 'string' },
          cited_at: { type: 'string' },
          defect: { type: 'string' },
          required_fix: { type: 'string' },
        },
        required: ['cited_at', 'defect', 'required_fix'],
      },
    },
    artifacts_written: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'checked', 'defects', 'artifacts_written'],
}

const STYLE_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string' },
    check_overlap_exit: { type: 'number' },
    overlap_hits: { type: 'number' },
    check_style_exit: { type: 'number' },
    style_violations: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rule: { type: 'string' },
          location: { type: 'string' },
          before: { type: 'string' },
          after: { type: 'string' },
          fixed: { type: 'boolean' },
        },
        required: ['rule', 'location', 'before', 'fixed'],
      },
    },
    sent_back_to_writer: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          location: { type: 'string' },
          defect: { type: 'string' },
          why_not_fixed_here: { type: 'string' },
        },
        required: ['location', 'defect', 'why_not_fixed_here'],
      },
    },
    word_counts: { type: 'object', additionalProperties: true },
    artifacts_written: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'check_overlap_exit', 'check_style_exit', 'style_violations', 'artifacts_written'],
}

const GATE_SCHEMA = {
  type: 'object',
  properties: {
    gate: { type: 'number' },
    round: { type: 'number' },
    verdict: { type: 'string' },
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          agent: { type: 'string' },
          artifact: { type: 'string' },
          defect: { type: 'string' },
          required_fix: { type: 'string' },
        },
        required: ['agent', 'artifact', 'defect', 'required_fix'],
      },
    },
    accepted: { type: 'array', items: { type: 'string' } },
    rules_checked: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rule: { type: 'string' },
          passed: { type: 'boolean' },
          evidence: { type: 'string' },
        },
        required: ['rule', 'passed', 'evidence'],
      },
    },
    open_items: { type: 'array', items: { type: 'string' } },
    artifacts_written: { type: 'array', items: { type: 'string' } },
  },
  required: ['gate', 'round', 'verdict', 'defects', 'accepted', 'rules_checked', 'artifacts_written'],
}

// ---------------------------------------------------------------- prompt builders

function defectBlock(defects) {
  if (!defects || !defects.length) return ''
  return `
THE TEAM LEAD REJECTED YOUR PREVIOUS ARTIFACT. Fix exactly these defects and nothing else. Do not
re-do accepted work and do not rewrite what was not named here:
${JSON.stringify(defects, null, 2)}
`
}

function codeAnalystPrompt(defects) {
  const reuse = EVIDENCE_MODE === 'reuse'
  return `You are the code-analyst for Article 2. You produce every number the manuscript will quote,
each one traceable to a table, a column and a filter.
${PROJECT_PATHS}
${reuse ? `
MODE: REUSE. The work below was already done and verified in this repository on 2026-09-19. Your
job is to VERIFY and CARRY FORWARD, not to recompute:
  - ${A2}/${PHASE2_DIR}/01_numbers.json and .md already exist. Read them first.
  - tables/A2_T0..A2_T8 already exist and reproduce: re-running
    \`python analysis/article2_generalizability.py --date-tag 260905 --out-dir <scratch>\`
    gives six byte-identical tables and three differing only at machine epsilon (< 1.4e-20).
  - All 18 panels exist in PDF, SVG and PNG under figures/panels_260917/.
  - The Shambhala rename is already applied and recorded in A2_T0 (84 keys, 78 of 79 numeric
    columns identical, only compute_time_s differing).
Do this:
  1. Re-run the analysis script into a scratch directory and confirm the assertions still hold:
     2,234 rows, 31 methods, 14 strategies, 3 imputations, 84 rows named 20_shambhala, no raw
     shambhala_ P/Q names. Report the actual counts you observed.
  2. Read 01_numbers.json, check each entry's table/column/filter against the table on disk, and
     correct any entry that does not resolve. Run
     \`python tools/audit_numbers.py\` against tables/ for anything you are unsure of.
  3. Confirm the 18-panel inventory with the §8 verification command 2.
  4. Copy the verified object to ${A2}/${RUN_DIR}/01_numbers.json and .md.
Do NOT regenerate or execute the notebooks. They were regenerated and executed on 2026-09-19 and
all three run with the errors recorded in §11 of the plan.
` : `
MODE: RECOMPUTE. Work through §6.2 agent 2's five tasks in order, writing an artifact checkpoint
after each one. Stop and report if any hand-written notebook cell cannot be cleanly extracted --
do not regenerate over it.
`}
WHAT TO READ TO LEARN (method and convention only; every number is recomputed):
  ${REPO}/harmonization-metrics-calculation/compute_batch_metrics.py -- groups L, M and N, for what
    each metric computes and what its docstring warns about.
  ${REPO}/harmonization-metrics/create_correlation_prediction_notebook.py -- the 01_raw baseline join.
  ${REPO}/figures_for_article/Finally_assembled_figures_for_article.ipynb cells 1 and 4 -- the
    palettes, TOP_IDS and both harshness maps. Palettes are imported, never re-derived.
  ${REPO}/figures_for_article/CLAUDE.md -- the snapshot rules.
  §1.3 to §1.5 of the plan -- the numbers you must reproduce.

CRITERIA YOU APPLY:
  - No number is retyped from the source document. Every one comes from
    metrics_comprehensive_260905.csv, Supplementary File 3.csv.gz or prediction_folds_long.csv.
  - Any disagreement with the source document is reported as a discrepancy carrying BOTH values and
    the filter that produced each. Discrepancies reach the manuscript text -- write them in a form
    the writer can quote directly. Never silently correct one.
  - The assertions are not relaxed to make a count fit. A result of 2,150 means the Shambhala
    rename was skipped; that is a bug in the code, not in the definition.
  - Rule 7b: every prediction number is reported in both fold cuts.
${defectBlock(defects)}
${FABRICATION}
${ARTIFACT_DISCIPLINE}
${HARD_RULES}

WRITE BEFORE RETURNING:
  ${A2}/${RUN_DIR}/01_numbers.json
  ${A2}/${RUN_DIR}/01_numbers.md
Then return the structured object.`
}

function literatureScoutPrompt(defects) {
  const reuse = EVIDENCE_MODE === 'reuse'
  return `You are the literature-scout for Article 2. You produce the citation landscape and the gap
statement the Introduction will claim.
${PROJECT_PATHS}
${reuse ? `
MODE: REUSE. ${A2}/${PHASE3_DIR}/02_literature.json and .md already exist, produced 2026-09-19 with
${A2}/tools/fetch_literature.py. Read them first, then:
  1. Spot-check at least 8 entries by re-resolving the PMID and confirming the quoted passage is in
     the paper you think it is. A known failure mode is recorded in §11 issue 15: NCBI elink
     returns pubmed_pmc_refs (the articles that CITE the query) before pubmed_pmc, which silently
     attributes quotes to the wrong paper. Match the linkname explicitly and read the retrieved
     TITLE before trusting an id.
  2. Two entries are quoted from their abstracts because no open-access full text exists. Confirm
     they are still labelled as such.
  3. The overfitting and degenerate-fold sweep is thin (§11 issue 16): only Varma & Simon 2006 and
     Nygaard 2016 are on point and openable in PubMed. If the Discussion needs more, reopen that
     sweep against JMLR and ACM, which are not in PubMed. Report what you added.
  4. Copy the verified object to ${A2}/${RUN_DIR}/02_literature.json and .md.
` : `
MODE: RECOMPUTE. Sweep all six themes below from scratch, appending to the artifact after each
thematic block so a token-limit kill loses at most one block.
`}
THE READING LIST, as Daniil specified it:
  1. Bulk transcriptomic batch correction, emphasis on CROSS-PLATFORM harmonization: what each
     benchmark used as its criterion, and whether any of them asked whether criteria agree.
  2. The three Borisov reviews cited in Article 1 (§2.4 of the plan), read IN FULL, not by
     abstract. They are the field's own statement of the harmonization problem and Article 2 must
     position against them. §3 of the 2022 review, "Evaluation of the Quality of Harmonization",
     is the anchor for Article 2's thesis.
  3. Model training and overfitting: leave-one-group-out validation, batch-confounded labels,
     degenerate folds, metric gaming. This is the theoretical backing for §1.5d and for trap 3 in
     the recipe figure, and the reason both fold cuts are reported together.
  4. The single-cell integration benchmark literature that supplied kBET, LISI, ASW, graph
     connectivity and the scIB composite -- with the point that those metrics were designed for a
     different problem.
  5. FL/DLBCL transcriptomic subtyping, for the biology the marker panel encodes.
  6. Daniil's own on-topic works from ORCID 0000-0003-1029-1174 (§2.4), cited where a
     signature-transfer claim needs them and nowhere else.

CRITERIA YOU APPLY:
  - A paper you cannot open is not a citation. No recalled titles, no reconstructed DOIs.
  - Every entry carries a verbatim quote from the FULL TEXT, not the abstract, wherever the full
    text is reachable, with the section it came from named. Set full_text_read accordingly.
  - The gap statement is a statement about what has NOT been done, phrased so the Introduction can
    claim it without overclaiming.
  - Target 25 to 40 candidate references.
${defectBlock(defects)}
${FABRICATION}
${ARTIFACT_DISCIPLINE}
${HARD_RULES}

WRITE BEFORE RETURNING:
  ${A2}/${RUN_DIR}/02_literature.json
  ${A2}/${RUN_DIR}/02_literature.md
Then return the structured object.`
}

function writerPrompt(numbers, literature, defects) {
  return `You are the writer for Article 2. You produce the full manuscript.
${PROJECT_PATHS}
THE NUMBERS (every one already traced to a table, a column and a filter -- quote these, do not
recompute and do not round further than the entry does):
${JSON.stringify(numbers).slice(0, 90000)}

THE LITERATURE (every entry already resolved to a live PMID with a quoted passage):
${JSON.stringify(literature).slice(0, 60000)}

WHAT TO READ TO LEARN:
  §3 of the plan -- the target shape, the section budgets, the eight Results sub-sections and the
    figure inventory. Follow it.
  The source document v2 -- the narrative Article 2 extends.
  Article 1 -- read it ONCE, in full, for the explicit purpose of not reproducing it, then write
    without it open.
  ${A2}/manuscript/figure_legends_260917.md IF IT EXISTS. It does not exist yet, and writing it is
    yours: every legend plus its alt text, for the renumbered Figures 1-6 and the Supplementary
    Figures. Write it alongside the draft, not after it.

CRITERIA YOU APPLY:
  - First-person plural, active voice: "We computed...", "We gated...".
  - One claim per sentence, each with its number and its figure panel.
  - No adjective carries an argument. No "significantly" without a p value.
  - NO PROOFLESS ADJECTIVE. If the text says "comprehensive", the adjacent clause states what makes
    it comprehensive -- the count, the coverage, the comparison. Same for "novel", "robust",
    "extensive", "substantial". An adjective that cannot be justified next to itself is deleted,
    not softened.
  - Abbreviations defined at first use, then used.
  - Limitations stated where they arise, not deferred to a limitations paragraph.
  - The discrepancies array from 01_numbers.json is written INTO THE TEXT, not into a footnote.
  - Rule 7b: both fold cuts side by side, in every table and wherever a prediction number appears.
  - The one sentence on Shambhala's two names belongs in Methods.
${defectBlock(defects)}
${FABRICATION}
${ARTIFACT_DISCIPLINE}
${HARD_RULES}

WRITE BEFORE RETURNING, section by section, so a kill loses one section and not the manuscript:
  ${A2}/${RUN_DIR}/03_draft.md
  ${A2}/manuscript/FL_metric_classes_F1000_260917.md   (the same content, at its final path)
  ${A2}/manuscript/figure_legends_260917.md
Then convert the manuscript to Word WITHOUT WAITING FOR APPROVAL -- from the moment it exists the
.docx is the main state and Daniil comments in it:
  ${A2}/manuscript/FL_metric_classes_F1000_260917.docx
Then return the full markdown of the draft as your text.`
}

function referenceVerifierPrompt(draftMd, literature, defects) {
  return `You are the reference-verifier for Article 2. You re-resolve every citation independently.
${PROJECT_PATHS}
THE DRAFT TO CHECK:
${String(draftMd).slice(0, 120000)}

WHAT THE LITERATURE-SCOUT CLAIMED (you verify this; you do not inherit it):
${JSON.stringify(literature).slice(0, 50000)}

THREE CHECKS PER CITATION, each performed independently:
  1. The paper exists and is reachable.
  2. The PMID and the DOI are right.
  3. It supports THE SPECIFIC SENTENCE THAT CITES IT -- judged against the passage in the body of
     the paper, not against the abstract.

Every failure is REPORTED, never patched. A citation that does not support its sentence is a defect
sent back to the writer; you do not swap in a different reference.

Known trap, recorded in §11 issue 15 of the plan: NCBI elink returns several PMC link sets and
pubmed_pmc_refs (the articles that CITE the query) comes first. Match the pubmed_pmc linkname
explicitly and read the retrieved title before trusting an id.

WRITE TWO FILES, because the supporting evidence lives apart from the manuscript. PMIDs appear in
the main manuscript; the quoted evidence appears only in the support document.

  ${A2}/manuscript/references_260917.md -- the reference list, one block per entry,
  Mendeley-paste ready, in this exact form:

    [12] Tran HTN, Ang KS, Chevrier M, et al. A benchmark of batch-effect correction methods for
         single-cell RNA sequencing data. Genome Biol. 2020;21(1):12.
         PMID: 31948481

  ${A2}/manuscript/reference_support_260917.md -- for each citation, which part of the cited
  article supports which part of the Article 2 text, quoted, with its section named:

    [12] Tran HTN et al., Genome Biol 2020;21(1):12
         Cited at: Introduction para 3 -- "benchmarks of integration methods have ranked..."
         Supporting passage (Results, "Overall performance"): "<verbatim quote>"
         Verdict: SUPPORTS -- verified against the full text, not the abstract
${defectBlock(defects)}
${FABRICATION}
${ARTIFACT_DISCIPLINE}
${HARD_RULES}

ALSO WRITE BEFORE RETURNING, appending per reference:
  ${A2}/${RUN_DIR}/04_references_verified.md
Then return the structured object.`
}

function styleEditorPrompt(draftMd, defects) {
  return `You are the style-editor for Article 2. Mechanical gates first, then the manual pass.
${PROJECT_PATHS}
THE DRAFT:
${String(draftMd).slice(0, 120000)}

RUN THE GATES FIRST, from ${A2}, and record the exit codes:
  source ~/venvs/collagen_3_11/bin/activate
  python tools/check_overlap.py manuscript/FL_metric_classes_F1000_260917.md \\
      --against ${REPO}/figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx \\
      --against manuscript_versions/Harmonization_metrics_extended_260802_v2.docx --ngram 8
  python tools/check_style.py manuscript/FL_metric_classes_F1000_260917.md --journal f1000
  grep -nEi "rather than|, not [a-z]+\\.|it is not .*, it is" manuscript/*.md

check_overlap must report zero hits outside tools/overlap_allow.txt. check_style must exit 0. The
grep must print nothing.

THEN THE MANUAL PASS, for the LLM register no regex catches. The banned list:
  - "rather than" -- named by Daniil as Claude AI-slop. Most of the time the contrast is not needed
    at all: "The metrics were recalculated with the python scripts in the repository." is
    sufficient, and adding "instead of taking them from the source article" makes it worse. Delete
    the contrast unless it carries information; if it genuinely does, write it as a full clause.
  - The bare antithesis -- "derived, not guessed", "it is not X, it is Y", "X, not Y". Daniil's
    words: these look stupid to readers and reviewers. State the positive claim on its own.
  - Proofless adjectives -- comprehensive, novel, robust, extensive, substantial, powerful,
    state-of-the-art -- deleted unless the adjacent clause states the measurement that justifies
    them.
  - delve into, underscores, leverage, seamless, pivotal, landscape, testament to, crucial,
    stands as, in the realm of, it is important to note, plays a vital role, navigating the
    complexities, tricolon padding, Furthermore/Moreover/Additionally chains, unearned em-dashes,
    hedge stacks ("may potentially help to"), empty intensifiers used without a number, and
    "novel" applied to this work by this work.

YOUR LIMIT: you may edit prose directly. You may NOT change a number, a citation or a claim. Those
go back to the writer as entries in sent_back_to_writer, with the reason.
${defectBlock(defects)}
${FABRICATION}
${ARTIFACT_DISCIPLINE}
${HARD_RULES}

WRITE BEFORE RETURNING:
  ${A2}/${RUN_DIR}/04_style_report.json
  ${A2}/${RUN_DIR}/04_style_report.md
  and the edited draft, in place, at ${A2}/manuscript/FL_metric_classes_F1000_260917.md
  and, in the same pass, ${A2}/manuscript/FL_metric_classes_F1000_260917.docx brought back into
  agreement with it -- PLAIN edits with python-docx, never tracked changes (rule 12). Verify with
  \`python -c "import zipfile;d=zipfile.ZipFile(P).read('word/document.xml').decode();print(d.count('<w:ins '),d.count('<w:del '))"\`
  that both counts are 0 before you return.
Then return the structured object.`
}

function teamleadPrompt(gate, round, payload) {
  const isDelivery = gate === 4
  const gateBody = {
    1: `GATE 1 -- are the numbers real and is the gap defensible?
Judge 01_numbers.json and 02_literature.json. Accept an artifact by name, or list its defects.
  - Re-derive a sample of the numbers yourself with
    \`python tools/audit_numbers.py\` against tables/, and by reading the CSV directly. Do not
    trust a number because the code-analyst asserted it.
  - Re-resolve a RANDOM 20% of the literature-scout's PMIDs yourself and confirm the quoted
    passage is in the paper named. Say which ones you checked.
  - Confirm the analysis set is 2,234 rows over 31 methods with 84 rows named 20_shambhala.
  - Confirm every prediction number carries both fold cuts.`,
    2: `GATE 2 -- does every claim in the draft trace to an artifact?
  - Every number in the draft resolves to a row in a table in tables/. Run
    \`python tools/audit_numbers.py manuscript/FL_metric_classes_F1000_260917.md --tables tables/\`
    and read the unsourced list.
  - Every citation has a PMID or an explicit [TO CONFIRM].
  - The overlap gate passes with zero 8-gram hits against Article 1 and the source document.
  - The discrepancies from 01_numbers.json appear in the body text, not in a footnote.
  - Methods has four to six subsections and is SHORTER than Article 1's.`,
    3: `GATE 3 -- accept the reviewed manuscript, or send it back with a specific defect list.
  - The reference-verifier's defect list is empty, or every entry has been fixed by the writer.
  - Re-resolve a RANDOM 20% of the verifier's own confirmations. The verifier is not trusted
    either. Name the ones you re-resolved.
  - check_style.py exits 0 and check_overlap.py reports zero hits outside the allow list.
  - The style-editor changed no number, no citation and no claim: diff its edit against the draft
    it received and confirm this.`,
    4: `DELIVERY -- final assembly.
  - Build the provenance table: every number in the finished manuscript mapped to its table,
    column and filter, and every citation to its PMID and the passage that supports it.
  - Build the open-items list: every [TO CONFIRM], every defect that survived two rounds, and
    every decision that belongs to Daniil. Nothing is silently dropped and nothing is quietly
    fixed by you writing the text yourself.
  - State explicitly that no Figma frame was modified by this workflow (rule 8). Figma assembly is
    a separate interactive step; if a before/after Page 2 geometry snapshot exists in the run
    folder, diff it and report. If none exists, say so -- do not claim a check you did not run.`,
  }[gate]

  return `You are the team lead for Article 2. You gate, you do not write the manuscript.
${PROJECT_PATHS}
${gateBody}

THE ARTIFACTS TO JUDGE (round ${round} of at most ${MAX_ROUNDS}):
${JSON.stringify(payload).slice(0, 110000)}

THE FIVE RULES YOU ENFORCE AND CANNOT WAIVE:
  1. Every number in the manuscript resolves to a row in a table in tables/.
  2. Every citation has a PMID or an explicit [TO CONFIRM], and 20% of them re-resolve.
  3. The overlap gate passes with zero 8-gram hits outside tools/overlap_allow.txt.
  4. check_style.py exits 0.
  5. No Figma frame was modified beyond the §3.4 renaming.

Record each of the five in rules_checked with the evidence you actually obtained. A rule you could
not check is passed:false with the reason as its evidence -- never passed:true by assumption.

YOUR OUTPUT IS A VERDICT, NOT PROSE. verdict is "accept" or "revise". Each defect names the agent
that must fix it, the artifact, what is wrong, and the required fix. ${isDelivery
  ? 'At delivery there is no revision round: everything unresolved becomes an open item.'
  : `This is round ${round}. After ${MAX_ROUNDS} rounds a surviving defect becomes an open item for Daniil and the workflow proceeds; you never fix it by writing the text yourself.`}
${FABRICATION}
${ARTIFACT_DISCIPLINE}
${HARD_RULES}

WRITE BEFORE RETURNING:
${isDelivery
  ? `  ${A2}/${RUN_DIR}/06_provenance.md
  ${A2}/${RUN_DIR}/06_open_items.md
  ${A2}/${RUN_DIR}/05_teamlead_gate4.json`
  : `  ${A2}/${RUN_DIR}/05_teamlead_gate${gate}.json
  ${A2}/${RUN_DIR}/05_teamlead_gate${gate}.md`}
Then return the structured object.`
}

// ---------------------------------------------------------------- gate driver

// Runs one gate and, while the verdict is "revise" and rounds remain, re-runs only the agents the
// team lead named. Returns the last verdict together with whatever the re-runs produced, so the
// caller keeps the newest artifacts even when the gate never reached "accept".
async function gateLoop(gateNo, phaseTitle, initialPayload, redo) {
  let payload = initialPayload
  let verdict = null
  for (let round = 1; round <= MAX_ROUNDS; round++) {
    verdict = await agent(teamleadPrompt(gateNo, round, payload), {
      label: `teamlead:gate${gateNo}:r${round}`,
      phase: phaseTitle,
      schema: GATE_SCHEMA,
    })
    if (!verdict) {
      log(`Gate ${gateNo} round ${round}: the team lead returned nothing — proceeding with the unjudged artifacts.`)
      return { verdict: null, payload }
    }
    if (verdict.verdict === 'accept' || !verdict.defects.length) {
      log(`Gate ${gateNo} accepted at round ${round}.`)
      return { verdict, payload }
    }
    if (round === MAX_ROUNDS) {
      log(`Gate ${gateNo} still has ${verdict.defects.length} defect(s) after ${MAX_ROUNDS} rounds — they become open items for Daniil and the run continues.`)
      return { verdict, payload }
    }
    log(`Gate ${gateNo} round ${round}: revise — ${verdict.defects.length} defect(s), re-running the named agents.`)
    payload = await redo(verdict.defects, payload, round)
  }
  return { verdict, payload }
}

const defectsFor = (defects, who) => defects.filter(d => d.agent === who)

// ---------------------------------------------------------------- run

log(`Article 2 / F1000 — phases: ${PHASES.join(', ')} | run folder: ${RUN_DIR} | evidence mode: ${EVIDENCE_MODE}`)

let numbers = null
let literature = null
let gate1 = null
let draft = null
let gate2 = null
let references = null
let style = null
let gate3 = null
let delivery = null

if (wants('evidence')) {
  phase('Evidence')

  // A barrier is correct here: gate 1 judges both artifacts together and the writer needs both.
  const pair = await parallel([
    () => agent(codeAnalystPrompt(null), { label: 'code-analyst', phase: 'Evidence', schema: NUMBERS_SCHEMA }),
    () => agent(literatureScoutPrompt(null), { label: 'literature-scout', phase: 'Evidence', schema: LITERATURE_SCHEMA }),
  ])
  numbers = pair[0]
  literature = pair[1]

  if (!numbers || !literature) {
    log(`Evidence incomplete — numbers: ${numbers ? 'ok' : 'missing'}, literature: ${literature ? 'ok' : 'missing'}. Stopping before the draft.`)
    return { phases: PHASES, runDir: RUN_DIR, numbers, literature, stopped_at: 'evidence' }
  }
  log(`Evidence done: ${numbers.numbers.length} numbers (${numbers.discrepancies.length} discrepancies), ${literature.references.length} references over ${literature.themes_covered.length} themes.`)

  const g1 = await gateLoop(1, 'Evidence', { numbers, literature }, async (defects, prev) => {
    const nDef = defectsFor(defects, 'code-analyst')
    const lDef = defectsFor(defects, 'literature-scout')
    const redone = await parallel([
      () => nDef.length
        ? agent(codeAnalystPrompt(nDef), { label: 'code-analyst:revise', phase: 'Evidence', schema: NUMBERS_SCHEMA })
        : Promise.resolve(prev.numbers),
      () => lDef.length
        ? agent(literatureScoutPrompt(lDef), { label: 'literature-scout:revise', phase: 'Evidence', schema: LITERATURE_SCHEMA })
        : Promise.resolve(prev.literature),
    ])
    numbers = redone[0] || prev.numbers
    literature = redone[1] || prev.literature
    return { numbers, literature }
  })
  gate1 = g1.verdict
}

if (wants('draft')) {
  phase('Draft')
  if (!numbers || !literature) {
    log('Draft phase requested without evidence in this run — the writer reads 01_numbers.json and 02_literature.json from the run folder itself.')
  }
  draft = await agent(writerPrompt(numbers || { note: `read ${RUN_DIR}/01_numbers.json` },
                                   literature || { note: `read ${RUN_DIR}/02_literature.json` }, null),
    { label: 'writer', phase: 'Draft' })

  if (!draft) {
    log('The writer produced nothing — stopping before review.')
    return { phases: PHASES, runDir: RUN_DIR, numbers, literature, gate1, draft: null, stopped_at: 'draft' }
  }
  log(`Draft done: ${String(draft).split(/\s+/).length} words in 03_draft.md.`)

  const g2 = await gateLoop(2, 'Draft', { draft: String(draft).slice(0, 80000), numbers }, async (defects, prev) => {
    const wDef = defectsFor(defects, 'writer')
    if (!wDef.length) return prev
    const redone = await agent(writerPrompt(numbers, literature, wDef), { label: 'writer:revise', phase: 'Draft' })
    draft = redone || draft
    return { draft: String(draft).slice(0, 80000), numbers }
  })
  gate2 = g2.verdict
}

if (wants('review')) {
  phase('Review')
  const draftForReview = draft || `[read ${RUN_DIR}/03_draft.md and manuscript/FL_metric_classes_F1000_260917.md from disk]`

  // A barrier is correct here too: gate 3 weighs the reference defects and the style report
  // against each other, and the style-editor's edits must not race the verifier's reading.
  const pair = await parallel([
    () => agent(referenceVerifierPrompt(draftForReview, literature || { note: `read ${RUN_DIR}/02_literature.json` }, null),
      { label: 'reference-verifier', phase: 'Review', schema: REFERENCE_SCHEMA }),
    () => agent(styleEditorPrompt(draftForReview, null),
      { label: 'style-editor', phase: 'Review', schema: STYLE_SCHEMA }),
  ])
  references = pair[0]
  style = pair[1]
  log(`Review done: ${references ? references.defects.length : '?'} citation defect(s), ${style ? style.style_violations.length : '?'} style violation(s).`)

  const g3 = await gateLoop(3, 'Review', { references, style, draft: String(draftForReview).slice(0, 60000) },
    async (defects, prev) => {
      const rDef = defectsFor(defects, 'reference-verifier')
      const sDef = defectsFor(defects, 'style-editor')
      const wDef = defectsFor(defects, 'writer')
      if (wDef.length) {
        const redone = await agent(writerPrompt(numbers, literature, wDef), { label: 'writer:revise2', phase: 'Review' })
        draft = redone || draft
      }
      const redone = await parallel([
        () => rDef.length
          ? agent(referenceVerifierPrompt(draft || prev.draft, literature, rDef), { label: 'reference-verifier:revise', phase: 'Review', schema: REFERENCE_SCHEMA })
          : Promise.resolve(prev.references),
        () => sDef.length
          ? agent(styleEditorPrompt(draft || prev.draft, sDef), { label: 'style-editor:revise', phase: 'Review', schema: STYLE_SCHEMA })
          : Promise.resolve(prev.style),
      ])
      references = redone[0] || prev.references
      style = redone[1] || prev.style
      return { references, style, draft: String(draft || prev.draft).slice(0, 60000) }
    })
  gate3 = g3.verdict
}

if (wants('delivery')) {
  phase('Delivery')
  delivery = await agent(teamleadPrompt(4, 1, { numbers, literature, references, style, gate1, gate2, gate3 }),
    { label: 'teamlead:delivery', phase: 'Delivery', schema: GATE_SCHEMA })
  log(delivery
    ? `Delivery done: ${delivery.open_items.length} open item(s) for Daniil.`
    : 'Delivery agent returned nothing — 06_provenance.md and 06_open_items.md may be missing.')
}

return {
  phases: PHASES,
  runDir: RUN_DIR,
  evidenceMode: EVIDENCE_MODE,
  numbers,
  literature,
  gate1,
  draft_words: draft ? String(draft).split(/\s+/).length : null,
  gate2,
  references,
  style,
  gate3,
  delivery,
}
