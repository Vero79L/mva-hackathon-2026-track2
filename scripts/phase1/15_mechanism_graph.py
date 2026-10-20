#!/usr/bin/env python3
"""第 15 步：因果鏈 YAML → 檢查 → 表、Mermaid、DOT/SVG（Spec 1 v1.1 第 6 節）。

讀：docs/mechanism_graph.yaml（你手寫的來源檔，腳本不會改它）
    $REGISTERS/fact_register.csv（節點引用的 fact_id 要存在）、$T1_RESULTS/hpo_terms.tsv（每個 HPO term 都要有節點）
寫：docs/mechanism_graph.resolved.yaml（加上 unexplained_phenotypes 等計算結果）、docs/MECHANISM.md、
    docs/figures/mechanism.mmd、mechanism.dot、mechanism.svg（有 graphviz 的 dot 才會產生 SVG）
規則：
  1 沒有來源的邊不能存在          2 邊的強度 = 來源裡最弱的那個（來源有標 strength 時檢查）
  3 model.genotype_match 必填     4 measured 主張的前提只有 predicted/asserted → WARN，措辭改「若…成立」
  5 每個 HPO term 要有節點；沒有入邊的列進 unexplained_phenotypes（照實呈現，不要硬連）
用法：python3 scripts/phase1/15_mechanism_graph.py [--init]
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
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t2common as C  # noqa: E402

# 疾病鏈：variant → … → phenotype。治療鏈（intervention → metabolite → enzyme → ptm → protein）
# 在 2026-10-19 red-team 後加入：治療軸原本完全不在任何證據載體裡，是全文唯一沒被自己的工具審過的一步。
LEVELS = ["intervention", "metabolite", "enzyme", "ptm",
          "variant", "transcript", "protein", "complex", "cellular_process", "cellular_outcome", "phenotype"]
ORDER = ["measured_in_proband", "measured_in_model", "predicted", "asserted"]
GENOTYPE_MATCH = {"same_variant", "same_gene_LoF", "same_gene_other", "pathway_level", "not_applicable"}
DOT_STYLE = {"measured_in_proband": ("solid", "3.5"), "measured_in_model": ("solid", "1.8"),
             "predicted": ("dashed", "1.8"), "asserted": ("dotted", "1.8")}
MMD_ARROW = {"measured_in_proband": "==>", "measured_in_model": "-->", "predicted": "-.->", "asserted": "-.->"}


def weakest(strengths):
    return max(strengths, key=ORDER.index)


def mmd_text(s):
    return str(s).replace('"', "#quot;").replace("\n", " ")


def dot_text(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def load_register_ids(p):
    if not p.exists():
        return None
    with open(p, newline="", encoding="utf-8") as fh:
        return {(r.get("fact_id") or "").strip() for r in csv.DictReader(fh)} - {""}


def load_hpo(p):
    # This file lives in the controlled area. `exists()` returns False when it is absent, but it
    # RAISES PermissionError when the path is present and unreadable -- which is what happens under
    # an OS sandbox, in a container that does not mount the controlled area, and for any reviewer
    # reproducing this repository. The step then died on line 1 instead of taking the "no
    # hpo_terms.tsv -> warn and skip rule 5" path it already documents. An unreadable file is
    # absent as far as this step is concerned; the caller warns either way.
    try:
        if not p.exists():
            return None
    except OSError:
        return None
    ids = []
    try:
        fh = open(p, encoding="utf-8")
    except OSError:
        return None
    with fh:
        for line in fh:
            t = line.split("\t")[0].strip()
            if t.startswith("HP:"):
                ids.append(t)
    return ids


def check(G, reg_ids, hpo_ids):
    fails, warns = [], []
    nodes = {}
    for n in G.get("nodes") or []:
        if n.get("id") in nodes:
            fails.append(f"節點 {n.get('id')} 重複")
        nodes[n.get("id")] = n
        if n.get("level") not in LEVELS:
            fails.append(f"節點 {n.get('id')}：level 要是 {LEVELS}")
        if n.get("fact") and reg_ids is not None:
            for f in str(n["fact"]).replace(";", ",").split(","):
                if f.strip() and f.strip() not in reg_ids:
                    fails.append(f"節點 {n['id']}：fact {f.strip()} 不在 fact_register.csv")
        if n.get("level") == "phenotype" and not str(n.get("hpo", "")).startswith("HP:"):
            fails.append(f"表現型節點 {n.get('id')} 要有 hpo: HP:xxxxxxx")
    edges = G.get("edges") or []
    ids = [e.get("id") for e in edges]
    for d in sorted({i for i in ids if ids.count(i) > 1}):
        fails.append(f"邊 {d} 重複")
    incoming = {}
    for e in edges:
        eid = e.get("id", "?")
        if e.get("from") not in nodes or e.get("to") not in nodes:
            fails.append(f"{eid}：from/to 節點不存在")
        if e.get("strength") not in ORDER:
            fails.append(f"{eid}：strength 要是 {ORDER}")
        srcs = e.get("sources") or []
        if not srcs:
            fails.append(f"{eid}：規則 1，沒有來源")
        for s in srcs:
            if not any(k in s for k in ("pmid", "doi", "file")):
                fails.append(f"{eid}：來源要有 pmid、doi 或 file")
        ss = [s["strength"] for s in srcs if s.get("strength") in ORDER]
        if ss and e.get("strength") in ORDER and e["strength"] != weakest(ss):
            fails.append(f"{eid}：規則 2，邊的強度 {e['strength']} 要等於來源最弱的 {weakest(ss)}")
        gm = (e.get("model") or {}).get("genotype_match")
        if gm not in GENOTYPE_MATCH:
            fails.append(f"{eid}：規則 3，model.genotype_match 要是 {sorted(GENOTYPE_MATCH)}")
        if not str(e.get("claim", "")).strip():
            fails.append(f"{eid}：claim 要寫")
        incoming.setdefault(e.get("to"), []).append(e)
    for e in edges:
        ins = incoming.get(e.get("from"), [])
        if str(e.get("strength", "")).startswith("measured") and ins and all(i.get("strength") in ("predicted", "asserted") for i in ins):
            warns.append(f"{e['id']}: rule 4 - this measured claim rests on premise {e['from']}, "
                         f"which is supported only by predicted/asserted edges, so the report must "
                         f"word it as \"if {e['from']} holds\"")
    phen = [n for n in nodes.values() if n.get("level") == "phenotype"]
    unexplained = [n["id"] for n in phen if n["id"] not in incoming]
    if hpo_ids is not None:
        have = {n.get("hpo") for n in phen}
        for h in hpo_ids:
            if h not in have:
                fails.append(f"規則 5：{h} 在 hpo_terms.tsv 裡但因果鏈沒有它的節點（連不上也要列，會自動進 unexplained）")
    else:
        warns.append("找不到 hpo_terms.tsv：跳過「每個 HPO term 都有節點」的檢查")
    return nodes, edges, incoming, unexplained, fails, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", action="store_true", help="docs/mechanism_graph.yaml 不存在時從範本建立")
    a = ap.parse_args()
    env = C.load_env()
    eng = C.ENGINE
    src = eng / "docs" / "mechanism_graph.yaml"
    if not src.exists():
        if not a.init:
            C.die(f"找不到 {src}。第一次用 --init 從範本建立，再照 Spec 1 第 6 節填")
        shutil.copy(eng / "templates" / "phase1" / "mechanism_graph.TEMPLATE.yaml", src)
        C.ok(f"已從範本建立 {src}")
        return
    G = C.read_yaml(src)
    reg_ids = load_register_ids(C.path("REGISTERS", env) / "fact_register.csv")
    hpo = load_hpo(C.path("T1_RESULTS", env) / "hpo_terms.tsv") if env.get("T1_RESULTS") else None
    nodes, edges, incoming, unexplained, fails, warns = check(G, reg_ids, hpo)
    if reg_ids is None:
        warns.append("找不到 fact_register.csv：跳過 fact 引用檢查")
    for w in warns:
        C.warn("WARN " + w)
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        C.die(f"{len(fails)} 個問題要修（Spec 1 第 6.3 節）")

    resolved = dict(G)
    resolved["unexplained_phenotypes"] = unexplained
    resolved["warnings"] = warns
    resolved["generated_at"] = C.now_iso()
    C.write_yaml(eng / "docs" / "mechanism_graph.resolved.yaml", resolved,
                 header="# 由 scripts/phase1/15_mechanism_graph.py 產生；改 docs/mechanism_graph.yaml，不要改這個檔")

    figs = eng / "docs" / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    mm = ["flowchart TB"]
    for n in nodes.values():
        mm.append(f'  {n["id"]}["{mmd_text(n.get("label_en") or n.get("label", n["id"]))}"]')
    for e in edges:
        mm.append(f'  {e["from"]} {MMD_ARROW[e["strength"]]}|{mmd_text(e["id"] + " · " + e["strength"])}| {e["to"]}')
    (figs / "mechanism.mmd").write_text("\n".join(mm) + "\n", encoding="utf-8")

    dot = ['digraph G {', '  rankdir=TB; nodesep=0.22; ranksep=0.45; node [shape=box, style="rounded", fontname="Helvetica", fontsize=15];',
           '  edge [fontname="Helvetica", fontsize=12, color="#45534D"];']
    for lvl in LEVELS:
        same = [n["id"] for n in nodes.values() if n.get("level") == lvl]
        if same:
            dot.append("  { rank=same; " + "; ".join(same) + "; }")
    for n in nodes.values():
        extra = ', style="rounded,dashed"' if n["id"] in unexplained else ""
        dot.append(f'  {n["id"]} [label="{dot_text(n.get("label_en") or n.get("label", n["id"]))}"{extra}];')
    for e in edges:
        st, w = DOT_STYLE[e["strength"]]
        # xlabel keeps parallel edges (two edges between the same pair) from colliding
        key = "xlabel" if sum(1 for x in edges if x["from"] == e["from"] and x["to"] == e["to"]) > 1 else "label"
        dot.append(f'  {e["from"]} -> {e["to"]} [style={st}, penwidth={w}, {key}="{dot_text(e["id"])}"];')
    dot.append("}")
    (figs / "mechanism.dot").write_text("\n".join(dot) + "\n", encoding="utf-8")
    env_dot = Path(sys.executable).parent / "dot"          # 沒有 conda activate 時，用 mva 環境裡的 dot（A2 裝在這裡）
    dotbin = shutil.which("dot") or (str(env_dot) if env_dot.exists() else None)
    if dotbin:
        subprocess.run([dotbin, "-Tsvg", str(figs / "mechanism.dot"), "-o", str(figs / "mechanism.svg")], check=True)
        # PNG for the report and GitHub (both render it); PDF for a LaTeX build of the report
        subprocess.run([dotbin, "-Tpng", "-Gdpi=150", str(figs / "mechanism.dot"), "-o", str(figs / "mechanism.png")], check=True)
        subprocess.run([dotbin, "-Tpdf", str(figs / "mechanism.dot"), "-o", str(figs / "mechanism.pdf")], check=True)
        C.ok("figures/mechanism.svg + .png + .pdf")
    else:
        C.warn("找不到 graphviz 的 dot：只產生 .mmd 與 .dot（安裝：conda install -n mva -c conda-forge graphviz）")

    # The graph is authored in Chinese; MECHANISM.md is read by the judging panel. Every edge
    # carries claim_en / counterevidence_en and every node a label_en, and the generated view
    # prefers them. (2026-10-19 adversarial review: the evidence carrier for the 35% criterion
    # was unreadable to the people scoring it.)
    def en(d, key):
        v = d.get(key + "_en")
        return v if (v is not None and str(v).strip()) else d.get(key, "")

    md = ["# Mechanism chain", "", "Strength legend (weakest last): " + " · ".join(ORDER), "",
          "| Edge | From → To | Claim | Strength | Model (genotype match) | Sources | Counter-evidence | Scenario-dependent |",
          "|---|---|---|---|---|---|---|---|"]
    for e in edges:
        srcs = []
        for s in e["sources"]:
            ident = f"PMID {s['pmid']}" if "pmid" in s else (f"doi:{s['doi']}" if "doi" in s else s.get("file", ""))
            srcs.append(ident + (f" ({s['locator']})" if s.get("locator") else ""))
        m = e.get("model") or {}
        md.append(f"| {e['id']} | {e['from']} → {e['to']} | {en(e, 'claim')} | {e['strength']} | "
                  f"{m.get('system_en') or m.get('system', '')} ({m.get('genotype_match', '')}) | {'; '.join(srcs)} | "
                  f"{en(e, 'counterevidence') or '—'} | {'yes' if e.get('scenario_dependent') else 'no'} |")
    md += ["", "## Phenotypes not explained by the current chain", ""]
    md += [f"- {en(nodes[h], 'label') or h} ({nodes[h].get('hpo', '')})" for h in unexplained] or ["- none"]
    md += ["", "## Node key", "",
           "| Node | Level | Label |", "|---|---|---|"]
    md += [f"| {n['id']} | {n.get('level','')} | {en(n, 'label')} |" for n in nodes.values()]
    if warns:
        md += ["", "## Wording constraints (rule 4)", ""] + [f"- {w}" for w in warns if "rule 4" in w]
    md += ["", "![mechanism](figures/mechanism.svg)"]
    (eng / "docs" / "MECHANISM.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    C.ok(f"{len(nodes)} 個節點、{len(edges)} 條邊、{len(unexplained)} 個目前無法解釋的表現型 → docs/MECHANISM.md")


if __name__ == "__main__":
    main()
