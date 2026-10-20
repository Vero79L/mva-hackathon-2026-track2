#!/usr/bin/env python3
"""第 19 步：公開安全檢查（Spec 1 v1.1 第 10 節）。engine 是要在 10/25 公開的 repo：commit 前擋下病人層級的資料。

FAIL（擋下）：基因體座標（<染色體>:<位置>、chr<染色體>:<位置>、後面緊接等位基因的 chr7:1234567A>T／chr7:1234567del、
             以分隔號串起來的 7-1234567-A-T／7_1234567_A_T、逗號分組的 chr7:1,234,567、NC_0000…:g.<位置>、
             g.<位置>；位置 5 位數以上）、VCF 格式的列、
             第一階段的私有檔名（handoff_from_track1.yaml、transcript_facts.yaml、t2_variants.*）、超過 5 MB 的檔案。
WARN（人工看）：基因型字樣（0/1、1|0）、AD= / DP= / GQ=。
例外：config/public_safety_allow.txt，一行一個「完全相同的字串<TAB>理由」（例如已在 ClinVar 公開的座標）。
範圍：預設檢查第一階段的輸出；--all 檢查整個 repo（git 追蹤 + 未追蹤）；--staged 只檢查暫存區（pre-commit 用）。
"""
# Make stdout/stderr UTF-8 regardless of the machine's locale: this repo is read and run by
# reviewers on systems where the preferred encoding may be ASCII, and a crash while *printing*
# a result is still a failed reproduction.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t2common as C  # noqa: E402

PHASE1_OUTPUTS = ["docs/transcript_facts_public.yaml", "docs/domain_map.yaml", "docs/domain_map.md",
                  "docs/mechanism_graph.yaml", "docs/mechanism_graph.resolved.yaml", "docs/MECHANISM.md",
                  "docs/figures/domain_map.svg", "docs/figures/mechanism.mmd", "docs/figures/mechanism.dot",
                  "docs/figures/mechanism.svg", "config/scenarios", "config/cases",
                  # Red-team 2026-10-20: until today this gate scanned only the GENERATED Phase-1
                  # outputs, so the documents a reviewer actually opens -- the report, the pitch
                  # script, the care-team annex, the plain-language page -- were never checked,
                  # even though the pre-commit hook runs this script on every commit. Those are
                  # the files a human types prose into, which is where a coordinate or a genotype
                  # gets pasted by accident.
                  "docs/REPORT.md", "docs/PITCH.md", "docs/PLAIN_LANGUAGE_SUMMARY.md",
                  "docs/SAFETY_ANNEX.md", "docs/METHODS_AND_AI.md", "docs/PRIMARY_HYPOTHESIS.md",
                  "docs/MVA_DECISION_TABLE.md", "docs/ROBUSTNESS.md", "docs/computed_vs_human.md",
                  "docs/candidate_table.md", "docs/candidates_canonical.json",
                  "docs/eligibility_matrix.md", "docs/eligibility_matrix.csv",
                  "README.md", "outputs/run.txt"]
PRIVATE_NAMES = re.compile(r"(^|/)(handoff_from_track1\.yaml|transcript_facts\.yaml|t2_variants\.(vcf|vep\.tsv)|"
                           r"fact_register\.csv|citation_check\.csv|claim_ledger\.csv|evidence_ledger\.csv|"
                           r"hpo_terms\.tsv|norm\.vcf\.gz)$"
                           # any variant-call file at all, however it is named (red-team 2026-10-19:
                           # the name list only caught the two files we happened to know about)
                           r"|\.(vcf|vcf\.gz|bcf|bam|cram|fastq|fq|fq\.gz|fastq\.gz|ped|gvcf|gvcf\.gz)$")
# The chromosome token, shared by the coordinate patterns below.
_CHROM = r"(?:chr)?(?:[1-9]|1\d|2[0-2]|X|Y|MT?)"
FAIL_PATTERNS = [
    ("genomic_coordinate", re.compile(r"(?<![\w.:-])" + _CHROM + r":\d{5,}(?:[-_]\d+)?(?![\w.])")),
    # A position written with its alleles attached is the form a coordinate actually arrives in
    # when it is pasted out of a VCF, a browser or an annotation tool -- and the pattern above
    # could not see it, because its trailing (?![\w.]) guard is broken by the very allele letter
    # that makes the string a variant. Red-team 2026-10-20: `chr7:1234567A>T`, `7-1234567-A-T`
    # and `chr7:1234567del` all passed the scan, so the pre-commit hook would not have blocked a
    # commit containing them while the scan reported "no coordinates found". Two further patterns,
    # because one regex that tries to cover both delimiters stops being readable.
    ("genomic_coordinate_allele", re.compile(
        r"(?<![\w.:-])" + _CHROM + r":\d{1,3}(?:,\d{3})+|"          # comma-grouped browser locus
        r"(?<![\w.:-])" + _CHROM + r":\d{5,}\s*"
        r"(?:[ACGTNacgtn]+\s*(?:>|->|/)\s*[ACGTNacgtn]+|del|dup|ins|inv|delins)")),
    ("variant_id_delimited", re.compile(
        r"(?<![\w.:-])" + _CHROM + r"[-_]\d{5,}[-_][ACGTNacgtn]+[-_][ACGTNacgtn]+(?![\w])")),
    ("refseq_genomic_hgvs", re.compile(r"\bN[CG]_\d{6}\.\d+:g\.\d+")),
    ("genomic_hgvs", re.compile(r"(?<![\w])g\.\d{5,}")),
    ("vcf_line", re.compile(r"^\S+\t\d+\t\S+\t[ACGTN]+\t[ACGTN,.*<>]+\t", re.M)),
]
WARN_PATTERNS = [
    ("genotype_string", re.compile(r"(?<![\w/|])[01][/|][01](?![\w/|])")),
    ("format_fields", re.compile(r"\b(AD|DP|GQ|PGT|PID)=")),
    # red-team 2026-10-19: the guard checked containers (file names) but never content for
    # phenotype terms. HPO terms are rules-permitted derived data, so this is a WARN and not a
    # FAIL -- but a combination of terms is a narrow fingerprint in a disease with hundreds of
    # cases worldwide, so every one of them has to be a deliberate choice, not an oversight.
    ("hpo_term", re.compile(r"\bHP:\d{7}\b")),
]
TEXT_EXT = {".md", ".yaml", ".yml", ".csv", ".tsv", ".txt", ".json", ".py", ".sh", ".svg", ".mmd", ".dot", ".html", ".toml", ""}


def git_files(eng, staged):
    if staged:
        cmd = [["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]]
    else:
        cmd = [["git", "ls-files"], ["git", "ls-files", "--others", "--exclude-standard"]]
    out = []
    for c in cmd:
        r = subprocess.run(c, cwd=eng, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            C.die(f"{' '.join(c)} 失敗：{r.stderr.strip()}（engine 是 git repo 嗎？）")
        out += [l for l in r.stdout.splitlines() if l.strip()]
    return sorted(set(out))


def phase1_files(eng):
    out = []
    for p in PHASE1_OUTPUTS:
        q = eng / p
        if q.is_dir():
            out += [str(f.relative_to(eng)) for f in q.rglob("*") if f.is_file()]
        elif q.exists():
            out.append(p)
    return sorted(set(out))


def load_allow(eng):
    p = eng / "config" / "public_safety_allow.txt"
    allow = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                s, _, why = line.partition("\t")
                allow[s.strip()] = why.strip()
    return allow


def scan(eng, files, allow, staged=False):
    fails, warns = [], []
    for rel in files:
        p = eng / rel
        # This scanner's own source necessarily contains every pattern it searches for, as
        # compiled regexes and as docstring examples. A hit there reports the detector, not a
        # leak, so skip it by path rather than silencing the pattern everywhere.
        if rel.replace("\\", "/").endswith("scripts/phase1/19_public_safety.py"):
            continue
        if PRIVATE_NAMES.search(rel):
            fails.append((rel, "private_file", "第一階段的私有檔不能進 repo"))
            continue
        if not p.exists():
            continue
        if p.stat().st_size > 5_000_000:
            fails.append((rel, "large_file", f"{p.stat().st_size / 1e6:.1f} MB > 5 MB"))
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if staged:   # pre-commit：檢查暫存區的版本，不是工作目錄
            r = subprocess.run(["git", "show", f":{rel}"], cwd=eng, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                text = r.stdout
        for name, rx in FAIL_PATTERNS:
            for m in rx.finditer(text):
                hit = m.group(0).strip()
                if hit in allow or any(hit in a for a in allow):
                    continue
                line = text.count("\n", 0, m.start()) + 1
                fails.append((f"{rel}:{line}", name, hit[:60]))
        for name, rx in WARN_PATTERNS:
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                warns.append((f"{rel}:{line}", name, m.group(0)[:40]))
    return fails, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="整個 repo（git 追蹤 + 未追蹤）")
    g.add_argument("--staged", action="store_true", help="只看暫存區（pre-commit hook 用）")
    a = ap.parse_args()
    eng = C.ENGINE
    files = git_files(eng, a.staged) if (a.all or a.staged) else phase1_files(eng)
    allow = load_allow(eng)
    fails, warns = scan(eng, files, allow, staged=a.staged)
    scope = "暫存區" if a.staged else ("整個 repo" if a.all else "第一階段輸出")
    print(f"公開安全檢查（{scope}，{len(files)} 個檔案，例外清單 {len(allow)} 條）")
    for w in warns[:30]:
        print(f"  ! WARN {w[0]} {w[1]}：{w[2]}")
    for f in fails:
        print(f"  ✗ FAIL {f[0]} {f[1]}：{f[2]}")
    if fails:
        print("\n✗ 不能 commit／公開。拿掉這些內容，或（確定已公開的值）把完全相同的字串加進 "
              "config/public_safety_allow.txt 並寫理由。", file=sys.stderr)
        sys.exit(1)
    print("  ✓ 沒有發現基因體座標、VCF 列或私有檔")


if __name__ == "__main__":
    main()
