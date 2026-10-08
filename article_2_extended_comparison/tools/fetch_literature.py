"""Resolve a DOI or PMID to PubMed metadata and, where open access, PMC full text.

Written for the Phase 3 literature work so every quote in `02_literature.json` can be
copied out of the paper itself instead of recalled. Cache lives beside this file.

    python tools/fetch_literature.py 36140419 10.1186/s12859-019-2641-8

The one thing worth knowing about it: `elink` returns several PMC link sets and the first
is NOT the article. `pubmed_pmc_refs` lists the articles that CITE it, so taking
linksetdbs[0] retrieves the wrong paper -- it returned a Nature organoid study as the
full text of ComBat, and quotes were being attributed from it before that was caught.
`pmcid()` matches the `pubmed_pmc` linkname explicitly for that reason.
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)
EUT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
UA = {"User-Agent": "Mozilla/5.0 (research; article2 literature scout)"}


def _get(url, raw=False):
    key = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:] + (".bin" if raw else ".txt"))
    if key.exists():
        return key.read_text(errors="ignore")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", "ignore")
    key.write_text(body)
    time.sleep(0.4)
    return body


def pmid_from_doi(doi):
    q = urllib.parse.quote(doi)
    d = json.loads(_get(f"{EUT}/esearch.fcgi?db=pubmed&term={q}%5Bdoi%5D&retmode=json"))
    ids = d["esearchresult"].get("idlist", [])
    return ids[0] if ids else None


def summary(pmid):
    d = json.loads(_get(f"{EUT}/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"))
    r = d["result"][str(pmid)]
    doi = next((x["value"] for x in r.get("articleids", []) if x["idtype"] == "doi"), None)
    return {"pmid": str(pmid), "title": r.get("title", "").rstrip("."),
            "journal": r.get("fulljournalname") or r.get("source"),
            "year": (r.get("pubdate") or "")[:4], "doi": doi,
            "authors": [a["name"] for a in r.get("authors", [])][:6]}


def pmcid(pmid):
    """The PMC id of THIS article, or None.

    elink returns several link sets and the first is not the article: `pubmed_pmc_refs`
    lists articles that CITE it. Taking linksetdbs[0] blindly retrieved a Nature organoid
    paper as the full text of ComBat, so the linkname is matched explicitly.
    """
    d = json.loads(_get(f"{EUT}/elink.fcgi?dbfrom=pubmed&db=pmc&id={pmid}&retmode=json"))
    for ls in d.get("linksets", []):
        for db in ls.get("linksetdbs", []):
            if db.get("linkname") == "pubmed_pmc" and db.get("links"):
                return "PMC" + db["links"][0]
    return None


def fulltext(pmcid_):
    """PMC full text as (section_name, paragraph) pairs; empty when not open access."""
    xml = _get(f"{EUT}/efetch.fcgi?db=pmc&id={pmcid_}&rettype=xml")
    xml = re.sub(r"<(xref|italic|bold|sup|sub)[^>]*>|</(xref|italic|bold|sup|sub)>", "", xml)
    out, section = [], "Body"
    for m in re.finditer(r"<title>(.*?)</title>|<p[^>]*>(.*?)</p>", xml, re.S):
        if m.group(1) is not None:
            section = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        else:
            txt = re.sub(r"<[^>]+>", " ", m.group(2))
            txt = re.sub(r"\s+", " ", txt).strip()
            if len(txt) > 80:
                out.append((section, txt))
    return out


def abstract(pmid):
    """The PubMed abstract, as (section, paragraph) pairs.

    Used only where PMC has no open-access full text. Labelled as an abstract in the
    output so nothing quoted from here is passed off as a full-text passage.
    """
    xml = _get(f"{EUT}/efetch.fcgi?db=pubmed&id={pmid}&rettype=xml")
    out = []
    for m in re.finditer(r'<AbstractText(?:\s+Label="([^"]*)")?[^>]*>(.*?)</AbstractText>',
                         xml, re.S):
        label = m.group(1) or "Abstract"
        txt = re.sub(r"<[^>]+>", " ", m.group(2))
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt:
            out.append((f"Abstract — {label}" if label != "Abstract" else "Abstract", txt))
    return out


def record(ident):
    pmid = ident if str(ident).isdigit() else pmid_from_doi(ident)
    if not pmid:
        return {"query": ident, "error": "no PMID"}
    rec = summary(pmid)
    pid = pmcid(pmid)
    rec["pmcid"] = pid
    paras = fulltext(pid) if pid else []
    rec["paragraphs"] = paras
    rec["full_text"] = bool(paras)
    if not paras:
        rec["paragraphs"] = abstract(pmid)
    return rec


if __name__ == "__main__":
    for ident in sys.argv[1:]:
        r = record(ident)
        print(f"\n===== {ident} =====")
        if "error" in r:
            print("  ", r["error"]); continue
        print(f'  PMID {r["pmid"]} | {r["journal"]} {r["year"]} | {r["pmcid"] or "no PMC"}')
        print(f'  {r["title"][:110]}')
        print(f'  full-text paragraphs: {len(r["paragraphs"])}')
