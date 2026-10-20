"""第 20 步 robustness harness 的測試。

重點不是「harness 會通過」——那每次 run.sh 都在跑。重點是**它會失敗**。
一個在任何情況下都通過的檢查不是檢查，是裝飾。這裡故意把引擎弄壞
（讓它認得候選藥的名字、讓某道閘不咬人），確認 harness 真的抓得到。
"""
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parents[1]
sys.path.insert(0, str(ENGINE / "src"))


def _load():
    spec = importlib.util.spec_from_file_location(
        "rb20", ENGINE / "scripts" / "phase1" / "20_robustness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RobustnessHarnessCatchesBreakage(unittest.TestCase):
    def setUp(self):
        self.rb = _load()
        self.rb.failures.clear()
        self.case, self.scoring, self.cands = self.rb.load_all()
        self.base = self.rb.verdicts(self.case, self.scoring, self.cands)

    def tearDown(self):
        self.rb.failures.clear()

    def test_clean_engine_passes(self):
        """先確認基準：沒動過的引擎，兩項斷言都過。"""
        r3 = self.rb.r3_name_blinding(self.case, self.scoring, self.cands, self.base)
        r4 = self.rb.r4_probes(self.case, self.scoring, self.cands, self.base)
        self.assertTrue(r3["passed"], r3["diffs"])
        self.assertTrue(all(r["passed"] for r in r4), r4)
        self.assertEqual(self.rb.failures, [])

    def test_name_blinding_catches_a_name_dependent_engine(self):
        """把引擎改成看名字辦事，R3 必須抓到。"""
        import triage
        real = triage.triage_one

        def peeking(cand, case, scoring):
            out = real(cand, case, scoring)
            if cand.get("id") == "C-NA":          # 偏袒自己選的那一個
                out["verdict"] = "STRONG"
            return out

        triage.triage_one = peeking
        try:
            base = self.rb.verdicts(self.case, self.scoring, self.cands)
            r3 = self.rb.r3_name_blinding(self.case, self.scoring, self.cands, base)
        finally:
            triage.triage_one = real
        self.assertFalse(r3["passed"],
                         "R3 放過了一個會認名字的引擎——這個檢查沒有作用")
        self.assertTrue(any("C-NA" in d for d in r3["diffs"]), r3["diffs"])
        self.assertTrue(self.rb.failures)

    def test_probes_catch_a_gate_that_stops_biting(self):
        """把腎臟閘的規則清空，PROBE-RENAL 必須失敗。"""
        import copy
        sc = copy.deepcopy(self.scoring)
        for lvl in sc["hard_gates"]["G3_renal"]["rule"]:
            sc["hard_gates"]["G3_renal"]["rule"][lvl] = {}
        base = self.rb.verdicts(self.case, sc, self.cands)
        r4 = self.rb.r4_probes(self.case, sc, self.cands, base)
        renal = next(r for r in r4 if r["probe"] == "PROBE-RENAL")
        self.assertFalse(renal["passed"],
                         "G3 已經不咬人了，PROBE-RENAL 還是通過——探針沒有作用")
        self.assertTrue(any("PROBE-RENAL" in f for f in self.rb.failures))

    def test_overdetermination_is_computed_not_asserted(self):
        """R1b 的數字必須跟著規則走：拿掉腎臟閘，C-AMPK 就不該再出現在淘汰名單。"""
        import copy
        rows = self.rb.r1b_overdetermination(self.case, self.scoring, self.cands)
        amp = next((r for r in rows if r["id"] == "C-AMPK"), None)
        self.assertIsNotNone(amp, "C-AMPK 應該在基準淘汰名單裡")
        self.assertEqual(amp["rules"], ["G3_renal"])
        sc = copy.deepcopy(self.scoring)
        for lvl in sc["hard_gates"]["G3_renal"]["rule"]:
            sc["hard_gates"]["G3_renal"]["rule"][lvl] = {}
        rows2 = self.rb.r1b_overdetermination(self.case, sc, self.cands)
        self.assertIsNone(next((r for r in rows2 if r["id"] == "C-AMPK"), None),
                          "拿掉唯一攔下 C-AMPK 的規則後，它還被列為淘汰")

    def test_single_points_of_failure_are_found(self):
        """R5 必須真的找出單一來源的邊，而不是回傳空表。"""
        r5 = self.rb.r5_leave_one_source_out()
        self.assertGreater(r5["chains"], 0, "找不到 D1→P 的路徑")
        spof = [r for r in r5["rows"] if r["chains_alive"] == 0]
        self.assertTrue(spof, "R5 沒找到任何單點失效，與已知的鏈結構不符")
        for r in spof:
            self.assertTrue(r["edges_unsourced"])


if __name__ == "__main__":
    unittest.main()
