# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Case-driven candidate triage for N-of-1 rare-disease drug repurposing.

Disease-agnostic. Validates every input against an explicit contract; unknown or
malformed inputs BLOCK — they never pass silently. The engine produces a
COMPUTED assessment only; the human research judgment lives in the canonical
candidate table and is never inferred from, or allowed to overwrite, the inputs.

Contract (a candidate dict):
  id, drug                       : required, non-empty
  net_effect                     : one of NET_EFFECTS
  evidence_distance              : int 0-5
  rescue_in_relevant_cells       : real bool
  properties                     : list, each in the allowed property enum (from scoring)
  competition_eligibility        : ELIGIBLE | INELIGIBLE | UNKNOWN  (absent => UNKNOWN)
  safety_assessment              : dict {oncology,renal,growth: one of SAFETY_STATUS}
STRONG requires: eligibility ELIGIBLE AND ev-dist>=3 AND rescue True AND every
safety gate explicitly assessed (not "not_assessed"). Missing assessment or unknown
eligibility can never reach STRONG. Unknown fields and unknown property values BLOCK.

Usage:
    uv run src/triage.py --case config/cases/bub1b_mva.yaml \
        --candidates evidence/candidates_from_canonical.yaml --scoring config/scoring.yaml
    uv run src/triage.py --selftest
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import yaml

NET_EFFECTS = {"strengthen", "inhibit", "restore_or_bypass", "weaken", "none"}
ELIGIBILITY = {"ELIGIBLE", "INELIGIBLE", "UNKNOWN"}
SAFETY_GATES = ("oncology", "renal", "growth")
SAFETY_STATUS = {"confirmed_risk", "not_observed", "not_assessed", "contradictory"}
KNOWN_CANDIDATE_FIELDS = {
    "id", "drug", "net_effect", "evidence_distance", "rescue_in_relevant_cells",
    "properties", "competition_eligibility", "safety_assessment"}


def load(p):
    return yaml.safe_load(Path(p).read_text())


# ---- allowed property enum derived from the scoring config (no drift) ----

def allowed_properties(scoring):
    props = {"approved_or_credible_pediatric_path"}
    for g in scoring["hard_gates"].values():
        for rule in g["rule"].values():
            for lst in rule.values():
                props.update(lst or [])
    return props


def known_levels(scoring, gate_key):
    return set(scoring["hard_gates"][gate_key]["rule"].keys())


# ---- validation ----

def validate_case(case, scoring):
    errs = []
    if not isinstance(case, dict):
        return [f"case is not a mapping ({type(case).__name__})"]
    if case.get("defect_direction") not in scoring["directionality"]:
        errs.append(f"unknown defect_direction '{case.get('defect_direction')}'")
    pc = case.get("patient_constraints")
    if not isinstance(pc, dict):
        errs.append(f"patient_constraints must be a mapping (got {type(pc).__name__})")
        return errs
    for gk in ("G1_oncology", "G2_pediatric", "G3_renal", "G4_growth"):
        driver = scoring["hard_gates"][gk]["driver"]
        if pc.get(driver) not in known_levels(scoring, gk):
            errs.append(f"{gk}: constraint '{driver}'='{pc.get(driver)}' is unknown")
    return errs


def validate_candidate(cand, scoring):
    if cand is None or not isinstance(cand, dict):
        return [f"candidate is not a mapping ({type(cand).__name__})"]
    errs = []
    unknown = set(cand) - KNOWN_CANDIDATE_FIELDS
    if unknown:
        errs.append(f"unknown field(s) {sorted(unknown)} — reject rather than ignore")
    if not cand.get("id") or not cand.get("drug"):
        errs.append("missing id or drug")
    if cand.get("net_effect") not in NET_EFFECTS:
        errs.append(f"net_effect '{cand.get('net_effect')}' invalid")
    ed = cand.get("evidence_distance")
    if isinstance(ed, bool) or not isinstance(ed, int) or not (0 <= ed <= 5):
        errs.append(f"evidence_distance '{ed}' must be int 0-5")
    if not isinstance(cand.get("rescue_in_relevant_cells", False), bool):
        errs.append("rescue_in_relevant_cells must be a real boolean")
    props = cand.get("properties", [])
    if not isinstance(props, list):
        errs.append("properties must be a list")
    else:
        bad = set(props) - allowed_properties(scoring)
        if bad:
            errs.append(f"unknown property value(s) {sorted(bad)}")
    elig = cand.get("competition_eligibility", "UNKNOWN")
    if elig not in ELIGIBILITY:
        errs.append(f"competition_eligibility '{elig}' invalid")
    sa = cand.get("safety_assessment")
    if sa is not None:
        if not isinstance(sa, dict):
            errs.append("safety_assessment must be a mapping")
        else:
            bad = {v for v in sa.values() if v not in SAFETY_STATUS}
            if bad:
                errs.append(f"safety_assessment status(es) {sorted(bad)} invalid")
    return errs


# ---- gate logic ----

def directionality_ok(cand, case, scoring):
    need = scoring["directionality"][case["defect_direction"]]
    got = cand.get("net_effect")
    return (got == need), f"net_effect '{got}' vs required '{need}'"


def gate(cand, case, scoring, gate_key):
    g = scoring["hard_gates"][gate_key]
    level = case["patient_constraints"].get(g["driver"])
    rule = g["rule"].get(level, {})
    props = set(cand.get("properties", []))
    for action, props_list in rule.items():
        want = set(props_list or [])
        hit = props & want
        if action.startswith("reject_if") and hit:
            return "REJECT", f"{gate_key}[{level}]: {sorted(hit)}"
        if action.startswith("require") and want and not hit:
            return "REJECT", f"{gate_key}[{level}]: missing one of {sorted(want)}"
        if action.startswith("flag_if") and hit:
            return "FLAG", f"{gate_key}[{level}]: watch {sorted(hit)}"
    return "PASS", f"{gate_key}[{level}]: ok"


def fully_safety_assessed(cand):
    sa = cand.get("safety_assessment") or {}
    return all(sa.get(g, "not_assessed") != "not_assessed" for g in SAFETY_GATES)


def triage_one(cand, case, scoring):
    cerr = validate_candidate(cand, scoring)
    if cerr:
        cid = cand.get("id", "?") if isinstance(cand, dict) else "?"
        drug = cand.get("drug", "?") if isinstance(cand, dict) else "?"
        return {"id": cid, "drug": drug, "verdict": "BLOCKED",
                "gate": "input-validation", "reasons": cerr}
    reasons, flags = [], []
    elig = cand.get("competition_eligibility", "UNKNOWN")
    if elig == "INELIGIBLE":
        return {"id": cand["id"], "drug": cand["drug"], "verdict": "REJECT",
                "gate": "eligibility", "reasons": ["competition_eligibility INELIGIBLE"]}
    ok, why = directionality_ok(cand, case, scoring)
    reasons.append(why)
    if not ok:
        return {"id": cand["id"], "drug": cand["drug"], "verdict": "REJECT",
                "gate": "directionality", "reasons": reasons}
    for gk in ("G1_oncology", "G2_pediatric", "G3_renal", "G4_growth"):
        res, why = gate(cand, case, scoring, gk)
        reasons.append(why)
        if res == "REJECT":
            return {"id": cand["id"], "drug": cand["drug"], "verdict": "REJECT",
                    "gate": gk, "reasons": reasons}
        if res == "FLAG":
            flags.append(gk)
    ed = cand["evidence_distance"]
    strong = (elig == "ELIGIBLE" and ed >= 3
              and cand.get("rescue_in_relevant_cells") is True
              and fully_safety_assessed(cand))
    tier = "STRONG" if strong else "CONDITIONAL"
    if tier == "CONDITIONAL" and not fully_safety_assessed(cand):
        reasons.append("safety not fully assessed -> cannot be STRONG")
    if tier == "CONDITIONAL" and elig != "ELIGIBLE":
        reasons.append(f"eligibility {elig} -> cannot be STRONG")
    return {"id": cand["id"], "drug": cand["drug"], "verdict": tier,
            "gate": "passed", "flags": flags, "evidence_distance": ed,
            "eligibility": elig, "reasons": reasons}


def run(case, scoring, cands):
    cerr = validate_case(case, scoring)
    if cerr:
        return {"case_blocked": cerr}, [{"id": "CASE", "drug": "-", "verdict": "BLOCKED",
                                         "gate": "case-validation", "reasons": cerr}]
    if not isinstance(cands, list):
        return {"case_blocked": ["candidates is not a list"]}, []
    return None, [triage_one(c, case, scoring) for c in cands]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case")
    ap.add_argument("--candidates")
    ap.add_argument("--scoring", default="config/scoring.yaml")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest(a.scoring)
    case, scoring = load(a.case), load(a.scoring)
    blocked, out = run(case, scoring, load(a.candidates)["candidates"])
    if blocked:
        print("CASE BLOCKED — invalid manifest:")
        for e in blocked["case_blocked"]:
            print("  -", e)
        return 2
    order = {"STRONG": 0, "CONDITIONAL": 1, "REJECT": 2, "BLOCKED": 3}
    print(f"\n=== Triage: {case['case_id']} ({case['disease']}) ===")
    for r in sorted(out, key=lambda r: order.get(r["verdict"], 9)):
        flags = f" flags={r.get('flags')}" if r.get("flags") else ""
        print(f"[{r['verdict']:<11}] {r['drug'][:34]:<34} ({r['gate']}){flags}")
    n = {k: sum(1 for r in out if r["verdict"] == k) for k in order}
    print("Summary:", n)
    return 3 if any(r["verdict"] == "BLOCKED" for r in out) else 0


def selftest(scoring_path):
    scoring = load(scoring_path)
    base_case = {"case_id": "t", "disease": "t", "defect_direction": "channel_overactivity",
                 "patient_constraints": {"age_group": "adult", "malignancy_status": "none",
                                         "renal": "normal", "growth": "normal"}}
    assessed = {"oncology": "not_observed", "renal": "not_observed", "growth": "not_observed"}

    def one(c):
        return triage_one(c, base_case, scoring)
    checks = []
    # 1. positive control WITH full safety assessment + eligible -> STRONG
    r = one({"id": "S1", "drug": "pos", "net_effect": "inhibit", "properties": [],
             "evidence_distance": 3, "rescue_in_relevant_cells": True,
             "competition_eligibility": "ELIGIBLE", "safety_assessment": assessed})
    checks.append(("positive_strong", r["verdict"] == "STRONG", r["verdict"]))
    # 2. SAME but no safety assessment -> NOT STRONG
    r = one({"id": "S2", "drug": "p2", "net_effect": "inhibit", "properties": [],
             "evidence_distance": 3, "rescue_in_relevant_cells": True,
             "competition_eligibility": "ELIGIBLE"})
    checks.append(("unassessed_not_strong", r["verdict"] != "STRONG", r["verdict"]))
    # 3. INELIGIBLE -> not STRONG (REJECT)
    r = one({"id": "S3", "drug": "p3", "net_effect": "inhibit", "properties": [],
             "evidence_distance": 3, "rescue_in_relevant_cells": True,
             "competition_eligibility": "INELIGIBLE", "safety_assessment": assessed})
    checks.append(("ineligible_not_strong", r["verdict"] != "STRONG", r["verdict"]))
    # 4. unknown property -> BLOCKED
    r = one({"id": "S4", "drug": "p4", "net_effect": "inhibit", "properties": ["nephrotoxicc"],
             "evidence_distance": 3, "rescue_in_relevant_cells": True,
             "competition_eligibility": "ELIGIBLE", "safety_assessment": assessed})
    checks.append(("unknown_property_blocked", r["verdict"] == "BLOCKED", r["verdict"]))
    # 5. None candidate -> BLOCKED (no crash)
    r = one(None)
    checks.append(("null_candidate_blocked", r["verdict"] == "BLOCKED", r["verdict"]))
    # 6. wrong direction -> REJECT
    r = one({"id": "S6", "drug": "wd", "net_effect": "strengthen", "properties": [],
             "evidence_distance": 2, "rescue_in_relevant_cells": False,
             "competition_eligibility": "ELIGIBLE", "safety_assessment": assessed})
    checks.append(("wrong_direction", r["gate"] == "directionality", r["gate"]))
    # 7. unknown defect_direction -> case BLOCKED
    checks.append(("unknown_direction",
                   len(validate_case(dict(base_case, defect_direction="x"), scoring)) > 0, "case"))
    # 8. ev-dist 999 + string "false" -> BLOCKED
    r = one({"id": "S8", "drug": "b", "net_effect": "inhibit", "properties": [],
             "evidence_distance": 999, "rescue_in_relevant_cells": "false",
             "competition_eligibility": "ELIGIBLE", "safety_assessment": assessed})
    checks.append(("bad_types_blocked", r["verdict"] == "BLOCKED", r["verdict"]))

    ok = all(c[1] for c in checks)
    for name, passed, obs in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {obs}")
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
