#!/usr/bin/env python3
"""第 10 步：Track 1 → Track 2 交接。鎖定變異身分、合子型、分相與事實模式 A／B／C（Spec 1 v1.1 第 1 節）。

讀：Track 1 的提交 CSV（run_manifest.tsv 裡最後一筆 08_draft 的檔名）、標準化 VCF（bcftools query，本機）。
寫：$T2_RESULTS/handoff_from_track1.yaml（含座標；不進 git、不在 iCloud 樹）。

用法（建議在你自己的終端機執行，不經過任何 AI）：
  python3 scripts/phase1/10_handoff.py --match full --rank-points 100 --f-max 1.000
  python3 scripts/phase1/10_handoff.py                  # 互動：照提問輸入排行榜回饋
選項：--submission-csv 指定 CSV；--gene 指定基因；--force 覆蓋既有交接檔。
畫面只印模式、合子型、分相與檔案位置，不印座標。
"""
# Make stdout/stderr UTF-8 regardless of the machine's locale: this repo is read and run by
# reviewers on systems where the preferred encoding may be ASCII, and a crash while *printing*
# a result is still a failed reproduction.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t2common as C  # noqa: E402

MODE = {"full": "A", "partial": "B", "none": "C"}
IDENTITY = {"A": "CONFIRMED", "B": "ASSUMED", "C": "HYPOTHESIZED"}


def find_bcftools():
    b = shutil.which("bcftools")
    if b:
        return b
    for base in ("~/miniforge3", "~/mambaforge", "~/miniconda3", "~/anaconda3"):
        p = Path(os.path.expanduser(base)) / "envs" / "mva" / "bin" / "bcftools"
        if p.exists():
            return str(p)
    C.die("找不到 bcftools：先 conda activate mva（Track 1 的環境）")


def read_manifest(t1_results):
    m = t1_results / "run_manifest.tsv"
    if not m.exists():
        return []
    with open(m, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def find_submission(t1_results, rows, explicit):
    if explicit:
        p = Path(os.path.expanduser(explicit))
        if not p.is_absolute():
            p = t1_results / p
        if not p.exists():
            C.die(f"找不到 {p}")
        return p, None
    drafts = [r for r in rows if r.get("step") == "08_draft" and r.get("note")]
    if drafts:
        last = drafts[-1]
        p = t1_results / last["note"]
        if p.exists():
            return p, last
        C.warn(f"run_manifest.tsv 記的 {last['note']} 不在 {t1_results}，改找最新的提交檔")
    cands = sorted(t1_results.glob("*_mva-tiered-v*.csv"), key=lambda p: p.stat().st_mtime)
    if not cands:
        C.die(f"{t1_results} 裡沒有提交 CSV：Track 1 還沒跑到 08_submission，或用 --submission-csv 指定")
    return cands[-1], None


def top_row(csv_path, proband):
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("proband_id") == proband]
    prim = [r for r in rows if (r.get("finding_type") or "primary").strip() == "primary"]
    if not prim:
        C.die(f"{csv_path.name} 沒有 {proband} 的 primary 列")
    prim.sort(key=lambda r: float(r["epcr"]), reverse=True)
    if len(prim) > 1 and float(prim[0]["epcr"]) == float(prim[1]["epcr"]):
        C.die("第 1、2 列 EPCR 同分：提交檔不符合 Track 1 的規則（第 1 列 EPCR 要唯一最高）")
    return prim[0]


def norm_key(chrom, pos, ref, alt):
    return f"{chrom.replace('chr', '')}:{int(pos)}:{ref.upper()}:{alt.upper()}"


def query_vcf(bcftools, vcf, key):
    chrom, pos, ref, alt = key.split(":")
    fmt = "%CHROM\t%POS\t%ID\t%REF\t%ALT\t%FILTER\t[%GT\t%GQ\t%DP\t%AD\t%PGT\t%PID]\n"
    try:
        out = subprocess.run([bcftools, "query", "-r", f"{chrom}:{pos}-{pos}", "-f", fmt, str(vcf)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    except subprocess.CalledProcessError as ex:
        C.die(f"bcftools query 失敗：{ex.stderr.strip()}（{vcf} 有索引嗎？）")
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) < 12:
            continue
        if p[3].upper() == ref and p[4].upper() == alt:
            return {"id": p[2], "filter": p[5], "gt": p[6], "gq": p[7], "dp": p[8], "ad": p[9], "pgt": p[10],
                    "pid": p[11]}
    C.die("提交檔第 1 列的變異在標準化 VCF 裡找不到同樣的寫法：回 Track 1 第 7 節檢查標準化（座標不印在畫面上）")


def zygosity(gt):
    alleles = gt.replace("|", "/").split("/")
    if len(alleles) == 2 and alleles[0] == alleles[1] and alleles[0] not in (".", "0"):
        return "hom"
    if "0" in alleles and any(a not in ("0", ".") for a in alleles):
        return "het"
    return "other"


def phase_of(q1, q2, k1, k2):
    """兩個異型合子：同一個多等位基因位點拆出 → trans；PID 相同 → 看 PGT；否則 unphased。"""
    c1, p1 = k1.split(":")[:2]
    c2, p2 = k2.split(":")[:2]
    if (c1, p1) == (c2, p2) and q1["id"] == q2["id"] and q1["id"] not in (".", ""):
        return "trans", "同一個多等位基因位點拆出的兩個 ALT（Track 1 第 10.4 節）"
    if q1["pid"] not in (".", "") and q1["pid"] == q2["pid"]:
        if q1["pgt"] in (".", "") or q2["pgt"] in (".", ""):
            return "unphased", "PID 相同但沒有 PGT"
        return ("trans" if q1["pgt"] != q2["pgt"] else "cis"), "讀段層級定相（PGT/PID）"
    return "unphased", "PID 不同或空白：短讀段連不起兩個變異"


def ask(label, cast=str, choices=None):
    if not sys.stdin.isatty():
        C.die(f"缺 {label}：在非互動模式（例如 Claude Code）要用參數提供，見 --help")
    while True:
        v = input(f"  {label}: ").strip()
        if choices and v.lower() not in choices:
            print(f"    請輸入 {'/'.join(choices)}")
            continue
        try:
            return cast(v)
        except ValueError:
            print("    格式不對，再輸入一次")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--match", choices=["full", "partial", "none"], help="提交頁面回饋的 match 類型")
    ap.add_argument("--rank-points", type=float)
    ap.add_argument("--f-max", type=float)
    ap.add_argument("--match-rank", type=int, help="命中的列（沒有就省略）")
    ap.add_argument("--submission-csv", help="Track 1 提交 CSV（預設讀 run_manifest.tsv 的最後一筆 08_draft）")
    ap.add_argument("--gene", help="預設：GENE 設定 → 提交檔 notes 的第一個字")
    ap.add_argument("--force", action="store_true", help="覆蓋既有的 handoff_from_track1.yaml")
    a = ap.parse_args()

    env = C.load_env(required=["T1_WORK", "T1_RESULTS", "T2_RESULTS"])
    t1_work, t1_results, t2_results = C.path("T1_WORK", env), C.path("T1_RESULTS", env), C.path("T2_RESULTS", env)
    C.assert_private_location(t2_results, "交接檔（含座標）")
    out = t2_results / "handoff_from_track1.yaml"
    if out.exists() and not a.force:
        C.die(f"{out} 已存在。要重做（例如 Track 1 第 2 次提交後）加 --force")
    proband = env.get("PROBAND", "PROBAND01")

    C.say("1/4 Track 1 的提交檔")
    rows = read_manifest(t1_results)
    sub, mrow = find_submission(t1_results, rows, a.submission_csv)
    first = top_row(sub, proband)
    C.ok(f"{sub.name}（第 1 列 EPCR {first['epcr']}）")
    keys = [norm_key(first["chrom_1"], first["pos_1"], first["ref_1"], first["alt_1"])]
    if (first.get("chrom_2") or "").strip():
        keys.append(norm_key(first["chrom_2"], first["pos_2"], first["ref_2"], first["alt_2"]))
    gene = a.gene or env.get("GENE") or (first.get("notes") or "").split(" ")[0].strip()
    if not gene:
        C.die("判斷不出基因：用 --gene 指定，或在 config/local.env 設 GENE=")
    C.ok(f"基因 {gene}；第 1 列有 {len(keys)} 個變異")

    C.say("2/4 基因型與品質（bcftools，本機）")
    vcf = t1_work / "norm.vcf.gz"
    if not vcf.exists():
        C.die(f"找不到 {vcf}：Track 1 第 7 節（05_annotate.sh）還沒跑")
    bcf = find_bcftools()
    q = [query_vcf(bcf, vcf, k) for k in keys]
    zyg = [zygosity(x["gt"]) for x in q]
    for i, z in enumerate(zyg, 1):
        C.ok(f"V{i}：{z}，FILTER {q[i - 1]['filter']}")

    C.say("3/4 分相")
    if len(keys) == 2:
        if "hom" in zyg:
            C.die("第 1 列是一對變異，但其中一個是同型合子：回 Track 1 的提交檔檢查")
        phase, basis = phase_of(q[0], q[1], keys[0], keys[1])
        if phase == "cis":
            C.die("兩個變異由讀段證實在同一條染色體上（cis）：這不是複合異型合子。停下來，回 Track 1 第 10.4 節")
    elif zyg[0] == "hom":
        phase, basis = "homozygous", "同型合子：兩個等位基因是同一個變異"
    else:
        phase, basis = "single_het", "只有一個異型合子變異：第二個等位基因未知"
        C.warn("第 1 列只有一個異型合子變異：情境表要加「第二等位基因未知」（Spec 1 第 5 節）")
    C.ok(f"{phase}（{basis}）")

    C.say("4/4 排行榜回饋 → 事實模式")
    match = a.match or ask("match（full / partial / none）", str, {"full", "partial", "none"}).lower()
    rank_points = a.rank_points if a.rank_points is not None else ask("Rank points", float)
    f_max = a.f_max if a.f_max is not None else ask("F-max", float)
    mode = MODE[match]
    if mode == "A" and rank_points < 100:
        C.warn("match=full 但 Rank points < 100：命中的不是第 1 列，檢查 --match-rank")
    variants = []
    for i, k in enumerate(keys, 1):
        variants.append({"id": f"V{i}", "key": k,
                         "submitted_as": ",".join(first[f] for f in (f"chrom_{i}", f"pos_{i}", f"ref_{i}", f"alt_{i}")),
                         "identity_status": IDENTITY[mode], "zygosity": zyg[i - 1],
                         "genotype": {kk: q[i - 1][kk] for kk in ("gt", "filter", "gq", "dp", "ad", "pgt", "pid")}})
    doc = {
        "schema": "handoff/2",
        "generated_at": C.now_iso(),
        "proband_id": proband,
        "track1": {"submission_csv": sub.name, "submission_sha256": C.sha256(sub),
                   "submitted_draft_at": (mrow or {}).get("time"),
                   "rules_commit": (mrow or {}).get("rules_commit") or next(
                       (r.get("rules_commit") for r in reversed(rows) if r.get("rules_commit")), None),
                   "feedback": {"match": match, "rank_points": rank_points, "f_max": f_max,
                                "match_rank": a.match_rank}},
        "mode": mode,
        "gene": gene,
        "variants": variants,
        "phase": {"evidence": phase, "basis": basis,
                  "status": "CONFIRMED_read_backed" if phase == "trans" and "PGT" in basis else
                  ("CONFIRMED_by_site" if phase == "trans" else "ASSUMED" if phase == "unphased" else phase)},
    }
    C.write_yaml(out, doc, header="# 含座標與基因型：只放 ~/mva-hackathon/results/track2（不進 git、不進 iCloud 樹）")
    C.ok(f"模式 {mode}；分相 {phase} → {out}")
    if mode == "B":
        C.warn("模式 B：用 Track 1 第 2 次提交消歧第二個等位基因，之後 --force 重跑這一步（Spec 1 第 1.2 節）")
    if mode == "C":
        C.warn("模式 C：Track 2 改以基因層假說進行；第 11 步照跑，但報告第一節要明說（Spec 1 第 1.2 節）")
    print("\n下一步：bash scripts/phase1/11_transcript_facts.sh")


if __name__ == "__main__":
    main()
