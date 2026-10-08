#!/usr/bin/env python
"""Phase 5: renumber figures, tables and Supplementary Files by order of first citation.

Runs after `tools/assemble_draft_260925.py`, on its `03_revision_edits.json`. Plan W2a:
the map is computed ONCE, from the finished text, and applied to every record, to the
supplementary legend order, and (separately) to the Figma frame names.

1. Walk the body records in reading order (legends and headings excluded) and record the
   first citation of every item: `Figure N`, `[FIG:fig_*]` (main), `Supplementary Figure N`,
   `[FIG:sfig_*]` (supplementary), `Table N`, `Supplementary File N`. A Supplementary File
   followed by "of the source benchmark" is Article 1's and is never renumbered.
2. Number each kind 1, 2, 3… in that order.
3. Rewrite every citation span, including the numbers repeated inside a letter list
   ("Supplementary Figures 4C, 4D and 5D", "Figure 1A and 1B"), through placeholders so
   that `Supplementary Figure 1` can never be rewritten inside `Supplementary Figure 10`.
4. Reorder the supplementary figure legends: the longest run already in order stays in
   place; every other legend is deleted at its old position and inserted at its new one.
5. A `[keep]` paragraph whose text the map changes becomes an `[edit]`.

Writes `workflow_runs/260924_run1/03_revision_edits_final.json`, `21_renumber_map.{json,md}`
and the final `manuscript/FL_metric_classes_F1000_260925.md`.

    python tools/assemble_draft_260925.py && python tools/renumber_260925.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assemble_draft_260925 import HEADING, OUT_MD, RUN, plain  # noqa: E402

EDITS = RUN / "03_revision_edits.json"
FINAL = RUN / "03_revision_edits_final.json"
MAP_JSON, MAP_MD = RUN / "21_renumber_map.json", RUN / "21_renumber_map.md"

LETTERS = r"[A-L](?![a-z])"
SEP = r"(?:\s*(?:,|and|to|–|-)\s*)"
# One citation span: the label, a number or token, then any letter list, where a list item
# may repeat a number ("4C, 4D"). Plural forms ("Supplementary Figures 4 to 6") included.
SPAN = re.compile(
    r"(?P<label>Supplementary Figures?|Supplementary Files?|(?<!Supplementary )Figures?|"
    r"Tables?)\s(?P<first>\d+)(?P<rest>(?:" + LETTERS + r")?(?:" + SEP +
    r"(?:\d+" + LETTERS + r"?|" + LETTERS + r"))*)"
    r"(?P<source> of the source benchmark)?")
TOKEN = re.compile(r"\[FIG:(\w+)\]")
LEGEND = re.compile(r"^\s*\*{0,2}(?:\[FIG:(\w+)\]|(Supplementary Figure|Figure|Table) "
                    r"(\d+))[.*\s]")


def kind_of(label: str) -> str:
    return {"Supplementary Figure": "sfig", "Supplementary File": "file",
            "Figure": "fig", "Table": "table"}[label.rstrip("s") if label != "Tables"
                                              else "Table"]


def is_legend(rec) -> bool:
    return bool(rec["new"]) and bool(LEGEND.match(rec["new"])) and rec["style"] == "" or (
        bool(rec["new"]) and bool(LEGEND.match(rec["new"])) and "Heading" not in
        rec["style"] and len(rec["new"]) > 60 and rec["new"].lstrip("*").startswith(
            ("Figure", "Supplementary Figure", "[FIG:", "Table")))


def first_citations(records) -> dict[str, list[str]]:
    """Old keys per kind, in order of first citation in the body."""
    order = {"fig": [], "sfig": [], "table": [], "file": []}
    for r in records:
        if not r["new"] or is_legend(r) or "Heading" in r["style"]:
            continue
        text = re.sub(r"<!--.*?-->", "", r["new"], flags=re.S)
        items = []
        for m in TOKEN.finditer(text):
            items.append((m.start(), "fig" if m.group(1).startswith("fig_") else "sfig",
                          f"[FIG:{m.group(1)}]"))
        for m in SPAN.finditer(text):
            if m.group("source"):
                continue
            k = kind_of(m.group("label"))
            nums = [m.group("first")] + re.findall(r"(\d+)", m.group("rest"))
            for n in nums:
                items.append((m.start(), k, n))
        for _, k, key in sorted(items, key=lambda x: x[0]):
            if key not in order[k]:
                order[k].append(key)
    return order


def build_map(order) -> dict[str, dict[str, int]]:
    return {k: {key: i + 1 for i, key in enumerate(keys)} for k, keys in order.items()}


def apply_map(text: str, nmap) -> str:
    """Rewrite every citation span and token through placeholders (no prefix collisions)."""
    if not text:
        return text

    def tok(m):
        name = m.group(1)
        k = "fig" if name.startswith("fig_") else "sfig"
        label = "Figure" if k == "fig" else "Supplementary Figure"
        return f"{label} \x00{k}:{nmap[k][f'[FIG:{name}]']}\x00"

    text = TOKEN.sub(tok, text)

    def span(m):
        if m.group("source"):
            return m.group(0)
        k = kind_of(m.group("label"))
        head = f"{m.group('label')} \x00{k}:{nmap[k].get(m.group('first'), m.group('first'))}\x00"
        rest = re.sub(r"(\d+)", lambda n: f"\x00{k}:{nmap[k].get(n.group(1), n.group(1))}"
                      "\x00", m.group("rest"))
        return head + rest

    text = SPAN.sub(span, text)
    return re.sub(r"\x00\w+:(\d+)\x00", r"\1", text)


def legend_number(rec, nmap):
    """(kind, final number) of a legend record, from its (already renumbered) title."""
    m = LEGEND.match(rec["new"] or "")
    if not m or m.group(1):
        return None
    k = {"Supplementary Figure": "sfig", "Figure": "fig", "Table": "table"}[m.group(2)]
    return k, int(m.group(3))


def lis_indices(seq):
    """Indices of one longest strictly increasing subsequence of `seq`."""
    import bisect
    tails, idx, prev = [], [], [-1] * len(seq)
    for i, v in enumerate(seq):
        j = bisect.bisect_left(tails, v)
        if j == len(tails):
            tails.append(v); idx.append(i)
        else:
            tails[j] = v; idx[j] = i
        prev[i] = idx[j - 1] if j else -1
    out, i = [], idx[-1] if idx else -1
    while i >= 0:
        out.append(i); i = prev[i]
    return set(out)


def main() -> int:
    records = json.loads(EDITS.read_text())
    nmap = build_map(first_citations(records))
    for r in records:
        new = apply_map(r["new"], nmap)
        if r["action"] == "keep" and new != r["new"]:
            r["action"] = "edit"
            r["source"] = "renumber_260925"
        r["new"] = new

    # Supplementary legends: keep the longest in-order run, move the others.
    legends = [(i, legend_number(r, nmap)) for i, r in enumerate(records)
               if r["new"] and r["action"] != "delete"]
    sleg = [(i, n) for i, (k, n) in ((i, x) for i, x in legends if x) if k == "sfig"]
    keep = lis_indices([n for _, n in sleg])
    moved = [sleg[j] for j in range(len(sleg)) if j not in keep]
    stay = [sleg[j] for j in sorted(keep)]
    out = []
    moved_by_target = {}
    for i, n in moved:
        # The moved legend goes right after the staying (or earlier moved) legend with the
        # largest smaller number; before the first staying one if it is the smallest.
        prev = max([s for s in stay if s[1] < n], key=lambda s: s[1], default=None)
        moved_by_target.setdefault(prev[0] if prev else ("before", stay[0][0]), []).append(
            (n, records[i]))
    moved_idx = {i for i, _ in moved}
    for i, r in enumerate(records):
        for n, mr in sorted(moved_by_target.get(("before", i), []), key=lambda x: x[0]):
            out.append(dict(mr, action="insert", id=f"{mr['id']}@moved", base=None,
                            source="renumber_260925 (legend moved)"))
        if i in moved_idx:
            if r["base"] is not None:
                out.append(dict(r, action="delete", new=None,
                                source="renumber_260925 (legend moved)"))
        else:
            out.append(r)
        for n, mr in sorted(moved_by_target.get(i, []), key=lambda x: x[0]):
            out.append(dict(mr, action="insert", id=f"{mr['id']}@moved", base=None,
                            source="renumber_260925 (legend moved)"))

    FINAL.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    MAP_JSON.write_text(json.dumps(nmap, indent=1, ensure_ascii=False))
    lines = ["# 21 — Renumbering map (Phase 5), 2026-09-25", "",
             "Computed once from the finished text by `tools/renumber_260925.py`, order of "
             "first citation in the body (legends and headings excluded). References to "
             "Article 1's Supplementary Files (\"… of the source benchmark\") are not "
             "renumbered.", ""]
    names = {"fig": "Figures", "sfig": "Supplementary Figures", "table": "Tables",
             "file": "Supplementary Files"}
    for k, m in nmap.items():
        lines += [f"## {names[k]}", "", "| before | after |", "|---|---|"]
        lines += [f"| {old} | {new} |" for old, new in m.items()]
        lines.append("")
    lines += [f"Supplementary legends moved: {len(moved)} "
              f"({', '.join(str(n) for _, n in sorted(moved, key=lambda x: x[1]))}); "
              f"kept in place: {len(stay)}.", ""]
    MAP_MD.write_text("\n".join(lines))

    md = []
    for r in out:
        if r["new"] is None:
            continue
        prefix = HEADING.get(r["style"], "") if r["action"] != "insert" else ""
        md += [prefix + plain(re.sub(r"(?<=\S) {2,}(?=\S)", " ",
                                     re.sub(r"<!--.*?-->", "", r["new"], flags=re.S)).strip()), ""]
    header = OUT_MD.read_text().split("---\n\n", 1)[0] + "---\n\n"
    OUT_MD.write_text(header + "\n".join(md))
    print("\n".join(lines))
    left = re.findall(r"\[FIG:\w+\]", "\n".join(r["new"] or "" for r in out))
    print(f"unresolved tokens: {len(left)}")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
