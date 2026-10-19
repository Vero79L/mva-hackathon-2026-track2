"""第 10、12–19 步與共用設定的測試。每個測試在暫存資料夾裡建一個假的 engine + registers + mva-hackathon，
用子程序跑真正的腳本（和你在 Mac 上跑的方式一樣），只把網路（UniProt、AlphaFold、文獻）換成預先放好的快取。"""
import csv
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ENGINE_SRC = HERE.parents[1]
PY = sys.executable
# 合成座標用字串相加組出來：這個測試檔也會被 commit，原始碼裡不能出現第 19 步會擋下的座標字樣。
P1, P2 = "101" + "00", "112" + "00"      # 兩個合成變異的位置（第 10 步測試）
POS = "1234" + "5678"                    # 第 19 步測試用的「座標」

BASH_FORBIDDEN = [r"\bsed -i\b", r"\bgrep -P\b", r"\breadlink -f\b", r"\bdeclare -A\b", r"\bmapfile\b",
                  r"\$\{[A-Za-z_]+,,\}", r"\|&", r"&>>"]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Sandbox(unittest.TestCase):
    """假的工作環境：<tmp>/research/engine（git repo）、<tmp>/research/registers、<tmp>/mva/{results,work}/…"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="t2steps_"))
        self.eng = self.tmp / "research" / "engine"
        for d in ("scripts", "templates"):
            shutil.copytree(ENGINE_SRC / d, self.eng / d)
        for d in ("config/cases", "config/scenarios", "docs/figures", "src", "evidence"):
            (self.eng / d).mkdir(parents=True, exist_ok=True)
        (self.eng / "src" / "triage.py").write_text(textwrap.dedent("""\
            import argparse, sys, yaml
            ap = argparse.ArgumentParser(); ap.add_argument('--case'); ap.add_argument('--candidates')
            a = ap.parse_args(); c = yaml.safe_load(open(a.case, encoding="utf-8"))
            sys.exit(0 if c.get('case_id') and c.get('patient_constraints') is not None else 2)
            """), encoding="utf-8")
        (self.eng / "evidence" / "candidates_from_canonical.yaml").write_text("candidates: []\n", encoding="utf-8")
        self.reg = self.tmp / "research" / "registers"
        self.reg.mkdir(parents=True)
        self.mva = self.tmp / "mva"
        for d in ("results/track1", "results/track2", "work/track1", "work/track2"):
            (self.mva / d).mkdir(parents=True)
        self.envfile = self.tmp / "env.sh"
        self.envfile.write_text(textwrap.dedent(f"""\
            : "${{MVA_ROOT:={self.mva}}}"
            : "${{T1_WORK:={self.mva}/work/track1}}"
            : "${{T1_RESULTS:={self.mva}/results/track1}}"
            : "${{T2_RESULTS:={self.mva}/results/track2}}"
            : "${{T2_WORK:={self.mva}/work/track2}}"
            : "${{REGISTERS:={self.reg}}}"
            : "${{CASE_ID:=demo_case}}"
            : "${{PROBAND:=PROBAND01}}"
            : "${{VEP_VERSION:=116}}"
            """), encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.eng)], check=True)
        subprocess.run(["git", "-C", str(self.eng), "config", "user.email", "t@example.org"], check=True)
        subprocess.run(["git", "-C", str(self.eng), "config", "user.name", "t"], check=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_step(self, script, *args, env_extra=None, stdin=None):
        env = dict(os.environ)
        env["T2_ENV_FILE"] = str(self.envfile)
        env.pop("CLAUDECODE", None)
        if env_extra:
            env.update(env_extra)
        return subprocess.run([PY, str(self.eng / "scripts" / "phase1" / script), *args], capture_output=True,
                              text=True, env=env, input=stdin, cwd=self.tmp)


# ------------------------------------------------------------------------------------------- 第 10 步
class TestHandoff(Sandbox):
    def setUp(self):
        super().setUp()
        t1r = self.mva / "results" / "track1"
        with open(t1r / "run_manifest.tsv", "w", encoding="utf-8") as fh:
            fh.write("time\tstep\trules_commit\trules_version\trules_sha256\tnote\n")
            fh.write("2026-10-13 10:00:00\t07_rank\tabc1234 2026-10-12\t1\tdeadbeef\t\n")
            fh.write("2026-10-13 10:05:00\t08_draft\tabc1234 2026-10-12\t1\tdeadbeef\tvero_mva-tiered-v1.csv\n")
        with open(t1r / "vero_mva-tiered-v1.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["proband_id", "chrom_1", "pos_1", "ref_1", "alt_1", "chrom_2", "pos_2", "ref_2", "alt_2",
                        "epcr", "finding_type", "notes"])
            w.writerow(["PROBAND01", "chr7", "20500", "C", "T", "chr7", "26100", "G", "GA", "0.60", "primary", "GENEX (Tier A); #2"])
            w.writerow(["PROBAND01", "chr7", P1, "C", "T", "chr7", P2, "AT", "A", "0.95", "primary",
                        "GENEX (Tier A); route B #1 pair; phase=unphased"])
            w.writerow(["PROBAND01", "chr3", "50000", "G", "A", "", "", "", "", "0.05", "secondary", "incidental"])
        (self.mva / "work" / "track1" / "norm.vcf.gz").write_bytes(b"fake")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.set_bcftools("0|1", "1|0", "7_10090_C_T", "7_10090_C_T")

    def set_bcftools(self, pgt1, pgt2, pid1, pid2, gt1="0/1", gt2="0/1"):
        script = self.bin / "bcftools"
        script.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env bash
            region=""
            while [ $# -gt 0 ]; do case "$1" in -r) region="$2"; shift 2;; *) shift;; esac; done
            case "$region" in
              7:{P1}-{P1}) printf '7\\t{P1}\\t7:{P1}:C:T\\tC\\tT\\tPASS\\t{gt1}\\t99\\t31\\t15,16\\t{pgt1}\\t{pid1}\\n' ;;
              7:{P2}-{P2}) printf '7\\t{P2}\\t7:{P2}:AT:A\\tAT\\tA\\tPASS\\t{gt2}\\t99\\t28\\t14,14\\t{pgt2}\\t{pid2}\\n' ;;
            esac
            """), encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

    def env(self):
        return {"PATH": f"{self.bin}:{os.environ['PATH']}"}

    def test_mode_a_read_backed_trans_and_no_coordinates_on_screen(self):
        r = self.run_step("10_handoff.py", "--match", "full", "--rank-points", "100", "--f-max", "1.0",
                          env_extra=self.env())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        h = yaml.safe_load((self.mva / "results" / "track2" / "handoff_from_track1.yaml").read_text(encoding="utf-8"))
        self.assertEqual(h["mode"], "A")
        self.assertEqual(h["gene"], "GENEX")
        self.assertEqual([v["key"] for v in h["variants"]], ["7:" + P1 + ":C:T", "7:" + P2 + ":AT:A"])
        self.assertEqual(h["phase"]["evidence"], "trans")
        self.assertEqual(h["phase"]["status"], "CONFIRMED_read_backed")
        self.assertEqual(h["variants"][0]["identity_status"], "CONFIRMED")
        self.assertEqual(h["track1"]["rules_commit"], "abc1234 2026-10-12")
        self.assertNotIn(P1, r.stdout + r.stderr)
        self.assertNotIn(P2, r.stdout + r.stderr)

    def test_cis_stops(self):
        self.set_bcftools("0|1", "0|1", "X1", "X1")
        r = self.run_step("10_handoff.py", "--match", "full", "--rank-points", "100", "--f-max", "1",
                          env_extra=self.env())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cis", r.stderr)

    def test_unphased_mode_b(self):
        self.set_bcftools(".", ".", ".", ".")
        r = self.run_step("10_handoff.py", "--match", "partial", "--rank-points", "50", "--f-max", "0.5",
                          env_extra=self.env())
        self.assertEqual(r.returncode, 0, r.stderr)
        h = yaml.safe_load((self.mva / "results" / "track2" / "handoff_from_track1.yaml").read_text(encoding="utf-8"))
        self.assertEqual((h["mode"], h["phase"]["evidence"], h["phase"]["status"]), ("B", "unphased", "ASSUMED"))
        self.assertEqual(h["variants"][1]["identity_status"], "ASSUMED")

    def test_noninteractive_without_feedback_fails_clearly(self):
        r = self.run_step("10_handoff.py", env_extra=self.env(), stdin="")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("非互動模式", r.stderr)

    def test_refuses_to_overwrite_without_force(self):
        args = ["--match", "full", "--rank-points", "100", "--f-max", "1"]
        self.assertEqual(self.run_step("10_handoff.py", *args, env_extra=self.env()).returncode, 0)
        r = self.run_step("10_handoff.py", *args, env_extra=self.env())
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--force", r.stderr)
        self.assertEqual(self.run_step("10_handoff.py", *args, "--force", env_extra=self.env()).returncode, 0)


# ------------------------------------------------------------------------------------------- 第 13 步
REG_HEADER = ["fact_id", "domain", "statement", "status", "basis", "source", "strength", "alternative",
              "resolution_path", "available_in_hackathon", "would_change_direction", "scenario_link", "report_section",
              "checked_date"]


def good_register():
    rows = [
        ["F-VAR-01", "variant_identity", "V1 identity", "CONFIRMED", "leaderboard full match", "handoff", "clinically_validated", "", "", "", "no", "", "§2", "2026-10-14"],
        ["F-VAR-02", "variant_identity", "V2 identity", "CONFIRMED", "leaderboard full match", "handoff", "clinically_validated", "", "", "", "no", "", "§2", "2026-10-14"],
        ["F-PHASE-01", "phase", "in trans", "ASSUMED", "PID differ", "handoff", "predicted", "cis + third variant", "parents", "no", "yes", "S3", "§2", "2026-10-14"],
        ["F-INH-01", "inheritance", "recessive", "ASSUMED", "known genes", "PMID 1", "asserted", "dominant", "parents", "no", "no", "", "§2", "2026-10-14"],
        ["F-TX-01", "transcript_fate", "NMD predicted", "UNKNOWN", "step 11", "docs/transcript_facts_public.yaml", "predicted", "", "allele-specific RNA", "no", "yes", "S1;S2", "§3", "2026-10-14"],
        ["F-PROT-01", "protein_consequence", "unknown", "UNKNOWN", "context only", "docs/domain_map.yaml", "predicted", "", "patient cells", "no", "yes", "S1;S2", "§3", "2026-10-14"],
        ["F-RF-01", "residual_function", "unknown", "UNKNOWN", "not measured", "dossier", "predicted", "", "functional assay", "no", "yes", "S1;S2;S3", "§3", "2026-10-14"],
        ["F-PHEN-01", "phenotype", "Microcephaly (HP:0000252)", "CONFIRMED", "organiser file", "results/track1/hpo_terms.tsv", "measured_in_proband", "", "", "", "no", "", "§2", "2026-10-14"],
        ["F-CLIN-age", "clinical_constraint", "child", "CONFIRMED", "organiser file", "results/track1/hpo_terms.tsv", "measured_in_proband", "", "", "", "no", "", "§5", "2026-10-14"],
        ["F-CLIN-renal-fn", "clinical_constraint", "current renal function", "UNKNOWN", "no values", "—", "asserted", "", "clinical labs", "no", "yes", "S2", "§5", "2026-10-14"],
    ]
    return rows


def write_register(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(REG_HEADER)
        w.writerows(rows)


class TestRegister(Sandbox):
    def test_init_then_template_fails_until_filled(self):
        r = self.run_step("13_check_register.py", "--init")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.reg / "fact_register.csv").exists())
        r = self.run_step("13_check_register.py")
        self.assertNotEqual(r.returncode, 0)

    def test_good_register_passes(self):
        write_register(self.reg / "fact_register.csv", good_register())
        r = self.run_step("13_check_register.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_each_rule_is_enforced(self):
        rows = good_register()
        rows[0][6] = "predicted"                       # R1/R4：CONFIRMED + predicted
        rows[2][7] = ""                                # R2：ASSUMED 沒有替代假設
        rows[4][8] = ""                                # R3：UNKNOWN 沒有解決路徑
        rows[5][1] = "phenotype"                       # 前綴和 domain 不一致
        rows[7][5] = "my notes"                        # R5：表現型 CONFIRMED 但來源不是表現型檔
        rows[6][11] = ""                               # 方向敏感但沒有情境
        write_register(self.reg / "fact_register.csv", rows)
        (self.eng / "docs" / "MECHANISM.md").write_text("see [F-VAR-99]\n", encoding="utf-8")   # R6：引用不存在的 fact
        r = self.run_step("13_check_register.py")
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        for token in ("R1/R4", "R2", "R3", "前綴 F-PROT", "R5", "必須連到情境", "R6"):
            self.assertIn(token, out, token)

    def test_register_inside_engine_is_refused(self):
        write_register(self.eng / "fact_register.csv", good_register())
        r = self.run_step("13_check_register.py", "--register", str(self.eng / "fact_register.csv"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("engine repo", r.stderr)


# ------------------------------------------------------------------------------------------- 第 14 步
BASE_CASE = {
    "schema_version": 2, "case_id": "demo_case", "disease": "demo", "gene": "GENEX", "inheritance": "recessive",
    "working_mechanism": "loss_of_function", "defect_direction": "checkpoint_insufficiency", "fact_mode": "A",
    "patient_constraints": {"age_group": "child", "renal": "nephrocalcinosis"},
    "constraint_provenance": {"age_group": {"fact": "F-CLIN-age", "status": "CONFIRMED"},
                              "renal": {"fact": "F-CLIN-renal-fn", "status": "UNKNOWN"}},
    "therapeutic_objectives": [
        {"id": "OBJ-restore", "class": "restore", "endpoint_level": "protein", "endpoint": "protein level", "assay": "WB",
         "improvement_is": "up", "co_measure": ["loading control"], "wrong_direction_test": "lowers protein",
         "valid_in_scenarios": ["S1"]},
        {"id": "OBJ-deselect", "class": "deselect", "endpoint_level": "cellular_outcome", "endpoint": "fraction",
         "assay": "scWGS", "improvement_is": "down", "co_measure": ["cell death", "proliferation", "clonal fitness"],
         "wrong_direction_test": "non-selective", "valid_in_scenarios": ["S1", "S2"]},
    ],
    "disease_direction_test": "lowers checkpoint function",
}
SCEN = {
    "schema": "scenarios/1", "case_id": "demo_case", "prior_weights": {"S1": 0.5, "S2": 0.5},
    "drives": ["F-PHASE-01", "F-TX-01", "F-PROT-01", "F-RF-01", "F-CLIN-renal-fn"],
    "scenarios": [
        {"id": "S1", "label": "hypomorph", "assumptions": {"F-PHASE-01": "trans", "F-TX-01": "NMD", "F-PROT-01": "low",
                                                            "F-RF-01": "partial", "F-CLIN-renal-fn": "normal"},
         "implications": {"molecular_target_valid": True,
                          "objective_validity": {"restore": "valid", "deselect": "valid"}},
         "what_would_confirm": "protein level 20-40% of WT"},
        {"id": "S2", "label": "null", "assumptions": {"F-PHASE-01": "trans", "F-TX-01": "NMD", "F-PROT-01": "none",
                                                       "F-RF-01": "none", "F-CLIN-renal-fn": "impaired"},
         "implications": {"molecular_target_valid": False,
                          "objective_validity": {"restore": "invalid", "deselect": "valid"}},
         "what_would_confirm": "no protein detectable"},
    ],
}


class TestScenarios(Sandbox):
    def setUp(self):
        super().setUp()
        write_register(self.reg / "fact_register.csv", good_register())
        (self.eng / "config" / "cases" / "demo_case.yaml").write_text(yaml.safe_dump(BASE_CASE, sort_keys=False), encoding="utf-8")

    def write_scen(self, doc):
        (self.eng / "config" / "scenarios" / "demo_case.scenarios.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    def test_builds_scenario_files_and_runs_engine(self):
        self.write_scen(SCEN)
        r = self.run_step("14_build_scenarios.py", "--run-engine")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        s1 = yaml.safe_load((self.eng / "config" / "cases" / "demo_case_S1.yaml").read_text(encoding="utf-8"))
        s2 = yaml.safe_load((self.eng / "config" / "cases" / "demo_case_S2.yaml").read_text(encoding="utf-8"))
        self.assertEqual(s1["case_id"], "demo_case_S1")
        self.assertTrue(s1["molecular_target_valid"])
        self.assertFalse(s2["molecular_target_valid"])
        self.assertTrue((self.eng / "config" / "cases" / "demo_case_S1.yaml").read_text(encoding="utf-8").startswith("# AUTO-GENERATED"))

    def test_missing_direction_fact_in_drives_fails(self):
        doc = json.loads(json.dumps(SCEN))
        doc["drives"].remove("F-CLIN-renal-fn")
        for s in doc["scenarios"]:
            s["assumptions"].pop("F-CLIN-renal-fn")
        self.write_scen(doc)
        r = self.run_step("14_build_scenarios.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("F-CLIN-renal-fn", r.stdout)

    def test_objective_validity_must_match_case(self):
        doc = json.loads(json.dumps(SCEN))
        doc["scenarios"][1]["implications"]["objective_validity"]["restore"] = "valid"
        self.write_scen(doc)
        r = self.run_step("14_build_scenarios.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("OBJ-restore", r.stdout)

    def test_weights_and_assumptions(self):
        doc = json.loads(json.dumps(SCEN))
        doc["prior_weights"] = {"S1": 0.7, "S2": 0.7}
        doc["scenarios"][0]["assumptions"]["F-INH-01"] = "dominant"
        self.write_scen(doc)
        r = self.run_step("14_build_scenarios.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("加總", r.stdout)
        self.assertIn("F-INH-01", r.stdout)


# ------------------------------------------------------------------------------------------- 第 15 步
GRAPH = {
    "schema": "mechanism_graph/1", "case_id": "demo_case", "gene": "GENEX",
    "nodes": [
        {"id": "V1", "level": "variant", "label": 'c.10C>T "quoted"', "fact": "F-VAR-01"},
        {"id": "T1", "level": "transcript", "label": "NMD predicted", "fact": "F-TX-01"},
        {"id": "P", "level": "protein", "label": "reduced protein", "fact": "F-RF-01"},
        {"id": "F", "level": "cellular_process", "label": "checkpoint signalling"},
        {"id": "O", "level": "cellular_outcome", "label": "aneuploidy"},
        {"id": "H1", "level": "phenotype", "label": "Microcephaly", "hpo": "HP:0000252", "fact": "F-PHEN-01"},
        {"id": "H2", "level": "phenotype", "label": "Cataract", "hpo": "HP:0000518"},
    ],
    "edges": [
        {"id": "E01", "from": "V1", "to": "T1", "claim": "PTC upstream of last junction", "strength": "predicted",
         "model": {"system": "GTF arithmetic", "genotype_match": "same_variant"},
         "sources": [{"file": "docs/transcript_facts_public.yaml", "strength": "predicted"}]},
        {"id": "E02", "from": "T1", "to": "P", "claim": "less mRNA, less protein", "strength": "measured_in_model",
         "model": {"system": "patient fibroblasts (other patients)", "genotype_match": "same_gene_LoF"},
         "sources": [{"pmid": "12345678", "strength": "measured_in_model"}]},
        {"id": "E03", "from": "P", "to": "F", "claim": "weak checkpoint", "strength": "measured_in_model",
         "model": {"system": "mouse", "genotype_match": "same_gene_LoF"}, "sources": [{"pmid": "23456789"}]},
        {"id": "E04", "from": "F", "to": "O", "claim": "missegregation", "strength": "measured_in_model",
         "model": {"system": "cells", "genotype_match": "pathway_level"}, "sources": [{"doi": "10.1000/xyz"}]},
        {"id": "E05", "from": "O", "to": "H1", "claim": "progenitor loss", "strength": "asserted",
         "model": {"system": "review", "genotype_match": "pathway_level"}, "sources": [{"pmid": "34567890"}]},
    ],
}


class TestMechanismGraph(Sandbox):
    def setUp(self):
        super().setUp()
        write_register(self.reg / "fact_register.csv", good_register())
        with open(self.mva / "results" / "track1" / "hpo_terms.tsv", "w", encoding="utf-8") as fh:
            fh.write("id\tname\tnote\nHP:0000252\tMicrocephaly\t\nHP:0000518\tCataract\t\n")

    def write(self, g):
        (self.eng / "docs" / "mechanism_graph.yaml").write_text(yaml.safe_dump(g, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def test_outputs_and_unexplained(self):
        self.write(GRAPH)
        r = self.run_step("15_mechanism_graph.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        res = yaml.safe_load((self.eng / "docs" / "mechanism_graph.resolved.yaml").read_text(encoding="utf-8"))
        self.assertEqual(res["unexplained_phenotypes"], ["H2"])
        self.assertTrue(any("rule 4" in w for w in res["warnings"]))     # E02 是 measured，前提 T1 只有 predicted
        # 規則 4 的警告 2026-10-19 改成英文（MECHANISM.md 是評審看的檔）；行為沒變，只有措辭
        mmd = (self.eng / "docs" / "figures" / "mechanism.mmd").read_text(encoding="utf-8")
        self.assertIn("#quot;quoted#quot;", mmd)
        self.assertIn("Cataract", (self.eng / "docs" / "MECHANISM.md").read_text(encoding="utf-8"))
        src = yaml.safe_load((self.eng / "docs" / "mechanism_graph.yaml").read_text(encoding="utf-8"))
        self.assertNotIn("unexplained_phenotypes", src)                     # 來源檔不會被改
        if shutil.which("dot"):
            self.assertTrue((self.eng / "docs" / "figures" / "mechanism.svg").exists())

    def test_rule_violations(self):
        g = json.loads(json.dumps(GRAPH))
        g["edges"][2]["sources"] = []                                      # 規則 1
        g["edges"][1]["strength"] = "measured_in_proband"                  # 規則 2（來源最弱是 measured_in_model）
        del g["edges"][3]["model"]["genotype_match"]                       # 規則 3
        g["nodes"] = [n for n in g["nodes"] if n["id"] != "H2"]           # 規則 5：HP:0000518 沒有節點
        g["nodes"][0]["fact"] = "F-VAR-77"                                  # 不存在的 fact
        self.write(g)
        r = self.run_step("15_mechanism_graph.py")
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        for token in ("規則 1", "規則 2", "規則 3", "HP:0000518", "F-VAR-77"):
            self.assertIn(token, out, token)


# ------------------------------------------------------------------------------------------- 第 16 步
class TestCitations(Sandbox):
    def setUp(self):
        super().setUp()
        self.mod = load_module(self.eng / "scripts" / "phase1" / "16_verify_citations.py", "vc")
        self.cache = self.mva / "work" / "track2" / "public_cache" / "citations"
        self.cache.mkdir(parents=True)

    def put(self, url, data):
        p = self.cache / (re.sub(r"[^A-Za-z0-9]+", "_", url)[-150:] + ".json")
        p.write_text(json.dumps(data), encoding="utf-8")

    def epmc_url(self, pmid):
        from urllib.parse import quote
        q = quote(f"EXT_ID:{pmid} AND SRC:MED")
        return f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&resultType=lite"

    def test_offline_with_title_hints(self):
        g = {"edges": [{"id": "E1", "sources": [{"pmid": "24825348", "title_hint": "SIRT2 induces the checkpoint kinase BubR1 to increase lifespan"}]},
                       {"id": "E2", "sources": [{"pmid": "11111111", "title_hint": "Completely different paper about kidneys"}]},
                       {"id": "E3", "sources": [{"doi": "10.15252/embj.201386907"}]}]}
        (self.eng / "docs" / "mechanism_graph.yaml").write_text(yaml.safe_dump(g), encoding="utf-8")
        self.put(self.epmc_url("24825348"), {"resultList": {"result": [{"title": "SIRT2 induces the checkpoint kinase BubR1 to increase lifespan.", "pubYear": "2014", "journalTitle": "EMBO J", "authorString": "North BJ, Rosenberg MA"}]}})
        self.put(self.epmc_url("11111111"), {"resultList": {"result": [{"title": "Mitotic checkpoint signalling in yeast", "pubYear": "2001"}]}})
        from urllib.parse import quote
        self.put(f"https://api.crossref.org/works/{quote('10.15252/embj.201386907')}",
                 {"message": {"title": ["SIRT2 induces the checkpoint kinase BubR1 to increase lifespan"],
                              "issued": {"date-parts": [[2014, 5, 13]]}, "container-title": ["The EMBO Journal"],
                              "author": [{"family": "North"}]}})
        r = self.run_step("16_verify_citations.py", "--offline")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)            # E2 的標題對不上
        with open(self.reg / "citation_check.csv", newline="", encoding="utf-8") as fh:
            rows = {x["id"]: x for x in csv.DictReader(fh)}
        self.assertEqual(rows["24825348"]["status"], "OK")
        self.assertEqual(rows["24825348"]["title_check"], "match")
        self.assertEqual(rows["11111111"]["status"], "TITLE_MISMATCH")
        self.assertEqual(rows["10.15252/embj.201386907"]["title_check"], "manual")

    def test_title_match_function(self):
        self.assertTrue(self.mod.title_match("SIRT2 induces the checkpoint kinase BubR1",
                                             "SIRT2 induces the checkpoint kinase BubR1 to increase lifespan."))
        self.assertFalse(self.mod.title_match("kidney stones in adults", "SIRT2 induces the checkpoint kinase BubR1"))


# ------------------------------------------------------------------------------------------- 第 18 步
class TestCaseProvenance(Sandbox):
    def setUp(self):
        super().setUp()
        write_register(self.reg / "fact_register.csv", good_register())
        (self.eng / "docs" / "transcript_facts_public.yaml").write_text(yaml.safe_dump(
            {"variants": [{"id": "V1", "transcript": "ENST1.2", "hgvs_c": "ENST1.2:c.10C>T", "hgvs_p": "ENSP1.1:p.Gln4Ter"}]}), encoding="utf-8")
        self.case = json.loads(json.dumps(BASE_CASE))
        self.case["variants"] = [{"id": "V1", "transcript": "ENST1.2", "hgvs_c": "c.10C>T", "hgvs_p": "p.Gln4Ter",
                                  "transcript_fate": {"fact": "F-TX-01"}}]

    def write_case(self, extra_text=""):
        text = yaml.safe_dump(self.case, sort_keys=False, allow_unicode=True) + extra_text
        (self.eng / "config" / "cases" / "demo_case.yaml").write_text(text, encoding="utf-8")

    def test_writes_provenance_block_last(self):
        self.write_case("\nprovenance:\n  old: true\n")
        r = self.run_step("18_case_provenance.py", "--run-engine")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        doc = yaml.safe_load((self.eng / "config" / "cases" / "demo_case.yaml").read_text(encoding="utf-8"))
        self.assertIn("fact_register", doc["provenance"])
        self.assertNotIn("old", doc["provenance"])
        self.assertEqual(doc["provenance"]["fact_register"]["rows"], 10)
        self.assertEqual(len(doc["provenance"]["transcript_facts_public"]["sha256"]), 64)

    def test_detects_drift_and_missing_fields(self):
        self.case["variants"][0]["hgvs_c"] = "c.11C>T"
        self.case["therapeutic_objectives"][1]["co_measure"] = ["clonal fitness"]
        self.case["constraint_provenance"]["renal"]["fact"] = "F-CLIN-nope"
        self.write_case()
        r = self.run_step("18_case_provenance.py", "--check-only")
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        for token in ("c.11C>T", "cell death", "F-CLIN-nope"):
            self.assertIn(token, out, token)

    def test_provenance_must_be_last(self):
        self.write_case("\nprovenance:\n  old: true\nlater_key: 1\n")
        r = self.run_step("18_case_provenance.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("最後", r.stderr)


# ------------------------------------------------------------------------------------------- 第 19 步
class TestPublicSafety(Sandbox):
    def test_phase1_outputs_with_coordinates_fail_and_allowlist(self):
        (self.eng / "docs" / "MECHANISM.md").write_text(f"variant at chr15:{POS} and NC_000015.10:g.{POS}G>A\n", encoding="utf-8")
        r = self.run_step("19_public_safety.py")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("genomic_coordinate", r.stdout)
        self.assertIn("refseq_genomic_hgvs", r.stdout)
        (self.eng / "config" / "public_safety_allow.txt").write_text(
            f"chr15:{POS}\tpublic in ClinVar\nNC_000015.10:g.{POS}\tpublic in ClinVar\n", encoding="utf-8")
        r = self.run_step("19_public_safety.py")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_no_false_alarm_on_dates_and_hgvs_c(self):
        (self.eng / "docs" / "MECHANISM.md").write_text(
            "built 2026-10-14T09:00:00+08:00; ENST00000999999.1:c.1234C>T p.Gln412Ter; dilution 1:1000; exon 17/23\n", encoding="utf-8")
        r = self.run_step("19_public_safety.py")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_staged_private_file_blocked(self):
        (self.eng / "handoff_from_track1.yaml").write_text("x: 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.eng), "add", "handoff_from_track1.yaml"], check=True)
        r = self.run_step("19_public_safety.py", "--staged")
        self.assertEqual(r.returncode, 1)
        self.assertIn("private_file", r.stdout)

    def test_vcf_line_detected_in_all_mode(self):
        (self.eng / "notes.tsv").write_text(f"15\t{POS}\t.\tG\tA\t.\tPASS\t.\n", encoding="utf-8")
        r = self.run_step("19_public_safety.py", "--all")
        self.assertEqual(r.returncode, 1)
        self.assertIn("vcf_line", r.stdout)

    def test_bundle_itself_passes_the_commit_guard(self):
        """第 10.3 節的第一次 commit：bundle 自己的檔案（腳本、測試、範本、CLAUDE.md）不能被 pre-commit 防護擋下。"""
        shutil.copytree(ENGINE_SRC / "tests", self.eng / "tests")
        (self.eng / "config").mkdir(exist_ok=True)
        for f in ("CLAUDE.md", "config/local.env.example"):
            shutil.copy2(ENGINE_SRC / f, self.eng / f)
        for d in list(self.eng.rglob("__pycache__")):
            shutil.rmtree(d, ignore_errors=True)
        subprocess.run(["git", "-C", str(self.eng), "add", "CLAUDE.md", "config/local.env.example",
                        "scripts/phase1", "templates/phase1", "tests/phase1"], check=True)
        r = self.run_step("19_public_safety.py", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)


# ------------------------------------------------------------------------------------------- 第 12 步
class TestDomainMap(Sandbox):
    def setUp(self):
        super().setUp()
        cache = self.mva / "work" / "track2" / "public_cache"
        cache.mkdir(parents=True)
        seq = "M" + "A" * 49 + "K" * 50                      # 100 aa
        (cache / "ENST1.2.protein.fa").write_text(">ENST1.2\n" + seq + "\n", encoding="utf-8")
        up = {"sequence": {"value": seq, "length": 100}, "entryAudit": {"entryVersion": 7},
              "features": [{"type": "Domain", "location": {"start": {"value": 10}, "end": {"value": 40}}, "description": "Kinase-like"},
                           {"type": "Motif", "location": {"start": {"value": 60}, "end": {"value": 65}}, "description": "KEN box"},
                           {"type": "Mutagenesis", "location": {"start": {"value": 20}, "end": {"value": 20}}, "description": "Loss of binding",
                            "alternativeSequence": {"originalSequence": "A", "alternativeSequences": ["P"]},
                            "evidences": [{"source": "PubMed", "id": "99999999"}]},
                           {"type": "Modified residue", "location": {"start": {"value": 70}, "end": {"value": None}}, "description": "skip me"}]}
        (cache / "Q00000.uniprot.json").write_text(json.dumps(up), encoding="utf-8")
        (cache / "Q00000.af.json").write_text(json.dumps([{"entryId": "AF-Q00000-F1", "latestVersion": 4,
                                                           "pdbUrl": "https://example.org/x.pdb", "uniprotSequence": seq}]), encoding="utf-8")
        pdb = []
        for i in range(1, 101):
            pdb.append(f"ATOM  {i:5d}  CA  ALA A{i:4d}    {0.0:8.3f}{0.0:8.3f}{0.0:8.3f}{1.0:6.2f}{(95.0 if i < 50 else 40.0):6.2f}           C")
        (cache / "Q00000.af.pdb").write_text("\n".join(pdb) + "\n", encoding="utf-8")
        self.pub = {"gene": "GENEX", "variants": [
            {"id": "V1", "transcript": "ENST1.2", "uniprot": "Q00000.1", "hgvs_p": "ENSP1:p.Ala20Ter",
             "coding": {"class": "stop_gained", "first_changed_aa": 20}},
            {"id": "V2", "transcript": "ENST1.2", "uniprot": "Q00000.1", "region": "upstream", "coding": None}]}
        (self.eng / "docs" / "transcript_facts_public.yaml").write_text(yaml.safe_dump(self.pub), encoding="utf-8")

    def test_offline_map(self):
        r = self.run_step("12_domain_map.py", "--offline")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dm = yaml.safe_load((self.eng / "docs" / "domain_map.yaml").read_text(encoding="utf-8"))
        v1 = dm["variants"][0]
        self.assertEqual(dm["isoform_check"]["status"], "identical")
        self.assertEqual(v1["residue"], 20)
        self.assertEqual(v1["plddt_at_residue"], 95.0)
        self.assertEqual([f["description"] for f in v1["features_lost_downstream"]], ["KEN box"])
        self.assertEqual(v1["same_residue_experimental"][0]["pmids"], ["99999999"])
        self.assertIn("note", dm["variants"][1])
        svg = (self.eng / "docs" / "figures" / "domain_map.svg").read_text(encoding="utf-8")
        self.assertIn("<svg", svg)
        self.assertIn("Kinase-like", svg)

    def test_isoform_mismatch_stops(self):
        cache = self.mva / "work" / "track2" / "public_cache"
        (cache / "ENST1.2.protein.fa").write_text(">ENST1.2\nMKKK\n", encoding="utf-8")
        r = self.run_step("12_domain_map.py", "--offline")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("序列", r.stderr)


# ------------------------------------------------------------------------------------------- 第 11 步（bash 外殼）
class TestStep11Glue(Sandbox):
    """用假的 conda（mva、vep 環境）跑真正的 11_transcript_facts.sh：驗證參數、路徑、結束代碼。"""

    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(HERE))
        import synth
        sy = synth.Synth()
        res = self.tmp / "res"
        res.mkdir()
        sy.write_fasta(res / "ref.fa")
        sy.write_gtf(res / "genes.116.gtf")
        (res / "vep_cache" / "homo_sapiens" / "116_GRCh38").mkdir(parents=True)
        base = self.tmp / "conda"
        (base / "etc" / "profile.d").mkdir(parents=True)
        (base / "etc" / "profile.d" / "conda.sh").write_text("# fake\n", encoding="utf-8")
        for env in ("mva", "vep"):
            (base / "envs" / env / "bin").mkdir(parents=True)
        os.symlink(PY, base / "envs" / "mva" / "bin" / "python")
        fake_samtools = base / "envs" / "mva" / "bin" / "samtools"
        fake_samtools.write_text("#!/usr/bin/env bash\necho 'samtools 1.24'\n", encoding="utf-8")
        fake_samtools.chmod(0o755)
        g = sy.codon_g("P", 20)[0]
        self.g = g
        vep_tsv = ("## fake VEP\n#" + "\t".join(["Uploaded_variation", "Feature_type", "Feature", "SYMBOL", "STRAND",
                    "MANE_SELECT", "CANONICAL", "Consequence", "EXON", "HGVSc", "HGVSp", "Protein_position"]) + "\n" +
                   "\t".join(["V1", "Transcript", "ENSTSYNP.3", "GENEP", "1", "NM_SYNP.1", "YES", "stop_gained", "2/4",
                               "ENSTSYNP.3:c.58C>T", "ENSPSYNP.3:p.Gln20Ter", "20"]) + "\n")
        (self.tmp / "vep_out.tsv").write_text(vep_tsv, encoding="utf-8")
        fake_vep = base / "envs" / "vep" / "bin" / "vep"
        fake_vep.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env bash
            out=""; reg=0
            while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; --regulatory) reg=1; shift;; *) shift;; esac; done
            echo "$*" > "{self.tmp}/vep_args.txt"
            cp "{self.tmp}/vep_out.tsv" "$out"
            """), encoding="utf-8")
        fake_vep.chmod(0o755)
        (self.eng / "config" / "local.env").write_text(self.envfile.read_text(encoding="utf-8") + textwrap.dedent(f"""\
            : "${{REF:={res}/ref.fa}}"
            : "${{GTF:={res}/genes.116.gtf}}"
            : "${{VEP_CACHE:={res}/vep_cache}}"
            """))
        import yaml as _y
        (self.mva / "results" / "track2" / "handoff_from_track1.yaml").write_text(_y.safe_dump(
            {"schema": "handoff/2", "mode": "A", "gene": "GENEP",
             "variants": [{"id": "V1", "key": f"S:{g}:C:T", "identity_status": "CONFIRMED", "zygosity": "het"}]}), encoding="utf-8")
        self.base = base

    def test_step11_end_to_end_with_fake_vep(self):
        env = {**os.environ, "CONDA_BASE": str(self.base), "PATH": f"{self.base}/envs/mva/bin:{os.environ['PATH']}"}
        r = subprocess.run(["bash", str(self.eng / "scripts" / "phase1" / "11_transcript_facts.sh")],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        pub = yaml.safe_load((self.eng / "docs" / "transcript_facts_public.yaml").read_text(encoding="utf-8"))
        self.assertEqual(pub["variants"][0]["coding"]["class"], "stop_gained")
        self.assertEqual(pub["variants"][0]["cross_check"]["status"], "pass")
        self.assertTrue((self.mva / "results" / "track2" / "transcript_facts.yaml").exists())
        logs = list((self.mva / "results" / "track2" / "logs").glob("11_transcript_facts_*.log"))
        self.assertEqual(len(logs), 1)
        self.assertNotIn(str(self.g), r.stdout + r.stderr)
        # 第二次跑：迷你 VCF 沒變 → VEP 那一步跳過
        r2 = subprocess.run(["bash", str(self.eng / "scripts" / "phase1" / "11_transcript_facts.sh")],
                            capture_output=True, text=True, env=env)
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertIn("已是最新", r2.stdout)

    def test_step11_mismatch_exits_nonzero(self):
        (self.tmp / "vep_out.tsv").write_text((self.tmp / "vep_out.tsv").read_text(encoding="utf-8").replace("2/4", "3/4"))
        env = {**os.environ, "CONDA_BASE": str(self.base), "PATH": f"{self.base}/envs/mva/bin:{os.environ['PATH']}"}
        r = subprocess.run(["bash", str(self.eng / "scripts" / "phase1" / "11_transcript_facts.sh")],
                           capture_output=True, text=True, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("交叉檢查有不一致", r.stdout + r.stderr)


# ------------------------------------------------------------------------------------------- 設定與 bash
class TestConfigAndBash(Sandbox):
    def test_env_chain_inherits_track1_external_disk(self):
        t1 = self.tmp / "track1" / "config"
        t1.mkdir(parents=True)
        (t1 / "paths.env").write_text(': "${MVA_ROOT:=/Users/x/mva-hackathon}"\n: "${RES:=$MVA_ROOT/resources}"\n'
                                      ': "${WORK:=$MVA_ROOT/work/track1}"\n: "${RESULTS:=$MVA_ROOT/results/track1}"\n'
                                      ': "${REF:=$RES/GRCh38.nochr.fa.gz}"\n', encoding="utf-8")
        (t1 / "local.env").write_text(': "${RES:=/Volumes/DISK-2/mva-hackathon/resources}"\n', encoding="utf-8")
        env_example = (ENGINE_SRC / "config" / "local.env.example").read_text(encoding="utf-8")
        ef = self.tmp / "local.env"
        ef.write_text(env_example, encoding="utf-8")
        code = ("import sys; sys.path.insert(0, %r); import t2common as C; e = C.load_env(envfile=%r); "
                "print(e['RES']); print(e['REF']); print(e['T2_RESULTS']); print(e['T1_WORK'])") % (
            str(self.eng / "scripts" / "phase1"), str(ef))
        r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                           env={**os.environ, "T1_CONF": str(t1), "HOME": "/Users/x"})
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], "/Volumes/DISK-2/mva-hackathon/resources")
        self.assertEqual(lines[1], "/Volumes/DISK-2/mva-hackathon/resources/GRCh38.nochr.fa.gz")
        self.assertEqual(lines[2], "/Users/x/mva-hackathon/results/track2")
        self.assertEqual(lines[3], "/Users/x/mva-hackathon/work/track1")

    def test_bash_scripts_parse_and_avoid_gnu_only_syntax(self):
        for sh in sorted((self.eng / "scripts" / "phase1").glob("*.sh")):
            r = subprocess.run(["bash", "-n", str(sh)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{sh.name}: {r.stderr}")
            text = "\n".join(l for l in sh.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
            for pat in BASH_FORBIDDEN:
                self.assertIsNone(re.search(pat, text), f"{sh.name} 用了 macOS bash 3.2 / BSD 不支援的 {pat}")

    def test_preflight_runs_to_the_end_without_crashing(self):
        cfg = self.eng / "config" / "local.env"
        cfg.write_text(self.envfile.read_text(encoding="utf-8"))
        r = subprocess.run(["bash", str(self.eng / "scripts" / "phase1" / "00_preflight.sh")], capture_output=True,
                           text=True, env={**os.environ, "CLAUDECODE": "", "T2_PREFLIGHT_SKIP_NETWORK": "1"})
        self.assertIn("9/9", r.stdout, r.stdout + r.stderr)
        self.assertEqual(r.returncode, 1)                     # 這個假環境缺很多東西，應該要列出 ✗
        self.assertNotIn("unbound variable", r.stderr)


if __name__ == "__main__":
    unittest.main()
