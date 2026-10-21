#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Countersign literature claims, one paper at a time.

registers/claim_signoff.csv records one thing: that a person has read the paper a claim rests
on. Nothing else in this repository can produce that record, so this tool does not write it on
anyone's behalf. What it automates is the clerical half -- finding the unsigned rows, pulling
each claim's text, counter-evidence, resolved citation titles and the per-PMID verdicts from the
dated audit files, writing the CSV, and regenerating the ledger. The signature itself is one
keypress per claim, after the evidence for that claim is on screen.

There is deliberately no flag that signs everything at once. A reviewer column filled without a
reviewer is the exact failure an external review already caught in this project once.

Usage:
    python3 sign_claims.py                 # review and sign the unsigned literature claims
    python3 sign_claims.py --list          # print the dossier, write nothing
    python3 sign_claims.py --name "..."    # reviewer name (default: $T2_REVIEWER, else Vero)
    python3 sign_claims.py --claim CL-MECH-E15   # one claim only (repeatable)
"""
import argparse
import csv
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REG = Path(os.environ.get("REGISTERS", HERE.parent / "registers"))
LEDGER = REG / "claim_ledger.csv"
SIGNOFF = REG / "claim_signoff.csv"
CITES = REG / "citation_check.csv"
AUDITS = sorted(REG.glob("citation_manual_check_*.md"))
HDR = ["claim_id", "reviewed_by", "reviewed_date", "note"]
AWAITING = "Awaiting countersignature."
W = 96


def wrap(text, indent="    "):
    out, line = [], indent
    for word in str(text).split():
        if len(line) + len(word) + 1 > W and line.strip():
            out.append(line)
            line = indent + word
        else:
            line = (line + " " + word) if line.strip() else indent + word
    if line.strip():
        out.append(line)
    return "\n".join(out)


def load_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pmids(row):
    return re.findall(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", row.get("source_url", ""))


def audit_lines(pmid):
    """Markdown table rows from the dated audit files whose first cell names this PMID."""
    hits = []
    for f in AUDITS:
        for raw in f.read_text(encoding="utf-8").splitlines():
            if raw.startswith("|") and re.match(r"^\|\s*(?:PMID\s*)?" + pmid + r"\b", raw):
                cells = [c.strip() for c in raw.strip().strip("|").split("|")]
                hits.append((f.name, cells))
    return hits


def dossier(claim, cite_by_pmid, note):
    print("=" * (W + 4))
    print(f"  {claim['claim_id']}   [{claim.get('strength','')} / {claim.get('disposition','')}]")
    print(f"  {claim.get('report_location','')}")
    print("=" * (W + 4))
    print("\n  CLAIM")
    print(wrap(claim.get("claim_text", "")))
    if claim.get("counterevidence", "").strip():
        print("\n  COUNTER-EVIDENCE ALREADY ON THE RECORD")
        print(wrap(claim["counterevidence"]))
    print("\n  SOURCES")
    for p in pmids(claim):
        c = cite_by_pmid.get(p, {})
        print(f"    PMID {p}  https://pubmed.ncbi.nlm.nih.gov/{p}/")
        if c:
            print(wrap(f"{c.get('first_author','?')} {c.get('year','?')}, {c.get('journal','?')} "
                       f"-- \"{c.get('title','?')}\"  [resolved: {c.get('title_check','?')}]", "      "))
        for loc in claim.get("source_locator", "").split("|"):
            if re.search(r"\b" + p + r"\b", loc):
                print(wrap("locator: " + loc.strip(), "      "))
        for fname, cells in audit_lines(p):
            print(wrap(f"{fname}: {' -- '.join(cells[1:])}", "      "))
    if note.strip():
        print("\n  CURRENT NOTE")
        print(wrap(note))
    flags = [w for w in ("abstract level only", "abstract-level", "main-text", "main text",
                         "needs the full text", "not cleared") if w in note.lower()]
    if flags:
        print("\n  ** This row's note says part of the claim is not cleared by an abstract read. **")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=os.environ.get("T2_REVIEWER", "Vero"))
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--list", action="store_true", help="print the dossier and exit")
    ap.add_argument("--claim", action="append", default=[], help="restrict to these claim ids")
    args = ap.parse_args()

    ledger = load_rows(LEDGER)
    if not ledger:
        sys.exit(f"no ledger at {LEDGER}; run make_claim_ledger.py first")
    sign = load_rows(SIGNOFF)
    by_id = {r["claim_id"]: r for r in sign}
    cites = {r["id"]: r for r in load_rows(CITES) if r.get("kind") == "pmid"}

    lit = [r for r in ledger if r.get("verification_mode") == "literature_read"]
    todo = [r for r in lit if not by_id.get(r["claim_id"], {}).get("reviewed_by", "").strip()]
    if args.claim:
        todo = [r for r in lit if r["claim_id"] in args.claim]
    signed = len(lit) - len([r for r in lit
                             if not by_id.get(r["claim_id"], {}).get("reviewed_by", "").strip()])
    print(f"\nliterature claims: {len(lit)} total, {signed} signed, {len(lit)-signed} unsigned")
    print(f"reviewer: {args.name}    date: {args.date}    register: {SIGNOFF}")
    print(f"audit files read for verdicts: {', '.join(f.name for f in AUDITS) or '(none)'}\n")
    if not todo:
        print("nothing to sign.")
        return

    if args.list or not sys.stdin.isatty():
        for r in todo:
            dossier(r, cites, by_id.get(r["claim_id"], {}).get("note", ""))
            print()
        if not args.list:
            print("stdin is not a terminal, so nothing was signed. Run this in your own shell.")
        return

    print("keys:  y = I have read these sources, sign it      s = skip")
    print("       w = sign with a written reservation         q = save and quit\n")
    changed = 0
    for i, r in enumerate(todo, 1):
        cid = r["claim_id"]
        row = by_id.setdefault(cid, {"claim_id": cid, "reviewed_by": "", "reviewed_date": "",
                                     "note": ""})
        if row not in sign:
            sign.append(row)
        print(f"\n[{i}/{len(todo)}]")
        dossier(r, cites, row.get("note", ""))
        while True:
            ans = input(f"\n  {cid}  [y/s/w/q] > ").strip().lower()
            if ans in ("y", "s", "w", "q"):
                break
        if ans == "q":
            break
        if ans == "s":
            continue
        reservation = ""
        if ans == "w":
            reservation = input("  reservation (one line) > ").strip()
        note = row.get("note", "").replace(AWAITING, "").strip()
        stamp = f"Countersigned by {args.name} {args.date}."
        if reservation:
            stamp += f" Reservation: {reservation.rstrip('.')}."
        row["reviewed_by"] = args.name
        row["reviewed_date"] = args.date
        row["note"] = (note + " " + stamp).strip()
        changed += 1
        print(f"  signed {cid}")

    if not changed:
        print("\nnothing signed, register untouched.")
        return

    tmp = SIGNOFF.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HDR, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in sign:
            w.writerow({k: r.get(k, "") for k in HDR})
    tmp.replace(SIGNOFF)
    print(f"\n{changed} claim(s) signed -> {SIGNOFF}")

    if REG != (HERE.parent / "registers"):
        print("REGISTERS is overridden, so the ledger was not regenerated.")
        return
    print("\nregenerating the ledger so every deliverable sees the new count:")
    rc = subprocess.call([sys.executable, str(HERE / "make_claim_ledger.py")])
    if rc:
        sys.exit(rc)
    print("\nnext, in this directory:")
    print("    sh run.sh                        # rebuild the reports")
    print("    bash tests/phase1/run_tests.sh   # expect OK")
    print(f"    {Path(sys.executable).name} make_manifest.py      # the sign-off line should move")


if __name__ == "__main__":
    main()
