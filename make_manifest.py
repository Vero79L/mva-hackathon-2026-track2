#!/usr/bin/env python3
"""Release manifest: a consistency gate that runs before every submission.

It fails (non-zero exit) when the deliverables disagree with their authoritative
sources, so a report, a pitch script and a candidate table can never go out
saying different things.

What it verifies
  - the candidate denominator is computed once, from docs/candidates_canonical.json,
    and no deliverable still carries an older count
  - the PRIMARY hypothesis line in docs/PRIMARY_HYPOTHESIS.md appears verbatim in
    docs/REPORT.md and docs/PITCH.md
  - no unfilled {{F-...}} slot remains in the report or the pitch
  - every deliverable exists; its SHA-256 is recorded in outputs/manifest.json

Usage:  python3 make_manifest.py          (run from research/engine/)
"""
# Make stdout/stderr UTF-8 regardless of the machine's locale: this repo is read and run by
# reviewers on systems where the preferred encoding may be ASCII, and a crash while *printing*
# a result is still a failed reproduction.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
DOCS = HERE / "docs"
# `--freeze` is the submission-day run: the pre-submission fill slots become blocking too.
FREEZE = "--freeze" in sys.argv[1:]

canon = json.loads((DOCS / "candidates_canonical.json").read_text(encoding="utf-8"))
cands = canon["candidates"]
n_int = sum(1 for c in cands if c["entity_type"] == "intervention")
n_br = sum(1 for c in cands if c["entity_type"] == "mechanism_branch")
n_neg = sum(1 for c in cands if c["entity_type"] == "negative_control")
denominator = (f"{n_int} interventions + {n_br} mechanism-branches + {n_neg} negative-control groups "
               f"= {len(cands)} entries")

ph_text = (DOCS / "PRIMARY_HYPOTHESIS.md").read_text(encoding="utf-8")
m = re.search(r"^PRIMARY:\s*(.+)$", ph_text, re.M)
if not m:
    sys.exit("docs/PRIMARY_HYPOTHESIS.md needs one line starting with 'PRIMARY: '")
primary = m.group(1).strip()

DELIVERABLES = [
    "docs/REPORT.md", "docs/PITCH.md", "docs/METHODS_AND_AI.md", "docs/PRIMARY_HYPOTHESIS.md",
    "docs/SAFETY_ANNEX.md", "docs/MVA_DECISION_TABLE.md",
    "docs/candidate_table.md", "docs/candidates_canonical.json", "docs/computed_vs_human.md",
]
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
                8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
                14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
                19: "nineteen", 20: "twenty", 21: "twenty-one", 22: "twenty-two",
                23: "twenty-three", 24: "twenty-four", 25: "twenty-five", 26: "twenty-six",
                27: "twenty-seven", 28: "twenty-eight", 29: "twenty-nine", 30: "thirty",
                31: "thirty-one", 32: "thirty-two", 33: "thirty-three", 34: "thirty-four",
                35: "thirty-five", 36: "thirty-six"}
WORD_NUM = {v: k for k, v in NUMBER_WORDS.items()}
NUM_RE = r"(\d{1,3}|" + "|".join(sorted(WORD_NUM, key=len, reverse=True)) + r")"


def as_int(tok):
    tok = tok.strip().lower()
    return int(tok) if tok.isdigit() else WORD_NUM.get(tok)


def count_rows(path, predicate=None):
    import csv as _csv
    with path.open(newline="", encoding="utf-8") as fh:
        return sum(1 for r in _csv.DictReader(fh) if predicate is None or predicate(r))


# ---- authoritative counts, computed from the sources themselves ----
# Until 2026-10-19 the only number this gate checked was "N entries". Everything else -- the
# claim-ledger size, the global-negative count, the self-test count, the registered-fact count,
# the product-row count, the number of disclosed safety-classifier interruptions -- was retyped
# by hand into prose and had drifted in five places at once. A reviewer comparing two of our own
# documents would have found it before we did, and in the AI-disclosure section that is expensive.
REG = HERE.parent / "registers"
TRUTH = {}
try:
    TRUTH["claims"] = count_rows(REG / "claim_ledger.csv")
    TRUTH["global-negative"] = count_rows(REG / "claim_ledger.csv",
                                          lambda r: r.get("claim_type") == "global_negative")
except FileNotFoundError:
    pass
try:
    TRUTH["registered facts"] = count_rows(REG / "fact_register.csv")
except FileNotFoundError:
    pass
try:
    TRUTH["product rows"] = count_rows(DOCS / "eligibility_matrix.csv")
except FileNotFoundError:
    pass
# Count the self-tests by RUNNING them, not by counting `checks.append(` calls: one of those
# calls sits in a loop and contributes four checks, so the textual count is wrong by three.
try:
    import subprocess
    _st = subprocess.run([sys.executable, str(HERE / "src" / "triage.py"), "--selftest",
                          "--scoring", str(HERE / "config" / "scoring.yaml")],
                         capture_output=True, text=True, cwd=str(HERE), timeout=120)
    _n = sum(1 for ln in _st.stdout.splitlines() if ln.startswith(("[PASS]", "[FAIL]")))
    if _n:
        TRUTH["self-tests"] = _n
    if _st.returncode != 0:
        problems_selftest = "src/triage.py --selftest does not pass"
    else:
        problems_selftest = None
except Exception as _e:          # never let the gate crash on an environment problem
    problems_selftest = f"could not run the self-tests: {_e}"

# phrase -> which TRUTH key it must agree with. Each is matched case-insensitively.
COUNT_CLAIMS = [
    (r"" + NUM_RE + r"\s+claims\b", "claims"),
    (r"" + NUM_RE + r"\s+global-negative\b", "global-negative"),
    (r"" + NUM_RE + r"\s+registered facts\b", "registered facts"),
    (r"" + NUM_RE + r"\s+product rows\b", "product rows"),
    (r"" + NUM_RE + r"[\s-]+(?:regression\s+)?self-tests\b", "self-tests"),
]
CHECKED_FOR_COUNTS = ["docs/REPORT.md", "docs/PITCH.md", "docs/METHODS_AND_AI.md",
                      "docs/PRIMARY_HYPOTHESIS.md", "docs/SAFETY_ANNEX.md",
                      "../registers/claim_ledger.csv"]

problems = []
pending = []
if problems_selftest:
    problems.append(problems_selftest)
for rel in ("docs/REPORT.md", "docs/PITCH.md"):
    path = HERE / rel
    if not path.exists():
        problems.append(f"{rel}: missing"); continue
    text = path.read_text(encoding="utf-8")
    if primary not in text:
        problems.append(f"{rel}: the PRIMARY line is not quoted verbatim")
    stale = re.findall(r"\b(\d{1,2}|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s+entries\b", text, re.I)
    for hit in stale:
        value = int(hit) if hit.isdigit() else next((k for k, v in NUMBER_WORDS.items() if v == hit.lower()), None)
        if value is not None and value != len(cands):
            problems.append(f"{rel}: says '{hit} entries' but the canonical table has {len(cands)}")
    slots = sorted(set(re.findall(r"\{\{FILL:[A-Z0-9-]+\}\}", text)))
    if slots:
        # These are filled at freeze (the frozen date and the pitch-video URL), so before the
        # freeze they are PENDING, not an inconsistency. `--freeze` makes them blocking.
        (problems if FREEZE else pending).append(f"{rel}: slots still to fill at freeze {slots}")

# ---- every retyped count must equal its source ----
for rel in CHECKED_FOR_COUNTS:
    path = HERE / rel
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    for pattern, key in COUNT_CLAIMS:
        if key not in TRUTH:
            continue
        for mm in re.finditer(pattern, text, re.I):
            got = as_int(mm.group(1))
            if got is not None and got != TRUTH[key]:
                problems.append(f"{rel}: says '{mm.group(0).strip()}' but {key} is {TRUTH[key]}")

# ---- the citation-verification artefact must not be older than the chain it verifies ----
# It was silently stale on 2026-10-19: the chain had gained PMIDs since the last run, and nothing
# said so. Staleness is PENDING rather than BLOCKED because the verifier needs network access the
# submission environment may not have; --freeze makes it blocking.
_cc = HERE.parent / "registers" / "citation_check.csv"
_mg = DOCS / "mechanism_graph.yaml"
if _cc.exists() and _mg.exists() and _cc.stat().st_mtime < _mg.stat().st_mtime:
    (problems if FREEZE else pending).append(
        "registers/citation_check.csv is older than docs/mechanism_graph.yaml — re-run "
        "scripts/phase1/16_verify_citations.py from a network that can reach Europe PMC/Crossref")

# ---- the two AI-disclosure documents must report the same number of interruptions ----
INTERRUPT = re.compile(NUM_RE + r"\**\s+responses?\s+(?:was|were)\s+interrupted", re.I)
seen = {}
for rel in ("docs/REPORT.md", "docs/METHODS_AND_AI.md"):
    path = HERE / rel
    if path.exists():
        m2 = INTERRUPT.search(path.read_text(encoding="utf-8"))
        if m2:
            seen[rel] = as_int(m2.group(1))
if len(set(seen.values())) > 1:
    problems.append("safety-classifier interruption count disagrees between deliverables: "
                    + ", ".join(f"{k}={v}" for k, v in seen.items()))

manifest = {"generated_from": "docs/candidates_canonical.json " + canon.get("updated", ""),
            "denominator": denominator, "primary_hypothesis": primary, "files": {}}
for rel in DELIVERABLES:
    path = HERE / rel
    if not path.exists():
        problems.append(f"missing deliverable {rel}"); continue
    manifest["files"][rel] = hashlib.sha256(path.read_bytes()).hexdigest()

if problems:
    print("MANIFEST BLOCKED — fix before submitting:")
    for item in problems:
        print("  -", item)
    sys.exit(1)

(HERE / "outputs").mkdir(exist_ok=True)
(HERE / "outputs" / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("manifest OK" + (" (freeze mode)" if FREEZE else ""))
for item in pending:
    print("  PENDING (filled at freeze; run with --freeze to make this blocking):", item)
print(" counts verified:", ", ".join(f"{k}={v}" for k, v in sorted(TRUTH.items())))
print(" denominator:", denominator)
print(" primary    :", primary[:90] + ("…" if len(primary) > 90 else ""))
print(f" files      : {len(manifest['files'])} hashed -> outputs/manifest.json")
