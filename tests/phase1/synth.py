"""合成基因體：測試 Spec 1 腳本用（不含任何真實資料）。

一條 6 kb 的合成染色體 S，上面兩個轉錄本：
  TXP（+ 股，4 個外顯子）與 TXM（- 股，4 個外顯子），都有 5'UTR、CDS（ATG 開頭、終止密碼子結尾、中間無終止）與 3'UTR。
另外提供一個「獨立」的參考實作（直接改整條染色體字串、重新剪接、轉譯），用來產生預期值，
和 transcript_facts.py 的座標換算互相比對。
"""
import random

COMP = str.maketrans("ACGT", "TGCA")
CODON = {}
_b = "TCAG"
_aa = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
for _i, _x in enumerate(_b):
    for _j, _y in enumerate(_b):
        for _k, _z in enumerate(_b):
            CODON[_x + _y + _z] = _aa[16 * _i + 4 * _j + _k]
SENSE = [c for c, a in CODON.items() if a != "*" and c != "ATG"]


def rc(s):
    return s.translate(COMP)[::-1]


def translate(s):
    out = []
    for i in range(0, len(s) - 2, 3):
        a = CODON[s[i:i + 3]]
        out.append(a)
        if a == "*":
            break
    return "".join(out)


class Synth:
    CHROM = "S"

    def __init__(self, seed=7):
        rnd = random.Random(seed)
        self.rnd = rnd
        L = 6000
        g = [rnd.choice("ACGT") for _ in range(L)]

        # ---- TXP（+ 股）
        self.p_exons = [(1001, 1100), (1301, 1450), (1701, 1800), (2001, 2400)]   # 轉錄方向 = 基因體遞增
        self.p_cds_start = 1051                                                  # c.1 的基因體座標
        coding_len = 50 + 150 + 100 + 150                                         # 450 = 150 個密碼子
        cds = "ATG" + "".join(rnd.choice(SENSE) for _ in range(148)) + "TAA"
        # 預先放好的密碼子：20、70、95 是 CAG（C>T 變 TAG）、120 是 CGA（C>T 變 TGA）、40 是 TGG（錯義測試）
        # 59 = GCC、60–61 = AAA AAA：外顯子 2 裡一段 6 個 A（c.178–183），給 indel 平移測試
        cds = self._plant(cds, {20: "CAG", 40: "TGG", 59: "GCC", 60: "AAA", 61: "AAA", 62: "GCC", 67: "CAG",
                                70: "CAG", 95: "CAG", 120: "CGA"})   # 67：密碼子跨外顯子 2/3 交界（c.199–201）
        assert len(cds) == coding_len
        tpos = self._tx_positions(self.p_exons, "+")
        start_i = tpos.index(self.p_cds_start)
        for k, base in enumerate(cds):
            g[tpos[start_i + k] - 1] = base
        for s, e in self._introns(self.p_exons, "+"):
            g[s - 1], g[s] = "G", "T"
            g[e - 2], g[e - 1] = "A", "G"
        self.p_stop_last = tpos[start_i + coding_len - 1]

        # ---- TXM（- 股）
        self.m_exons_asc = [(3001, 3200), (3401, 3500), (3701, 3850), (4001, 4100)]
        self.m_exons = sorted(self.m_exons_asc, key=lambda x: x[0], reverse=True)   # 轉錄方向 = 基因體遞減
        tposm = self._tx_positions(self.m_exons, "-")
        # 5'UTR 40 nt（外顯子 1 的前 40 個轉錄本鹼基），CDS 從第 41 個開始
        mstart_i = 40
        self.m_cds_start = tposm[mstart_i]
        mcds = "ATG" + "".join(rnd.choice(SENSE) for _ in range(149)) + "TGA"     # 151 個密碼子 = 453 nt
        mcds = self._plant(mcds, {15: "CAA", 80: "TGG", 140: "CAG"})
        for k, base in enumerate(mcds):
            gp = tposm[mstart_i + k]
            g[gp - 1] = base.translate(COMP)                                         # 轉錄本鹼基 → + 股鹼基
        self.m_stop_last = tposm[mstart_i + len(mcds) - 1]
        for s, e in self._introns(self.m_exons, "-"):
            # - 股內含子：轉錄方向開頭（基因體高端）是 GT，結尾（基因體低端）是 AG → + 股寫反向互補
            g[e - 1], g[e - 2] = "C", "A"     # GT 的反向互補 AC，放在高端
            g[s - 1], g[s] = "C", "T"         # AG 的反向互補 CT，放在低端
        self.seq = "".join(g)
        self.p_cds = cds
        self.m_cds = mcds

    # ------------------------------------------------------------ 建構工具
    @staticmethod
    def _plant(cds, codons):
        cl = [cds[i:i + 3] for i in range(0, len(cds), 3)]
        for idx, c in codons.items():
            cl[idx - 1] = c
        return "".join(cl)

    @staticmethod
    def _tx_positions(exons_tx_order, strand):
        out = []
        for s, e in exons_tx_order:
            out.extend(range(s, e + 1) if strand == "+" else range(e, s - 1, -1))
        return out

    @staticmethod
    def _introns(exons_tx_order, strand):
        asc = sorted(exons_tx_order)
        return [(asc[i][1] + 1, asc[i + 1][0] - 1) for i in range(len(asc) - 1)]

    # ------------------------------------------------------------ 檔案
    def write_fasta(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f">{self.CHROM}\n")
            for i in range(0, len(self.seq), 60):
                fh.write(self.seq[i:i + 60] + "\n")
        offset = len(f">{self.CHROM}\n")
        with open(str(path) + ".fai", "w", encoding="utf-8") as fh:
            fh.write(f"{self.CHROM}\t{len(self.seq)}\t{offset}\t60\t61\n")

    def gtf_lines(self):
        lines = []

        def attrs(tid, gname, ver, tags):
            a = f'gene_id "G{gname}"; gene_version "1"; transcript_id "{tid}"; transcript_version "{ver}"; gene_name "{gname}";'
            for t in tags:
                a += f' tag "{t}";'
            return a

        def emit(tid, gname, ver, strand, exons_asc, cds_ranges, start, stop):
            tags = ["Ensembl_canonical", "MANE_Select"]
            lo, hi = exons_asc[0][0], exons_asc[-1][1]
            lines.append(f"{self.CHROM}\tsynth\ttranscript\t{lo}\t{hi}\t.\t{strand}\t.\t{attrs(tid, gname, ver, tags)}")
            for s, e in exons_asc:
                lines.append(f"{self.CHROM}\tsynth\texon\t{s}\t{e}\t.\t{strand}\t.\t{attrs(tid, gname, ver, tags)}")
            for s, e in cds_ranges:
                lines.append(f"{self.CHROM}\tsynth\tCDS\t{s}\t{e}\t.\t{strand}\t0\t{attrs(tid, gname, ver, tags)}")
            lines.append(f"{self.CHROM}\tsynth\tstart_codon\t{start[0]}\t{start[1]}\t.\t{strand}\t0\t{attrs(tid, gname, ver, tags)}")
            lines.append(f"{self.CHROM}\tsynth\tstop_codon\t{stop[0]}\t{stop[1]}\t.\t{strand}\t0\t{attrs(tid, gname, ver, tags)}")

        # TXP：CDS 不含終止密碼子（Ensembl 慣例）
        p_stop = (self.p_stop_last - 2, self.p_stop_last)
        p_cds = [(1051, 1100), (1301, 1450), (1701, 1800), (2001, p_stop[0] - 1)]
        emit("ENSTSYNP", "GENEP", "3", "+", self.p_exons, p_cds, (1051, 1053), p_stop)
        # TXM
        m_stop = (self.m_stop_last, self.m_stop_last + 2)            # 基因體遞增寫法
        tpos = self._tx_positions(self.m_exons, "-")
        cds_set = tpos[tpos.index(self.m_cds_start): tpos.index(self.m_stop_last) - 2]   # 不含終止密碼子
        m_cds = []
        for s, e in self.m_exons_asc:
            inside = [p for p in cds_set if s <= p <= e]
            if inside:
                m_cds.append((min(inside), max(inside)))
        emit("ENSTSYNM", "GENEM", "5", "-", self.m_exons_asc, m_cds, (self.m_cds_start - 2, self.m_cds_start), m_stop)
        return lines

    def write_gtf(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("#!genome-build synthetic\n")
            fh.write("\n".join(self.gtf_lines()) + "\n")

    # ------------------------------------------------------------ 獨立參考實作
    def tx(self, which):
        if which == "P":
            return {"exons": self.p_exons, "strand": "+", "cds_start": self.p_cds_start, "stop_last": self.p_stop_last}
        return {"exons": self.m_exons, "strand": "-", "cds_start": self.m_cds_start, "stop_last": self.m_stop_last}

    def tpos(self, which):
        t = self.tx(which)
        return self._tx_positions(t["exons"], t["strand"])

    def c_of_g(self, which, g):
        """獨立算 c. 編號（只處理外顯子內的位置）。"""
        tp = self.tpos(which)
        t = self.tx(which)
        ti = tp.index(g)
        si = tp.index(t["cds_start"])
        ei = tp.index(t["stop_last"])
        if ti < si:
            return f"-{si - ti}"
        if ti <= ei:
            return str(ti - si + 1)
        return f"*{ti - ei}"

    def ref_base(self, g):
        return self.seq[g - 1]

    def mutate_and_translate(self, which, pos, ref, alt):
        """直接改整條染色體，外顯子座標依 delta 平移，重新剪接、轉譯。回傳（參考蛋白, 突變蛋白）。"""
        assert self.seq[pos - 1:pos - 1 + len(ref)] == ref
        new = self.seq[:pos - 1] + alt + self.seq[pos - 1 + len(ref):]
        delta = len(alt) - len(ref)
        t = self.tx(which)
        ex_new = []
        for s, e in t["exons"]:
            s2 = s + delta if s > pos else s
            e2 = e + delta if e >= pos + len(ref) - 1 or (e > pos) else e
            ex_new.append((s2, e2))

        def spliced(seq, exons, strand):
            parts = [seq[s - 1:e] for s, e in exons]
            if strand == "-":
                return "".join(rc(p) for p in parts)
            return "".join(parts)

        ref_tx = spliced(self.seq, t["exons"], t["strand"])
        mut_tx = spliced(new, ex_new, t["strand"])
        tp = self.tpos(which)
        si = tp.index(t["cds_start"])
        # 起始密碼子在變異 5' 端時，突變序列的起點不變
        return translate(ref_tx[si:]), translate(mut_tx[si:])

    def codon_g(self, which, codon_no):
        """第 n 個密碼子三個鹼基的基因體座標（轉錄方向）。"""
        tp = self.tpos(which)
        si = tp.index(self.tx(which)["cds_start"])
        return [tp[si + (codon_no - 1) * 3 + k] for k in range(3)]
