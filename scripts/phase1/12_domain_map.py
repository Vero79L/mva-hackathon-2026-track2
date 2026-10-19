#!/usr/bin/env python3
"""第 12 步：蛋白質結構域對映（Spec 1 v1.1 第 3 節）。

讀 docs/transcript_facts_public.yaml（公開安全版）→ UniProt 特徵 + AlphaFold pLDDT → 每個變異殘基的結構脈絡。
只把蛋白質 accession 送到 UniProt / AlphaFold DB（公開資料庫，不含病人資訊）；回應快取在 $T2_WORK/public_cache。
先確認 UniProt 的序列和 MANE 轉錄本轉譯出來的蛋白完全一樣，位置才能直接對應。

輸出（公開安全）：docs/domain_map.yaml、docs/domain_map.md、docs/figures/domain_map.svg
用法：python3 scripts/phase1/12_domain_map.py [--acc O60566] [--offline] [--allow-isoform-mismatch]
"""
# Make stdout/stderr UTF-8 regardless of the machine's locale: this repo is read and run by
# reviewers on systems where the preferred encoding may be ASCII, and a crash while *printing*
# a result is still a failed reproduction.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t2common as C  # noqa: E402

KEEP = {"Domain", "Region", "Motif", "Repeat", "Zinc finger", "Coiled coil", "Compositional bias", "Binding site",
        "Active site", "Site", "Modified residue", "Cross-link", "Mutagenesis", "Natural variant", "Helix", "Beta strand"}
LANES = [("Domain", "結構域"), ("Region", "區段"), ("Motif", "模體"), ("Repeat", "重複"), ("Coiled coil", "捲曲螺旋"),
         ("Zinc finger", "鋅指")]
POINT_TYPES = {"Modified residue", "Binding site", "Active site", "Site", "Cross-link"}
UA = {"User-Agent": "mva-track2-spec1/1.1 (rare-disease hackathon; public data only)"}


def http_get(url, cache_path, offline):
    if cache_path.exists():
        return cache_path.read_bytes()
    if offline:
        C.die(f"--offline 但快取沒有 {cache_path.name}")
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            data = urllib.request.urlopen(req, timeout=60).read()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
            return data
        except Exception as ex:   # 網路暫時失敗就重試
            if attempt == 2:
                C.die(f"連不到 {url}：{ex}（00_preflight.sh 的網路檢查有過嗎？）")
            time.sleep(2 * (attempt + 1))


def uniprot_search(gene, cache, offline):
    q = urllib.parse.quote(f"gene_exact:{gene} AND organism_id:9606 AND reviewed:true")
    url = f"https://rest.uniprot.org/uniprotkb/search?query={q}&format=json&fields=accession,length"
    d = json.loads(http_get(url, cache / f"uniprot_search_{gene}.json", offline))
    res = d.get("results") or []
    if len(res) != 1:
        C.die(f"UniProt 對 {gene} 找到 {len(res)} 個 reviewed 條目：用 --acc 指定")
    return res[0]["primaryAccession"]


def parse_features(up):
    feats = []
    for f in up.get("features", []):
        if f.get("type") not in KEEP:
            continue
        loc = f.get("location") or {}
        s = (loc.get("start") or {}).get("value")
        e = (loc.get("end") or {}).get("value")
        if s is None or e is None:
            continue
        pmids = sorted({ev.get("id") for ev in f.get("evidences", []) if ev.get("source") == "PubMed" and ev.get("id")})
        rec = {"type": f["type"], "start": int(s), "end": int(e), "description": f.get("description", "")}
        if f["type"] in ("Mutagenesis", "Natural variant"):
            alt = f.get("alternativeSequence") or {}
            rec["original"] = alt.get("originalSequence")
            rec["alternative"] = ",".join(alt.get("alternativeSequences") or [])
        if pmids:
            rec["pmids"] = pmids
        feats.append(rec)
    return feats


def variant_residue(v):
    cod = v.get("coding") or {}
    if cod.get("first_changed_aa"):
        return int(cod["first_changed_aa"])
    m = re.match(r"(\d+)", str(v.get("protein_position") or ""))
    return int(m.group(1)) if m else None


def svg_map(acc, length, feats, plddt, variants, out):
    W, left, right = 960, 120, 24
    lane_h, top = 22, 46
    lanes = [t for t, _ in LANES if any(f["type"] == t for f in feats)]
    H = top + lane_h * (len(lanes) + 2) + 70
    scale = (W - left - right) / max(length, 1)

    def x(r):
        return left + (r - 1) * scale

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'font-family="Helvetica, Arial, sans-serif" font-size="12">',
         f"<title>{html.escape(acc)} domain map with variant positions</title>",
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    y_axis = top - 14
    o.append(f'<line x1="{left}" y1="{y_axis}" x2="{x(length)}" y2="{y_axis}" stroke="#555" stroke-width="1"/>')
    step = 100 if length > 400 else 50
    for r in list(range(1, length + 1, step)) + [length]:
        o.append(f'<line x1="{x(r):.1f}" y1="{y_axis - 4}" x2="{x(r):.1f}" y2="{y_axis}" stroke="#555"/>')
        o.append(f'<text x="{x(r):.1f}" y="{y_axis - 7}" text-anchor="middle" fill="#555" font-size="10">{r}</text>')
    for i, t in enumerate(lanes):
        y = top + i * lane_h
        label = dict(LANES)[t]
        o.append(f'<text x="{left - 8}" y="{y + 14}" text-anchor="end" fill="#333">{label}</text>')
        for f in [f for f in feats if f["type"] == t]:
            w = max(2.0, (f["end"] - f["start"] + 1) * scale)
            tip = html.escape(f"{f['type']} {f['start']}-{f['end']}: {f['description']}")
            o.append(f'<rect x="{x(f["start"]):.1f}" y="{y + 3}" width="{w:.1f}" height="{lane_h - 6}" rx="3" '
                     f'fill="#c9d1cc" stroke="#7d8a84" stroke-width="0.6"><title>{tip}</title></rect>')
            if w > 60:
                o.append(f'<text x="{x(f["start"]) + 4:.1f}" y="{y + 15}" fill="#1c2a25" font-size="10">'
                         f'{html.escape(f["description"][:int(w / 6)])}</text>')
    # 點狀特徵（修飾位點、結合位點）
    yp = top + len(lanes) * lane_h
    o.append(f'<text x="{left - 8}" y="{yp + 14}" text-anchor="end" fill="#333">位點</text>')
    for f in [f for f in feats if f["type"] in POINT_TYPES]:
        tip = html.escape(f"{f['type']} {f['start']}: {f['description']}")
        o.append(f'<line x1="{x(f["start"]):.1f}" y1="{yp + 4}" x2="{x(f["start"]):.1f}" y2="{yp + 18}" '
                 f'stroke="#7d8a84" stroke-width="1"><title>{tip}</title></line>')
    # pLDDT 帶
    yb = yp + lane_h + 4
    o.append(f'<text x="{left - 8}" y="{yb + 10}" text-anchor="end" fill="#333">pLDDT</text>')
    for r in range(1, length + 1):
        v = plddt.get(r)
        if v is None:
            continue
        shade = "#0b3c8c" if v >= 90 else "#4f86d9" if v >= 70 else "#a9c4ee" if v >= 50 else "#e3ebf8"
        o.append(f'<rect x="{x(r):.2f}" y="{yb}" width="{max(scale, 0.6):.2f}" height="12" fill="{shade}"/>')
    # 變異
    ytop, ybot = y_axis, yb + 16
    for v in variants:
        r = v.get("residue")
        if not r:
            continue
        o.append(f'<line x1="{x(r):.1f}" y1="{ytop}" x2="{x(r):.1f}" y2="{ybot}" stroke="#c0392b" stroke-width="2"/>')
        o.append(f'<text x="{x(r):.1f}" y="{ybot + 14}" text-anchor="middle" fill="#c0392b" font-weight="bold">'
                 f'{html.escape(v["id"] + " " + (v.get("hgvs_p_short") or ""))}</text>')
    o.append(f'<text x="{left}" y="{H - 8}" fill="#666" font-size="10">UniProt {html.escape(acc)} 特徵（人工策劃註解）；'
             f'pLDDT 色帶：深藍 ≥90、藍 70–90、淺藍 50–70、最淺 &lt;50（AlphaFold 預測）</text>')
    o.append("</svg>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(o) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--acc", help="UniProt accession（預設用 VEP 的 SWISSPROT 欄）")
    ap.add_argument("--offline", action="store_true", help="只用快取，不連網")
    ap.add_argument("--allow-isoform-mismatch", action="store_true", help="序列不同時仍輸出（並標記），報告必須說明")
    a = ap.parse_args()
    env = C.load_env(required=["T2_WORK"])
    eng = C.ENGINE
    cache = C.path("T2_WORK", env) / "public_cache"
    pub = C.read_yaml(eng / "docs" / "transcript_facts_public.yaml")
    gene = pub.get("gene")
    variants = pub.get("variants") or []
    acc = a.acc or next((str(v["uniprot"]).split(".")[0] for v in variants if v.get("uniprot")), None)
    if not acc:
        acc = uniprot_search(gene, cache, a.offline)
    C.say(f"UniProt {acc}（{gene}）")
    up = json.loads(http_get(f"https://rest.uniprot.org/uniprotkb/{acc}.json", cache / f"{acc}.uniprot.json", a.offline))
    up_seq = (up.get("sequence") or {}).get("value", "")
    length = (up.get("sequence") or {}).get("length") or len(up_seq)
    feats = parse_features(up)
    C.ok(f"{length} aa，{len(feats)} 個特徵")

    # 序列一致性：UniProt canonical vs MANE 轉錄本的轉譯
    tid = variants[0]["transcript"] if variants else None
    pf = cache / f"{tid}.protein.fa" if tid else None
    iso = {"uniprot_isoform_from_vep": next((v.get("uniprot_isoform") for v in variants if v.get("uniprot_isoform")), None)}
    if pf and pf.exists():
        tx_seq = "".join(pf.read_text(encoding="utf-8").splitlines()[1:]).strip()
        iso["status"] = "identical" if tx_seq == up_seq else ("length_differs" if len(tx_seq) != len(up_seq) else "sequence_differs")
        iso["transcript_protein_length"] = len(tx_seq)
    else:
        iso["status"] = "not_checked"
        C.warn("沒有轉錄本蛋白序列快取（第 11 步會寫）：無法確認 UniProt 序列和 MANE 蛋白一致")
    if iso["status"] in ("length_differs", "sequence_differs"):
        msg = (f"UniProt {acc} 的序列和 {tid} 轉譯出來的蛋白不同（{iso['status']}）：殘基位置不能直接對應。"
               "改用 VEP 的 UNIPROT_ISOFORM 對應的 isoform（--acc），或加 --allow-isoform-mismatch 並在報告說明")
        if not a.allow_isoform_mismatch:
            C.die(msg)
        C.warn(msg)
    else:
        C.ok(f"序列一致性：{iso['status']}")

    # AlphaFold
    af = json.loads(http_get(f"https://alphafold.ebi.ac.uk/api/prediction/{acc}", cache / f"{acc}.af.json", a.offline))
    af = af[0] if isinstance(af, list) and af else af
    pdb = http_get(af["pdbUrl"], cache / f"{acc}.af.pdb", a.offline).decode()
    plddt = {}
    for line in pdb.splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            plddt[int(line[22:26])] = float(line[60:66])
    af_seq = af.get("uniprotSequence") or af.get("sequence")
    if af_seq and af_seq != up_seq:
        C.warn("AlphaFold 模型的序列和目前的 UniProt 序列不同（UniProt 已更新？）：pLDDT 只當參考")
    C.ok(f"AlphaFold {af.get('entryId')} v{af.get('latestVersion')}：{len(plddt)} 個殘基有 pLDDT")

    out_vars, svg_vars = [], []
    for v in variants:
        r = variant_residue(v)
        cod = v.get("coding") or {}
        cls = cod.get("class") or v.get("region")
        rec = {"id": v["id"], "hgvs_p": v.get("hgvs_p"), "class": cls, "residue": r}
        if r:
            trunc = cls in ("stop_gained", "frameshift")
            rec["features_at_residue"] = [f for f in feats if f["start"] <= r <= f["end"] and f["type"] not in ("Helix", "Beta strand")]
            rec["same_residue_experimental"] = [f for f in feats if f["type"] in ("Mutagenesis", "Natural variant") and f["start"] <= r <= f["end"]]
            if trunc:
                rec["features_lost_downstream"] = [f for f in feats if f["start"] >= r and f["type"] in dict(LANES)]
                rec["fraction_of_protein_lost"] = round((length - r + 1) / length, 3)
            win = [plddt[i] for i in range(r - 5, r + 6) if i in plddt]
            rec["plddt_at_residue"] = plddt.get(r)
            rec["plddt_window_mean"] = round(sum(win) / len(win), 1) if win else None
        else:
            rec["note"] = "非編碼變異：沒有對應的殘基（上游／內含子／UTR）"
        rec["strength"] = {"features": "asserted（UniProt 人工策劃）", "plddt": "predicted（AlphaFold）",
                           "mutagenesis": "measured_in_model（UniProt 引用的實驗；要回原文確認）"}
        out_vars.append(rec)
        short = (v.get("hgvs_p") or "").split(":")[-1]
        svg_vars.append({"id": v["id"], "residue": r, "hgvs_p_short": short})

    doc = {"schema": "domain_map/2", "generated_at": C.now_iso(), "gene": gene, "uniprot": acc,
           "uniprot_entry_version": (up.get("entryAudit") or {}).get("entryVersion"),
           "protein_length": length, "isoform_check": iso,
           "alphafold": {"entry": af.get("entryId"), "version": af.get("latestVersion")},
           "features": feats, "variants": out_vars,
           "limitations": ["pLDDT 低不代表不重要：無序區段常常有功能",
                           "UniProt 特徵是註解不是本病人的實驗；特徵邊界是人工畫的",
                           "截斷型變異的「下游喪失特徵」是結構推論；蛋白是否存在要看第 2 節的 NMD 預測與第 5 節的情境"],
           "limitations_en": [
               "A low pLDDT does not mean a region is unimportant: disordered segments are often functional.",
               "UniProt features are annotation, not an experiment on this patient, and feature boundaries are drawn by hand.",
               "For a truncating variant, 'features lost downstream' is a structural inference. Whether any protein exists at all depends on the NMD prediction in report section 2 and on the scenarios in section 8."]}
    C.write_yaml(eng / "docs" / "domain_map.yaml", doc, header="# 由 scripts/phase1/12_domain_map.py 產生，不要手改")
    svg_map(acc, length, feats, plddt, svg_vars, eng / "docs" / "figures" / "domain_map.svg")

    md = [f"# {gene} protein domain map (UniProt {acc}, {length} aa)", "",
          "Generated by `scripts/phase1/12_domain_map.py` from `docs/transcript_facts_public.yaml`.", "",
          f"- Sequence identity (UniProt canonical vs MANE transcript translation): **{iso['status']}**",
          f"- AlphaFold：{af.get('entryId')} v{af.get('latestVersion')}", "",
          "| Variant | Class | Residue | Feature at that residue | Experimental / natural variation at the same residue | Features lost downstream | pLDDT (mean +/-5) |",
          "|---|---|---|---|---|---|---|"]
    for r in out_vars:
        at = "; ".join(f"{f['type']}: {f['description']} ({f['start']}–{f['end']})" for f in r.get("features_at_residue", [])) or "—"
        ex = "; ".join(f"{f['type']} {f.get('original', '')}→{f.get('alternative', '')}: {f['description']}" for f in r.get("same_residue_experimental", [])) or "—"
        lost = "; ".join(f"{f['description'] or f['type']} ({f['start']}–{f['end']})" for f in r.get("features_lost_downstream", [])) or "—"
        pl = f"{r.get('plddt_at_residue')}（{r.get('plddt_window_mean')}）" if r.get("residue") else "—"
        md.append(f"| {r['id']} {r.get('hgvs_p') or ''} | {r['class']} | {r.get('residue') or '—'} | {at} | {ex} | {lost} | {pl} |")
    md += ["", "![domain map](figures/domain_map.svg)", "", "## How far this can be read", ""] + [f"- {x}" for x in doc.get("limitations_en") or doc["limitations"]]
    (eng / "docs" / "domain_map.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    pm = sorted({p for f in feats for p in f.get("pmids", [])})
    C.ok(f"寫出 docs/domain_map.yaml、domain_map.md、figures/domain_map.svg；UniProt 引用 {len(pm)} 篇 PubMed（第 16 步可一併驗證）")


if __name__ == "__main__":
    main()
