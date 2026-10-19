"""transcript_facts.py 的測試：合成基因體、兩股、各種變異類型、和（模擬的）VEP 交叉檢查。"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
P1 = HERE.parents[1] / "scripts" / "phase1"
sys.path.insert(0, str(P1))
sys.path.insert(0, str(HERE))

import synth  # noqa: E402
import transcript_facts as TF  # noqa: E402

VEP_COLS = ["Uploaded_variation", "Location", "Allele", "Feature_type", "Feature", "BIOTYPE", "SYMBOL", "STRAND",
            "MANE_SELECT", "CANONICAL", "Consequence", "IMPACT", "EXON", "INTRON", "cDNA_position", "CDS_position",
            "Protein_position", "Amino_acids", "Codons", "HGVSc", "HGVSp", "HGVSg", "DISTANCE", "SIFT", "PolyPhen",
            "SWISSPROT", "UNIPROT_ISOFORM"]


def vep_row(vid, which, **kw):
    tid = "ENSTSYNP.3" if which == "P" else "ENSTSYNM.5"
    r = {c: "-" for c in VEP_COLS}
    r.update({"Uploaded_variation": vid, "Feature_type": "Transcript", "Feature": tid, "BIOTYPE": "protein_coding",
              "SYMBOL": "GENEP" if which == "P" else "GENEM", "STRAND": "1" if which == "P" else "-1",
              "MANE_SELECT": "NM_SYN" + which + ".1", "CANONICAL": "YES", "SWISSPROT": "Q00000.1"})
    r.update(kw)
    return r


def write_vep(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("## ENSEMBL VARIANT EFFECT PREDICTOR (simulated for tests)\n")
        fh.write("#" + "\t".join(VEP_COLS) + "\n")
        for r in rows:
            fh.write("\t".join(str(r.get(c, "-")) for c in VEP_COLS) + "\n")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="t2tf_"))
        cls.sy = synth.Synth()
        cls.fa_path = cls.tmp / "s.fa"
        cls.gtf_path = cls.tmp / "s.gtf"
        cls.sy.write_fasta(cls.fa_path)
        cls.sy.write_gtf(cls.gtf_path)
        txs = TF.load_transcripts(str(cls.gtf_path), gene="GENEP")
        txs.update(TF.load_transcripts(str(cls.gtf_path), gene="GENEM"))
        cls.P, cls.M = txs["ENSTSYNP"], txs["ENSTSYNM"]
        cls.fa = TF.Fasta(cls.fa_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def snv_at(self, which, g, alt):
        ref = self.sy.ref_base(g)
        tx = self.P if which == "P" else self.M
        return ref, TF.analyse_variant(tx, self.fa, "S", g, ref, alt)


class TestCoordinates(Base):
    def test_every_exonic_position_both_strands(self):
        for which, tx in (("P", self.P), ("M", self.M)):
            for g in self.sy.tpos(which):
                self.assertEqual(tx.locate(g)["c"], self.sy.c_of_g(which, g), f"{which} {g}")

    def test_g2t_t2g_roundtrip(self):
        for tx in (self.P, self.M):
            for t in range(1, tx.tlen + 1):
                self.assertEqual(tx.g2t(tx.t2g(t)), t)

    def test_reference_proteins_match_designed_cds(self):
        for which, tx, cds in (("P", self.P, self.sy.p_cds), ("M", self.M, self.sy.m_cds)):
            segs = self.fa.fetch_many("S", tx.exons)
            seq = "".join(segs[r] if tx.strand == "+" else TF.revcomp(segs[r]) for r in tx.exons)
            self.assertEqual(TF.translate(seq[tx.cds_start_t - 1:]), synth.translate(cds))

    def test_intron_labels(self):
        loc = self.P.locate(1105)                       # 內含子 1，donor +5
        self.assertEqual((loc["region"], loc["c"], loc["intron"], loc["side"]), ("intron", "50+5", "1/3", "donor"))
        loc = self.P.locate(1298)                       # 內含子 1，acceptor -3
        self.assertEqual((loc["c"], loc["side"]), ("51-3", "acceptor"))
        loc = self.M.locate(3503)                       # - 股：內含子 2 的 acceptor -3
        self.assertEqual((loc["region"], loc["c"], loc["intron"]), ("intron", "211-3", "2/3"))
        loc = self.M.locate(3698)                       # - 股：內含子 2 的 donor +3（外顯子 2 的轉錄本終點是 3701）
        self.assertEqual((loc["c"], loc["side"]), ("210+3", "donor"))

    def test_utr_upstream_downstream(self):
        self.assertEqual(self.P.locate(1010)["c"], "-41")
        self.assertEqual(self.P.locate(2200)["c"], "*50")
        up = self.P.locate(900)
        self.assertEqual((up["region"], up["distance"], up["c"]), ("upstream", 101, "-151"))
        upm = self.M.locate(4300)
        self.assertEqual((upm["region"], upm["distance"], upm["c"]), ("upstream", 200, "-240"))
        dn = self.P.locate(2450)
        self.assertEqual((dn["region"], dn["distance"], dn["c"]), ("downstream", 50, "*300"))


class TestCodingEffects(Base):
    def test_stop_gained_and_nmd_classes_plus_strand(self):
        expect = {20: ("NMD_predicted", 242, ["start_proximal_150nt"]),
                  70: ("NMD_predicted", 92, []),
                  95: ("escape_within_50nt_of_last_junction", 17, ["penultimate_exon_50nt"]),
                  120: ("escape_last_exon", -58, ["last_exon"])}
        for cno, (cls, dist, rules) in expect.items():
            g = self.sy.codon_g("P", cno)[0]
            _, f = self.snv_at("P", g, "T")
            self.assertEqual(f["class_b"], "stop_gained")
            self.assertEqual(f["coding"]["ptc_aa"], cno)
            self.assertEqual(f["coding"]["nmd_class"], cls, cno)
            self.assertEqual(f["coding"]["ptc_to_last_junction_nt"], dist, cno)
            self.assertEqual(f["coding"]["nmd_escape_rules"], rules, cno)
            self.assertEqual(f["coding"]["nmd_strength"], "predicted")

    def test_stop_gained_minus_strand(self):
        g = self.sy.codon_g("M", 15)[0]
        ref, f = self.snv_at("M", g, "A")                # 轉錄本 C>T = + 股 G>A
        self.assertEqual(ref, "G")
        self.assertEqual((f["class_b"], f["c_position"], f["exon"]), ("stop_gained", "43", "1/4"))
        self.assertEqual(f["coding"]["stop_codon"], "TAA")
        self.assertEqual(f["coding"]["ptc_to_last_junction_nt"], 267)
        g = self.sy.codon_g("M", 140)[0]
        _, f = self.snv_at("M", g, "A")
        self.assertEqual(f["coding"]["nmd_class"], "escape_last_exon")

    def test_missense_synonymous_start_stop(self):
        g = self.sy.codon_g("P", 40)[1]                  # TGG 第 2 個鹼基 G>C → TCG
        _, f = self.snv_at("P", g, "C")
        self.assertEqual((f["class_b"], f["c_position"], f["coding"]["ref_aa"], f["coding"]["alt_aa"]),
                         ("missense", "119", "Trp", "Ser"))
        g = self.sy.codon_g("P", 62)[2]                  # GCC → GCT
        _, f = self.snv_at("P", g, "T")
        self.assertEqual(f["class_b"], "synonymous")
        g = self.sy.codon_g("P", 1)[0]                   # ATG → GTG
        _, f = self.snv_at("P", g, "G")
        self.assertEqual(f["class_b"], "start_lost")
        g = self.sy.codon_g("P", 150)[2]                 # TAA → TAC
        _, f = self.snv_at("P", g, "C")
        self.assertEqual(f["class_b"], "stop_lost")

    def test_frameshift_deletion_in_homopolymer(self):
        # c.177 是 GCC 的最後一個鹼基（錨定），刪掉 AAAAAA 的第一個 A（VCF 左對齊寫法）
        anchor = self.sy.codon_g("P", 59)[2]
        ref = self.sy.ref_base(anchor) + self.sy.ref_base(anchor + 1)
        alt = ref[0]
        f = TF.analyse_variant(self.P, self.fa, "S", anchor, ref, alt)
        p_ref, p_mut = self.sy.mutate_and_translate("P", anchor, ref, alt)
        first = next(i for i in range(min(len(p_ref), len(p_mut))) if p_ref[i] != p_mut[i]) + 1
        self.assertEqual(f["class_b"], "frameshift")
        self.assertEqual(f["coding"]["first_changed_aa"], first)
        self.assertEqual(f["coding"]["ptc_aa"], len(p_mut) if p_mut.endswith("*") else None)
        self.assertEqual(f["c_position"], "178")
        win = TF.indel_c_window(self.P, self.fa, anchor, ref, alt)
        self.assertIn("183", win)                         # VEP 會寫 c.183del（往 3' 端移）
        self.assertIn("178", win)

    def test_frameshift_insertion_minus_strand(self):
        anchor = 3800
        ref = self.sy.ref_base(anchor)
        alt = ref + "T"
        f = TF.analyse_variant(self.M, self.fa, "S", anchor, ref, alt)
        p_ref, p_mut = self.sy.mutate_and_translate("M", anchor, ref, alt)
        first = next(i for i in range(min(len(p_ref), len(p_mut))) if p_ref[i] != p_mut[i]) + 1
        self.assertEqual(f["class_b"], "frameshift")
        self.assertEqual(f["coding"]["first_changed_aa"], first)
        self.assertEqual(f["coding"]["ptc_aa"], len(p_mut) if p_mut.endswith("*") else None)

    def test_inframe_deletion(self):
        g0 = self.sy.codon_g("P", 30)[2]                 # 錨定 = 第 30 個密碼子最後一個鹼基，刪掉第 31 個密碼子
        ref = "".join(self.sy.ref_base(g) for g in range(g0, g0 + 4))
        f = TF.analyse_variant(self.P, self.fa, "S", g0, ref, ref[0])
        self.assertIn(f["class_b"], ("inframe_deletion", "inframe_delins"))

    def test_boundary_and_splice_classes(self):
        ref = "".join(self.sy.ref_base(g) for g in range(1448, 1453))
        f = TF.analyse_variant(self.P, self.fa, "S", 1448, ref, ref[0])   # 刪掉 1449–1452，跨過外顯子 2 的終點 1450
        self.assertEqual(f["region"], "boundary")
        self.assertEqual(f["class_b"], "splice_canonical")
        _, f = self.snv_at("P", 1102, "A" if self.sy.ref_base(1102) != "A" else "C")   # donor +2
        self.assertEqual(f["splice"]["class"], "splice_canonical")
        _, f = self.snv_at("P", 1105, "A" if self.sy.ref_base(1105) != "A" else "C")   # donor +5
        self.assertEqual(f["splice"]["class"], "splice_region")
        _, f = self.snv_at("P", 1200, "A" if self.sy.ref_base(1200) != "A" else "C")   # 深層內含子
        self.assertEqual(f["splice"]["class"], "intronic")

    def test_ref_mismatch_is_reported(self):
        g = self.sy.codon_g("P", 40)[0]
        wrong = "A" if self.sy.ref_base(g) != "A" else "C"
        f = TF.analyse_variant(self.P, self.fa, "S", g, wrong, "G")
        self.assertEqual(f["class_b"], "manual_review")
        self.assertIn("不是 VCF 的 REF", f["coding"]["reason"])


class TestEdgeCases(Base):
    def test_stop_codon_split_across_exon_junction(self):
        gs = self.sy.codon_g("P", 67)
        self.assertEqual([self.P.exon_of_g(g) for g in gs], [2, 2, 3])
        _, f = self.snv_at("P", gs[0], "T")                       # CAG → TAG，跨 2/3 交界
        self.assertEqual((f["class_b"], f["c_position"]), ("stop_gained", "199"))
        self.assertEqual(f["coding"]["stop_codon"], "TAG")
        self.assertEqual(f["coding"]["ptc_to_last_junction_nt"], 350 - 249)
        self.assertEqual(f["coding"]["exon_of_ptc"], "2/4")

    def test_minus_strand_homopolymer_deletion_window(self):
        tp = self.sy.tpos("M")
        seq_t = "".join(synth.rc(self.sy.ref_base(g)) for g in tp)     # 轉錄本方向的序列
        si = tp.index(self.sy.m_cds_start)
        run = next(i for i in range(si + 30, si + 400) if seq_t[i] == seq_t[i + 1] == seq_t[i + 2])
        g_hi, g_lo = tp[run], tp[run + 2]                            # 轉錄本 5' 端（基因體高）與 3' 端（基因體低）
        anchor = g_lo - 1                                            # 左對齊：刪掉基因體最低的那個鹼基
        ref = self.sy.ref_base(anchor) + self.sy.ref_base(g_lo)
        f = TF.analyse_variant(self.M, self.fa, "S", anchor, ref, ref[0])
        self.assertEqual(f["class_b"], "frameshift")
        win = TF.indel_c_window(self.M, self.fa, anchor, ref, ref[0])
        self.assertIn(self.sy.c_of_g("M", g_lo), win)                # HGVS 3' 端（轉錄方向）
        self.assertIn(self.sy.c_of_g("M", g_hi), win)

    def test_upstream_downstream_minus_strand_distances(self):
        up = self.M.locate(4150)
        self.assertEqual((up["region"], up["distance"]), ("upstream", 50))
        dn = self.M.locate(2990)
        self.assertEqual((dn["region"], dn["distance"]), ("downstream", 11))

    def _del_at(self, which, anchor, nbases):
        """VCF 左錨定刪除：刪掉 anchor 之後的 nbases 個基因體鹼基。"""
        tx = self.P if which == "P" else self.M
        ref = "".join(self.sy.ref_base(anchor + i) for i in range(nbases + 1))
        return TF.analyse_variant(tx, self.fa, "S", anchor, ref, ref[0])

    def test_multibase_updown_uses_edge_nearest_transcript(self):
        """多鹼基變異的 distance 要用離轉錄本最近的那一端（VEP 的 DISTANCE 定義）。

        迴歸測試：11a 以 400 個公開 ClinVar 變異比對時，distance 有 20 筆不一致，全部是
        上游的多鹼基變異——當時取的是轉錄方向的第一個鹼基（上游時等於遠端），距離被高估
        一個 span 長度。下游在兩股上剛好就是近端，所以沒有被抓到。
        """
        f = self._del_at("P", 895, 5)       # + 股，span 896-900，轉錄本起點 1001
        self.assertEqual((f["region"], f["distance_to_transcript_nt"]), ("upstream", 101))
        f = self._del_at("P", 2450, 5)      # + 股，span 2451-2455，轉錄本終點 2400
        self.assertEqual((f["region"], f["distance_to_transcript_nt"]), ("downstream", 51))
        f = self._del_at("M", 4149, 5)      # - 股，span 4150-4154，轉錄本起點 4100
        self.assertEqual((f["region"], f["distance_to_transcript_nt"]), ("upstream", 50))
        f = self._del_at("M", 2984, 5)      # - 股，span 2985-2989，轉錄本終點 3001
        self.assertEqual((f["region"], f["distance_to_transcript_nt"]), ("downstream", 12))

    def test_snv_updown_distance_unchanged_by_nearest_edge_rule(self):
        """單鹼基變異 s == e，近端規則不能改變既有行為。"""
        for which, g, region, d in (("P", 900, "upstream", 101), ("P", 2450, "downstream", 50),
                                    ("M", 4150, "upstream", 50), ("M", 2990, "downstream", 11)):
            _, f = self.snv_at(which, g, "T" if self.sy.ref_base(g) != "T" else "A")
            self.assertEqual((f["region"], f["distance_to_transcript_nt"]), (region, d), f"{which} {g}")


class TestCrossCheck(Base):
    def _facts_run(self, rows, variants, expect_rc):
        d = self.tmp / f"run_{len(os.listdir(self.tmp))}"
        d.mkdir()
        h = d / "handoff.yaml"
        TF.C.write_yaml(h, {"schema": "handoff/2", "mode": "A", "gene": "GENEP", "variants": variants})
        write_vep(d / "v.tsv", rows)
        cmd = [sys.executable, str(P1 / "transcript_facts.py"), "facts", "--handoff", str(h), "--vep", str(d / "v.tsv"),
               "--gtf", str(self.gtf_path), "--ref", str(self.fa_path), "--out", str(d / "private.yaml"),
               "--public", str(d / "public.yaml"), "--protein-cache", str(d / "cache")]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, expect_rc, p.stdout + p.stderr)
        return TF.C.read_yaml(d / "private.yaml"), TF.C.read_yaml(d / "public.yaml"), d

    def test_consistent_vep_passes_and_public_has_no_coordinates(self):
        g1 = self.sy.codon_g("P", 20)[0]
        rows = [vep_row("V1", "P", Consequence="stop_gained", IMPACT="HIGH", EXON="2/4", HGVSc="ENSTSYNP.3:c.58C>T",
                        HGVSp="ENSPSYNP.3:p.Gln20Ter", Protein_position="20", Amino_acids="Q/*",
                        HGVSg=f"S:g.{g1}C>T"),
                vep_row("V2", "P", Consequence="upstream_gene_variant", IMPACT="MODIFIER", DISTANCE="101"),
                {"Uploaded_variation": "V2", "Feature_type": "RegulatoryFeature", "Feature": "ENSR000SYN",
                 "BIOTYPE": "promoter", "Consequence": "regulatory_region_variant"}]
        variants = [{"id": "V1", "key": f"S:{g1}:C:T", "identity_status": "CONFIRMED", "zygosity": "het"},
                    {"id": "V2", "key": f"S:900:{self.sy.ref_base(900)}:{'A' if self.sy.ref_base(900) != 'A' else 'C'}",
                     "identity_status": "CONFIRMED", "zygosity": "het"}]
        priv, pub, d = self._facts_run(rows, variants, 0)
        self.assertEqual(priv["variants"][0]["coding"]["nmd_class"], "NMD_predicted")
        self.assertEqual(priv["variants"][1]["region"], "upstream")
        self.assertEqual(priv["variants"][1]["regulatory_features"][0]["type"], "promoter")
        text = (d / "public.yaml").read_text(encoding="utf-8")
        self.assertNotIn(f"S:{g1}", text)
        self.assertNotIn("g.", text.replace("chg.", ""))
        self.assertNotIn("ENSR000SYN", text)
        self.assertEqual(pub["variants"][1]["regulatory_feature_types"], ["promoter"])
        self.assertTrue((d / "cache" / "ENSTSYNP.3.protein.fa").exists())

    def test_wrong_exon_number_fails_with_code_3(self):
        g1 = self.sy.codon_g("P", 20)[0]
        rows = [vep_row("V1", "P", Consequence="stop_gained", EXON="3/4", HGVSc="ENSTSYNP.3:c.58C>T",
                        HGVSp="ENSPSYNP.3:p.Gln20Ter", Protein_position="20")]
        variants = [{"id": "V1", "key": f"S:{g1}:C:T", "identity_status": "CONFIRMED"}]
        priv, _, _ = self._facts_run(rows, variants, 3)
        checks = {c["name"]: c["status"] for c in priv["variants"][0]["cross_check"]["checks"]}
        self.assertEqual(checks["exon_number"], "fail")
        self.assertEqual(checks["c_position"], "pass")

    def test_frameshift_vep_3prime_shift_and_ter_count(self):
        anchor = self.sy.codon_g("P", 59)[2]
        ref = self.sy.ref_base(anchor) + self.sy.ref_base(anchor + 1)
        p_ref, p_mut = self.sy.mutate_and_translate("P", anchor, ref, ref[0])
        first = next(i for i in range(min(len(p_ref), len(p_mut))) if p_ref[i] != p_mut[i]) + 1
        ter_n = len(p_mut) - first + 1
        a3 = {v: k for k, v in TF.THREE.items()}
        hp = f"ENSPSYNP.3:p.{TF.THREE[p_ref[first - 1]]}{first}{TF.THREE[p_mut[first - 1]]}fsTer{ter_n}"
        rows = [vep_row("V1", "P", Consequence="frameshift_variant", EXON="2/4", HGVSc="ENSTSYNP.3:c.183del",
                        HGVSp=hp, Protein_position=str(first))]
        variants = [{"id": "V1", "key": f"S:{anchor}:{ref}:{ref[0]}", "identity_status": "CONFIRMED"}]
        priv, _, _ = self._facts_run(rows, variants, 0)
        checks = {c["name"]: c for c in priv["variants"][0]["cross_check"]["checks"]}
        self.assertEqual(checks["c_position"]["status"], "pass")
        self.assertEqual(checks["frameshift_ter_n"]["status"], "pass")
        self.assertTrue(a3)
        # 故意把 Ter 數字寫錯 → 抓得到
        rows[0]["HGVSp"] = hp.replace(f"Ter{ter_n}", f"Ter{ter_n + 5}")
        priv, _, _ = self._facts_run(rows, variants, 3)
        checks = {c["name"]: c for c in priv["variants"][0]["cross_check"]["checks"]}
        self.assertEqual(checks["frameshift_ter_n"]["status"], "fail")

    def test_intronic_and_minus_strand_checks(self):
        g = 3503
        alt = "A" if self.sy.ref_base(g) != "A" else "C"
        rows = [vep_row("V1", "M", Consequence="splice_polypyrimidine_tract_variant&intron_variant", INTRON="2/3",
                        HGVSc=f"ENSTSYNM.5:c.211-3{TF.revcomp(self.sy.ref_base(g))}>{TF.revcomp(alt)}")]
        variants = [{"id": "V1", "key": f"S:{g}:{self.sy.ref_base(g)}:{alt}", "identity_status": "CONFIRMED"}]
        d = self.tmp / "minus"
        d.mkdir(exist_ok=True)
        h = d / "h.yaml"
        TF.C.write_yaml(h, {"mode": "A", "gene": "GENEM", "variants": variants})
        write_vep(d / "v.tsv", rows)
        p = subprocess.run([sys.executable, str(P1 / "transcript_facts.py"), "facts", "--handoff", str(h),
                            "--vep", str(d / "v.tsv"), "--gtf", str(self.gtf_path), "--ref", str(self.fa_path),
                            "--out", str(d / "o.yaml"), "--public", str(d / "p.yaml")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_public_yaml_and_screen_never_show_coordinates(self):
        g = self.sy.codon_g("P", 40)[0]
        wrong = "A" if self.sy.ref_base(g) != "A" else "C"
        rows = [vep_row("V1", "P", Consequence="missense_variant", EXON="2/4", HGVSc="ENSTSYNP.3:c.118A>G")]
        variants = [{"id": "V1", "key": f"S:{g}:{wrong}:G", "identity_status": "CONFIRMED"}]
        d = self.tmp / "leak"
        d.mkdir(exist_ok=True)
        TF.C.write_yaml(d / "h.yaml", {"mode": "A", "gene": "GENEP", "variants": variants})
        write_vep(d / "v.tsv", rows)
        p = subprocess.run([sys.executable, str(P1 / "transcript_facts.py"), "facts", "--handoff", str(d / "h.yaml"),
                            "--vep", str(d / "v.tsv"), "--gtf", str(self.gtf_path), "--ref", str(self.fa_path),
                            "--out", str(d / "o.yaml"), "--public", str(d / "p.yaml")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 3)
        pub = (d / "p.yaml").read_text(encoding="utf-8")
        self.assertIn("manual_review", pub)
        self.assertNotIn(str(g), pub)
        self.assertNotIn(str(g), p.stdout + p.stderr)

    def test_missing_vep_row_fails(self):
        g1 = self.sy.codon_g("P", 20)[0]
        variants = [{"id": "V1", "key": f"S:{g1}:C:T", "identity_status": "CONFIRMED"}]
        priv, _, _ = self._facts_run([], variants, 3)
        self.assertEqual(priv["variants"][0]["cross_check"]["checks"][0]["name"], "vep_row")


class TestHelpers(Base):
    def test_hgvs_parsers(self):
        self.assertEqual(TF.hgvsc_first("ENST1.2:c.123+5G>A"), "123+5")
        self.assertEqual(TF.hgvsc_first("ENST1.2:c.-14C>T"), "-14")
        self.assertEqual(TF.hgvsc_first("ENST1.2:c.*37del"), "*37")
        self.assertEqual(TF.hgvsc_first("ENST1.2:c.1833_1835del"), "1833")
        self.assertEqual(TF.hgvsc_first("ENST1.2:c.-15+1G>A"), "-15+1")
        self.assertIsNone(TF.hgvsc_first("-"))
        d = TF.parse_hgvsp("ENSP1.1:p.Lys612AsnfsTer4")
        self.assertEqual((d["pos"], d["fs_ter_n"]), (612, 4))
        self.assertTrue(TF.parse_hgvsp("ENSP1.1:p.Arg41Ter")["stop"])
        self.assertEqual(TF.parse_hgvsp("ENSP1.1:p.Arg41Trp")["alt"], "Trp")
        self.assertTrue(TF.parse_hgvsp("ENSP1.1:p.Leu12%3D")["syn"])
        self.assertIsNone(TF.parse_hgvsp("ENSP1.1:p.Lys612fsTer?")["fs_ter_n"])

    def test_mini_vcf(self):
        d = self.tmp / "mini"
        d.mkdir(exist_ok=True)
        TF.C.write_yaml(d / "h.yaml", {"variants": [{"id": "V1", "key": "15:100:C:T"}, {"id": "V2", "key": "15:200:AT:A"}]})
        subprocess.run([sys.executable, str(P1 / "transcript_facts.py"), "mini-vcf", "--handoff", str(d / "h.yaml"),
                        "--out", str(d / "m.vcf")], check=True, capture_output=True)
        lines = (d / "m.vcf").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[2], "15\t100\tV1\tC\tT\t.\t.\t.")
        self.assertEqual(lines[3], "15\t200\tV2\tAT\tA\t.\t.\t.")


class TestSelftest(Base):
    def test_selftest_mode_reports_concordance(self):
        d = self.tmp / "self"
        d.mkdir(exist_ok=True)
        vcf = ["##fileformat=VCFv4.2", "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"]
        rows = []
        k = 0
        # 每股 30 個外顯子 SNV（CDS 內），VEP 欄位用獨立參考實作產生
        for which, tx in (("P", self.P), ("M", self.M)):
            cds_pos = [g for g in self.sy.tpos(which) if tx.locate(g)["region"] == "cds"]
            for g in cds_pos[5:65:2]:
                k += 1
                ref = self.sy.ref_base(g)
                alt = "A" if ref != "A" else "G"
                vid = f"CV{k}"
                vcf.append(f"S\t{g}\t{vid}\t{ref}\t{alt}\t.\t.\t.")
                f = TF.analyse_variant(tx, self.fa, "S", g, ref, alt)
                c = self.sy.c_of_g(which, g)
                cons = {"missense": "missense_variant", "synonymous": "synonymous_variant",
                        "stop_gained": "stop_gained", "start_lost": "start_lost"}.get(f["class_b"], "coding_sequence_variant")
                rows.append(vep_row(vid, which, Consequence=cons, EXON=tx.locate(g)["exon"],
                                    HGVSc=f"{tx.id_version}:c.{c}{ref}>{alt}"))
        (d / "s.vcf").write_text("\n".join(vcf) + "\n", encoding="utf-8")
        write_vep(d / "s.tsv", rows)
        p = subprocess.run([sys.executable, str(P1 / "transcript_facts.py"), "selftest", "--vcf", str(d / "s.vcf"),
                            "--vep", str(d / "s.tsv"), "--gtf", str(self.gtf_path), "--ref", str(self.fa_path),
                            "--report", str(d / "r.tsv")], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("100.0%", p.stdout)
        with open(d / "r.tsv", encoding="utf-8") as fh:
            self.assertEqual(len(list(csv.DictReader(fh, delimiter="\t"))), 60)


if __name__ == "__main__":
    unittest.main()
