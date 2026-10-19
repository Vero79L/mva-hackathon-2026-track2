#!/usr/bin/env python3
"""轉錄本層事實：方法 B（GTF 算術 + 參考序列）與方法 A（VEP 離線）交叉檢查。Spec 1 v1.1 第 2 節。

子指令
  mini-vcf  --handoff H --out t2_variants.vcf
            把交接檔裡的變異寫成給 VEP 的迷你 VCF（ID 欄 = V1、V2…）。
  facts     --handoff H --vep t2_variants.vep.tsv --gtf GTF --ref REF --out PRIVATE.yaml --public PUBLIC.yaml
            [--protein-cache DIR]
            每個變異：區域（CDS / UTR / 內含子 / 上游…）、c. 位置、外顯子或內含子編號、編碼後果（用參考序列
            實際轉譯，不靠查表）、PTC 位置與 NMD 預測、+4 鹼基，並和 VEP 逐項比對。
  selftest  --vcf clinvar_sample.vcf --vep clinvar_sample.vep.tsv --gtf GTF --ref REF --report report.tsv
            用公開的 ClinVar 變異檢查方法 B 和 VEP 是否一致（11a_selftest_clinvar.sh 呼叫）。

結束代碼：0 全部一致；3 有交叉檢查不一致（輸出照樣寫出，標 cross_check: fail）；1 輸入或設定錯誤。
全部離線：只讀本機的 VCF 衍生檔、GTF、FASTA；不連網。
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
import gzip
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t2common as C  # noqa: E402

COMP = str.maketrans("ACGTNacgtn", "TGCANtgcan")
CODON = {}
_b = "TCAG"
_aa = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
for _i, _x in enumerate(_b):
    for _j, _y in enumerate(_b):
        for _k, _z in enumerate(_b):
            CODON[_x + _y + _z] = _aa[16 * _i + 4 * _j + _k]
THREE = {"A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys", "Q": "Gln", "E": "Glu", "G": "Gly", "H": "His",
         "I": "Ile", "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe", "P": "Pro", "S": "Ser", "T": "Thr", "W": "Trp",
         "Y": "Tyr", "V": "Val", "*": "Ter", "X": "Xaa"}
ONE = {v: k for k, v in THREE.items()}

NMD_RULE_SOURCE = ("50–55 nt 規則（Nagy & Maquat 1998）；逃逸規則依 aenmd 的實作（Klonowski et al. 2023, "
                   "Bioinformatics 39:btad556），源自 Lindeboom et al. 2016 / 2019")


def revcomp(s):
    return s.translate(COMP)[::-1]


def translate(seq):
    """從第一個鹼基開始轉譯到第一個終止密碼子（含 *）或序列結尾。"""
    out = []
    for i in range(0, len(seq) - 2, 3):
        aa = CODON.get(seq[i:i + 3].upper(), "X")
        out.append(aa)
        if aa == "*":
            break
    return "".join(out)


# ---------------------------------------------------------------- FASTA
class Fasta:
    """取參考序列。.gz（bgzip + .fai + .gzi）用 samtools faidx；未壓縮且有 .fai 時直接讀檔。"""

    def __init__(self, path):
        self.path = str(path)
        self.plain = not self.path.endswith(".gz") and os.path.exists(self.path + ".fai")
        self.cache = {}
        self.fai = {}
        if self.plain:
            with open(self.path + ".fai", encoding="utf-8") as fh:
                for line in fh:
                    name, length, offset, lb, lw = line.split("\t")[:5]
                    self.fai[name] = (int(length), int(offset), int(lb), int(lw))
        elif not os.path.exists(self.path):
            C.die(f"找不到參考序列 {self.path}")

    def fetch_many(self, chrom, ranges):
        """ranges: [(start, end)] 1-based、含兩端；回傳 {(start, end): 序列（+ 股，大寫）}"""
        need = [r for r in ranges if (chrom, r) not in self.cache]
        if need:
            if self.plain:
                for s, e in need:
                    self.cache[(chrom, (s, e))] = self._read_plain(chrom, s, e)
            else:
                regions = [f"{chrom}:{s}-{e}" for s, e in need]
                try:
                    out = subprocess.run(["samtools", "faidx", self.path] + regions, capture_output=True, text=True,
                                         check=True).stdout
                except FileNotFoundError:
                    C.die("找不到 samtools：先 conda activate mva（或用 run_t2_phase1.sh 執行）")
                except subprocess.CalledProcessError as ex:
                    C.die(f"samtools faidx 失敗：{ex.stderr.strip()}（.fai / .gzi 在嗎？）")
                seqs, cur = [], None
                for line in out.splitlines():
                    if line.startswith(">"):
                        if cur is not None:
                            seqs.append("".join(cur))
                        cur = []
                    else:
                        cur.append(line.strip())
                if cur is not None:
                    seqs.append("".join(cur))
                if len(seqs) != len(need):
                    C.die(f"samtools faidx 回傳 {len(seqs)} 段，預期 {len(need)} 段")
                for r, sq in zip(need, seqs):
                    self.cache[(chrom, r)] = sq.upper()
        return {r: self.cache[(chrom, r)] for r in ranges}

    def fetch(self, chrom, s, e):
        return self.fetch_many(chrom, [(s, e)])[(s, e)]

    def _read_plain(self, chrom, s, e):
        if chrom not in self.fai:
            C.die(f"參考序列裡沒有染色體 {chrom}")
        length, offset, lb, lw = self.fai[chrom]
        s0, e0 = max(1, s) - 1, min(e, length)
        out = []
        with open(self.path, "rb") as fh:
            pos = s0
            while pos < e0:
                line_i, col = divmod(pos, lb)
                fh.seek(offset + line_i * lw + col)
                take = min(lb - col, e0 - pos)
                out.append(fh.read(take).decode())
                pos += take
        return "".join(out).upper()


# ---------------------------------------------------------------- GTF / 轉錄本
ATTR_RE = re.compile(r'(\S+) "([^"]*)"')


class Tx:
    """一個轉錄本。所有座標 1-based、含兩端。exons 依轉錄方向排列。"""

    def __init__(self, tid, version, gene, chrom, strand, exons, cds, start_codon, stop_codon, tags):
        self.tid, self.version, self.gene, self.chrom, self.strand = tid, version, gene, chrom, strand
        self.rev = strand == "-"
        self.tags = sorted(set(tags))
        self.exons = sorted(exons, key=lambda x: x[0], reverse=self.rev)
        self.cum = [0]
        for s, e in self.exons:
            self.cum.append(self.cum[-1] + e - s + 1)
        self.tlen = self.cum[-1]
        self.n = len(self.exons)
        self.coding = bool(cds)
        self.cds_start_t = self.stop_last_t = None
        if self.coding:
            if start_codon:
                g = max(e for s, e in start_codon) if self.rev else min(s for s, e in start_codon)
            else:
                g = max(e for s, e in cds) if self.rev else min(s for s, e in cds)
            self.cds_start_t = self.g2t(g)
            if stop_codon:
                g2 = min(s for s, e in stop_codon) if self.rev else max(e for s, e in stop_codon)
                self.stop_last_t = self.g2t(g2)
            else:   # Ensembl 的 CDS 不含終止密碼子；沒有 stop_codon 列時假設它緊接在 CDS 之後
                g2 = min(s for s, e in cds) if self.rev else max(e for s, e in cds)
                self.stop_last_t = self.g2t(g2) + 3

    @property
    def id_version(self):
        return f"{self.tid}.{self.version}" if self.version else self.tid

    @property
    def last_junction_t(self):
        """最後一個外顯子接合處 = 倒數第二個外顯子最後一個鹼基的轉錄本座標。"""
        return self.cum[-2] if self.n > 1 else None

    def g2t(self, g):
        for i, (s, e) in enumerate(self.exons):
            if s <= g <= e:
                return self.cum[i] + ((e - g) if self.rev else (g - s)) + 1
        return None

    def t2g(self, t):
        for i, (s, e) in enumerate(self.exons):
            if self.cum[i] < t <= self.cum[i + 1]:
                k = t - self.cum[i] - 1
                return (e - k) if self.rev else (s + k)
        return None

    def exon_of_t(self, t):
        for i in range(self.n):
            if self.cum[i] < t <= self.cum[i + 1]:
                return i + 1
        return None

    def exon_of_g(self, g):
        for i, (s, e) in enumerate(self.exons):
            if s <= g <= e:
                return i + 1
        return None

    def c_of_t(self, t):
        """轉錄本座標 → c. 編號字串（-N、N、*N）。"""
        if not self.coding:
            return f"n.{t}"
        if t < self.cds_start_t:
            return f"-{self.cds_start_t - t}"
        if t <= self.stop_last_t:
            return str(t - self.cds_start_t + 1)
        return f"*{t - self.stop_last_t}"

    def tx_start_g(self):
        return self.exons[0][1] if self.rev else self.exons[0][0]

    def tx_end_g(self):
        return self.exons[-1][0] if self.rev else self.exons[-1][1]

    def locate(self, g):
        """單一基因體位置相對於這個轉錄本的位置。"""
        t = self.g2t(g)
        if t is not None:
            ex = self.exon_of_t(t)
            if self.coding and t < self.cds_start_t:
                region = "five_prime_utr"
            elif self.coding and t > self.stop_last_t:
                region = "three_prime_utr"
            else:
                region = "cds" if self.coding else "noncoding_exon"
            return {"region": region, "t": t, "c": self.c_of_t(t), "exon": f"{ex}/{self.n}"}
        lo = min(s for s, e in self.exons)
        hi = max(e for s, e in self.exons)
        if g < lo or g > hi:
            upstream = (g > hi) if self.rev else (g < lo)
            if upstream:
                d = (g - self.tx_start_g()) if self.rev else (self.tx_start_g() - g)
                c = f"-{(self.cds_start_t - 1) + d}" if self.coding else f"n.-{d}"
                return {"region": "upstream", "distance": d, "c": c}
            d = (self.tx_end_g() - g) if self.rev else (g - self.tx_end_g())
            c = f"*{(self.tlen - self.stop_last_t) + d}" if self.coding else f"n.*{d}"
            return {"region": "downstream", "distance": d, "c": c}
        for i in range(self.n - 1):           # 內含子：第 i+1 個內含子在外顯子 i+1 與 i+2 之間
            s1, e1 = self.exons[i]
            s2, e2 = self.exons[i + 1]
            if self.rev:
                inside, d_don, d_acc = e2 < g < s1, s1 - g, g - e2
            else:
                inside, d_don, d_acc = e1 < g < s2, g - e1, s2 - g
            if inside:
                if d_don <= d_acc:   # HGVS：正中間時用 +
                    c = f"{self.c_of_t(self.cum[i + 1])}+{d_don}"
                    side, dist = "donor", d_don
                else:
                    c = f"{self.c_of_t(self.cum[i + 1] + 1)}-{d_acc}"
                    side, dist = "acceptor", d_acc
                return {"region": "intron", "intron": f"{i + 1}/{self.n - 1}", "c": c, "side": side,
                        "distance": dist}
        return {"region": "unknown"}


def _quoted(line, key):
    """從 GTF 屬性欄抓 key "值"；找不到回傳 None。比正規表示式快，給逐行過濾用。"""
    i = line.find(key + ' "')
    if i < 0:
        return None
    j = i + len(key) + 2
    k = line.find('"', j)
    return line[j:k] if k > j else None


def load_transcripts(gtf, tx_ids=(), gene=None, mane_only=False):
    """讀 GTF，回傳 {transcript_id（無版本）: Tx}。只收指定轉錄本、指定基因、或（mane_only）全部 MANE Select。"""
    want = set(t.split(".")[0] for t in tx_ids if t)
    rec = {}
    opener = gzip.open if str(gtf).endswith(".gz") else open
    if not os.path.exists(gtf):
        C.die(f"找不到 GTF：{gtf}")
    with opener(gtf, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            tid = _quoted(line, "transcript_id")
            if not tid:
                continue
            if mane_only:
                if "MANE_Select" not in line:
                    continue
            elif not (tid in want or (gene and _quoted(line, "gene_name") == gene)):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 9 or p[2] not in ("transcript", "exon", "CDS", "start_codon", "stop_codon"):
                continue
            attrs = dict(ATTR_RE.findall(p[8]))
            r = rec.setdefault(tid, {"chrom": p[0], "strand": p[6], "version": attrs.get("transcript_version"),
                                     "gene": attrs.get("gene_name"), "exon": [], "CDS": [], "start_codon": [],
                                     "stop_codon": [], "tags": set()})
            for t in re.findall(r'tag "([^"]+)"', p[8]):
                r["tags"].add(t)
            if p[2] != "transcript":
                r[p[2]].append((int(p[3]), int(p[4])))
    out = {}
    for tid, r in rec.items():
        if r["exon"]:
            out[tid] = Tx(tid, r["version"], r["gene"], r["chrom"], r["strand"], r["exon"], r["CDS"],
                          r["start_codon"], r["stop_codon"], r["tags"])
    return out


# ---------------------------------------------------------------- 變異 × 轉錄本
def var_kind(ref, alt):
    if len(ref) == 1 and len(alt) == 1:
        return "snv"
    if len(ref) > len(alt) and alt == ref[:len(alt)] and len(alt) == 1:
        return "del"
    if len(alt) > len(ref) and ref == alt[:len(ref)] and len(ref) == 1:
        return "ins"
    return "delins"


def affected_span(pos, ref, alt):
    """VCF 寫法 → 真正被改動的基因體鹼基範圍（插入回傳錨定鹼基）。"""
    k = var_kind(ref, alt)
    if k == "del":
        return pos + 1, pos + len(ref) - 1
    if k == "ins":
        return pos, pos
    return pos, pos + len(ref) - 1


def build_mutated(tx, fasta, pos, ref, alt):
    """回傳（參考轉錄本序列, 突變轉錄本序列, 突變序列每個鹼基對應的參考轉錄本座標或 None, 錯誤訊息）。"""
    seqs = fasta.fetch_many(tx.chrom, list(tx.exons))
    vstart, vend = pos, pos + len(ref) - 1
    host = [i for i, (s, e) in enumerate(tx.exons) if s <= vstart and vend <= e]
    if not host:
        return None, None, None, "變異跨越外顯子邊界或不在外顯子內"
    hi = host[0]
    s, e = tx.exons[hi]
    if var_kind(ref, alt) == "ins" and pos == e:
        # 插入在外顯子這一側的最後一個基因體鹼基之後：+ 股是外顯子 3' 端、- 股是外顯子 5' 端，都是交界
        return None, None, None, "插入點在外顯子／內含子交界"
    gseq = seqs[(s, e)]
    if gseq[vstart - s:vend - s + 1] != ref.upper():
        # 不寫座標：這段文字會進公開安全版的 YAML
        return None, None, None, "參考序列和 VCF 的 REF 不一致，不是 VCF 的 REF（參考序列版本或座標寫法不對）"
    ref_tx, mut_tx, origin = [], [], []
    same_len = len(ref) == len(alt)
    for i, (es, ee) in enumerate(tx.exons):
        sq = seqs[(es, ee)]
        # 每個鹼基的參考轉錄本座標（O(1)：外顯子在轉錄方向的起點 + 偏移）
        if tx.rev:
            tco = [tx.cum[i] + (ee - (es + k)) + 1 for k in range(len(sq))]
        else:
            tco = [tx.cum[i] + k + 1 for k in range(len(sq))]
        bases = list(zip(sq, tco))                                    # (鹼基, 參考轉錄本座標)，+ 股順序
        if i == hi:
            o = vstart - es
            if same_len:      # SNV / 等長取代：位置一對一，保留原座標
                new = bases[:o] + [(b, bases[o + k][1]) for k, b in enumerate(alt.upper())] + bases[o + len(ref):]
            else:
                common = 0    # 保留和 ALT 開頭相同的錨定鹼基
                while common < min(len(ref), len(alt)) and ref[common].upper() == alt[common].upper():
                    common += 1
                new = bases[:o + common] + [(b, None) for b in alt[common:].upper()] + bases[o + len(ref):]
        else:
            new = bases
        if tx.rev:
            sq_ref = revcomp(sq)
            new = [(b.translate(COMP), t) for b, t in reversed(new)]
        else:
            sq_ref = sq
        ref_tx.append(sq_ref)
        for b, t in new:
            mut_tx.append(b)
            origin.append(t)
    return "".join(ref_tx), "".join(mut_tx), origin, None


def coding_effect(tx, fasta, pos, ref, alt):
    """用參考序列實際轉譯參考與突變轉錄本，回傳編碼後果。"""
    ref_seq, mut_seq, origin, err = build_mutated(tx, fasta, pos, ref, alt)
    if err:
        return {"class": "manual_review", "reason": err}
    try:
        cds_mut0 = origin.index(tx.cds_start_t)                      # 起始密碼子第一個鹼基（0-based）
    except ValueError:
        return {"class": "start_lost_or_edited", "reason": "起始密碼子被改動"}
    p_ref = translate(ref_seq[tx.cds_start_t - 1:])
    p_mut = translate(mut_seq[cds_mut0:])
    if not p_ref.startswith("M"):
        return {"class": "manual_review", "reason": f"參考轉錄本 {tx.id_version} 的 CDS 不是 ATG 開頭（GTF 與 FASTA 版本不符？）"}
    if not p_ref.endswith("*"):
        return {"class": "manual_review", "reason": "參考 CDS 沒有終止密碼子"}
    if len(p_ref) * 3 != tx.stop_last_t - tx.cds_start_t + 1:
        return {"class": "manual_review",
                "reason": "參考 CDS 中間就遇到終止密碼子（硒蛋白的 TGA？或 GTF 註解不完整）：編碼後果要人工判讀"}
    out = {"protein_length_ref": len(p_ref) - 1, "protein_ref_seq": p_ref[:-1]}
    if p_mut == p_ref:
        out["class"] = "synonymous"
        return out
    i = next((k for k in range(min(len(p_ref), len(p_mut))) if p_ref[k] != p_mut[k]), min(len(p_ref), len(p_mut)))
    first = i + 1
    delta = len(alt) - len(ref)
    out["first_changed_aa"] = first
    out["ref_aa"] = THREE.get(p_ref[i], p_ref[i]) if i < len(p_ref) else None
    out["alt_aa"] = THREE.get(p_mut[i], p_mut[i]) if i < len(p_mut) else None
    ter = (len(p_mut)) if p_mut.endswith("*") else None
    if i == 0:
        out["class"] = "start_lost"
    elif delta % 3 != 0:
        out["class"] = "frameshift"
        out["immediate_stop"] = bool(i < len(p_mut) and p_mut[i] == "*")
        out["ptc_aa"] = ter
        out["fs_ter_n"] = (ter - first + 1) if ter else None
    elif i < len(p_mut) and p_mut[i] == "*" and i < len(p_ref) - 1:
        out["class"] = "stop_gained"
        out["ptc_aa"] = first
    elif i == len(p_ref) - 1:
        out["class"] = "stop_lost"
        out["ptc_aa"] = ter
    elif len(p_mut) == len(p_ref) and sum(1 for a, b in zip(p_ref, p_mut) if a != b) == 1:
        out["class"] = "missense"
    elif delta < 0:
        out["class"] = "inframe_deletion"
    elif delta > 0:
        out["class"] = "inframe_insertion"
    else:
        out["class"] = "inframe_delins"
    out["protein_length_alt"] = (len(p_mut) - 1) if p_mut.endswith("*") else len(p_mut)
    if out.get("ptc_aa") and out["class"] in ("stop_gained", "frameshift"):
        ptc_first0 = cds_mut0 + (out["ptc_aa"] - 1) * 3          # 突變序列中 PTC 第一個鹼基（0-based）
        out["stop_codon"] = mut_seq[ptc_first0:ptc_first0 + 3]
        out["plus4_base"] = mut_seq[ptc_first0 + 3] if ptc_first0 + 3 < len(mut_seq) else None
        out.update(nmd_prediction(tx, origin, ptc_first0, cds_mut0))
    return out


def nmd_prediction(tx, origin, ptc_first0, cds_mut0):
    """NMD 預測（只是 predicted）。距離都在突變後的轉錄本座標上算。"""
    res = {"nmd_strength": "predicted", "nmd_rule_source": NMD_RULE_SOURCE}
    if tx.n == 1:
        res.update(nmd_class="escape_single_exon", ptc_to_last_junction_nt=None, nmd_escape_rules=["single_exon"])
        return res
    # PTC 所在外顯子：用 PTC 三個鹼基中第一個保留下來的參考座標
    ref_t = next((origin[k] for k in range(ptc_first0, min(ptc_first0 + 3, len(origin))) if origin[k] is not None), None)
    if ref_t is None:
        res.update(nmd_class="manual_review", reason="PTC 落在插入的鹼基上")
        return res
    ex = tx.exon_of_t(ref_t)
    try:
        lj_mut0 = origin.index(tx.last_junction_t)                   # 倒數第二個外顯子的最後一個鹼基
    except ValueError:
        res.update(nmd_class="manual_review", reason="最後一個接合處附近的鹼基被改動")
        return res
    dist = lj_mut0 - ptc_first0                                       # PTC 第一個鹼基到最後一個接合處
    ex_len = tx.exons[ex - 1][1] - tx.exons[ex - 1][0] + 1
    rules = []
    if ex == tx.n:
        cls = "escape_last_exon"
        rules.append("last_exon")
    elif dist > 55:
        cls = "NMD_predicted"
    elif dist >= 50:
        cls = "borderline_50_55"
    else:
        cls = "escape_within_50nt_of_last_junction"
    if 0 <= dist <= 50 and ex != tx.n:
        rules.append("penultimate_exon_50nt")
    if ptc_first0 - cds_mut0 < 150:
        rules.append("start_proximal_150nt")
    if ex_len > 407:
        rules.append("long_exon_407nt")
    res.update(nmd_class=cls, ptc_to_last_junction_nt=dist, exon_of_ptc=f"{ex}/{tx.n}", exon_of_ptc_length=ex_len,
               nmd_escape_rules=rules)
    if cls == "NMD_predicted" and rules:
        res["nmd_note"] = "預測會進 NMD，但觸發了逃逸規則（" + "、".join(rules) + "）：效率可能不完全"
    return res


def indel_c_window(tx, fasta, pos, ref, alt):
    """indel 可以左右平移的範圍內，所有可能的 c. 起點（VEP 依 HGVS 往 3' 端移，VCF 往左對齊，兩者寫法可能不同）。"""
    k = var_kind(ref, alt)
    if k not in ("del", "ins"):
        return set()
    span = 200
    lo, hi = max(1, pos - span), pos + len(ref) + span
    seq = fasta.fetch(tx.chrom, lo, hi)

    def b(g):
        return seq[g - lo] if lo <= g <= hi else "N"

    labels = set()
    if k == "del":
        d = ref[1:].upper()
        L = len(d)
        g1 = pos + 1                     # 第一個被刪的鹼基
        left = g1
        while left - 1 >= lo and b(left - 1) == b(left - 1 + L):
            left -= 1
        right = g1
        while right + L <= hi and b(right) == b(right + L):
            right += 1
        gs = range(left, right + 1)
        cands = set(gs) | set(g + L - 1 for g in gs)
    else:
        ins = alt[1:].upper()
        L = len(ins)
        p = pos
        left = p
        while left >= lo and b(left) == ins[-1]:
            ins = ins[-1] + ins[:-1]
            left -= 1
        right = p
        ins2 = alt[1:].upper()
        while right + 1 <= hi and b(right + 1) == ins2[0]:
            ins2 = ins2[1:] + ins2[0]
            right += 1
        cands = set(range(left - L, right + L + 2))
    for g in cands:
        loc = tx.locate(g)
        if loc.get("c"):
            labels.add(loc["c"])
    return labels


# ---------------------------------------------------------------- VEP 輸出
def read_vep(path):
    header, rows = None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("##"):
                continue
            if line.startswith("#"):
                header = line[1:].rstrip("\n").split("\t")
                continue
            if header is None:
                continue
            vals = line.rstrip("\n").split("\t")
            rows.append(dict(zip(header, vals)))
    if header is None:
        C.die(f"{path} 不是 VEP --tab 輸出（沒有 # 開頭的表頭）")
    return rows


def blank(v):
    return v in (None, "", "-")


def pick_vep_row(rows, vid, gene=None, tid=None):
    cands = [r for r in rows if r.get("Uploaded_variation") == vid and r.get("Feature_type", "Transcript") == "Transcript"]
    if tid:
        hit = [r for r in cands if r.get("Feature", "").split(".")[0] == tid.split(".")[0]]
        if hit:
            return hit[0], "requested"
    if gene:
        cands = [r for r in cands if r.get("SYMBOL") == gene]
    mane = [r for r in cands if not blank(r.get("MANE_SELECT"))]
    if mane:
        return mane[0], "MANE_SELECT"
    canon = [r for r in cands if r.get("CANONICAL") == "YES"]
    if canon:
        return canon[0], "CANONICAL"
    return None, None


POS_RE = re.compile(r"^(?P<pos>[-*]?\d+)(?P<off>[+-]\d+)?")
HGVSP_RE = re.compile(r"p\.\(?(?P<ref>[A-Z][a-z]{2}|Ter)(?P<pos>\d+)(?P<rest>.*?)\)?$")


def hgvsc_first(hgvsc):
    """'ENST…:c.123+5G>A' → '123+5'；'c.-14C>T' → '-14'；'c.*37del' → '*37'。"""
    if blank(hgvsc) or ":c." not in hgvsc:
        return None
    body = hgvsc.split(":c.", 1)[1]
    m = POS_RE.match(body)
    if not m:
        return None
    return m.group("pos") + (m.group("off") or "")


def parse_hgvsp(hgvsp):
    if blank(hgvsp) or ":p." not in hgvsp:
        return None
    body = "p." + hgvsp.split(":p.", 1)[1].replace("%3D", "=")
    m = HGVSP_RE.match(body)
    if not m:
        return None
    rest = m.group("rest")
    d = {"ref": m.group("ref"), "pos": int(m.group("pos")), "rest": rest}
    fm = re.search(r"fsTer(\d+|\?)", rest)
    if fm:
        d["fs_ter_n"] = None if fm.group(1) == "?" else int(fm.group(1))
    elif rest == "Ter":
        d["stop"] = True
    elif re.fullmatch(r"[A-Z][a-z]{2}", rest):
        d["alt"] = rest
    elif rest in ("=",):
        d["syn"] = True
    return d


VEP_CLASS = {
    "stop_gained": {"stop_gained", "frameshift"},
    "frameshift_variant": {"frameshift"},
    "missense_variant": {"missense"},
    "synonymous_variant": {"synonymous"},
    "inframe_deletion": {"inframe_deletion", "inframe_delins"},
    "inframe_insertion": {"inframe_insertion", "inframe_delins"},
    "protein_altering_variant": {"inframe_delins", "inframe_deletion", "inframe_insertion", "missense"},
    "start_lost": {"start_lost", "start_lost_or_edited"},
    "stop_lost": {"stop_lost"},
    "stop_retained_variant": {"synonymous"},
    "splice_donor_variant": {"splice_canonical"},
    "splice_acceptor_variant": {"splice_canonical"},
    "splice_donor_5th_base_variant": {"splice_region"},
    "splice_donor_region_variant": {"splice_region"},
    "splice_polypyrimidine_tract_variant": {"splice_region", "intronic"},
    "splice_region_variant": {"splice_region", "splice_canonical"},
    "intron_variant": {"intronic", "splice_region", "splice_canonical"},
    "5_prime_UTR_variant": {"five_prime_utr"},
    "3_prime_UTR_variant": {"three_prime_utr"},
    "upstream_gene_variant": {"upstream"},
    "downstream_gene_variant": {"downstream"},
}


def check(checks, name, vep, gtf, status=None):
    if status is None:
        status = "pass" if str(vep) == str(gtf) else "fail"
    checks.append({"name": name, "vep": vep, "gtf": gtf, "status": status})


# ---------------------------------------------------------------- 一個變異的完整事實
def analyse_variant(tx, fasta, chrom, pos, ref, alt):
    """方法 B：位置、區域、編碼後果、NMD、剪接距離。"""
    ref, alt = ref.upper(), alt.upper()
    s, e = affected_span(pos, ref, alt)
    loc_s, loc_e = tx.locate(s), tx.locate(e)
    regions = {loc_s["region"], loc_e["region"]}
    fact = {"strand": tx.strand, "transcript": tx.id_version, "gtf_tags": tx.tags, "kind": var_kind(ref, alt)}
    if len(regions) > 1 or (loc_s.get("exon") and loc_e.get("exon") and loc_s["exon"] != loc_e["exon"]):
        fact.update(region="boundary", c_position=loc_s.get("c"), note="變異跨越外顯子／內含子交界：剪接影響要人工判讀")
        fact["class_b"] = "splice_canonical"
        return fact
    loc = loc_s if not tx.rev else loc_e       # 轉錄方向的第一個鹼基
    fact["region"] = loc["region"]
    fact["c_position"] = loc.get("c")
    if loc.get("exon"):
        fact["exon"] = loc["exon"]
    if loc["region"] == "intron":
        fact["intron"] = loc["intron"]
        d = loc["distance"]
        if d <= 2:
            cls = "splice_canonical"
        elif (loc["side"] == "donor" and d <= 8) or (loc["side"] == "acceptor" and d <= 12):
            cls = "splice_region"
        else:
            cls = "intronic"
        fact["splice"] = {"class": cls, "side": loc["side"], "distance_to_exon_nt": d,
                          "strength": "predicted (位置規則；實際剪接要 SpliceAI 或 RNA)"}
        fact["class_b"] = cls
        return fact
    if loc["region"] in ("upstream", "downstream"):
        # VEP 的 DISTANCE 是「變異離轉錄本最近的那一端」到轉錄本的距離，不是轉錄方向的第一個鹼基
        # （後者是 loc，c_position 必須用它）。SNV 的 s == e，兩者相同；多鹼基變異則差一個 span 長度，
        # 上游的情況在兩股上都會算成遠端而高估。跨界的 span 在前面已經回傳 boundary，所以這裡
        # loc_s 與 loc_e 必定同區，min() 在兩股上都正好是近端。
        fact["distance_to_transcript_nt"] = min(loc_s["distance"], loc_e["distance"])
        fact["class_b"] = loc["region"]
        return fact
    if loc["region"] in ("five_prime_utr", "three_prime_utr", "noncoding_exon"):
        fact["class_b"] = loc["region"]
        return fact
    eff = coding_effect(tx, fasta, pos, ref, alt)
    fact["coding"] = {k: v for k, v in eff.items() if k != "protein_ref_seq"}
    fact["_protein_ref_seq"] = eff.get("protein_ref_seq")
    fact["class_b"] = eff["class"]
    # 外顯子內但離邊界 ≤3 nt：剪接區
    ti = tx.g2t(s)
    exn = tx.exon_of_t(ti)
    if exn is not None:
        start_t, end_t = tx.cum[exn - 1] + 1, tx.cum[exn]
        edge = min(ti - start_t, end_t - ti)
        if edge < 3 and not (exn == 1 and ti - start_t < 3) and not (exn == tx.n and end_t - ti < 3):
            fact["splice"] = {"class": "exonic_splice_region", "distance_to_boundary_nt": edge,
                              "strength": "predicted (位置規則)"}
    return fact


def cross_check(fact, row, tx, fasta, pos, ref, alt):
    checks = []
    if row is None:
        checks.append({"name": "vep_row", "vep": None, "gtf": fact.get("region"), "status": "fail",
                       "note": "VEP 沒有這個基因的轉錄本列（變異離基因太遠？調大 VEP_DISTANCE）"})
        return checks
    check(checks, "transcript_version", row.get("Feature"), tx.id_version)
    strand = {"1": "+", "-1": "-"}.get(row.get("STRAND", ""), row.get("STRAND"))
    check(checks, "strand", strand, tx.strand)
    terms = set((row.get("Consequence") or "").split("&"))
    allowed = set()
    for t in terms:
        allowed |= VEP_CLASS.get(t, set())
    cls = fact.get("class_b")
    if allowed:
        check(checks, "consequence_class", "&".join(sorted(terms)), cls, "pass" if cls in allowed else "fail")
    if fact.get("exon") and not blank(row.get("EXON")):
        check(checks, "exon_number", row.get("EXON"), fact["exon"])
    if fact.get("intron") and not blank(row.get("INTRON")):
        check(checks, "intron_number", row.get("INTRON"), fact["intron"])
    vep_c = hgvsc_first(row.get("HGVSc"))
    if vep_c is not None and fact.get("c_position") is not None:
        if fact["kind"] in ("del", "ins") and fact.get("region") not in ("upstream", "downstream"):
            win = indel_c_window(tx, fasta, pos, ref, alt)
            st = "pass" if (vep_c == fact["c_position"] or vep_c in win) else "fail"
            checks.append({"name": "c_position", "vep": vep_c, "gtf": fact["c_position"], "status": st,
                           "note": "indel：VEP 依 HGVS 移到 3' 端，接受平移範圍內的任何位置"})
        else:
            check(checks, "c_position", vep_c, fact["c_position"])
    hp = parse_hgvsp(row.get("HGVSp"))
    cod = fact.get("coding") or {}
    if hp and cod.get("first_changed_aa"):
        check(checks, "protein_first_changed", hp["pos"], cod["first_changed_aa"])
        if cod.get("class") == "missense" and hp.get("alt"):
            check(checks, "protein_alt_aa", hp["alt"], cod.get("alt_aa"))
        if cod.get("class") == "frameshift" and "fs_ter_n" in hp:
            check(checks, "frameshift_ter_n", hp["fs_ter_n"], cod.get("fs_ter_n"))
    if cod.get("class") == "synonymous" and hp:
        check(checks, "synonymous", hp.get("rest"), "=", "pass" if hp.get("syn") or hp.get("rest") == "=" else "fail")
    if fact.get("region") in ("upstream", "downstream") and not blank(row.get("DISTANCE")):
        d_vep = int(row["DISTANCE"])
        d_gtf = fact.get("distance_to_transcript_nt")
        checks.append({"name": "distance", "vep": d_vep, "gtf": d_gtf,
                       "status": "pass" if d_gtf is not None and abs(d_vep - d_gtf) <= 1 else "fail"})
    return checks


def predictor_fields(row):
    if row is None:
        return {}
    out = {}
    for k in ("SIFT", "PolyPhen"):
        if not blank(row.get(k)):
            out[k.lower()] = row[k]
    if out:
        out["strength"] = "predicted"
    return out


def regulatory_rows(rows, vid):
    out = []
    for r in rows:
        if r.get("Uploaded_variation") == vid and r.get("Feature_type") == "RegulatoryFeature":
            out.append({"id": r.get("Feature"), "type": r.get("BIOTYPE") or r.get("Consequence")})
    return out


# ---------------------------------------------------------------- 子指令
def cmd_mini_vcf(a):
    H = C.read_yaml(a.handoff)
    lines = ["##fileformat=VCFv4.2", "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"]
    for v in H["variants"]:
        c, p, r, al = v["key"].split(":")
        lines.append(f"{c}\t{p}\t{v['id']}\t{r}\t{al}\t.\t.\t.")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    if out.exists() and out.read_text(encoding="utf-8") == text:      # 內容沒變就不改檔案時間，VEP 那一步才能跳過
        C.ok(f"迷你 VCF 沒變：{out.name}")
        return
    out.write_text(text, encoding="utf-8")
    C.ok(f"迷你 VCF：{len(H['variants'])} 個變異 → {out.name}")


PRIVATE_ONLY = ("key", "hgvs_g", "regulatory_features", "genotype")


def cmd_facts(a):
    C.assert_private_location(a.out, "transcript_facts（含座標）")
    H = C.read_yaml(a.handoff)
    rows = read_vep(a.vep)
    gene = H.get("gene")
    fasta = Fasta(a.ref)
    want = set()
    for v in H["variants"]:
        r, _ = pick_vep_row(rows, v["id"], gene)
        if r:
            want.add(r["Feature"])
    txs = load_transcripts(a.gtf, tx_ids=want, gene=gene)
    if not txs:
        C.die(f"GTF 裡找不到 {gene} 的轉錄本（GTF 版本 = VEP 版本嗎？）")
    mane = [t for t in txs.values() if "MANE_Select" in t.tags and t.gene == gene]
    facts = {"schema": "transcript_facts/2", "generated_at": C.now_iso(), "gene": gene, "mode": H.get("mode"),
             "tools": {"vep_version": os.environ.get("VEP_VERSION"), "gtf": Path(a.gtf).name,
                       "reference": Path(a.ref).name}, "variants": []}
    public = {"schema": "transcript_facts_public/2", "generated_at": facts["generated_at"], "gene": gene,
              "mode": H.get("mode"), "tools": facts["tools"], "variants": []}
    any_fail = False
    protein_seq = None
    for v in H["variants"]:
        chrom, pos, ref, alt = v["key"].split(":")
        pos = int(pos)
        row, how = pick_vep_row(rows, v["id"], gene)
        tx = txs.get(row["Feature"].split(".")[0]) if row else (mane[0] if mane else None)
        if tx is None:
            C.die(f"{v['id']}：找不到可用的轉錄本")
        fact = analyse_variant(tx, fasta, chrom, pos, ref, alt)
        protein_seq = fact.pop("_protein_ref_seq", None) or protein_seq
        checks = cross_check(fact, row, tx, fasta, pos, ref, alt)
        status = "pass" if checks and all(c["status"] == "pass" for c in checks) else "fail"
        any_fail = any_fail or status == "fail"
        rec = {"id": v["id"], "identity_status": v.get("identity_status"), "zygosity": v.get("zygosity"),
               "transcript": tx.id_version, "transcript_choice": how or "gtf_mane_fallback",
               "mane_select": row.get("MANE_SELECT") if row else None,
               "consequence": row.get("Consequence") if row else fact.get("class_b"),
               "impact": row.get("IMPACT") if row else None,
               "region": fact.get("region"), "exon": fact.get("exon"), "intron": fact.get("intron"),
               "c_position": fact.get("c_position"),
               "hgvs_c": row.get("HGVSc") if row and not blank(row.get("HGVSc")) else None,
               "hgvs_p": row.get("HGVSp") if row and not blank(row.get("HGVSp")) else None,
               "protein_position": row.get("Protein_position") if row and not blank(row.get("Protein_position")) else None,
               "amino_acids": row.get("Amino_acids") if row and not blank(row.get("Amino_acids")) else None,
               "uniprot": row.get("SWISSPROT") if row and not blank(row.get("SWISSPROT")) else None,
               "uniprot_isoform": row.get("UNIPROT_ISOFORM") if row and not blank(row.get("UNIPROT_ISOFORM")) else None,
               "coding": fact.get("coding"), "splice": fact.get("splice"),
               "distance_to_transcript_nt": fact.get("distance_to_transcript_nt"),
               "predictors": predictor_fields(row),
               "cross_check": {"status": status, "checks": checks}}
        if fact.get("note"):
            rec["note"] = fact["note"]
        priv = dict(rec)
        priv["key"] = v["key"]
        priv["hgvs_g"] = row.get("HGVSg") if row else None
        priv["regulatory_features"] = regulatory_rows(rows, v["id"])
        facts["variants"].append(priv)
        pub = {k: val for k, val in rec.items() if k not in PRIVATE_ONLY}
        reg = regulatory_rows(rows, v["id"])
        if reg:
            pub["regulatory_feature_types"] = sorted(set(r["type"] for r in reg if r.get("type")))
        public["variants"].append(pub)
        mark = "✓" if status == "pass" else "✗"
        cls = (fact.get("coding") or {}).get("class") or fact.get("class_b")
        print(f"  {mark} {v['id']}：{tx.id_version} · {fact.get('region')} · {cls} · 交叉檢查 {status}"
              f"（{sum(c['status'] == 'pass' for c in checks)}/{len(checks)}）", flush=True)
        for c in checks:
            if c["status"] != "pass":
                print(f"      ✗ {c['name']}：VEP={c['vep']}　GTF={c['gtf']}", flush=True)
    C.write_yaml(a.out, facts, header="# 含基因體座標：只放 ~/mva-hackathon/results/track2，不進 git、不進 iCloud 樹")
    C.write_yaml(a.public, public, header="# 公開安全版：無基因體座標、無基因型品質。由 scripts/phase1/11_transcript_facts.sh 產生，不要手改")
    if a.protein_cache and protein_seq:
        pc = Path(a.protein_cache)
        pc.mkdir(parents=True, exist_ok=True)
        tid = facts["variants"][0]["transcript"] if facts["variants"] else "protein"
        (pc / f"{tid}.protein.fa").write_text(f">{tid} translated from GTF+FASTA\n{protein_seq}\n", encoding="utf-8")
    C.ok(f"寫出 {Path(a.out).name}（本機）與 {Path(a.public).name}（公開安全）")
    if any_fail:
        C.warn("有交叉檢查不一致：先看上面 ✗ 的項目（Spec 1 第 2.7 節的處理順序），不要直接用這份結果")
        sys.exit(3)


def cmd_selftest(a):
    rows = read_vep(a.vep)
    variants = []
    with open(a.vcf, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            variants.append((p[2], p[0], int(p[1]), p[3], p[4]))
    want = set(r["Feature"] for r in rows if not blank(r.get("MANE_SELECT")) and r.get("Feature_type") == "Transcript")
    C.info(f"讀 GTF（{len(want)} 個 MANE 轉錄本）…")
    txs = load_transcripts(a.gtf, tx_ids=want)
    fasta = Fasta(a.ref)
    stats, out_rows, skipped = {}, [], []
    by_strand = {"+": 0, "-": 0}
    for vid, chrom, pos, ref, alt in variants:
        for r in rows:
            if r.get("Uploaded_variation") != vid or blank(r.get("MANE_SELECT")) or r.get("Feature_type") != "Transcript":
                continue
            tx = txs.get(r["Feature"].split(".")[0])
            if tx is None:
                continue
            try:
                fact = analyse_variant(tx, fasta, chrom, pos, ref, alt)
                if fact.get("class_b") == "manual_review":     # 硒蛋白、REF 不符等：記下來，不算進分母
                    skipped.append((vid, tx.id_version, (fact.get("coding") or {}).get("reason")))
                    continue
                checks = cross_check(fact, r, tx, fasta, pos, ref, alt)
            except Exception as ex:   # 自我檢查要把錯誤記下來，不中斷
                checks = [{"name": "exception", "vep": None, "gtf": repr(ex), "status": "fail"}]
                fact = {"class_b": "error"}
            by_strand[tx.strand] = by_strand.get(tx.strand, 0) + 1
            for c in checks:
                s = stats.setdefault(c["name"], [0, 0])
                s[0 if c["status"] == "pass" else 1] += 1
            fails = [c for c in checks if c["status"] != "pass"]
            out_rows.append({"variant": vid, "transcript": tx.id_version, "strand": tx.strand,
                             "vep_consequence": r.get("Consequence"), "class_b": fact.get("class_b"),
                             "n_checks": len(checks), "n_fail": len(fails),
                             "failed": "; ".join(f"{c['name']}:VEP={c['vep']}|GTF={c['gtf']}" for c in fails)})
    with open(a.report, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["variant", "transcript", "strand", "vep_consequence", "class_b",
                                           "n_checks", "n_fail", "failed"], delimiter="\t")
        w.writeheader()
        w.writerows(out_rows)
    total = sum(p + f for p, f in stats.values())
    passed = sum(p for p, f in stats.values())
    pairs = len(out_rows)
    clean = sum(1 for r in out_rows if r["n_fail"] == 0)
    print(f"\n自我檢查：{pairs} 個「變異 × MANE 轉錄本」（+ 股 {by_strand.get('+', 0)}、- 股 {by_strand.get('-', 0)}）", flush=True)
    for name, (p, f) in sorted(stats.items()):
        print(f"  {name:<24} {p:>5} 一致　{f:>4} 不一致", flush=True)
    rate = clean / pairs if pairs else 0
    print(f"完全一致的比例：{clean}/{pairs} = {rate:.1%}（報告：{a.report}）", flush=True)
    if skipped:
        print(f"另有 {len(skipped)} 組需要人工判讀、不計入（例如硒蛋白）：", flush=True)
        for vid, tid, why in skipped[:10]:
            print(f"  - {vid} {tid}：{why}", flush=True)
    if pairs < 50 or by_strand.get("-", 0) < 10 or by_strand.get("+", 0) < 10:
        C.die("樣本太少或缺一股，無法判斷：加大 N 再跑")
    if rate < a.min_rate:
        C.die(f"一致比例低於 {a.min_rate:.0%}：打開報告看不一致的類型，先修 transcript_facts.py 再碰病人變異", 3)
    C.ok("方法 B 和 VEP 在公開變異上一致，可以進行第 11 步")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mini-vcf")
    m.add_argument("--handoff", required=True)
    m.add_argument("--out", required=True)
    f = sub.add_parser("facts")
    for k in ("handoff", "vep", "gtf", "ref", "out", "public"):
        f.add_argument("--" + k, required=True)
    f.add_argument("--protein-cache")
    s = sub.add_parser("selftest")
    for k in ("vcf", "vep", "gtf", "ref", "report"):
        s.add_argument("--" + k, required=True)
    s.add_argument("--min-rate", type=float, default=0.99)
    a = ap.parse_args()
    {"mini-vcf": cmd_mini_vcf, "facts": cmd_facts, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    main()
