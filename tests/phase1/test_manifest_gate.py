#!/usr/bin/env python3
"""測 make_manifest.py 這道一致性閘本身會不會擋。

為什麼需要這組測試：這份作品的核心主張之一是「交付物之間的數字不可能漂移，因為發佈前有一道
會擋的閘」。在這組測試之前，那個主張的唯一證據是閘曾經擋過我們自己——也就是軼事。引擎有
20_robustness.py 去擾動它，檢查器卻沒有任何東西擾動它。這裡用同樣的方法對檢查器做一次：
把整棵樹複製到暫存區，一次只破壞一個東西，然後要求閘用正確的訊息擋下來。

設計上刻意只斷言「訊息出現」而不斷言「乾淨樹會通過」。乾淨樹在提交日之前本來就會因為人工
步驟（簽核、PDF 重建、填日期）而有未完成項，若把 baseline 綁成全綠，這組測試會在真正該綠的
那一天之外每天都紅，那是沒有用的測試。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
REGISTERS = ENGINE.parent / "registers"
# make_manifest.py 讀的 register：只複製這四個，fact_register.csv 之外的都是生成檔。
REG_FILES = ("claim_ledger.csv", "citation_check.csv", "fact_register.csv", "ai_usage_register.csv")


def _ignore(_dir, names):
    return [n for n in names if n in {".git", "__pycache__", ".venv", "node_modules"}]


class ManifestGate(unittest.TestCase):
    """每個測試拿一棵乾淨的複製樹，破壞一處，然後跑閘。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="t2manifest_"))
        cls.src = cls.tmp / "src_tree"
        (cls.src / "research").mkdir(parents=True)
        shutil.copytree(ENGINE, cls.src / "research" / "engine", ignore=_ignore, symlinks=True)
        (cls.src / "research" / "registers").mkdir()
        for name in REG_FILES:
            if (REGISTERS / name).exists():
                shutil.copy2(REGISTERS / name, cls.src / "research" / "registers" / name)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def tree(self):
        """一棵新的複製樹，回傳它的 engine 目錄。"""
        dest = Path(tempfile.mkdtemp(prefix="case_", dir=str(self.tmp)))
        shutil.copytree(self.src, dest / "t", ignore=_ignore, symlinks=True)
        return dest / "t" / "research" / "engine"

    def run_gate(self, eng, *args):
        r = subprocess.run([sys.executable, "make_manifest.py", *args], cwd=eng,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, r.stdout + r.stderr

    def assertBlocks(self, eng, needle, *args):
        rc, out = self.run_gate(eng, *args)
        self.assertNotEqual(rc, 0, f"閘沒有擋下來：預期訊息包含 {needle!r}\n{out}")
        self.assertIn(needle, out, f"閘擋了，但訊息不對：預期包含 {needle!r}\n{out}")

    # ---- 數字漂移：同一個數字出現在兩份文件，改一邊就要被抓 ----

    def test_entries_count_drift_is_caught(self):
        """任一交付物把候選分母寫錯就擋（不只報告和 pitch）。"""
        eng = self.tree()
        p = eng / "docs" / "PLAIN_LANGUAGE_SUMMARY.md"
        t = p.read_text(encoding="utf-8")
        self.assertIn("17 entries", t, "fixture 假設這份文件寫了 17 entries")
        p.write_text(t.replace("17 entries", "18 entries", 1), encoding="utf-8")
        self.assertBlocks(eng, "but the canonical")

    def test_retyped_claim_count_drift_is_caught(self):
        """報告重打的 ledger 列數必須等於 ledger 實際列數。"""
        eng = self.tree()
        p = eng / "docs" / "REPORT.md"
        t = p.read_text(encoding="utf-8")
        # Read the count out of the report rather than hard-coding it: the ledger grows (a product
        # row was added on 2026-10-20 and this test failed on the literal "36"), and a fixture that
        # has to be edited whenever the thing it guards changes is a fixture that gets switched off.
        m = re.search(r"\b(\d+) claims\b", t)
        self.assertIsNotNone(m, "fixture 假設報告寫了 'N claims'")
        self.assertNotEqual(m.group(1), "99")
        p.write_text(t.replace(f"{m.group(1)} claims", "99 claims", 1), encoding="utf-8")
        self.assertBlocks(eng, "99 claims")

    def test_count_drift_inside_the_xlsx_methods_form_is_caught(self):
        """組織方的 methods 表單是 .xlsx，閘以前根本讀不到它裡面的數字。

        2026-10-20 發現：那份已提交的表單還寫著舊的 ledger 列數，而且帶著報告早已撤回的
        全稱否定。一道只檢查「容易讀的檔」的閘，破洞的形狀就是一個 spreadsheet。
        """
        import zipfile
        eng = self.tree()
        x = eng / "docs" / "Vero7878_track2_methods.xlsx"
        self.assertTrue(x.exists(), "fixture 假設 methods 表單在交付物裡")
        zin = zipfile.ZipFile(x)
        items = [(i, zin.read(i.filename)) for i in zin.infolist()]
        zin.close()
        sheet = "xl/worksheets/sheet1.xml"
        m = re.search(r"\b(\d+) claims\b",
                      next(d for i, d in items if i.filename == sheet).decode("utf-8"))
        self.assertIsNotNone(m, "fixture 假設表單裡寫了 'N claims'")
        with zipfile.ZipFile(x, "w", zipfile.ZIP_DEFLATED) as zout:
            for i, data in items:
                if i.filename == sheet:
                    data = data.decode("utf-8").replace(f"{m.group(1)} claims", "99 claims", 1).encode("utf-8")
                zout.writestr(i, data)
        self.assertBlocks(eng, "99 claims")

    def test_a_withdrawn_claim_reappearing_is_caught(self):
        """撤回過的句子重新出現在任何交付物裡就擋。

        2026-10-20 與 10-21 各發生一次：被報告撤回的陳述還活在組織方的 .xlsx 表單裡。
        自相矛盾的兩份交付物比單一個錯誤更貴，因為評審得自己決定要相信哪一份。
        """
        eng = self.tree()
        p = eng / "docs" / "PLAIN_LANGUAGE_SUMMARY.md"
        t = p.read_text(encoding="utf-8")
        p.write_text(t + "\n\nThis closes the readthrough route.\n", encoding="utf-8")
        self.assertBlocks(eng, "still contains a withdrawn claim")

    def test_suite_size_drift_outside_the_deliverables_is_caught(self):
        """套件大小被手抄在 README、runbook 與 runner 裡，閘以前不算這個數字。

        2026-10-21：同一個數字在 75 → 77 → 78 之間漂了三次，四份檔案各說各話，而閘一次都沒抓到——
        因為它寫在測試檔裡而不是任何 register 裡，沒有東西去算它。評審第一個打開的就是 README。
        """
        eng = self.tree()
        p = eng / "README.md"
        t = p.read_text(encoding="utf-8")
        m = re.search(r"Ran (\d+) tests", t)
        self.assertIsNotNone(m, "fixture 假設 README 寫了實際的套件大小")
        self.assertNotEqual(m.group(1), "99")
        p.write_text(t.replace(f"Ran {m.group(1)} tests", "Ran 99 tests", 1), encoding="utf-8")
        self.assertBlocks(eng, "but tests/phase1 contains")

    def test_a_quoted_detectability_number_that_the_arithmetic_does_not_produce_is_caught(self):
        """報告在散文裡引用 power_table.md 的兩格數字，閘要對帳回算術本身。

        2026-10-21 加這一條時它立刻抓到自己：表格用 0.33 當「三分之一」，算出 300，
        而報告寫的是 0.30 -> 0.20，也就是 294。引用一格生成的數字就是會漂的那種數字。
        """
        eng = self.tree()
        p = eng / "docs" / "REPORT.md"
        t = p.read_text(encoding="utf-8")
        self.assertIn("**294 scored cells per arm**", t, "fixture 假設報告引用了參考設計那一格")
        p.write_text(t.replace("**294 scored cells per arm**", "**120 scored cells per arm**", 1),
                     encoding="utf-8")
        # needle 必須只在失敗訊息裡出現："units per arm" 也是成功那行
        # "counts verified: ... reference-design units per arm=294" 的一部分。
        self.assertBlocks(eng, "but the two-proportion computation gives")

    # ---- 主要假說：報告和 pitch 必須逐字相同 ----

    def test_primary_sentence_paraphrase_is_caught(self):
        """把 pitch 裡的 PRIMARY 句改一個字就擋——這是最容易被悄悄改掉的一句。"""
        eng = self.tree()
        p = eng / "docs" / "PITCH.md"
        t = p.read_text(encoding="utf-8")
        self.assertIn("niacin (nicotinic acid)", t)
        p.write_text(t.replace("niacin (nicotinic acid)", "niacin", 1), encoding="utf-8")
        self.assertBlocks(eng, "PRIMARY line is not quoted verbatim")

    # ---- 生成快照：不能提交一個失敗的 run ----

    def test_failed_run_snapshot_is_caught(self):
        eng = self.tree()
        p = eng / "outputs" / "run.txt"
        p.write_text("== selftest ==\nALL PASS\nSTEP FAILED (manifest) rc=1\n", encoding="utf-8")
        self.assertBlocks(eng, "records a failed run")

    # ---- 影片長度：超時是科學嚴謹救不回來的失敗 ----

    def test_pitch_over_length_is_caught(self):
        """在最後一拍塞進一段話，讓估計長度超過上限。"""
        eng = self.tree()
        p = eng / "docs" / "PITCH.md"
        t = p.read_text(encoding="utf-8")
        p.write_text(t + "\n\n**2:55–3:40 — overrun.**\n" + ("word " * 200) + "\n",
                     encoding="utf-8")
        # needle must appear ONLY in the failure; "180s limit" also shows up in the
        # success line "pitch length : 2:53 (173s, 180s limit)", which made the
        # unperturbed-tree test fail the moment the manifest first went green.
        self.assertBlocks(eng, "docs/PITCH.md is estimated at")

    def test_pitch_stated_length_must_match_computed(self):
        """舞台指示裡寫的長度本身也要對帳，不能是斷言。"""
        eng = self.tree()
        p = eng / "docs" / "PITCH.md"
        t = p.read_text(encoding="utf-8")
        self.assertIn("Measured 2:53 spoken", t)
        p.write_text(t.replace("Measured 2:53 spoken", "Measured 1:30 spoken", 1), encoding="utf-8")
        self.assertBlocks(eng, "computed length is")

    # ---- AI 揭露：登錄簿有、文件沒寫，是兩種失敗裡較嚴重的那一種 ----

    def test_undisclosed_ai_provider_is_caught(self):
        eng = self.tree()
        reg = eng.parent / "registers" / "ai_usage_register.csv"
        reg.write_text(reg.read_text(encoding="utf-8")
                       + "2026-10-20,Mistral,Le Chat,unknown,no,no,script text,drafting\n",
                       encoding="utf-8")
        self.assertBlocks(eng, "undisclosed AI use")

    def test_report_omitting_a_disclosed_provider_is_caught(self):
        """METHODS 揭露了、報告沒寫，等於兩份交付物對「誰看過資料」說法不同。"""
        eng = self.tree()
        p = eng / "docs" / "REPORT.md"
        t = p.read_text(encoding="utf-8")
        self.assertIn("OpenAI", t, "fixture 假設報告 §14 有寫第二個供應商")
        p.write_text(t.replace("OpenAI, ChatGPT/Codex", "a second assistant"), encoding="utf-8")
        self.assertBlocks(eng, "disagree about who had access")

    # ---- 交付物缺檔 ----

    def test_missing_deliverable_is_caught(self):
        eng = self.tree()
        (eng / "docs" / "PLAIN_LANGUAGE_SUMMARY.md").unlink()
        self.assertBlocks(eng, "missing deliverable")

    # ---- 送出的 PDF 不能比它的來源舊（freeze 時才擋）----

    def test_stale_pdf_blocks_at_freeze_only(self):
        eng = self.tree()
        pdf = eng / "docs" / "Vero7878_track2_report.pdf"
        rep = eng / "docs" / "REPORT.md"
        if not pdf.exists():
            self.skipTest("還沒建過 PDF")
        old = rep.stat().st_mtime - 3600
        os.utime(pdf, (old, old))
        self.assertBlocks(eng, "superseded report", "--freeze")
        rc, out = self.run_gate(eng)
        self.assertNotIn("superseded report", out.split("PENDING")[0],
                         "freeze 之前這一條應該是 PENDING，不是 BLOCKED")

    def test_a_quoted_continuous_endpoint_effect_the_arithmetic_does_not_produce_is_caught(self):
        """§6 引用了連續型終點（Stage A/B）的兩個數字：三皿每組只看得到 d = 2.29，
        以及 d = 1.0 需要 16 皿每組。兩個都由 21_quant_checks 重算，不是互相比對。"""
        eng = self.tree()
        p = eng / "docs" / "REPORT.md"
        p.write_text(p.read_text(encoding="utf-8").replace("standardised difference of **d = 2.29**",
                                                           "standardised difference of **d = 0.80**"),
                     encoding="utf-8")
        self.assertBlocks(eng, "two-sample computation gives")

    def test_a_deliverable_promising_a_file_that_does_not_exist_is_caught(self):
        """2026-10-21 的真實缺陷：METHODS_AND_AI.md 說 AI 合規的截圖證據 archived 在
        registers/ai_usage_evidence/、available on request，而那個資料夾從來不存在。
        閘當時不看引用的路徑存不存在，所以 compliance 一節可以在全綠的 manifest 底下
        承諾一個拿不出來的東西。"""
        eng = self.tree()
        p = eng / "docs" / "METHODS_AND_AI.md"
        p.write_text(p.read_text(encoding="utf-8")
                     + "\n\nFull audit trail archived in `docs/ai_usage_proof/`, "
                       "available on request.\n", encoding="utf-8")
        self.assertBlocks(eng, "which does not exist")

    def test_a_citation_that_leaves_the_repository_does_not_block(self):
        """閘宣告的範圍是 repo 內。交付物也會引用 repo 外的 registers/ 和 ../DATA-LOCATION.md，
        而這支閘跟著 repo 走，分不出真的外圍目錄和重現／擾動用的修剪樹——兩者都有一個
        registers/，裡面放的檔案子集不同。這一條把那個界限釘住：上面那個檢查第一版對
        repo 外的路徑一律照抓，結果在一棵完全沒被動過的樹上報了九個不存在的檔案。"""
        eng = self.tree()
        p = eng / "docs" / "REPORT.md"
        p.write_text(p.read_text(encoding="utf-8")
                     + "\n\nSee `registers/not_a_real_file_2026.md` and `../NOT-REAL.md`.\n",
                     encoding="utf-8")
        _rc, out = self.run_gate(eng)
        self.assertNotIn("which does not exist", out, out)

    def test_a_retyped_ai_register_count_that_the_file_does_not_support_is_caught(self):
        """2026-10-21 的真實缺陷：REPORT §14 寫「three of its seven rows」，而
        ai_usage_register.csv 是六列、其中兩列符合。兩個數字都是手打的，而且錯在
        整份提交裡主題最是「我們的陳述能不能被信任」的那一節。供應商清單早就被三向
        閘住，描述同一個檔案形狀的計數却沒有。"""
        eng = self.tree()
        p = eng / "docs" / "REPORT.md"
        t = p.read_text(encoding="utf-8")
        self.assertIn("Of its **six** usage rows", t)
        p.write_text(t.replace("Of its **six** usage rows", "Of its **nine** usage rows"),
                     encoding="utf-8")
        self.assertBlocks(eng, "AI-register usage rows is 6")

    def test_a_data_value_containing_a_slash_is_not_read_as_a_promised_file(self):
        """路徑檢查的假陽性類別，實際發生過。ClinVar 的欄位值本身帶斜線，
        §2 和 §13 都直接引用 `Pathogenic/Likely_pathogenic`，第一版檢查把它讀成一個
        被承諾的檔案，就在一句完全正確的文字上擋住發佈。這裡的假陽性跟漏抱一樣貴，
        因為繞過它的方法是去改準確的叙述。"""
        eng = self.tree()
        p = eng / "docs" / "REPORT.md"
        p.write_text(p.read_text(encoding="utf-8")
                     + "\n\nClassified `Pathogenic/Likely_pathogenic` with `CLNSIG=Benign/Likely_"
                       "benign` and consequence `missense_variant/splice_region_variant`.\n",
                     encoding="utf-8")
        _rc, out = self.run_gate(eng)
        self.assertNotIn("which does not exist", out, out)

    # ---- 機器人性檢查：閘不能只是回傳失敗 ----

    def test_gate_is_not_blocking_on_everything(self):
        """一棵沒被動過的樹不能因為我們上面擾動的那些理由而擋。

        不要求全綠（人工簽核、PDF 重建等在提交日之前本來就還沒做），但要求擾動訊息
        在未擾動的樹上不出現——否則上面每一條測試都只是在測一個永遠會失敗的程式。
        """
        eng = self.tree()
        _rc, out = self.run_gate(eng)
        for needle in ("but the canonical", "99 claims", "PRIMARY line is not quoted verbatim",
                       "records a failed run", "docs/PITCH.md is estimated at", "computed length is",
                       "undisclosed AI use", "missing deliverable",
                       "but tests/phase1 contains", "still contains a withdrawn claim",
                       "but the two-proportion computation gives",
                       "but the design effect gives", "which does not exist",
                       "AI-register usage rows is"):
            self.assertNotIn(needle, out, f"未擾動的樹就報了 {needle!r}：\n{out}")


if __name__ == "__main__":
    unittest.main()
