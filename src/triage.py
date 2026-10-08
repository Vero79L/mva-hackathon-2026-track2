# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Case-driven candidate triage for N-of-1 rare-disease drug repurposing.

Disease-agnostic: reads a case manifest and a gates config, validates both,
then applies the directionality prerequisite followed by the parameterized
patient-specific hard gates. Unknown or malformed inputs BLOCK — they never
pass silently. Swap the case file to run another disease; no code change.

Usage:
    uv run src/triage.py --case config/cases/bub1b_mva.yaml \
        --candidates evidence/candidates.yaml --scoring config/scoring.yaml
    uv run src/triage.py --selftest      # run the regression checks
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import yaml

NET_EFFECTS = {"strengthen", "inhibit", "restore_or_bypass", "weaken", "none"}


def load(p):
    return yaml.safe_load(Path(p).read_text())


# ---- validation (nothing passes without clean inputs) ----

def known_levels(scoring, gate_key):
    return set(scoring["hard_gates"][gate_key]["rule"].keys())


def validate_case(case, scoring):
    errs = []
    if case.get("defect_direction") not in scoring["directionality"]:
        errs.append(f"unknown defect_direction '{case.get('defect_direction')}' "
                    f"(known: {sorted(scoring['directionality'])})")
    pc = case.get("patient_constraints", {}) or {}
    for gk in ("G1_oncology", "G2_pediatric", "G3_renal", "G4_growth"):
        driver = scoring["hard_gates"][gk]["driver"]
        lvl = pc.get(driver)
        if lvl not in known_levels(scoring, gk):
            errs.append(f"{gk}: constraint '{driver}'='{lvl}' is unknown "
                        f"(known: {sorted(known_levels(scoring, gk))})")
    return errs


def validate_candidate(cand):
    errs = []
    if not cand.get("id") or not cand.get("drug"):
        errs.append("missing id or drug")
    if cand.get("net_effect") not in NET_EFFECTS:
        errs.append(f"net_effect '{cand.get('net_effect')}' invalid (known: {sorted(NET_EFFECTS)})")
    ed = cand.get("evidence_distance")
    if isinstance(ed, bool) or not isinstance(ed, int) or not (0 <= ed <= 5):
        errs.append(f"evidence_distance '{ed}' must be an integer 0-5")
    r = cand.get("rescue_in_relevant_cells", False)
    if not isinstance(r, bool):
        errs.append(f"rescue_in_relevant_cells '{r}' must be a real boolean (not a string)")
    if not isinstance(cand.get("properties", []), list):
        errs.append("properties must be a list")
    return errs


# ---- gate logic ----

def directionality_ok(cand, case, scoring):
    need = scoring["directionality"][case["defect_direction"]]  # validated to exist
    got = cand.get("net_effect")
    if got == need:
        return True, f"net_effect '{got}' matches required '{need}'"
    return False, f"net_effect '{got}' != required '{need}' (wrong direction)"


def gate(cand, case, scoring, gate_key):
    g = scoring["hard_gates"][gate_key]
    level = case["patient_constraints"].get(g["driver"])  # validated to be known
    rule = g["rule"].get(level, {})
    props = set(cand.get("properties", []))
    for action, props_list in rule.items():
        want = set(props_list or [])
        hit = props & want
        if action.startswith("reject_if") and hit:
            return "REJECT", f"{gate_key}[{level}]: candidate is {sorted(hit)}"
        if action.startswith("require"):
            if want and not (props & want):            # empty require list = no requirement
                return "REJECT", f"{gate_key}[{level}]: missing one of {sorted(want)}"
        if action.startswith("flag_if") and hit:
            return "FLAG", f"{gate_key}[{level}]: watch {sorted(hit)}"
    return "PASS", f"{gate_key}[{level}]: ok"


def triage_one(cand, case, scoring):
    cerr = validate_candidate(cand)
    if cerr:
        return {"id": cand.get("id", "?"), "drug": cand.get("drug", "?"),
                "verdict": "BLOCKED", "gate": "input-validation", "reasons": cerr}
    reasons, flags = [], []
    ok, why = directionality_ok(cand, case, scoring)
    reasons.append(why)
    if ok is False:
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
    tier = "STRONG" if (ed >= 3 and cand.get("rescue_in_relevant_cells") is True) else "CONDITIONAL"
    return {"id": cand["id"], "drug": cand["drug"], "verdict": tier,
            "gate": "passed", "flags": flags, "evidence_distance": ed, "reasons": reasons}


def run(case, scoring, cands):
    cerr = validate_case(case, scoring)
    if cerr:
        return {"case_blocked": cerr}, []
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
    print(f"\n=== Triage: {case['case_id']} ({case['disease']}) ===")
    order = {"STRONG": 0, "CONDITIONAL": 1, "REJECT": 2, "BLOCKED": 3}
    for r in sorted(out, key=lambda r: order.get(r["verdict"], 9)):
        flags = f" flags={r.get('flags')}" if r.get("flags") else ""
        print(f"[{r['verdict']:<11}] {r['drug']:<30} ({r['gate']}){flags}")
    n = {k: sum(1 for r in out if r["verdict"] == k) for k in order}
    print("Summary:", n)
    return 0


def selftest(scoring_path):
    """The 5 regression checks the external audit defined, plus case-level checks."""
    scoring = load(scoring_path)
    base_case = {"case_id": "t", "disease": "t", "defect_direction": "channel_overactivity",
                 "patient_constraints": {"age_group": "adult", "malignancy_status": "none",
                                         "renal": "normal", "growth": "normal"}}
    checks = []

    def one(cand, case=base_case):
        return triage_one(cand, case, scoring)

    # 1. adult positive control: approved inhibitor, ev-dist 3, rescue True -> STRONG (empty require must pass)
    r = one({"id": "S1", "drug": "pos", "net_effect": "inhibit", "properties": [],
             "evidence_distance": 3, "rescue_in_relevant_cells": True})
    checks.append(("adult_positive", r["verdict"] == "STRONG", r["verdict"]))
    # 2. wrong direction -> REJECT at directionality
    r = one({"id": "S2", "drug": "wd", "net_effect": "strengthen", "properties": [],
             "evidence_distance": 2})
    checks.append(("wrong_direction", r["gate"] == "directionality" and r["verdict"] == "REJECT", r["verdict"]))
    # 3. unknown defect_direction -> case BLOCKED
    bad = dict(base_case, defect_direction="unmapped")
    cerr = validate_case(bad, scoring)
    checks.append(("unknown_direction", len(cerr) > 0, cerr))
    # 4. age typo -> case BLOCKED
    bad = dict(base_case, patient_constraints=dict(base_case["patient_constraints"], age_group="adlut"))
    cerr = validate_case(bad, scoring)
    checks.append(("unknown_age", len(cerr) > 0, cerr))
    # 5. ev-dist 999 + rescue string "false" -> BLOCKED at input validation
    r = one({"id": "S5", "drug": "bad", "net_effect": "inhibit", "properties": [],
             "evidence_distance": 999, "rescue_in_relevant_cells": "false"})
    checks.append(("bad_types", r["verdict"] == "BLOCKED", r["verdict"]))

    ok = all(c[1] for c in checks)
    for name, passed, obs in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {obs}")
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
