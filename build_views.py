# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Generate every candidate view from ONE canonical source — no string guessing.

Reads  docs/candidates_canonical.json (the single source of truth).
Writes docs/candidate_table.md, docs/candidate_table.html,
       evidence/candidates_from_canonical.yaml (engine fixture),
       docs/computed_vs_human.md (engine COMPUTED vs human research judgment).

Engine inputs come ONLY from each candidate's explicit `engine_inputs` block
(schema-validated fields). Narrative prose is never parsed into engine flags, so
swapping a synonym or a negation in the prose cannot change the structured result.

Usage: uv run build_views.py       (run from research/engine/)
"""
# Make stdout/stderr UTF-8 regardless of the machine's locale: this repo is read and run by
# reviewers on systems where the preferred encoding may be ASCII, and a crash while *printing*
# a result is still a failed reproduction.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import json, html, sys
from pathlib import Path
import yaml

HERE = Path(__file__).parent
CANON = HERE / "docs" / "candidates_canonical.json"
DATA = json.loads(CANON.read_text(encoding="utf-8"))
C = DATA["candidates"]

REQUIRED_EI = {"net_effect", "evidence_distance", "rescue_in_relevant_cells",
               "competition_eligibility", "properties", "safety_assessment", "objective_class",
               "safety_gap_declared"}
# property -> the hard gate that reads it (mirrors src/triage.py PROPERTY_SAFETY_GATE)
PROPERTY_SAFETY_GATE = {
    "pro_tumor": "oncology", "pro_proliferative": "oncology",
    "increases_CIN": "oncology", "immunosuppressive": "oncology",
    "nephrotoxic": "renal", "renal_cleared_narrow_TI": "renal",
    "anti_anabolic": "growth", "growth_suppressive": "growth",
}
UNRESOLVED = ("confirmed_risk", "contradictory", "not_assessed")
OBJECTIVE_CLASSES = {"restore", "mitigate", "deselect", "protect"}
SAFETY_GATES = ("oncology", "renal", "growth")
SAFETY_STATUS = {"confirmed_risk", "not_observed", "not_assessed", "contradictory"}
ELIGIBILITY = {"ELIGIBLE", "INELIGIBLE", "UNKNOWN"}

# ---- validate the canonical engine_inputs RAW TYPES before generating anything ----
# No coercion, no repair: a string "false" or an int-like string is a bad input and
# must stop the build here (Spec 0 §2.2), otherwise the fixture would launder it.
errs = []
for c in C:
    cid = c.get("id", "?")
    ei = c.get("engine_inputs")
    if not isinstance(ei, dict):
        errs.append(f"{cid}: missing engine_inputs"); continue
    miss = REQUIRED_EI - set(ei)
    if miss:
        errs.append(f"{cid}: engine_inputs missing {sorted(miss)}"); continue
    ed = ei["evidence_distance"]
    if isinstance(ed, bool) or not isinstance(ed, int) or not (0 <= ed <= 5):
        errs.append(f"{cid}: evidence_distance must be int 0-5, got {ed!r} ({type(ed).__name__})")
    r = ei["rescue_in_relevant_cells"]
    if not isinstance(r, bool):
        errs.append(f"{cid}: rescue_in_relevant_cells must be a real bool, got {r!r} ({type(r).__name__})")
    if ei["objective_class"] not in OBJECTIVE_CLASSES:
        errs.append(f"{cid}: objective_class {ei['objective_class']!r} not in {sorted(OBJECTIVE_CLASSES)}")
    if ei["competition_eligibility"] not in ELIGIBILITY:
        errs.append(f"{cid}: competition_eligibility {ei['competition_eligibility']!r} not in {sorted(ELIGIBILITY)}")
    if not isinstance(ei["properties"], list):
        errs.append(f"{cid}: properties must be a list, got {type(ei['properties']).__name__}")
    sa = ei["safety_assessment"]
    if not isinstance(sa, dict):
        errs.append(f"{cid}: safety_assessment must be a mapping, got {type(sa).__name__}")
    else:
        for g in SAFETY_GATES:
            if g not in sa:
                errs.append(f"{cid}: safety_assessment missing '{g}'")
            elif sa[g] not in SAFETY_STATUS:
                errs.append(f"{cid}: safety_assessment[{g}] = {sa[g]!r} not in {sorted(SAFETY_STATUS)}")
    # ---- the reverse direction (red-team 2026-10-19) ----
    # The hard gates read properties[] only. A candidate assessed `contradictory` or
    # `confirmed_risk` on a gate, but carrying no property for that gate, PASSES the gate --
    # the gate is structurally blind to a risk the candidate's own safety block admits.
    # triage.py's safety_input_conflicts() checked only the other direction
    # (a risk tag vs safety "not_observed"), so this one went through silently.
    # We do not fix it by adding a property after the fact -- that is rule-fitting, and it
    # would rewrite verdicts to taste. We require the gap to be DECLARED, exactly, in the
    # canonical entry, so "clears the gates" can never again be read as "carries no risk".
    if isinstance(sa, dict) and isinstance(ei.get("properties"), list):
        tagged = {PROPERTY_SAFETY_GATE[p] for p in ei["properties"] if p in PROPERTY_SAFETY_GATE}
        actual = sorted(g for g in SAFETY_GATES
                        if sa.get(g, "not_assessed") in UNRESOLVED and g not in tagged)
        declared = ei.get("safety_gap_declared")
        if not isinstance(declared, list):
            errs.append(f"{cid}: safety_gap_declared must be a list, got {type(declared).__name__}")
        elif sorted(declared) != actual:
            errs.append(f"{cid}: safety_gap_declared {sorted(declared)} != the gate-silent axes "
                        f"implied by safety_assessment + properties {actual}")
if errs:
    print("CANONICAL INVALID — fix before generating:")
    for e in errs:
        print("  -", e)
    sys.exit(1)

# ---- counts (single denominator) ----
interventions = [c for c in C if c["entity_type"] == "intervention"]
branches = [c for c in C if c["entity_type"] == "mechanism_branch"]
negs = [c for c in C if c["entity_type"] == "negative_control"]
by_judg = {}
for c in C:
    by_judg.setdefault(c["research_judgment"], []).append(c["id"])
denom = (f"{len(interventions)} interventions + {len(branches)} mechanism-branches "
         f"+ {len(negs)} negative-control groups = {len(C)} entries")

# ---- markdown table ----
md = [f"# Candidate table (generated from candidates_canonical.json, {DATA['updated']})", "",
      f"Denominator: {denom}.",
      "Research judgment: " + ", ".join(f"{k}={len(v)}" for k, v in sorted(by_judg.items())), "",
      "| ID | Candidate | Type | Eligibility | Research | Dir | Ev-dist | Reason |",
      "|---|---|---|---|---|---|---|---|"]
for c in C:
    md.append(f"| {c['id']} | {c['drug']} | {c['entity_type']} | {c['competition_eligibility']} "
              f"| {c['research_judgment']} | {c['directionality']} | {c['evidence_distance']} "
              f"| {c['disposition_reason']} |")
(HERE / "docs" / "candidate_table.md").write_text("\n".join(md) + "\n", encoding="utf-8")

# ---- HTML fragment (escaped) ----
def pill(j):
    cls = {"SUPPORTED": "pk", "CONDITIONAL": "pc", "INSUFFICIENT": "pc", "REJECTED": "pr"}.get(j, "pc")
    return f'<span class="pill {cls}">{html.escape(j)}</span>'
rows = []
for c in C:
    rows.append("<tr>" + "".join(
        f"<td>{x}</td>" for x in (
            f"<code>{html.escape(c['id'])}</code>", html.escape(c["drug"]), html.escape(c["entity_type"]),
            html.escape(c["competition_eligibility"]), pill(c["research_judgment"]),
            html.escape(c["directionality"]), c["evidence_distance"], html.escape(c["disposition_reason"]))) + "</tr>")
htmlout = (f"<!-- generated from candidates_canonical.json {DATA['updated']} -->\n"
           f"<p class='sm muted'>Denominator: {html.escape(denom)}.</p>\n"
           "<table><thead><tr><th>ID</th><th>Candidate</th><th>Type</th><th>Eligibility</th>"
           "<th>Research</th><th>Dir</th><th>Ev-dist</th><th>Reason</th></tr></thead>\n<tbody>\n"
           + "\n".join(rows) + "\n</tbody></table>\n")
(HERE / "docs" / "candidate_table.html").write_text(htmlout, encoding="utf-8")

# ---- engine fixture (from explicit engine_inputs; safe YAML) ----
fixture = {"_generated_from": "docs/candidates_canonical.json",
           "_note": "Engine fixture from explicit engine_inputs — no prose parsing. "
                    "Scientific judgment is research_judgment in the canonical file.",
           "candidates": []}
for c in C:
    ei = c["engine_inputs"]
    # pass-through: validated above, never int()/bool()/list()/dict() here (Spec 0 §2.2)
    fixture["candidates"].append({
        "id": c["id"], "drug": c["drug"],
        "net_effect": ei["net_effect"],
        "evidence_distance": ei["evidence_distance"],
        "rescue_in_relevant_cells": ei["rescue_in_relevant_cells"],
        "competition_eligibility": ei["competition_eligibility"],
        "properties": ei["properties"],
        "safety_assessment": ei["safety_assessment"],
        "objective_class": ei["objective_class"],
        "safety_gap_declared": ei["safety_gap_declared"]})
(HERE / "evidence" / "candidates_from_canonical.yaml").write_text(
    "# AUTO-GENERATED from docs/candidates_canonical.json by build_views.py — do not edit by hand\n"
    + yaml.safe_dump(fixture, sort_keys=False, allow_unicode=True), encoding="utf-8")

# ---- computed (engine) vs human comparison ----
sys.path.insert(0, str(HERE / "src"))
import triage  # noqa: E402
scoring = triage.load(HERE / "config" / "scoring.yaml")
case = triage.load(HERE / "config" / "cases" / "bub1b_mva.yaml")
_, out = triage.run(case, scoring, fixture["candidates"])
computed = {r["id"]: r["verdict"] for r in out}
# What the gates could NOT see, surfaced next to the verdict rather than left in the engine's
# reasons list: a PASS on a gate means "no properties[] tag the rule acts on", never "no risk".
silent = {r["id"]: r.get("gate_silent_safety") or [] for r in out}
unact = {r["id"]: r.get("unactioned_risk_tags") or [] for r in out}
cmp_md = ["# Computed (engine) vs human research judgment", "",
          "The engine produces a COMPUTED gate verdict; the human research judgment is the",
          "scientific disposition. Divergence is expected and explained — the engine never",
          "overwrites, nor is inferred from, the human judgment.", "",
          "A gate PASS means no `properties[]` tag that the rule acts on at this patient's level —",
          "not an absence of risk. The last two columns make that difference visible: *gate-silent*",
          "axes are assessed as unresolved but carry no tag the gate reads, and *unactioned* tags are",
          "risks the gate can see but has no rule for at this level.", "",
          "| ID | Human | Engine | Explanation of divergence | Gate-silent axes | Unactioned risk tags |",
          "|---|---|---|---|---|---|"]
EXPL = {
 "C-NAD": "engine REJECTs on INELIGIBLE (NMN/NR are supplements, no approved product); human keeps the SIRT2-BubR1 mechanism-branch CONDITIONAL — its approved-product instance is evaluated separately as C-NA",
 "C-NA": "engine CONDITIONAL and human CONDITIONAL agree; if they ever diverge, the reason must be written here (oncology gate is 'contradictory' by design, so STRONG is unreachable until the decisive ex vivo experiment is run)",
 "C-AMPK": "engine REJECTs at renal gate (metformin renal_cleared_narrow_TI vs nephrocalcinosis); human keeps the deselection mechanism CONDITIONAL pending a non-renal AMPK agent",
 "C-RT": "engine REJECTs on INELIGIBLE (no approved renal-safe UGA agent); human keeps the mechanism-branch CONDITIONAL",
 "C-PBA": "engine has no INSUFFICIENT terminal; an eligible-but-weak candidate reads CONDITIONAL",
 "C-DQ": "human REJECTED is a research judgment (downstream action + endpoint mismatch), not one of the four gates — and note the engine's own note in the last column: a senolytic TKI pair tagged `immunosuppressive` passes the oncology gate because the rule does not act on that tag at the `history` level",
 "C-FOL": "engine has no INSUFFICIENT terminal; reads CONDITIONAL",
 "N-CQ": "eligible + directionally plausible so engine passes gates; human REJECTED on chronic pediatric toxicity + hypothesis-only (not a gate)",
}
for c in C:
    h, e = c["research_judgment"], computed.get(c["id"], "?")
    same = (h == e) or (h == "REJECTED" and e == "REJECT")
    expl = "—" if same else EXPL.get(c["id"], "divergence: review")
    # declared in the canonical entry, so it is present even for candidates the engine rejects
    # before reaching the gates (eligibility / directionality short-circuit)
    gs = ", ".join(c["engine_inputs"]["safety_gap_declared"]) or "—"
    reached = computed.get(c["id"]) in ("STRONG", "CONDITIONAL")
    ua = ("; ".join(x.split(": ", 1)[-1] for x in unact.get(c["id"], [])) or "—") if reached \
        else "not evaluated (rejected before the gates)"
    cmp_md.append(f"| {c['id']} | {h} | {e} | {expl} | {gs} | {ua} |")
(HERE / "docs" / "computed_vs_human.md").write_text("\n".join(cmp_md) + "\n", encoding="utf-8")

# ---- optional: product-level eligibility matrix (docs/eligibility_matrix.csv -> .md) ----
import csv
EM = HERE / "docs" / "eligibility_matrix.csv"
if EM.exists():
    with EM.open(newline="", encoding="utf-8") as fh:
        rows_em = list(csv.DictReader(fh))
    need = ["molecule", "product", "form_route", "jurisdiction", "indication", "age_range",
            "status", "status_date", "source_url", "source_type", "counterexample"]
    # source_type is required (red-team 2026-10-19): section 7 claims an openable source URL per
    # row, and three rows pointed at a site landing page or a search listing. A URL that is not a
    # product label is still a legitimate source -- but the row has to say which kind it is.
    bad = [r for r in rows_em if any(not (r.get(k) or "").strip()
           for k in ("molecule", "product", "status", "status_date", "source_url", "source_type"))]
    if bad:
        print("ELIGIBILITY MATRIX INVALID — every row needs molecule, product, status, status_date, source_url:")
        for r in bad:
            print("  -", r.get("molecule"), r.get("product"))
        sys.exit(1)
    em_md = ["# Product-level eligibility matrix (generated from docs/eligibility_matrix.csv)", "",
             "Approval is a property of a product (molecule x form/route x jurisdiction x indication x age range), "
             "not of a molecule. Every status carries the date it was checked and a URL that opens.", "",
             "| Molecule | Product | Form / route | Jurisdiction | Indication (label wording) | Age range | Status | Checked | Source | Source type | Counterexample |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows_em:
        em_md.append("| " + " | ".join((r.get(k) or "").replace("|", "/") for k in need) + " |")
    (HERE / "docs" / "eligibility_matrix.md").write_text("\n".join(em_md) + "\n", encoding="utf-8")
    print(f"  eligibility matrix: {len(rows_em)} product rows -> docs/eligibility_matrix.md")

print(f"Generated 4 views from {len(C)} canonical entries ({denom}).")
print("  research judgment: " + ", ".join(f"{k}={len(v)}" for k, v in sorted(by_judg.items())))
div = [c["id"] for c in C if not ((c["research_judgment"] == computed.get(c["id"]))
       or (c["research_judgment"] == "REJECTED" and computed.get(c["id"]) == "REJECT"))]
print(f"  computed-vs-human divergences (explained): {div}")
