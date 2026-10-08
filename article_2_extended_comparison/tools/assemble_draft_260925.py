#!/usr/bin/env python
"""Assemble the three Phase 3 drafts into the revised master and check the gate-3 rules.

Inputs, all in `workflow_runs/260924_run1/`:

* `00_paragraph_index.json` — the base .docx, paragraph by paragraph (`P0`…`P177`), with
  every Mendeley citation as a `⟦CIT:…⟧` token;
* `03a_draft_reviewed.md`, `03b_draft_unreviewed.md`, `08_legends.md` — the writers'
  blocks, `### P<n>[+k] [keep|edit|delete|insert]`, each followed by its text;
* `10_stat_requests_*.json` — the writers' open requests.

Outputs:

* `manuscript/FL_metric_classes_F1000_260925.md` — the revised text in reading order,
  citation tokens rendered as their plain text, provenance comments stripped;
* `workflow_runs/260924_run1/03_revision_edits.json` — one record per base paragraph and
  per insert, with the action and the tokenised text, which Phase 5 turns into tracked
  changes against the base .docx;
* a gate report printed and written to `03_assembly_report.md`.

Gate checks (rules 14, 16, 19 and the brief's paragraph discipline): a paragraph owned by
two drafts; an edited paragraph whose CIT token sequence differs from the base; a deleted
paragraph that held a citation; the total of 46 CIT tokens and the four numeric brackets;
unknown `[FIG:…]` tokens; surviving `[STAT: …]` markers; more than five main tables.

    python tools/assemble_draft_260925.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "workflow_runs/260924_run1"
DRAFTS = ["03a_draft_reviewed.md", "03b_draft_unreviewed.md", "08_legends.md"]
OUT_MD = ROOT / "manuscript/FL_metric_classes_F1000_260925.md"
OUT_JSON = RUN / "03_revision_edits.json"
REPORT = RUN / "03_assembly_report.md"

FIG_TOKENS = {"fig_markers_lm", "fig_prediction_n", "fig_election", "sfig_harshness",
              "sfig_lmn_scatter", "sfig_metric_clustermap", "sfig_expression",
              "sfig_pca", "sfig_marker_qc", "sfig_gene_method"}
NUMERIC_CITES = ["[38]", "[50,51]", "[52]"]
HEADING = {"Heading1": "## ", "Heading2": "### ", "Heading3": "#### "}

BLOCK_RE = re.compile(r"^### (P\d+)(?:\+(\d+))?\s*\[(keep|edit|delete|insert)\]\s*$")
CIT_RE = re.compile(r"⟦CIT:(.*?)⟧")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def parse_draft(path: Path) -> list[dict]:
    """Blocks of one draft, in file order; text runs to the next block or `## ` heading."""
    blocks, cur = [], None
    for line in path.read_text().splitlines():
        m = BLOCK_RE.match(line.strip())
        if m:
            cur = {"pid": m.group(1), "k": int(m.group(2) or 0), "action": m.group(3),
                   "lines": [], "source": path.name}
            blocks.append(cur)
            continue
        if line.startswith("## ") and cur is not None:
            cur = None  # a trailing section (Change log, Status) ends the last block
            continue
        if cur is not None:
            cur["lines"].append(line)
    for b in blocks:
        raw = "\n".join(b.pop("lines")).strip()
        b["raw"] = raw
        # Removing an inline provenance comment leaves two spaces behind it.
        b["text"] = re.sub(r"(?<=\S) {2,}(?=\S)", " ", COMMENT_RE.sub("", raw)).strip()
    return blocks


def plain(text: str) -> str:
    return CIT_RE.sub(lambda m: m.group(1), text)


def main() -> int:
    base = json.loads((RUN / "00_paragraph_index.json").read_text())
    by_id = {p["id"]: p for p in base}
    problems, notes = [], []
    edits: dict[str, dict] = {}
    inserts: dict[str, list[dict]] = {}
    for name in DRAFTS:
        path = RUN / name
        if not path.exists():
            problems.append(f"missing draft {name}")
            continue
        for b in parse_draft(path):
            if b["pid"] not in by_id:
                problems.append(f"{name}: unknown paragraph {b['pid']}")
                continue
            if b["action"] == "insert":
                inserts.setdefault(b["pid"], []).append(b)
                continue
            if b["pid"] in edits:
                problems.append(f"{b['pid']} claimed by {edits[b['pid']]['source']} "
                                f"and {name}")
            edits[b["pid"]] = b

    records, out_lines = [], []
    for p in base:
        b = edits.get(p["id"], {"action": "keep", "text": "", "source": ""})
        base_cits = CIT_RE.findall(p["text"])
        if b["action"] == "edit":
            new_cits = CIT_RE.findall(b["text"])
            if new_cits != base_cits:
                problems.append(f"{p['id']}: CIT tokens changed {base_cits} -> {new_cits}")
            text = b["text"]
        elif b["action"] == "delete":
            if base_cits:
                problems.append(f"{p['id']}: deleted a paragraph holding {base_cits}")
            text = None
        else:
            text = p["text"]
        records.append({"id": p["id"], "action": b["action"], "source": b["source"],
                        "style": p["style"], "base": p["text"], "new": text})
        if text is not None:
            prefix = HEADING.get(p["style"], "")
            out_lines += [prefix + plain(text), ""]
        for k, ins in enumerate(sorted(inserts.get(p["id"], []), key=lambda x: x["k"])):
            if CIT_RE.search(ins["text"]):
                notes.append(f"{p['id']}+{ins['k']}: an insert carries a CIT token — it "
                             "must be one moved from a deleted paragraph")
            records.append({"id": f"{p['id']}+{ins['k']}", "action": "insert",
                            "source": ins["source"], "style": "", "base": None,
                            "new": ins["text"]})
            out_lines += [plain(ins["text"]), ""]

    body = "\n".join(out_lines)
    all_new = "\n".join(r["new"] for r in records if r["new"])
    n_cit = len(CIT_RE.findall(all_new))
    if n_cit != 46:
        problems.append(f"{n_cit} CIT tokens in the revision, the invariant is 46")
    for c in NUMERIC_CITES:
        want = 2 if c == "[38]" else 1
        got = all_new.count(c)
        if got != want:
            problems.append(f"numeric citation {c}: {got} occurrences, expected {want}")
    bad_fig = sorted(set(re.findall(r"\[FIG:([a-z_]+)\]", all_new)) - FIG_TOKENS)
    if bad_fig:
        problems.append(f"unknown figure tokens {bad_fig}")
    stat_markers = re.findall(r"\[STAT:\s*([^\]]+)\]", all_new)
    main_tables = sorted(set(re.findall(r"\*\*Table (\d)\.", all_new)))
    if len(main_tables) > 5:
        problems.append(f"{len(main_tables)} main tables {main_tables}, the budget is 5")
    requests = []
    for f in sorted(RUN.glob("10_stat_requests_*.json")):
        requests += json.loads(f.read_text() or "[]")
    open_req = [r for r in requests if r.get("status") == "open"]

    header = ("# FL_metric_classes_F1000: revision round 1 draft (assembled 2026-09-25)\n\n"
              "> Assembled by `tools/assemble_draft_260925.py` from the three Phase 3 "
              "drafts over Daniil's edited .docx; figures, tables and "
              "Supplementary Files renumbered by order of first citation in Phase 5.\n\n---\n\n")
    OUT_MD.write_text(header + body)
    OUT_JSON.write_text(json.dumps(records, indent=1, ensure_ascii=False))
    fig_used = sorted(set(re.findall(r"\[FIG:([a-z_]+)\]", all_new)))
    actions = {a: sum(r["action"] == a for r in records)
               for a in ("keep", "edit", "delete", "insert")}
    lines = ["# 03 — Assembly report (gate 3 mechanics), 2026-09-25", "",
             f"Paragraph actions: {actions}. CIT tokens: {n_cit} (invariant 46). "
             f"Main tables: {main_tables}. Figure tokens used: {fig_used}.", "",
             f"**Open [STAT] markers: {len(stat_markers)}** {stat_markers}", "",
             f"**Open stat requests: {len(open_req)}** "
             f"{[r.get('id') for r in open_req]}", "",
             "## Problems (block gate 3)", ""] + [f"- {x}" for x in problems or ["none"]]
    lines += ["", "## Notes", ""] + [f"- {x}" for x in notes or ["none"]]
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
