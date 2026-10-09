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
import json, html, sys
from pathlib import Path
import yaml

HERE = Path(__file__).parent
CANON = HERE / "docs" / "candidates_canonical.json"
DATA = json.loads(CANON.read_text())
C = DATA["candidates"]

REQUIRED_EI = {"net_effect", "evidence_distance", "rescue_in_relevant_cells",
               "competition_eligibility", "properties", "safety_assessment"}

# ---- validate the canonical engine_inputs before generating anything ----
errs = []
for c in C:
    ei = c.get("engine_inputs")
    if not isinstance(ei, dict):
        errs.append(f"{c['id']}: missing engine_inputs"); continue
    miss = REQUIRED_EI - set(ei)
    if miss:
        errs.append(f"{c['id']}: engine_inputs missing {sorted(miss)}")
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
(HERE / "docs" / "candidate_table.md").write_text("\n".join(md) + "\n")

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
(HERE / "docs" / "candidate_table.html").write_text(htmlout)

# ---- engine fixture (from explicit engine_inputs; safe YAML) ----
fixture = {"_generated_from": "docs/candidates_canonical.json",
           "_note": "Engine fixture from explicit engine_inputs — no prose parsing. "
                    "Scientific judgment is research_judgment in the canonical file.",
           "candidates": []}
for c in C:
    ei = c["engine_inputs"]
    fixture["candidates"].append({"id": c["id"], "drug": c["drug"],
        "net_effect": ei["net_effect"], "evidence_distance": int(ei["evidence_distance"]),
        "rescue_in_relevant_cells": bool(ei["rescue_in_relevant_cells"]),
        "competition_eligibility": ei["competition_eligibility"],
        "properties": list(ei["properties"]), "safety_assessment": dict(ei["safety_assessment"])})
(HERE / "evidence" / "candidates_from_canonical.yaml").write_text(
    "# AUTO-GENERATED from docs/candidates_canonical.json by build_views.py — do not edit by hand\n"
    + yaml.safe_dump(fixture, sort_keys=False, allow_unicode=True))

# ---- computed (engine) vs human comparison ----
sys.path.insert(0, str(HERE / "src"))
import triage  # noqa: E402
scoring = triage.load(HERE / "config" / "scoring.yaml")
case = triage.load(HERE / "config" / "cases" / "bub1b_mva.yaml")
_, out = triage.run(case, scoring, fixture["candidates"])
computed = {r["id"]: r["verdict"] for r in out}
cmp_md = ["# Computed (engine) vs human research judgment", "",
          "The engine produces a COMPUTED gate verdict; the human research judgment is the",
          "scientific disposition. Divergence is expected and explained — the engine never",
          "overwrites, nor is inferred from, the human judgment.", "",
          "| ID | Human | Engine | Explanation of divergence |", "|---|---|---|---|"]
EXPL = {
 "C-NAD": "engine REJECTs at pediatric gate: no approved pediatric product is fixed (eligibility UNKNOWN); human keeps the SIRT2-BubR1 mechanism CONDITIONAL for study",
 "C-AMPK": "engine REJECTs at renal gate (metformin renal_cleared_narrow_TI vs nephrocalcinosis); human keeps the deselection mechanism CONDITIONAL pending a non-renal AMPK agent",
 "C-RT": "engine REJECTs on INELIGIBLE (no approved renal-safe UGA agent); human keeps the mechanism-branch CONDITIONAL",
 "C-PBA": "engine has no INSUFFICIENT terminal; an eligible-but-weak candidate reads CONDITIONAL",
 "C-DQ": "human REJECTED is a research judgment (downstream action + endpoint mismatch), not one of the four gates",
 "C-FOL": "engine has no INSUFFICIENT terminal; reads CONDITIONAL",
 "N-CQ": "eligible + directionally plausible so engine passes gates; human REJECTED on chronic pediatric toxicity + hypothesis-only (not a gate)",
}
for c in C:
    h, e = c["research_judgment"], computed.get(c["id"], "?")
    same = (h == e) or (h == "REJECTED" and e == "REJECT")
    expl = "—" if same else EXPL.get(c["id"], "divergence: review")
    cmp_md.append(f"| {c['id']} | {h} | {e} | {expl} |")
(HERE / "docs" / "computed_vs_human.md").write_text("\n".join(cmp_md) + "\n")

print(f"Generated 4 views from {len(C)} canonical entries ({denom}).")
print("  research judgment: " + ", ".join(f"{k}={len(v)}" for k, v in sorted(by_judg.items())))
div = [c["id"] for c in C if not ((c["research_judgment"] == computed.get(c["id"]))
       or (c["research_judgment"] == "REJECTED" and computed.get(c["id"]) == "REJECT"))]
print(f"  computed-vs-human divergences (explained): {div}")
