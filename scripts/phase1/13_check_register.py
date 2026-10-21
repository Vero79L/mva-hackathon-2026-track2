#!/usr/bin/env python3
"""第 13 步：事實三層登錄表的規則檢查（Spec 1 v1.1 第 4 節，規則 R1–R6 + 格式）。

登錄表在 $REGISTERS/fact_register.csv（研究資料夾，不進 engine repo）。第一次執行會從範本建立空白表。
檢查：欄位與值域、fact_id 前綴與 domain 一致、R1–R6、必填的 domain 都有、所有文件引用的 fact_id 都存在。
用法：python3 scripts/phase1/13_check_register.py [--register 檔案] [--init]
結束代碼：0 全部通過（可能有 WARN）；1 有 FAIL。
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
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t2common as C  # noqa: E402

HEADER = ["fact_id", "domain", "statement", "status", "basis", "source", "strength", "alternative", "resolution_path",
          "available_in_hackathon", "would_change_direction", "scenario_link", "report_section", "checked_date"]
PREFIX = {"VAR": "variant_identity", "PHASE": "phase", "INH": "inheritance", "TX": "transcript_fate",
          "PROT": "protein_consequence", "RF": "residual_function", "PHEN": "phenotype", "CLIN": "clinical_constraint"}
REQUIRED_DOMAINS = set(PREFIX.values())
STATUS = {"CONFIRMED", "ASSUMED", "UNKNOWN"}
STRENGTH = {"measured_in_proband", "clinically_validated", "measured_in_model", "predicted", "asserted"}
FACT_RE = re.compile(r"\bF-[A-Z]+-[A-Za-z0-9][A-Za-z0-9_-]*")
DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
# 範本的每個待填格都寫成 <說明>。整格就是一對角括號 = 沒填。這個檢查存在的理由：2026-10-19
# 到 10-21 之間，九列臨床／表現型事實一直留著範本的佔位字串，而 R1–R6 全部通過——因為
# 「statement 非空」對佔位字串來說是真的。引擎讀的 case 檔有真值，所以科學沒受影響，
# 但登錄表是報告引用的那一份，看不見自己沒填完的檢查器等於沒有檢查。
# 不會誤判 HGVS：c.2210T>G 沒有左角括號，而這裡要求整格以 < 開頭、以 > 結尾。
PLACEHOLDER_RE = re.compile(r"^<[^<>]*>$")
PLACEHOLDER_COLS = ("statement", "basis", "source", "alternative", "resolution_path", "report_section")


def ref_files(eng, case_id):
    files = [eng / "docs" / "mechanism_graph.yaml", eng / "docs" / "MECHANISM.md", eng / "docs" / "REPORT.md",
             eng / "config" / "cases" / f"{case_id}.yaml", eng / "config" / "scenarios" / f"{case_id}.scenarios.yaml",
             eng / "docs" / "PRIMARY_HYPOTHESIS.md"]
    return [f for f in files if f.exists()]


def check(rows, refs_text):
    fails, warns = [], []
    ids = [r["fact_id"] for r in rows]
    for d in sorted({i for i in ids if ids.count(i) > 1}):
        fails.append((d, "fact_id 重複"))
    for i, r in enumerate(rows, 2):
        fid = r["fact_id"].strip()
        where = fid or f"第 {i} 列"
        m = re.match(r"^F-([A-Z]+)-", fid)
        if not m:
            fails.append((where, "fact_id 格式要像 F-VAR-01"))
        elif m.group(1) not in PREFIX:
            fails.append((where, f"前綴 {m.group(1)} 不在 {sorted(PREFIX)}"))
        elif PREFIX[m.group(1)] != r["domain"]:
            fails.append((where, f"前綴 F-{m.group(1)} 應該配 domain={PREFIX[m.group(1)]}，現在是 {r['domain']}"))
        if r["status"] not in STATUS:
            fails.append((where, f"status 要是 {sorted(STATUS)}"))
        if r["strength"] not in STRENGTH:
            fails.append((where, f"strength 要是 {sorted(STRENGTH)}"))
        if not r["statement"].strip() or not r["basis"].strip() or not r["source"].strip():
            fails.append((where, "statement、basis、source 都要填"))
        for col in PLACEHOLDER_COLS:
            if PLACEHOLDER_RE.match(r[col].strip()):
                fails.append((where, f"{col} 還是範本的佔位字串 {r[col].strip()[:48]}：填真值，或清空"))
        # R1 / R4：CONFIRMED 只能來自病人身上的量測或外部臨床驗證；predicted 永遠不是 CONFIRMED
        if r["status"] == "CONFIRMED" and r["strength"] not in ("measured_in_proband", "clinically_validated"):
            fails.append((where, "R1/R4：CONFIRMED 的 strength 只能是 measured_in_proband 或 clinically_validated"))
        # R2：ASSUMED 要有替代假設
        if r["status"] == "ASSUMED" and not r["alternative"].strip():
            fails.append((where, "R2：ASSUMED 要寫 alternative（替代假設）"))
        # R3：UNKNOWN 要有解決路徑與比賽期間是否可得
        if r["status"] == "UNKNOWN":
            if not r["resolution_path"].strip():
                fails.append((where, "R3：UNKNOWN 要寫 resolution_path"))
            if r["available_in_hackathon"] not in ("yes", "no"):
                fails.append((where, "R3：UNKNOWN 的 available_in_hackathon 要是 yes / no"))
        # 方向敏感的非確認事實一定要進情境
        if r["would_change_direction"] not in ("yes", "no"):
            fails.append((where, "would_change_direction 要是 yes / no"))
        elif r["would_change_direction"] == "yes" and r["status"] != "CONFIRMED" and not r["scenario_link"].strip():
            fails.append((where, "會改變方向的 ASSUMED/UNKNOWN 必須連到情境（scenario_link = S1/S2/S3…）"))
        # R5：臨床／表現型事實只來自主辦方的表現型檔；沒有日期的「目前狀態」或功能數值是 UNKNOWN
        if r["domain"] in ("phenotype", "clinical_constraint") and r["status"] == "CONFIRMED":
            if not re.search(r"hpo_terms\.tsv|phenotype|表現型", r["source"], re.I):
                fails.append((where, "R5：CONFIRMED 的臨床／表現型事實，source 要指向主辦方的表現型檔（hpo_terms.tsv）"))
            if re.search(r"-(now|fn|current)\b", fid) and not DATE_RE.search(r["basis"] + r["source"]):
                fails.append((where, "R5：目前狀態／功能數值沒有日期，只能是 UNKNOWN"))
        if r["checked_date"] and not DATE_RE.fullmatch(r["checked_date"].strip()):
            fails.append((where, "checked_date 要寫成 YYYY-MM-DD"))
        if not r["checked_date"].strip():
            warns.append((where, "checked_date 空白"))
    missing = REQUIRED_DOMAINS - {r["domain"] for r in rows}
    if missing:
        fails.append(("（全表）", "缺這些 domain：" + "、".join(sorted(missing))))
    # R6：文件引用的 fact_id 都要存在；登錄表裡沒人引用的提醒一下
    known = set(ids)
    cited = set()
    for name, text in refs_text.items():
        for fid in set(FACT_RE.findall(text)):
            cited.add(fid)
            if fid not in known:
                fails.append((fid, f"R6：{name} 引用了登錄表裡沒有的 fact_id"))
    for r in rows:
        if r["fact_id"] not in cited and not r["report_section"].strip():
            warns.append((r["fact_id"], "沒有任何文件引用，report_section 也空白：確認它還需要嗎"))
    return fails, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--register")
    ap.add_argument("--init", action="store_true", help="登錄表不存在時，從範本建立")
    a = ap.parse_args()
    env = C.load_env()
    reg = Path(a.register) if a.register else C.path("REGISTERS", env) / "fact_register.csv"
    if C.is_under(reg, C.ENGINE):
        C.die(f"登錄表不能放在 engine repo 裡（{reg}）：它是工作檔，放 research/registers/")
    if not reg.exists():
        if not a.init:
            C.die(f"找不到 {reg}。第一次用 --init 從範本建立，再照 Spec 1 第 4.3 節填")
        reg.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(C.ENGINE / "templates" / "phase1" / "fact_register.TEMPLATE.csv", reg)
        C.ok(f"已從範本建立 {reg}：照 Spec 1 第 4.3 節填，再跑一次這支")
        return
    with open(reg, newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        if rd.fieldnames != HEADER:
            C.die(f"表頭不對。應該是：\n{','.join(HEADER)}\n現在是：\n{','.join(rd.fieldnames or [])}")
        rows = [{k: (v or "").strip() for k, v in r.items()} for r in rd]
    rows = [r for r in rows if r["fact_id"] and not r["fact_id"].startswith("#")]
    refs = {f.name: f.read_text(encoding="utf-8") for f in ref_files(C.ENGINE, env.get("CASE_ID", "bub1b_mva"))}
    fails, warns = check(rows, refs)
    C.say(f"{reg.name}：{len(rows)} 個事實；檢查了 {len(refs)} 份引用文件")
    by = {}
    for r in rows:
        by.setdefault(r["status"], 0)
        by[r["status"]] += 1
    C.info("　".join(f"{k} {v}" for k, v in sorted(by.items())))
    for w in warns:
        C.warn(f"WARN {w[0]}：{w[1]}")
    for f in fails:
        print(f"  ✗ FAIL {f[0]}：{f[1]}")
    if fails:
        C.die(f"{len(fails)} 個問題要修（Spec 1 第 4.4 節）")
    C.ok("R1–R6 全部通過")


if __name__ == "__main__":
    main()
