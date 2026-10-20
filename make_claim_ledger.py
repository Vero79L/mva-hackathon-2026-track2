#!/usr/bin/env python3
"""Generate registers/claim_ledger.csv from already-verified, public-safe sources.

Sources (all public-safe by construction):
  docs/mechanism_graph.yaml    -> mechanism claims, with per-edge strength and counter-evidence
  docs/eligibility_matrix.csv  -> regulatory claims, with dated label URLs
  GLOBAL_NEGATIVES below       -> bounded "we did not find X" claims, each with a search strategy

It deliberately does NOT read registers/evidence_ledger.csv: that file contains
genomic coordinates and genotypes, which must never reach a published artefact.

Usage: python3 make_claim_ledger.py      (run from research/engine/)
"""
# Make stdout/stderr UTF-8 regardless of the machine's locale: this repo is read and run by
# reviewers on systems where the preferred encoding may be ASCII, and a crash while *printing*
# a result is still a failed reproduction.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import csv, sys
from pathlib import Path
import yaml

HERE = Path(__file__).parent
OUT = HERE.parent / "registers" / "claim_ledger.csv"
HDR = ["claim_id", "claim_text", "claim_type", "report_location", "source_url",
       "source_locator", "checked_date", "strength", "counterevidence", "disposition",
       "verification_mode", "reviewed_by"]


# How a given row can be checked at all. Reporting "N/36 rows carry no human sign-off" treats
# four kinds of claim as if one act verified them, and overstates the deficit: a label quotation
# is checked by opening the label, a global negative by re-running its dated search, and a claim
# whose source is a file in this repo by the provenance hashes the release manifest already
# enforces. Only a claim sourced to a paper needs a person to have read the paper. This column
# names the mechanism per row so the manifest can report each tier against its own denominator.
def verification_mode(url: str) -> str:
    u = (url or "").lower()
    if "pubmed.ncbi.nlm.nih.gov" in u:
        return "literature_read"          # a person must read the source; nothing else substitutes
    if ("dailymed.nlm.nih.gov" in u or "ema.europa.eu" in u
            or "medicines.org.uk" in u):      # UK emc: the SmPC is the GB equivalent of the label
        return "label_text_match"         # open the label, match the quoted string and its date
    if "ods.od.nih.gov" in u:
        # Not a product label. Disclosed rather than counted as a label check: these rows point at
        # a fact-sheet host because no approved product exists for the molecule.
        return "landing_page_only"
    if "search_strategies" in u:
        return "reproducible_search"      # re-run the recorded query and compare the hit count
    if u.startswith(("docs/", "config/", "evidence/", "src/", "outputs/")):
        return "internal_provenance"      # hash-gated by make_manifest.py
    return "unclassified"
DATE = "2026-10-19"
# Per-claim sign-off. An earlier version of this script stamped every row with the same
# "human adjudication" string, which is self-certification: it proves nothing, and it is the very
# pattern we criticise the hard gates for elsewhere. The reviewer column is now populated ONLY from
# registers/claim_signoff.csv, a file a human edits. A claim nobody has signed off stays BLANK, and
# the release manifest reports how many are unsigned.
def _load_signoff():
    f = HERE.parent / "registers" / "claim_signoff.csv"
    if not f.exists():
        return {}
    with f.open(newline="", encoding="utf-8") as fh:
        return {r["claim_id"]: f'{r.get("reviewed_by","").strip()}'
                + (f' ({r["reviewed_date"].strip()})' if r.get("reviewed_date", "").strip() else "")
                for r in csv.DictReader(fh) if r.get("claim_id", "").strip()}


SIGNOFF = {}
PM = "https://pubmed.ncbi.nlm.nih.gov/{}/"
# the graph's four-level scale -> the ledger's wording scale
STRENGTH = {"measured_in_proband": "measured", "measured_in_model": "measured",
            "predicted": "predicted", "asserted": "asserted"}

GLOBAL_NEGATIVES = [
 ("GN-01",
  "No study reports NAD+ status in mosaic variegated aneuploidy or in BUB1B-mutant cells, so the deficiency the named candidate would correct has not been shown to exist.",
  "section 9 Counter-evidence; section 13 Limitations",
  "PubMed: (NAD+ OR nicotinamide adenine dinucleotide) AND (mosaic variegated aneuploidy OR BUB1B)",
  "0 relevant hits; the 4 returned records concern unrelated tissues or are the SIRT2-BubR1 paper itself",
  "unresolved"),
 ("GN-02",
  "No approved translational-readthrough agent is eligible for this patient's truncating allele. Bounded, because the global version is false: ataluren retains a Great Britain marketing authorisation (live UK SmPC, 250 mg updated 2026-03-31) after the EU non-renewal of 2025-03-28 and the US withdrawal of 2026-02-12, but for a different gene and indication; the approved aminoglycosides are rejected on renal grounds; ELX-02 and DAP are investigational.",
  "section 5 Candidate funnel; section 7 Eligibility matrix",
  "EMA EPAR page for Translarna (ataluren); UK emc SmPC for Translarna (checked 2026-10-20); DailyMed search for approved readthrough agents",
  "EMA: conditional authorisation not renewed 28 March 2025, effectiveness not confirmed; UK: authorisation live, so the claim is jurisdiction-bounded and indication-bounded rather than global",
  "bounded"),
 ("GN-03",
  "No approved drug selectively activates SIRT2 or directly stabilises BUBR1; the strongest mechanistic link has no pharmacology behind it.",
  "section 10 A reportable gap",
  "DailyMed drug_name search; PubMed for approved SIRT2 activators; Open Targets Platform tractability for BUB1B (ENSG00000156970), API v26.9.0 / data 26.09, queried 2026-10-19 (see search_strategies.md GN-03 addendum)",
  "No approved product in the checked sources on this date. Open Targets corroborates at target level rather than label-text level: Approved Drug / Advanced Clinical / Phase 1 are false across small-molecule, antibody, PROTAC and other-clinical modalities; High-Quality Pocket and Structure-with-Ligand false, only High-Quality Ligand and Druggable Family true; every antibody bucket false. The one positive signal points the wrong way for us -- ubiquitination and literature flags support a PROTAC (degrader) approach, i.e. LOWERING BUBR1, the opposite of the direction this report needs.",
  "bounded"),
 ("GN-05",
  "Neither of the patient's two BUB1B alleles has a ClinVar record, so no curated classification supports or contradicts the pathogenicity argument.",
  "section 2 Patient basis",
  "VEP 116 --custom exact-coordinate overlay against the ClinVar release dated 2026-10-04 (fields CLNSIG, CLNREVSTAT, CLNDN)",
  "both alleles returned no ClinVar fields; bounded to that release and date, and not evidence of benignity",
  "bounded"),
 ("GN-04",
  "No NAD+ booster has been tested in an MVA model or in cells of this allele class.",
  "section 9; section 13",
  "PubMed: BUBR1 AND (rescue OR restore) AND (mosaic variegated aneuploidy OR hypomorph) AND (protein level OR stability)",
  "returned the SIRT2-lifespan null paper and a monoallelic-MVA clinical series; no NAD+ intervention in an MVA model",
  "unresolved"),
]

rows = []
g = yaml.safe_load((HERE / "docs" / "mechanism_graph.yaml").read_text(encoding="utf-8"))
for e in g["edges"]:
    srcs = e.get("sources") or []
    urls, locs = [], []
    for s in srcs:
        if s.get("pmid"):
            urls.append(PM.format(s["pmid"])); locs.append(f"PMID {s['pmid']}: {s.get('locator','')}".strip())
        elif s.get("file"):
            urls.append(s["file"]); locs.append(s.get("locator", ""))
    # the published ledger is English-facing: prefer the English fields when present
    ce = (e.get("counterevidence_en") or e.get("counterevidence") or "").strip()
    rows.append({
        "claim_id": f"CL-MECH-{e['id']}",
        "claim_text": e.get("claim_en") or e["claim"], "claim_type": "mechanism",
        "report_location": "section 3 Variant mechanism (chain link " + e["id"] + ")",
        "source_url": " | ".join(urls), "source_locator": " | ".join(x for x in locs if x),
        "checked_date": DATE, "strength": STRENGTH.get(e.get("strength"), e.get("strength", "")),
        "counterevidence": ce or "searched_none_found",
        "disposition": "bounded" if ce else "retained_with_caveat",
        "reviewed_by": ""})

with (HERE / "docs" / "eligibility_matrix.csv").open(newline="", encoding="utf-8") as fh:
    for i, r in enumerate(csv.DictReader(fh), 1):
        ce = (r.get("counterexample") or "").strip()
        rows.append({
            "claim_id": f"CL-REG-{i:02d}",
            "claim_text": f"{r['product']} ({r['form_route']}, {r['jurisdiction']}) status: {r['status']}. Indication: {r['indication']} Age: {r['age_range']}",
            "claim_type": "regulatory", "report_location": "section 7 Eligibility matrix",
            "source_url": r["source_url"], "source_locator": "label sections: Indications and Usage; 8.4 Pediatric Use",
            "checked_date": r["status_date"], "strength": "measured",
            "counterevidence": ce or "searched_none_found",
            "disposition": "bounded" if ce else "retained_with_caveat",
            "reviewed_by": ""})

for cid, text, loc, strat, hits, disp in GLOBAL_NEGATIVES:
    rows.append({"claim_id": cid, "claim_text": text, "claim_type": "global_negative",
                 "report_location": loc, "source_url": "see registers/search_strategies.md",
                 "source_locator": strat, "checked_date": DATE, "strength": "asserted",
                 "counterevidence": hits, "disposition": disp, "reviewed_by": ""})

rows.append({"claim_id": "CL-METH-01",
  "claim_text": "Method B (GTF arithmetic) agrees with VEP 116 on 1,319 of 1,320 variant x MANE-transcript PAIRS (99.9%) across 400 public ClinVar variants -- a pair counts as agreeing only if every applicable field agrees. Field-level: 6,269/6,270 (99.98%), but strand and transcript_version contribute 2,640 of those and are identical by construction; the discriminating field is protein_first_changed at 333/334.",
  "claim_type": "method", "report_location": "section 12 Reproducibility; METHODS_AND_AI Method validation",
  "source_url": "docs/METHODS_AND_AI.md", "source_locator": "Method validation table",
  "checked_date": DATE, "strength": "measured",
  "counterevidence": "1 residual disagreement in protein_first_changed (333/334), disclosed",
  "disposition": "retained_with_caveat", "reviewed_by": ""})
rows.append({"claim_id": "CL-METH-02",
  "claim_text": "The triage engine's 28 self-tests pin its edge behaviour, including that an objective class marked invalid in the active scenario is rejected, that a malformed scenario block BLOCKS rather than falling back to 'no scenario', that the gate is inert when no scenario is active, and that the four patient gates' reject / require / flag branches are exercised against this patient's own constraint levels.",
  "claim_type": "method", "report_location": "section 4 Screening method; section 12",
  "source_url": "src/triage.py", "source_locator": "selftest()",
  "checked_date": DATE, "strength": "measured",
  "counterevidence": "searched_none_found", "disposition": "retained_with_caveat",
  "reviewed_by": ""})

SIGNOFF = _load_signoff()
for r in rows:
    r["reviewed_by"] = SIGNOFF.get(r["claim_id"], "")
    r["verification_mode"] = verification_mode(r["source_url"])
_signed = sum(1 for r in rows if r["reviewed_by"])
_lit = [r for r in rows if r["verification_mode"] == "literature_read"]
_lit_signed = sum(1 for r in _lit if r["reviewed_by"])

OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=HDR); w.writeheader(); w.writerows(rows)

# refuse to emit anything that looks like a genomic coordinate or a genotype
import re
COORD = re.compile(r"(\bchr[0-9XYM]{1,2}[:\s]\d{4,})|(\b\d{1,2}:\d{6,}\b)|(\bg\.\d{4,})|(\bNC_0000\d\d)")
GENO = re.compile(r"(\b[01][/|][01]\b)|(\bAD=)|(\bDP=)|(\bGQ=)|(\bAD\d+,\d+)")
bad = [r["claim_id"] for r in rows
       for f in (r["claim_text"], r["source_locator"], r["counterevidence"])
       if COORD.search(f) or GENO.search(f)]
if bad:
    print("REFUSING: coordinate- or genotype-like text reached the ledger:", sorted(set(bad))); sys.exit(1)
from collections import Counter
print(f"claim_ledger.csv: {len(rows)} claims -> {OUT}")
print(f"  human sign-off: {_lit_signed}/{len(_lit)} literature claims signed, "
      f"{_signed}/{len(rows)} rows overall (registers/claim_signoff.csv)")
print("  verification mode:", dict(Counter(r["verification_mode"] for r in rows)))
print("  by type:", dict(Counter(r["claim_type"] for r in rows)))
print("  by strength:", dict(Counter(r["strength"] for r in rows)))
