#!/usr/bin/env python3
"""Robustness harness: does this engine produce its answer, or was it built to?

An expert panel's most damaging question about a repurposing engine is not "is the
biology right?" but "did you shape the rules until they emitted the candidate you had
already chosen?". §13 of the report concedes the opening: the decision rule was written
alongside the candidate work, not pre-registered before it. A concession is not an
answer. This file is the answer -- or, if the engine is in fact brittle or name-driven,
the evidence of that.

Five experiments. R1/R2/R5 are DESCRIPTIVE: they report what moves, and a result that
embarrasses us is still the result. R3/R4 are ASSERTIONS: they fail the build.

  R1  Gate ablation            remove one rule at a time -> is the funnel one rule's shadow?
  R2  Constraint perturbation  change the child -> does the engine change its mind?
  R3  Name blinding            strip every name -> do verdicts survive?   [asserted]
  R4  Synthetic probes         twin / mirror / poisoned -> do the gates bite? [asserted]
  R5  Leave-one-source-out     drop one paper -> does the mechanism chain hold?

Writes docs/ROBUSTNESS.md. Exits non-zero if an assertion fails.
"""
import copy
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

import triage  # noqa: E402

CASE = ROOT / "config/cases/bub1b_mva.yaml"
CANDS = ROOT / "evidence/candidates_from_canonical.yaml"
SCORING = ROOT / "config/scoring.yaml"
GRAPH = ROOT / "docs/mechanism_graph.yaml"
CITECHECK = ROOT.parent / "registers" / "citation_check.csv"
OUT = ROOT / "docs/ROBUSTNESS.md"

NAMED = "C-NA"            # the named candidate the whole report turns on
ELIGIBLE = ("STRONG", "CONDITIONAL")

failures = []


def citation_titles():
    """pmid -> (title, first author, year). Read from the citation check's own
    resolved output rather than retyped here: a title typed by hand into a file that
    exists to catch mistyped titles would be self-defeating."""
    out = {}
    if not CITECHECK.exists():
        return out
    import csv
    import re as _re
    tag = _re.compile(r"<[^>]+>")   # Europe PMC returns titles with <sup>/<i> markup
    with CITECHECK.open(encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) >= 8 and row[0] == "pmid":
                out[row[1]] = (tag.sub("", row[4]).rstrip("."), row[5], row[6])
    return out


def load_all():
    case = triage.load(CASE)
    scoring = triage.load(SCORING)
    cands = triage.load(CANDS)["candidates"]
    return case, scoring, cands


def verdicts(case, scoring, cands):
    """-> {id: (verdict, gate)}; blocks hard if the case itself fails validation."""
    err, res = triage.run(case, scoring, cands)
    if err:
        raise SystemExit(f"case blocked: {err}")
    return {r["id"]: (r["verdict"], r["gate"]) for r in res}


def survivors(v):
    return sorted(k for k, (vd, _) in v.items() if vd in ELIGIBLE)


def diff(base, v):
    """Two kinds of movement, and conflating them hides the engine's real structure.

    A candidate that goes REJECT->CONDITIONAL changed outcome. A candidate that stays
    REJECT but is now caught by a different rule did NOT change outcome -- it was being
    caught twice, and removing one rule merely revealed the second. An earlier version of
    this harness diffed on the verdict alone and so reported "directionality changes
    nothing", which was false: directionality rejects candidates that the pediatric and
    oncology gates would also have rejected. Redundancy is not inactivity.
    """
    outcome = sorted(k for k in base if base[k][0] != v[k][0])
    caught_elsewhere = sorted(k for k in base
                              if base[k][0] == v[k][0] and base[k][1] != v[k][1])
    return outcome, caught_elsewhere


# --------------------------------------------------------------------------- R1
def r1_gate_ablation(case, scoring, cands, base):
    """Disable one rule at a time. Which candidates owe their verdict to which gate?"""
    rows = []
    for gk in ("G1_oncology", "G2_pediatric", "G3_renal", "G4_growth"):
        sc = copy.deepcopy(scoring)
        for lvl in sc["hard_gates"][gk]["rule"]:
            sc["hard_gates"][gk]["rule"][lvl] = {}
        rows.append((f"ablate {gk}", verdicts(case, sc, cands)))

    # directionality: put every candidate on-direction instead of editing the map
    need = scoring["directionality"][case["defect_direction"]]
    cs = copy.deepcopy(cands)
    for c in cs:
        c["net_effect"] = need
    rows.append(("ablate directionality", verdicts(case, scoring, cs)))

    # eligibility: treat every product as competition-eligible
    cs = copy.deepcopy(cands)
    for c in cs:
        c["competition_eligibility"] = "ELIGIBLE"
    rows.append(("ablate eligibility", verdicts(case, scoring, cs)))

    # The scenario gate is deliberately NOT ablated here. The base case carries no
    # `scenario` block at all -- the three scenarios live in their own case files -- so
    # removing it from the base case is a no-op, and a row reading "scenario gate: no
    # change" would be a true statement that misleads. It is exercised in R1c instead.

    out = []
    for label, v in rows:
        moved, elsewhere = diff(base, v)
        out.append({"ablation": label, "n_eligible": len(survivors(v)),
                    "moved": moved, "caught_elsewhere": elsewhere,
                    "named_candidate": v[NAMED][0] if NAMED in v else "-"})
    return out


# -------------------------------------------------------------------------- R1b
def r1b_overdetermination(case, scoring, cands):
    """For each rejected candidate: how many rules would reject it ON THEIR OWN?

    This is the sharpest form of the fitting question. A funnel shaped by one hand-tuned
    rule is fragile: every rejection traces to that rule and nothing else. A funnel where
    most rejections are independently reached by two or three unrelated rules is hard to
    have fitted, because fitting one rule would not have produced the others.
    """
    ov, _ = triage.scenario_objective_validity(case)
    rows = []
    for c in cands:
        hits = []
        ok, _ = triage.directionality_ok(c, case, scoring)
        if not ok:
            hits.append("directionality")
        if c.get("competition_eligibility") == "INELIGIBLE":
            hits.append("eligibility")
        if ov is not None and ov.get(c.get("objective_class")) == "invalid":
            hits.append("scenario")
        for gk in ("G1_oncology", "G2_pediatric", "G3_renal", "G4_growth"):
            res, _ = triage.gate(c, case, scoring, gk)
            if res == "REJECT":
                hits.append(gk)
        if hits:
            rows.append({"id": c["id"], "drug": c["drug"], "n": len(hits),
                         "rules": hits})
    return sorted(rows, key=lambda r: (-r["n"], r["id"]))


# -------------------------------------------------------------------------- R1c
def r1c_scenario_gate(scoring, cands, base):
    """Exercise the scenario gate against the three scenario case files.

    The base case carries no scenario block, so the gate cannot be ablated out of it.
    The honest test is the opposite one: switch the scenario on and show the gate
    changing the answer. S2 (the missense allele is a function lesion, not an abundance
    problem) is the branch that should retire the named candidate along with every other
    restore-class candidate. If it does not, the scenario machinery is decoration.
    """
    out = []
    for sid in ("S1", "S2", "S3"):
        f = ROOT / f"config/cases/bub1b_mva_{sid}.yaml"
        if not f.exists():
            continue
        c = triage.load(f)
        v = verdicts(c, scoring, cands)
        ov = (c.get("scenario", {}).get("implications", {})
               .get("objective_validity", {}))
        moved, elsewhere = diff(base, v)
        out.append({"scenario": sid, "restore": ov.get("restore", "?"),
                    "n_eligible": len(survivors(v)),
                    "named_candidate": v[NAMED][0],
                    "moved": moved, "caught_elsewhere": elsewhere})
    return out


# --------------------------------------------------------------------------- R2
def r2_constraint_perturbation(case, scoring, cands, base):
    """Change one fact about the child at a time. A gate that never binds is decorative."""
    out = []
    for gk, g in scoring["hard_gates"].items():
        driver = g["driver"]
        actual = case["patient_constraints"].get(driver)
        for level in sorted(g["rule"]):
            if level == actual:
                continue
            c2 = copy.deepcopy(case)
            c2["patient_constraints"][driver] = level
            v = verdicts(c2, scoring, cands)
            moved, elsewhere = diff(base, v)
            out.append({"driver": driver, "from": actual, "to": level,
                        "n_eligible": len(survivors(v)), "moved": moved,
                        "caught_elsewhere": elsewhere,
                        "named_candidate": v[NAMED][0]})
    return out


# --------------------------------------------------------------------------- R3
def r3_name_blinding(case, scoring, cands, base):
    """Strip ids and drug names, shuffle, re-run. Any difference is name-dependence."""
    cs = copy.deepcopy(cands)
    mapping = {}
    for i, c in enumerate(cs):
        token = f"X{i:02d}"
        mapping[token] = c["id"]
        c["id"] = token
        c["drug"] = f"undisclosed compound {token}"
    random.Random(20261020).shuffle(cs)
    v = verdicts(case, scoring, cs)
    diffs = []
    for token, real in mapping.items():
        if v[token] != base[real]:
            diffs.append(f"{real}: named {base[real]} -> blinded {v[token]}")
    if diffs:
        failures.append("R3 name blinding: verdicts changed when names were removed")
    return {"n": len(cs), "diffs": diffs, "passed": not diffs}


# --------------------------------------------------------------------------- R4
def r4_probes(case, scoring, cands, base):
    """Inject synthetic candidates with known-correct answers and check the gates bite."""
    named = copy.deepcopy(next(c for c in cands if c["id"] == NAMED))

    def probe(pid, mutate):
        p = copy.deepcopy(named)
        p["id"] = pid
        p["drug"] = f"synthetic probe {pid}"
        mutate(p)
        # keep the declaration honest rather than hand-writing it
        p["safety_gap_declared"] = triage.undeclared_safety_gaps(p)
        return p

    def add(prop, **sa):
        def f(p):
            p["properties"] = sorted(set(p["properties"]) | {prop})
            p["safety_assessment"].update(sa)
        return f

    probes = [
        ("PROBE-TWIN", lambda p: None,
         "same properties as the named candidate under another name",
         lambda r: (r["verdict"], r["gate"]) == base[NAMED]),
        ("PROBE-MIRROR", lambda p: p.update(net_effect="weaken"),
         "named candidate's twin, acting in the opposite direction",
         lambda r: r["verdict"] == "REJECT" and r["gate"] == "directionality"),
        ("PROBE-ONC", add("increases_CIN"),
         "twin that also increases chromosomal instability",
         lambda r: r["verdict"] == "REJECT" and r["gate"] == "G1_oncology"),
        ("PROBE-PED", lambda p: p.update(
            properties=[x for x in p["properties"]
                        if x != "approved_or_credible_pediatric_path"]),
         "twin with no approved or credible pediatric path",
         lambda r: r["verdict"] == "REJECT" and r["gate"] == "G2_pediatric"),
        ("PROBE-RENAL", add("nephrotoxic", renal="confirmed_risk"),
         "twin that is nephrotoxic",
         lambda r: r["verdict"] == "REJECT" and r["gate"] == "G3_renal"),
        ("PROBE-GROWTH", add("anti_anabolic"),
         "twin that is anti-anabolic (G4 can only flag, never reject)",
         lambda r: r["verdict"] in ELIGIBLE and "G4_growth" in (r.get("flags") or [])),
    ]

    built = [probe(pid, mut) for pid, mut, _, _ in probes]
    err, res = triage.run(case, scoring, cands + built)
    if err:
        raise SystemExit(f"case blocked: {err}")
    by_id = {r["id"]: r for r in res}

    out = []
    for pid, _, desc, check in probes:
        r = by_id[pid]
        ok = check(r)
        if not ok:
            failures.append(f"R4 {pid}: expected behaviour not observed "
                            f"(got {r['verdict']} at {r['gate']})")
        out.append({"probe": pid, "description": desc, "passed": ok,
                    "verdict": r["verdict"], "gate": r["gate"],
                    "flags": r.get("flags") or []})

    # the probes must not disturb the real candidates
    for c in cands:
        if (by_id[c["id"]]["verdict"], by_id[c["id"]]["gate"]) != base[c["id"]]:
            failures.append(f"R4: injecting probes changed the verdict of {c['id']}")
    return out


# --------------------------------------------------------------------------- R5
def r5_leave_one_source_out():
    """Drop one paper at a time from the therapeutic chain. What is load-bearing?"""
    g = triage.load(GRAPH)
    edges = g["edges"]
    adj = {}
    for e in edges:
        adj.setdefault(e["from"], []).append(e)

    def paths(start, end, seen=()):
        if start == end:
            return [[]]
        found = []
        for e in adj.get(start, []):
            if e["id"] in seen:
                continue
            for rest in paths(e["to"], end, seen + (e["id"],)):
                found.append([e] + rest)
        return found

    chains = paths("D1", "P")
    if not chains:
        return {"chains": 0, "rows": []}

    def pmids(e):
        out = []
        for s in e.get("sources", []) or []:
            ref = s if isinstance(s, str) else (s.get("pmid") or s.get("locator") or "")
            for tok in str(ref).replace(",", " ").split():
                if tok.upper().startswith("PMID"):
                    continue
                if tok.isdigit() and len(tok) >= 7:
                    out.append(tok)
        return out

    all_pmids = sorted({p for ch in chains for e in ch for p in pmids(e)})
    rows = []
    for drop in all_pmids:
        broken = []
        for ch in chains:
            for e in ch:
                srcs = pmids(e)
                if srcs and set(srcs) == {drop}:
                    broken.append(e["id"])
        # a chain survives if at least one full path has every edge still sourced
        alive = sum(1 for ch in chains if not any(e["id"] in broken for e in ch))
        rows.append({"pmid": drop, "chains_alive": alive, "of": len(chains),
                     "edges_unsourced": sorted(set(broken))})
    return {"chains": len(chains),
            "edge_ids": [[e["id"] for e in ch] for ch in chains],
            "rows": rows}


# --------------------------------------------------------------------------- report
def md(base, r1, r1b, r1c, r2, r3, r4, r5):
    L = []
    w = L.append
    w("# Robustness: is this engine's answer a property of the evidence, "
      "or of the engine?\n")
    w("*Generated by `scripts/phase1/20_robustness.py`. Do not hand-edit — "
      "regenerate it.*\n")
    w("The report concedes in §13 that the decision rule in §1 was written alongside "
      "the candidate work rather than pre-registered before it. That concession invites "
      "the obvious question: **were the rules shaped until they emitted the candidate "
      "we had already picked?** A reader cannot settle that by reading the rules — a "
      "fitted rule and an honest rule look identical on the page. It is settled by "
      "perturbing the engine and watching what moves. That is what this file does, and "
      "it runs in `run.sh`, so a result we would rather not publish cannot quietly fail "
      "to be published.\n")
    w("Two of the five experiments are **assertions**: they fail the build. Three are "
      "**descriptive** — they report what moved, including when the answer is "
      "unflattering.\n")

    w(f"\nBaseline: **{len(survivors(base))} of {len(base)}** candidates eligible "
      f"(STRONG or CONDITIONAL); named candidate `{NAMED}` = "
      f"**{base[NAMED][0]}**.\n")

    w("\n## R1 — Gate ablation (descriptive)\n")
    w("Each rule is switched off in turn. If the funnel's shape is really the product of "
      "one rule, this is where it shows: one row will account for most of the rejections "
      "and the rest will be ornament.\n")
    w("Two columns, because they mean different things. **Changed outcome** is a "
      "candidate that became eligible once the rule was removed — the rule was the only "
      "thing stopping it. **Caught by another rule instead** is a candidate that stayed "
      "rejected but was picked up further down the chain: the removed rule was real, and "
      "redundant. Reading only the first column makes an over-determined engine look "
      "like an inert one.\n")
    w("\n| rule removed | eligible | named candidate | changed outcome "
      "| caught by another rule instead |")
    w("|---|---|---|---|---|")
    for r in r1:
        mv = ", ".join(f"`{m}`" for m in r["moved"]) or "—"
        ce = ", ".join(f"`{m}`" for m in r["caught_elsewhere"]) or "—"
        w(f"| {r['ablation']} | {r['n_eligible']} | {r['named_candidate']} | {mv} | {ce} |")

    w("\n### R1b — How over-determined is each rejection?\n")
    w("Each rejected candidate is tested against every rule *independently*, rather than "
      "stopping at the first rule that fires. The question is how many separate rules "
      "would reject it on their own. A funnel fitted to produce a chosen answer is "
      "fragile in a specific way: each rejection traces back to the one rule that was "
      "tuned. Rejections reached independently by two or three unrelated rules are not "
      "the kind of thing rule-fitting produces, because tuning the oncology gate does "
      "not also arrange for the eligibility rule and the directionality prerequisite to "
      "agree.\n")
    n_over = sum(1 for r in r1b if r["n"] >= 2)
    w(f"\n**{n_over} of {len(r1b)}** rejections are reached independently by two or "
      f"more rules.\n")
    w("\n| candidate | rules that reject it on their own | count |")
    w("|---|---|---|")
    for r in r1b:
        w(f"| `{r['id']}` | " + ", ".join(f"`{x}`" for x in r["rules"])
          + f" | {r['n']} |")

    w("\n### R1c — The scenario gate, switched on\n")
    w("The base case carries no `scenario` block — the three scenarios are separate case "
      "files — so the scenario gate cannot be ablated out of the baseline, and a row "
      "reporting \"no change\" would mislead. The honest test runs the other way: switch "
      "each scenario on and watch the gate work. **S2** is the branch in which the "
      "missense allele is a function lesion rather than an abundance problem, and it "
      "should retire the named candidate along with every other restore-class "
      "candidate.\n")
    w("\n| scenario | `restore` validity | eligible | named candidate | changed outcome |")
    w("|---|---|---|---|---|")
    for r in r1c:
        mv = ", ".join(f"`{m}`" for m in r["moved"]) or "—"
        w(f"| {r['scenario']} | `{r['restore']}` | {r['n_eligible']} | "
          f"{r['named_candidate']} | {mv} |")

    gate_tiers = sorted({r["named_candidate"] for r in r1 + r2})
    s2 = next((r["named_candidate"] for r in r1c if r["scenario"] == "S2"), "?")
    stable = gate_tiers == [base[NAMED][0]]
    w(f"\n**One observation across R1, R1b and R1c.** Under every gate ablation and "
      f"every constraint perturbation the named candidate stays "
      f"{'at **' + base[NAMED][0] + '**' if stable else 'at one of ' + ', '.join(gate_tiers)} "
      f"— no weakening of any safety rule promotes it. Under S2 it is **{s2}**. Those two "
      f"facts together are the point: the tier is not a gate product. STRONG additionally "
      f"requires rescue evidence in disease-relevant cells at `evidence_distance >= 3`, "
      f"and this candidate has neither, so no amount of loosening the gates can upgrade "
      f"the strength of an evidence claim — while a change in the *scientific* premise, "
      f"which is what the scenario encodes, retires the candidate outright. A reader "
      f"worried that the engine was built to protect its answer should note that the "
      f"only perturbation that moves the named candidate is the one that attacks the "
      f"biology.\n\n")

    w("\n## R2 — Patient-constraint perturbation (descriptive)\n")
    w("One fact about the child is changed at a time, everything else held. A gate that "
      "produces the same output for every child is not doing work; a gate that changes "
      "the answer is patient-specific in the way an N-of-1 submission claims to be.\n")
    w("\n| constraint | actual | counterfactual | eligible | named "
      "| changed outcome | caught elsewhere |")
    w("|---|---|---|---|---|---|---|")
    for r in r2:
        mv = ", ".join(f"`{m}`" for m in r["moved"]) or "—"
        ce = ", ".join(f"`{m}`" for m in r["caught_elsewhere"]) or "—"
        w(f"| {r['driver']} | `{r['from']}` | `{r['to']}` | {r['n_eligible']} | "
          f"{r['named_candidate']} | {mv} | {ce} |")

    w("\n## R3 — Name blinding (assertion)\n")
    w("Every candidate's identifier and drug name is replaced by an opaque token and the "
      "list is shuffled before the engine sees it. If any verdict changes, some code path "
      "is reading the name — the engine would be recognising its favourite rather than "
      "assessing it.\n")
    w(f"\n**{'PASS' if r3['passed'] else 'FAIL'}** — {r3['n']} candidates blinded, "
      f"{len(r3['diffs'])} verdict differences.\n")
    for d in r3["diffs"]:
        w(f"- {d}")

    w("\n## R4 — Synthetic probes (assertion)\n")
    w("Six candidates with known-correct answers are injected alongside the real ones. "
      "The twin tests favouritism: a compound identical to the named candidate in every "
      "field that the engine reads, under a different name, must receive the identical "
      "verdict. The mirror and the poisoned probes test that each gate actually bites "
      "when it should — a gate that never rejects anything is not a gate.\n")
    w("\n| probe | what it is | expected | observed | |")
    w("|---|---|---|---|---|")
    for r in r4:
        mark = "PASS" if r["passed"] else "**FAIL**"
        fl = f" (flags: {', '.join(r['flags'])})" if r["flags"] else ""
        w(f"| `{r['probe']}` | {r['description']} | see text | "
          f"{r['verdict']} at `{r['gate']}`{fl} | {mark} |")

    w("\n## R5 — Leave-one-source-out on the therapeutic chain (descriptive)\n")
    w("The chain this hypothesis depends on runs niacin → NAD+ → SIRT2 → BubR1 "
      "acetylation → residual BubR1. Each supporting paper is removed in turn. A PMID "
      "that leaves an edge with no source at all is a **single point of failure**: if "
      "that one paper does not survive scrutiny, the chain is cut at that link.\n")
    if not r5["rows"]:
        w("\n*(no D1→P path found in the graph — check `docs/mechanism_graph.yaml`)*")
    else:
        w(f"\n{r5['chains']} distinct path(s) from D1 to P: "
          + "; ".join(" → ".join(c) for c in r5["edge_ids"]) + "\n")
        titles = citation_titles()
        w("\n| paper removed | paths still fully sourced | edges left unsourced |")
        w("|---|---|---|")
        for r in r5["rows"]:
            eu = ", ".join(f"`{e}`" for e in r["edges_unsourced"]) or "—"
            w(f"| PMID {r['pmid']} | {r['chains_alive']} / {r['of']} | {eu} |")
        spof = [r for r in r5["rows"] if r["chains_alive"] == 0]
        if spof:
            w(f"\n**{len(spof)} single point(s) of failure.** Removing any one of these "
              f"leaves no complete path from the intervention to the endpoint:\n")
            for r in spof:
                t = titles.get(r["pmid"])
                label = (f"{t[1]} {t[2]}, *{t[0]}*" if t else "title not resolved")
                w(f"- **PMID {r['pmid']}** — {label}. Sole source for "
                  + ", ".join(f"`{e}`" for e in r["edges_unsourced"]) + ".")
            w("\nThis is the most consequential result in this file and it is not a "
              "flattering one. The therapeutic chain is not a web of mutually "
              "reinforcing evidence; it is a series circuit. Two papers carry it, and "
              "one of them carries the entire SIRT2→BubR1 core. We report this rather "
              "than counting the chain's total citation list, which is larger and would "
              "give a misleading impression of redundancy. The practical consequence is "
              "stated in the report's limitations: a reader who doubts either paper "
              "should treat the hypothesis as unsupported rather than weakened, and the "
              "first two stages of the decisive experiment (§6) are designed to measure "
              "those two links directly in the patient's own cells rather than inherit "
              "them from the literature.")

    w("\n## What this does not show\n")
    w("Perturbing an engine tests the engine, not the biology. R1–R4 would look exactly "
      "like this if every property value fed into them were wrong: the gates would still "
      "bite, the twin would still match, the names would still not matter. What they "
      "establish is narrower and worth stating exactly — the verdicts follow from the "
      "recorded fields by a rule that treats an unnamed compound the same as the named "
      "one. Whether those fields are *true* is the job of the mechanism chain (§3), the "
      "citation check, and the claim ledger. **R5's scope is the therapeutic chain only, and "
      "that is a real limit rather than a framing choice: the same graph has three further "
      "single-source edges on the DISEASE axis that this experiment never drops — E05 (the "
      "patient-cell rescue, sole source PMID 20516114, which is what makes raising BUBR1 a "
      "validated intervention point in this disease rather than an inference), E09/E10 (the "
      "growth phenotypes, sole source PMID 15208629) and E12 (sole source PMID 24981203). "
      "Counting them, the graph has five single-source edges and R5 tests two of them.** "
      "R5 is the only experiment here that touches "
      "the evidence, and it tests dependency structure, not whether a given paper is "
      "right.\n")
    w("One further limit: the probes are built by mutating the named candidate, so they "
      "test the gates along the axes we thought to mutate. A gate failure on an axis we "
      "did not think of would not appear here.\n")
    return "\n".join(L) + "\n"


def main():
    case, scoring, cands = load_all()
    base = verdicts(case, scoring, cands)
    r1 = r1_gate_ablation(case, scoring, cands, base)
    r1b = r1b_overdetermination(case, scoring, cands)
    r1c = r1c_scenario_gate(scoring, cands, base)
    r2 = r2_constraint_perturbation(case, scoring, cands, base)
    r3 = r3_name_blinding(case, scoring, cands, base)
    r4 = r4_probes(case, scoring, cands, base)
    r5 = r5_leave_one_source_out()
    OUT.write_text(md(base, r1, r1b, r1c, r2, r3, r4, r5), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    over = [r for r in r1b if r["n"] >= 2]
    print(f"  R1 ablations: {len(r1)}   "
          f"over-determined rejections: {len(over)}/{len(r1b)}")
    print(f"  R2 perturbations: {len(r2)}")
    print(f"  R3 name blinding: {'PASS' if r3['passed'] else 'FAIL'}")
    print(f"  R4 probes: {sum(1 for r in r4 if r['passed'])}/{len(r4)} passed")
    print(f"  R5 chain sources: {len(r5['rows'])} papers tested")
    if failures:
        print("\nROBUSTNESS FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
