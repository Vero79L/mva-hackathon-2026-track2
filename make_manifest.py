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

import hashlib, json, math, re, sys
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
    "docs/ROBUSTNESS.md", "docs/PLAIN_LANGUAGE_SUMMARY.md",
    # The organizers' own methods form. It is a submitted deliverable and a judge opens it, but
    # being a .xlsx it was read by nothing: on 2026-10-20 it still said "36 claims: ... 11
    # regulatory" after the ledger had grown, and it carried a global negative the report had
    # already withdrawn. A gate that checks only the files it finds easy to read is a gate with a
    # hole shaped like a spreadsheet.
    "docs/Vero7878_track2_methods.xlsx",
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


def deliverable_text(path):
    """The text of a deliverable, including the .xlsx methods form.

    Everything else here is Markdown, JSON or CSV and reads as text. The methods spreadsheet is a
    zip, so `read_text` returns binary noise and every count check silently matched nothing in it.
    Pull the cell text out instead: sheet1 holds inline strings in this workbook, and
    sharedStrings is read too in case a later edit moves them there.
    """
    if path.suffix.lower() == ".xlsx":
        import zipfile
        try:
            with zipfile.ZipFile(path) as z:
                parts = [n for n in z.namelist()
                         if n.endswith(("sharedStrings.xml",)) or re.search(r"worksheets/sheet\d+\.xml$", n)]
                raw = " ".join(z.read(n).decode("utf-8", errors="replace") for n in sorted(parts))
        except Exception as ex:                      # a corrupt deliverable is a problem, not a pass
            return f"__UNREADABLE_XLSX__ {ex}"
        import html as _html
        return _html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return path.read_text(encoding="utf-8")


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
# "N load-bearing PMIDs" is a count the report states about itself and nothing checked it.
# Load-bearing means a citation that carries part of the argument and therefore has a recorded
# title to compare against; the `manual` rows are UniProt feature annotations pulled in by
# --include-uniprot and carry none of it. Adding a citation to the mechanism graph without
# updating the prose is exactly the drift this gate exists to catch.
try:
    TRUTH["load-bearing PMIDs"] = count_rows(REG / "citation_check.csv",
                                             lambda r: r.get("title_check") == "match")
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

# The size of the phase-1 suite is retyped in four places: the README's Tests section, the runbook's
# run table, the methods prose and the runner's own usage line. It drifted three times (75 -> 77 ->
# 78) and this gate caught none of them, because the number lives in test files rather than in a
# register, so nothing computed it. Counting `def test_` statically is exact for this suite -- every
# test is a plain method, none is generated in a loop -- and it costs nothing, unlike running the
# suite from inside the gate.
_testfiles = sorted((HERE / "tests" / "phase1").glob("test_*.py"))
if _testfiles:
    TRUTH["phase-1 tests"] = sum(len(re.findall(r"^\s*def test_", f.read_text(encoding="utf-8"), re.M))
                                 for f in _testfiles)

# phrase -> which TRUTH key it must agree with. Each is matched case-insensitively.
COUNT_CLAIMS = [
    (r"" + NUM_RE + r"\s+claims\b", "claims"),
    (r"" + NUM_RE + r"\s+global-negative\b", "global-negative"),
    (r"" + NUM_RE + r"\s+registered facts\b", "registered facts"),
    (r"" + NUM_RE + r"\s+product rows\b", "product rows"),
    (r"" + NUM_RE + r"[\s-]+(?:regression\s+)?self-tests\b", "self-tests"),
    (r"\*{0,2}" + NUM_RE + r"\*{0,2}\s+load-bearing PMIDs\b", "load-bearing PMIDs"),
]
CHECKED_FOR_COUNTS = ["docs/REPORT.md", "docs/PITCH.md", "docs/METHODS_AND_AI.md",
                      "docs/PRIMARY_HYPOTHESIS.md", "docs/SAFETY_ANNEX.md",
                      "docs/PLAIN_LANGUAGE_SUMMARY.md", "docs/MVA_DECISION_TABLE.md",
                      "docs/ROBUSTNESS.md",
                      "docs/Vero7878_track2_methods.xlsx",
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
    slots = sorted(set(re.findall(r"\{\{FILL:[A-Z0-9-]+\}\}", text)))
    if slots:
        # These are filled at freeze (the frozen date and the pitch-video URL), so before the
        # freeze they are PENDING, not an inconsistency. `--freeze` makes them blocking.
        (problems if FREEZE else pending).append(f"{rel}: slots still to fill at freeze {slots}")

# ---- the candidate denominator must agree in EVERY deliverable, not just two ----
# This check used to run on the report and the pitch only. The denominator is the number a
# reviewer is most likely to carry from one document to another, so every deliverable that
# states it has to be checked, including ones added later.
ENTRIES_RE = re.compile(r"\b" + NUM_RE + r"\s+entries\b", re.I)
for rel in DELIVERABLES:
    path = HERE / rel
    if not path.exists():
        continue
    for mm in ENTRIES_RE.finditer(deliverable_text(path)):
        got = as_int(mm.group(1))
        if got is not None and got != len(cands):
            problems.append(f"{rel}: says '{mm.group(0).strip()}' but the canonical "
                            f"table has {len(cands)}")

# ---- every retyped count must equal its source ----
for rel in CHECKED_FOR_COUNTS:
    path = HERE / rel
    if not path.exists():
        continue
    text = deliverable_text(path)
    if text.startswith("__UNREADABLE_XLSX__"):
        problems.append(f"{rel}: cannot be read as a deliverable - {text}")
        continue
    for pattern, key in COUNT_CLAIMS:
        if key not in TRUTH:
            continue
        for mm in re.finditer(pattern, text, re.I):
            got = as_int(mm.group(1))
            if got is not None and got != TRUTH[key]:
                problems.append(f"{rel}: says '{mm.group(0).strip()}' but {key} is {TRUTH[key]}")

# ---- claims we have WITHDRAWN must not survive anywhere a judge reads ----
# Twice now a retracted statement outlived its retraction in a file nobody greps. The readthrough
# global negative sat in the organizers' .xlsx methods form after the report had withdrawn it (found
# 2026-10-20, and only because the gate learned to read .xlsx). The ClinVar negative -- false rather
# than merely stale -- sat in that same form in three places, in the report and in two registers
# (found 2026-10-21, by querying ClinVar at gene level). A withdrawn claim is worse than an
# uncorrected one: the submission's own documents then contradict each other, and the reviewer
# decides which of us to believe. Each entry below is the exact wording as it was PUBLISHED, so a
# correction that quotes what the text used to say does not trip it.
WITHDRAWN = [
    ("neither allele has a ClinVar record in the 2026-10-04 release",
     "withdrawn 2026-10-21: the truncating allele is ClinVar VCV000533901, Pathogenic/Likely pathogenic, two-star"),
    ("neither variant has a ClinVar record",
     "withdrawn 2026-10-21, the report's own wording of the same false negative"),
    ("there was nothing to look up",
     "withdrawn 2026-10-21: there was a record to look up"),
    ("This closes the readthrough route",
     "withdrawn 2026-10-20: ataluren retains a Great Britain marketing authorisation"),
]
for rel in CHECKED_FOR_COUNTS + ["README.md"]:
    path = HERE / rel
    if not path.exists():
        continue
    text = deliverable_text(path)
    if text.startswith("__UNREADABLE_XLSX__"):
        continue                      # already reported by the count scan above
    for phrase, why in WITHDRAWN:
        if phrase in text:
            problems.append(f"{rel}: still contains a withdrawn claim, '{phrase}' - {why}")

# The suite size is stated in files that are not deliverables -- the README a judge opens first, the
# runbook, the runner itself -- so it cannot ride on CHECKED_FOR_COUNTS; and the phrasings differ
# enough that one generic "N tests" pattern would also match unrelated prose in the same paragraph
# ("61 pipeline and transcript checks"). Each shape is therefore named.
SUITE_SIZE_CLAIMS = [
    ("README.md", r"Ran\s+" + NUM_RE + r"\s+tests"),
    ("README.md", NUM_RE + r"\s+checks: the pipeline"),
    ("CLAUDE.md", r"expect\s+" + NUM_RE + r"\s+tests\s+OK"),
    ("docs/METHODS_AND_AI.md", r"suite stands at \*{0,2}" + NUM_RE + r"\*{0,2}"),
    ("docs/REPORT.md", r"is\s+" + NUM_RE + r"\s+checks in total"),
    ("tests/phase1/run_tests.sh", r"Ran\s+" + NUM_RE + r"\s+tests"),
]
if "phase-1 tests" in TRUTH:
    for rel, pattern in SUITE_SIZE_CLAIMS:
        path = HERE / rel
        if not path.exists():
            continue
        for mm in re.finditer(pattern, path.read_text(encoding="utf-8"), re.I):
            got = as_int(mm.group(1))
            if got is not None and got != TRUTH["phase-1 tests"]:
                problems.append(f"{rel}: says '{mm.group(0).strip()}' but tests/phase1 contains "
                                f"{TRUTH['phase-1 tests']} tests")

# ---- the detectability numbers must be the ones the arithmetic produces ----
# docs/power_table.md is generated and the report quotes two of its cells in prose. A quoted cell is
# exactly the kind of number that drifts when an assumption changes, so both the generated table and
# the report are checked against a fresh computation rather than against each other.
_pw = DOCS / "power_table.md"
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_qc", HERE / "scripts" / "phase1" / "21_quant_checks.py")
    _qc = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_qc)
    _units = _qc.n_per_arm(0.30, 0.20)
    _cult = math.ceil(_units * _qc.design_effect(100, 0.05) / 100)
    TRUTH["reference-design units per arm"] = _units
    TRUTH["reference-design cultures per arm at ICC 0.05"] = _cult
except Exception as _exc:                                        # noqa: BLE001
    pending.append(f"docs/power_table.md: could not recompute the detectability numbers ({_exc})")
else:
    if not _pw.exists():
        (problems if FREEZE else pending).append(
            "docs/power_table.md does not exist - run scripts/phase1/21_quant_checks.py power")
    else:
        for rel in ("docs/power_table.md", "docs/REPORT.md"):
            txt = (HERE / rel).read_text(encoding="utf-8")
            for mm in re.finditer(r"\*{0,2}([\d,]{2,6})\*{0,2}\s+scored cells per arm", txt):
                got = as_int(mm.group(1).replace(",", ""))
                if got is not None and got != _units:
                    problems.append(f"{rel}: says '{mm.group(0).strip()}' but the two-proportion "
                                    f"computation gives {_units} units per arm")
            for mm in re.finditer(r"\*{0,2}(\d{1,4})\*{0,2}\s+cultures per arm at an? "
                                  r"(?:intra-culture correlation of 0\.05|ICC = 0\.05)", txt):
                got = as_int(mm.group(1))
                if got is not None and got != _cult:
                    problems.append(f"{rel}: says '{mm.group(0).strip()}' but the design effect gives "
                                    f"{_cult} cultures per arm")

# ---- the citation-verification artefact must not be older than the chain it verifies ----
# It was silently stale on 2026-10-19: the chain had gained PMIDs since the last run, and nothing
# said so. Staleness is PENDING rather than BLOCKED because the verifier needs network access the
# submission environment may not have; --freeze makes it blocking.
_cc = HERE.parent / "registers" / "citation_check.csv"
_mg = DOCS / "mechanism_graph.yaml"
if not _cc.exists():
    # A MISSING artefact must not be quieter than a stale one. Before 2026-10-19 this check only
    # fired when the file existed and was old, so deleting it bought silence -- including under
    # --freeze. An external audit exploited exactly that.
    (problems if FREEZE else pending).append(
        "registers/citation_check.csv does not exist - the citation verification has never been run "
        "for this tree; run scripts/phase1/16_verify_citations.py --include-uniprot")
elif _mg.exists() and _cc.stat().st_mtime < _mg.stat().st_mtime:
    # Say WHY it is stale, not just that it is. The operator needs to know whether the
    # graph edit introduced a PMID that has never been checked (serious) or only touched
    # prose around PMIDs already verified (still stale, still blocking at freeze, but a
    # different kind of problem). This reports the gap; it does not forgive it. The gate
    # stays exactly as strict -- weakening a check after watching it fire against us is
    # the rule-fitting this report criticises elsewhere.
    import csv as _csv1
    _verified = set()
    with _cc.open(newline="", encoding="utf-8") as _fh:
        for _r in _csv1.DictReader(_fh):
            _rid = (_r.get("id") or "").strip()
            if _rid.isdigit():
                _verified.add(_rid)
    # PMIDs live in structured `sources[].pmid` fields, not in prose. An earlier version
    # of this diagnostic regex-scanned the raw YAML for "PMID 1234567" and found 4 of the
    # 14, because most citations never spell the prefix -- and it would also have matched
    # 7-digit HPO identifiers. A diagnostic that reports the wrong number is worse than no
    # diagnostic, so this parses the graph.
    import yaml as _yaml1
    _g = _yaml1.safe_load(_mg.read_text(encoding="utf-8")) or {}
    _in_graph = {str(_src["pmid"]).strip()
                 for _e in _g.get("edges", []) or []
                 for _src in (_e.get("sources") or [])
                 if isinstance(_src, dict) and _src.get("pmid")}
    _uncovered = sorted(_in_graph - _verified)
    _detail = (f"; all {len(_in_graph)} PMIDs in the graph already have a verified row, "
               f"so this is a timestamp ordering rather than an unchecked citation"
               if not _uncovered else
               f"; {len(_uncovered)} PMID(s) in the graph have NO verified row: "
               f"{_uncovered[:6]}")
    (problems if FREEZE else pending).append(
        "registers/citation_check.csv is older than docs/mechanism_graph.yaml - re-run "
        "scripts/phase1/16_verify_citations.py --include-uniprot from a network that can "
        "reach Europe PMC/Crossref" + _detail)
elif _cc.exists():
    import csv as _csv2
    with _cc.open(newline="", encoding="utf-8") as _fh:
        _bad = [r["id"] for r in _csv2.DictReader(_fh)
                if r.get("status") not in ("OK", "", None) or r.get("title_check") == "mismatch"]
    if _bad:
        problems.append(f"citation_check.csv has {len(_bad)} unresolved rows: {_bad[:6]}")

# ---- the robustness report must describe the engine as it is now ----
# ROBUSTNESS.md states what the engine does under ablation, blinding and probe injection.
# If the engine changes and the report does not, it becomes a confident false statement
# about code that no longer exists -- worse than having no robustness report at all.
# Unlike the citation check this needs no network, so there is no excuse for staleness and
# it BLOCKS rather than pends.
_rb = DOCS / "ROBUSTNESS.md"
_rb_inputs = [HERE / "src/triage.py", HERE / "config/scoring.yaml",
              HERE / "evidence/candidates_from_canonical.yaml",
              HERE / "config/cases/bub1b_mva.yaml", DOCS / "mechanism_graph.yaml"]
if not _rb.exists():
    problems.append("docs/ROBUSTNESS.md does not exist - run scripts/phase1/20_robustness.py")
else:
    _newer = [str(f.relative_to(HERE)) for f in _rb_inputs
              if f.exists() and f.stat().st_mtime > _rb.stat().st_mtime]
    if _newer:
        problems.append("docs/ROBUSTNESS.md is older than " + ", ".join(_newer)
                        + " - re-run scripts/phase1/20_robustness.py")
    if "**FAIL**" in _rb.read_text(encoding="utf-8"):
        problems.append("docs/ROBUSTNESS.md records a failed assertion - the engine is "
                        "name-dependent or a gate is not biting; fix the engine, not the doc")

# ---- claim sign-off is a human act; report how much of it has actually happened ----
_led = HERE.parent / "registers" / "claim_ledger.csv"
if _led.exists():
    import csv as _csv3
    with _led.open(newline="", encoding="utf-8") as _fh:
        _rows = list(_csv3.DictReader(_fh))
    # Report each verification tier against its own denominator. Counting all 36 rows as
    # needing one human act overstated the deficit: a label quotation is checked by opening the
    # label, a global negative by re-running its dated search, and a row sourced to a file in
    # this repo by the provenance hashes this gate already enforces. Only a claim sourced to a
    # paper needs a person to have read the paper, and that is the number worth blocking on.
    _lit = [r for r in _rows if (r.get("verification_mode") or "") == "literature_read"]
    _lit_unsigned = [r["claim_id"] for r in _lit if not (r.get("reviewed_by") or "").strip()]
    if _lit and _lit_unsigned:
        (problems if FREEZE else pending).append(
            f"{len(_lit_unsigned)}/{len(_lit)} literature claims carry no human sign-off "
            f"(registers/claim_signoff.csv): {_lit_unsigned[:8]}"
            + (" ..." if len(_lit_unsigned) > 8 else "")
            + ". The other "
            f"{len(_rows) - len(_lit)} rows are verified by the mechanism named in their "
            f"verification_mode column (label text, reproducible search, internal provenance), "
            f"not by a literature read. A generated ledger can prove its sources; it cannot "
            f"prove that a person read them.")
    if not _lit and _rows and "verification_mode" not in _rows[0]:
        problems.append("registers/claim_ledger.csv has no verification_mode column - "
                        "re-run make_claim_ledger.py")
    _landing = [r["claim_id"] for r in _rows
                if (r.get("verification_mode") or "") == "landing_page_only"]
    if _landing:
        pending.append(
            f"{len(_landing)} eligibility rows cite a fact-sheet host rather than a product "
            f"label ({', '.join(_landing)}) - correct by construction (no approved product "
            f"exists for those molecules), recorded so it is a stated choice")

# ---- provenance hashes in the case manifest must match the files they name ----
_case = HERE / "config" / "cases" / "bub1b_mva.yaml"
if _case.exists():
    import hashlib as _hl, yaml as _yaml
    _prov = (_yaml.safe_load(_case.read_text(encoding="utf-8")) or {}).get("provenance") or {}
    for _k, _v in _prov.items():
        if not isinstance(_v, dict) or "file" not in _v or "sha256" not in _v:
            continue
        _f = HERE / _v["file"]
        if not _f.exists():
            continue
        if _hl.sha256(_f.read_bytes()).hexdigest() != _v["sha256"]:
            problems.append(f"provenance hash for {_v['file']} no longer matches the file - "
                            f"re-run scripts/phase1/18_case_provenance.py")

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

# ---- the pitch must fit the three-minute limit, as a measurement rather than an intention ----
# "Target 2:55 spoken" was an assertion in a stage direction, and the script had drifted to an
# estimated 2:57 after one sentence was added. A video over the limit is the one failure mode that
# no amount of scientific rigour recovers from, so the length is computed here from the spoken
# word count and blocks with a margin. 2.6 words/second is a brisk-but-clear delivery rate;
# WPM_RATE is deliberately conservative, because a slower read is the realistic failure.
WPM_RATE = 2.6
LIMIT_S = 180
MARGIN_S = 6                      # block at 174s so a slower-than-modelled read still fits
_pitch = DOCS / "PITCH.md"
if _pitch.exists():
    _pt = _pitch.read_text(encoding="utf-8")
    _beats, _total = [], 0.0
    for _b in re.split(r"\n(?=\*\*\d:\d\d)", _pt):
        _m = re.match(r"\*\*(\d:\d\d)[\u2013-](\d:\d\d)", _b)
        if not _m:
            continue
        # strip bold stage directions and parenthetical italic cues: they are not spoken
        _spoken = re.sub(r"\*\(.*?\)\*", "", re.sub(r"\*\*.*?\*\*", "", _b))
        _w = len(_spoken.split())
        _sec = lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1])
        _budget = _sec(_m.group(2)) - _sec(_m.group(1))
        _est = _w / WPM_RATE
        _total += _est
        _beats.append((_m.group(1), _m.group(2), _budget, _w, _est))
    if not _beats:
        problems.append("docs/PITCH.md has no parseable beat timings (expected '**M:SS-M:SS')")
    else:
        if _total > LIMIT_S - MARGIN_S:
            problems.append(
                f"docs/PITCH.md is estimated at {int(_total//60)}:{int(_total%60):02d} "
                f"({_total:.0f}s at {WPM_RATE} words/s) against a {LIMIT_S}s limit - cut to "
                f"{LIMIT_S - MARGIN_S}s or less so a slower read still fits")
        _over = [f"{a}-{b} ({w} words = {e:.0f}s vs {bu}s)"
                 for a, b, bu, w, e in _beats if e > bu + 1.5]
        if _over:
            pending.append("docs/PITCH.md beats over their own labelled budget: "
                           + "; ".join(_over))
        TRUTH_PITCH = f"{int(_total//60)}:{int(_total%60):02d} ({_total:.0f}s, {LIMIT_S}s limit)"
        # The stage direction states the length in prose. That is the same drift this gate exists
        # to stop -- the previous wording said "Target 2:55" while the script had reached 2:57 --
        # so the stated figure is checked against the computed one rather than trusted.
        _claimed = re.search(r"Measured (\d):(\d\d) spoken", _pt)
        if not _claimed:
            problems.append("docs/PITCH.md does not state its measured length "
                            "(expected 'Measured M:SS spoken') - the length claim must be checkable")
        else:
            _cs = int(_claimed.group(1)) * 60 + int(_claimed.group(2))
            if abs(_cs - _total) > 2:
                problems.append(
                    f"docs/PITCH.md says 'Measured {_claimed.group(1)}:{_claimed.group(2)} spoken' "
                    f"but the computed length is {int(_total//60)}:{int(_total%60):02d} - "
                    f"update the sentence")

# ---- every AI provider the disclosure names must have a row in the usage register ----
# The interruption-count check above was added because a disagreement inside the AI-disclosure
# section is the most expensive kind. The same exposure existed one level up and was not checked:
# METHODS_AND_AI.md named a second provider that had no row in registers/ai_usage_register.csv,
# so the document claimed a usage the register could not evidence. Declared and recorded must
# match in both directions -- a provider in the register but absent from the disclosure is the
# worse failure of the two, because that is undisclosed use.
# Third direction, added 2026-10-20: the report's own AI statement enumerated providers too, and
# named only one while METHODS_AND_AI.md named two. Two deliverables disagreeing about who had
# access is the single most expensive inconsistency available in this competition, so all three
# documents are held to the same list.
_meth = DOCS / "METHODS_AND_AI.md"
_aiu = REG / "ai_usage_register.csv"
_rep_ai = DOCS / "REPORT.md"
if _meth.exists() and _aiu.exists():
    _mt = _meth.read_text(encoding="utf-8")
    _reg_text = _aiu.read_text(encoding="utf-8").lower()
    _rt_ai = _rep_ai.read_text(encoding="utf-8").lower() if _rep_ai.exists() else ""
    # provider -> the strings that identify it in either document
    PROVIDERS = {"Anthropic/Claude": ("anthropic", "claude"),
                 "OpenAI": ("openai", "chatgpt", "codex"),
                 "Google/Gemini": ("gemini", "google deepmind"),
                 "Meta/Llama": ("llama",),
                 "Mistral": ("mistral",),
                 "xAI/Grok": ("grok",)}
    for _name, _keys in PROVIDERS.items():
        _in_doc = any(k in _mt.lower() for k in _keys)
        _in_reg = any(k in _reg_text for k in _keys)
        if _in_doc and not _in_reg:
            problems.append(
                f"docs/METHODS_AND_AI.md names the AI provider '{_name}' but "
                f"registers/ai_usage_register.csv has no row for it - add the row (date, "
                f"product/tier, training setting, whether patient-derived input was involved, "
                f"purpose) or remove the claim")
        if _in_reg and not _in_doc:
            problems.append(
                f"registers/ai_usage_register.csv records use of '{_name}' but "
                f"docs/METHODS_AND_AI.md does not disclose it - undisclosed AI use")
        # The report's AI statement is a summary, but it enumerates providers, so an omission
        # there reads as a denial. Anthropic/Claude is exempt: the report names the products
        # rather than the vendor in several places and the substring test would be noise.
        if _in_doc and _name != "Anthropic/Claude" and not any(k in _rt_ai for k in _keys):
            problems.append(
                f"docs/METHODS_AND_AI.md discloses the AI provider '{_name}' but "
                f"docs/REPORT.md section 14 does not name it - the two deliverables disagree "
                f"about who had access")

# ---- outputs/run.txt is committed as "the latest clean run", so check that it is one ----
# It is a generated snapshot that run.sh truncates and rewrites, which means a failed run leaves
# a failed snapshot in the working tree. Committing that would publish a transcript ending in
# STEP FAILED under a report claiming the pipeline runs clean. The failure string cannot appear
# during a successful run, because run.sh exits at the first failing step and never reaches this
# gate, so the check is safe to run from inside the run it is checking.
_runtxt = HERE / "outputs" / "run.txt"
if not _runtxt.exists():
    problems.append("outputs/run.txt is missing - run ./run.sh")
else:
    _rt = _runtxt.read_text(encoding="utf-8", errors="replace")
    if "STEP FAILED" in _rt:
        problems.append("outputs/run.txt records a failed run - fix the cause and re-run ./run.sh "
                        "before committing the snapshot")
    _stale = [r for r in ("docs/REPORT.md", "docs/candidates_canonical.json", "src/triage.py",
                          "config/scoring.yaml", "docs/mechanism_graph.yaml")
              if (HERE / r).exists() and (HERE / r).stat().st_mtime > _runtxt.stat().st_mtime]
    if _stale:
        (problems if FREEZE else pending).append(
            "outputs/run.txt is older than " + ", ".join(_stale)
            + " - re-run ./run.sh so the committed snapshot is of the submitted code")

# ---- the submitted PDF must not be older than the Markdown it is built from ----
# Everything else in this gate protects files a reviewer reads in the repository. The artifact
# the judges actually open is the PDF, it is built by a separate script that run.sh deliberately
# does not call (no TeX toolchain in a clean reproduction), and nothing checked whether it still
# corresponds to REPORT.md. A stale PDF would present a superseded report under a green manifest,
# which is the worst failure available here: every consistency claim in the repository would be
# true and the submitted document would still be wrong. Pending before the freeze, because the
# PDF is rebuilt last; blocking under --freeze, which is the submission-day run.
_pdf = DOCS / "Vero7878_track2_report.pdf"
_rep = DOCS / "REPORT.md"
if not _pdf.exists():
    (problems if FREEZE else pending).append(
        "docs/Vero7878_track2_report.pdf does not exist - build it with `sh make_pdf.sh` "
        "(needs pandoc + xelatex); the PDF is the artifact the judges open")
elif _rep.exists() and _pdf.stat().st_mtime < _rep.stat().st_mtime:
    _age = (_rep.stat().st_mtime - _pdf.stat().st_mtime) / 60.0
    (problems if FREEZE else pending).append(
        f"docs/Vero7878_track2_report.pdf is {_age:.0f} min older than docs/REPORT.md - "
        f"rebuild it with `sh make_pdf.sh` or the submitted PDF is a superseded report")

manifest = {"generated_from": "docs/candidates_canonical.json " + canon.get("updated", ""),
            "denominator": denominator, "primary_hypothesis": primary, "files": {}}
if _pdf.exists():   # pin the submitted artifact too, not only its source
    manifest["submitted_pdf"] = {"file": "docs/Vero7878_track2_report.pdf",
                                 "sha256": hashlib.sha256(_pdf.read_bytes()).hexdigest()}
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
try:
    print(" pitch length  :", TRUTH_PITCH)
except NameError:
    pass
print(" denominator:", denominator)
print(" primary    :", primary[:90] + ("…" if len(primary) > 90 else ""))
print(f" files      : {len(manifest['files'])} hashed -> outputs/manifest.json")
