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
        self.assertIn("36 claims", t)
        p.write_text(t.replace("36 claims", "99 claims", 1), encoding="utf-8")
        self.assertBlocks(eng, "99 claims")

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
        self.assertBlocks(eng, "180s limit")

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

    # ---- 機器人性檢查：閘不能只是回傳失敗 ----

    def test_gate_is_not_blocking_on_everything(self):
        """一棵沒被動過的樹不能因為我們上面擾動的那些理由而擋。

        不要求全綠（人工簽核、PDF 重建等在提交日之前本來就還沒做），但要求擾動訊息
        在未擾動的樹上不出現——否則上面每一條測試都只是在測一個永遠會失敗的程式。
        """
        eng = self.tree()
        _rc, out = self.run_gate(eng)
        for needle in ("but the canonical", "99 claims", "PRIMARY line is not quoted verbatim",
                       "records a failed run", "180s limit", "computed length is",
                       "undisclosed AI use", "missing deliverable"):
            self.assertNotIn(needle, out, f"未擾動的樹就報了 {needle!r}：\n{out}")


if __name__ == "__main__":
    unittest.main()
