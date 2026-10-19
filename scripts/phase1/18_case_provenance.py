#!/usr/bin/env python3
"""第 18 步：Case 檔 v2 的交叉核對與來源雜湊（Spec 1 v1.1 第 9 節）。

核對 config/cases/<CASE_ID>.yaml（你手寫的 v2）：
  - 所有 fact: 引用都在 fact_register.csv；constraint_provenance 和 patient_constraints 一一對應
  - variants 的 hgvs_c / hgvs_p / transcript 和 docs/transcript_facts_public.yaml 一致（避免手抄漂移）
  - fact_mode 和交接檔的模式一致
  - therapeutic_objectives 每一項的欄位齊全；deselect 一定要同時量 cell death / proliferation
然後重寫檔案最後的 provenance: 區塊（各來源檔的 sha256）。provenance 要放在檔案最後一段。
用法：python3 scripts/phase1/18_case_provenance.py [--check-only] [--run-engine]
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
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t2common as C  # noqa: E402

CLASSES = ("restore", "mitigate", "deselect", "protect")
OBJ_KEYS = ("id", "class", "endpoint_level", "endpoint", "assay", "improvement_is", "co_measure",
            "wrong_direction_test", "valid_in_scenarios")


def facts_in(obj, path="", out=None):
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "fact" and isinstance(v, str):
                out.extend((path + ".fact", f.strip()) for f in re.split(r"[;,]", v) if f.strip())
            else:
                facts_in(v, f"{path}.{k}" if path else k, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            facts_in(v, f"{path}[{i}]", out)
    return out


def check(case, reg_ids, public, handoff_mode):
    fails, warns = [], []
    if case.get("schema_version") != 2:
        warns.append("schema_version 不是 2：這還是 v1 的 case 檔")
    if reg_ids is None:
        warns.append("找不到 fact_register.csv：跳過 fact 引用檢查")
    else:
        for where, f in facts_in(case):
            if f not in reg_ids:
                fails.append(f"{where}：{f} 不在 fact_register.csv")
    pc = case.get("patient_constraints") or {}
    cp = case.get("constraint_provenance") or {}
    if set(pc) != set(cp):
        fails.append(f"constraint_provenance 的鍵 {sorted(cp)} 要和 patient_constraints {sorted(pc)} 一樣")
    for k, v in cp.items():
        if not isinstance(v, dict) or not v.get("fact") or not v.get("status"):
            fails.append(f"constraint_provenance.{k} 要有 fact 與 status")
    if public:
        pv = {v["id"]: v for v in public.get("variants") or []}
        for v in case.get("variants") or []:
            vid = v.get("id")
            if vid not in pv:
                warns.append(f"variants：{vid} 不在 transcript_facts_public.yaml（v1 的寫法？）")
                continue
            for k in ("transcript", "hgvs_c", "hgvs_p"):
                want = pv[vid].get(k)
                got = v.get(k)
                if want and got and str(got) != str(want).split(":")[-1] and str(got) != str(want):
                    fails.append(f"variants.{vid}.{k} = {got}，但第 11 步算出 {want}")
    if handoff_mode and case.get("fact_mode") and case.get("fact_mode") != handoff_mode:
        fails.append(f"fact_mode = {case.get('fact_mode')}，交接檔是 {handoff_mode}")
    objs = case.get("therapeutic_objectives") or []
    if not objs:
        warns.append("還沒有 therapeutic_objectives（第 8 節）")
    seen = set()
    for o in objs:
        oid = o.get("id", "?")
        miss = [k for k in OBJ_KEYS if o.get(k) in (None, "", [])]
        if o.get("class") == "protect":
            miss = [k for k in miss if k not in ("assay", "valid_in_scenarios")]
        if miss:
            fails.append(f"therapeutic_objectives.{oid} 缺：{', '.join(miss)}")
        if o.get("class") not in CLASSES:
            fails.append(f"therapeutic_objectives.{oid}：class 要是 {CLASSES}")
        seen.add(o.get("class"))
        if o.get("class") == "deselect":
            cm = " ".join(map(str, o.get("co_measure") or [])).lower()
            if "death" not in cm or "prolif" not in cm:
                fails.append(f"therapeutic_objectives.{oid}：deselect 一定要同時量 cell death 與 proliferation（分辨修復與淘汰）")
        if o.get("class") == "protect" and o.get("feasible_in_hackathon") is not False:
            warns.append(f"therapeutic_objectives.{oid}：protect 類的終點是長期事件，feasible_in_hackathon 應為 false")
    if objs and set(CLASSES) - seen:
        warns.append("therapeutic_objectives 少了這幾類：" + "、".join(sorted(set(CLASSES) - seen)))
    if objs and not str(case.get("disease_direction_test") or "").strip():
        fails.append("disease_direction_test 要寫（第 8.3 節）")
    return fails, warns


def _drop_trailing_header(lines):
    """每跑一次就留下一行舊的 provenance 註解，跑 n 次就有 n 行——把它們清掉再寫新的。
    （2026-10-19：case 檔裡已經累積了 7 份同樣的註解，評審打開檔案會看到。）"""
    out = list(lines)
    while out and (not out[-1].strip() or out[-1].lstrip().startswith("# provenance")):
        out.pop()
    return out


def replace_provenance(text, block):
    lines = text.splitlines()
    idx = next((i for i, l in enumerate(lines) if re.match(r"^provenance:\s*$", l)), None)
    if idx is None:
        return "\n".join(_drop_trailing_header(lines)).rstrip("\n") + "\n\n" + block
    after = [l for l in lines[idx + 1:] if l.strip() and not l.startswith((" ", "\t", "#"))]
    if after:
        C.die("provenance: 後面還有其他頂層欄位：把 provenance 區塊移到檔案最後再跑")
    return "\n".join(_drop_trailing_header(lines[:idx])).rstrip("\n") + "\n\n" + block


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--run-engine", action="store_true")
    ap.add_argument("--candidates", default="evidence/candidates_from_canonical.yaml")
    a = ap.parse_args()
    env = C.load_env()
    eng = C.ENGINE
    cid = env.get("CASE_ID", "bub1b_mva")
    case_p = eng / "config" / "cases" / f"{cid}.yaml"
    case = C.read_yaml(case_p)
    reg = C.path("REGISTERS", env) / "fact_register.csv"
    reg_ids, nrows = None, 0
    if reg.exists():
        with open(reg, newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if (r.get("fact_id") or "").strip()]
        reg_ids, nrows = {r["fact_id"].strip() for r in rows}, len(rows)
    pub_p = eng / "docs" / "transcript_facts_public.yaml"
    public = C.read_yaml(pub_p) if pub_p.exists() else None
    handoff = C.path("T2_RESULTS", env) / "handoff_from_track1.yaml" if env.get("T2_RESULTS") else None
    hmode = (C.read_yaml(handoff) or {}).get("mode") if handoff and handoff.exists() else None
    fails, warns = check(case, reg_ids, public, hmode)
    for w in warns:
        C.warn(w)
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        C.die(f"{len(fails)} 個問題要修（Spec 1 第 9 節）")
    C.ok(f"{case_p.name} 核對通過")
    if not a.check_only:
        prov = {}

        def add(key, p, label, **extra):
            if p and Path(p).exists():
                prov[key] = {"file": label, "sha256": C.sha256(p), **extra}

        add("handoff", handoff, "results/track2/handoff_from_track1.yaml", mode=hmode)
        add("transcript_facts_public", pub_p, "docs/transcript_facts_public.yaml")
        add("domain_map", eng / "docs" / "domain_map.yaml", "docs/domain_map.yaml")
        add("mechanism_graph", eng / "docs" / "mechanism_graph.yaml", "docs/mechanism_graph.yaml")
        add("scenarios", eng / "config" / "scenarios" / f"{cid}.scenarios.yaml", f"config/scenarios/{cid}.scenarios.yaml")
        add("fact_register", reg, "research/registers/fact_register.csv", rows=nrows)
        prov["built_at"] = C.now_iso()
        import yaml
        block = "# provenance：由 scripts/phase1/18_case_provenance.py 產生（放在檔案最後）\n" + \
            yaml.safe_dump({"provenance": prov}, sort_keys=False, allow_unicode=True)
        case_p.write_text(replace_provenance(case_p.read_text(encoding="utf-8"), block), encoding="utf-8")
        C.ok(f"provenance 已更新（{len(prov) - 1} 個來源檔）")
    if a.run_engine:
        r = subprocess.run([sys.executable, "src/triage.py", "--case", f"config/cases/{cid}.yaml", "--candidates",
                            a.candidates], cwd=eng, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:])
            C.die("引擎讀 case 檔 v2 失敗")
        C.ok("引擎接受 case 檔 v2")


if __name__ == "__main__":
    main()
