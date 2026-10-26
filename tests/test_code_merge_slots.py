"""code_merge_slots 的离线单元测试（只用 python3 标准库，不需要 Dify）。

运行：python3 tests/test_code_merge_slots.py
说明：这里只验证合并逻辑本身；Dify Code 节点沙箱里的实际行为（如 import re 是否允许、
__is_success 的实际类型）需要以后在 Dify 中实测。
"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE_PATH = os.path.join(ROOT, "dify", "code_merge_slots.py")
JSON_PATH = os.path.join(ROOT, "dify", "chatflow-design.json")
DOC_PATH = os.path.join(ROOT, "docs", "workflow-nodes.md")

SRC = open(CODE_PATH, encoding="utf-8").read()
NS = {}
exec(compile(SRC, CODE_PATH, "exec"), NS)
main, SLOTS = NS["main"], NS["SLOTS"]


def run(is_success=1, new=None, old=None):
    new, old = new or {}, old or {}
    kw = {"is_success": is_success}
    for k in SLOTS:
        kw["new_" + k] = new.get(k, "")
        kw["old_" + k] = old.get(k, "")
    return main(**kw)


FULL_OLD = {"brand": "BYD 比亚迪", "vehicle_model": "海豚 Dolphin", "power_state": "不能READY",
            "symptom": "早上开不了", "model_year": "2022"}


class TestSync(unittest.TestCase):
    def test_json_code_identical(self):
        d = json.load(open(JSON_PATH, encoding="utf-8"))
        node = [n for n in d["nodes"] if n["id"] == "code_merge_slots"][0]
        self.assertEqual(node["code"].strip(), SRC.strip())
        self.assertEqual([o["name"] for o in node["outputs"]], SLOTS + ["fault_query"])

    def test_doc_code_identical(self):
        doc = open(DOC_PATH, encoding="utf-8").read()
        sec = doc[doc.index("### 2.1"):doc.index("## 3.")]
        block = re.search(r"```python\n(.*?)```", sec, re.S).group(1)
        self.assertEqual(block.strip(), SRC.strip())


class TestIsSuccess(unittest.TestCase):
    def test_fail_keeps_all_old(self):
        for v in (0, "0", "0.0", False, "False", "false"):
            r = run(v, {k: "新值" for k in SLOTS}, FULL_OLD)
            for k in SLOTS:
                self.assertEqual(r[k], FULL_OLD.get(k, ""), (v, k))

    def test_success_or_missing_uses_new(self):
        for v in (1, "1", True, None, ""):
            r = run(v, {"brand": "Tesla"}, {})
            self.assertEqual(r["brand"], "Tesla", v)


class TestEmpty(unittest.TestCase):
    def test_empty_new_keeps_old(self):
        for v in ("", None, "   ", "\n\t", "null", "None", "undefined", "？", "。"):
            r = run(1, {"brand": v}, FULL_OLD)
            self.assertEqual(r["brand"], "BYD 比亚迪", repr(v))

    def test_first_turn_empty_old(self):
        r = run(1, {"brand": "Tesla", "symptom": "开不了"}, {})
        self.assertEqual((r["brand"], r["symptom"], r["vehicle_model"]), ("Tesla", "开不了", ""))

    def test_whitespace_trimmed(self):
        r = run(1, {"brand": "  Tesla \n"}, {})
        self.assertEqual(r["brand"], "Tesla")


UNSURE_INPUTS = ["不确定", "不知道", "未知", "unknown", "Unknown", "UNKNOWN", " unknown ",
                 "不清楚", "没注意", "没注意到", "不太清楚", "不记得", "说不清", "Not sure",
                 "not sure", "I don't know", "idk", "N/A", "n/a", "不知道。", "不确定？",
                 "我也不太清楚呢", "没留意", "待确认", "不 确 定", "不详"]


class TestUncertain(unittest.TestCase):
    def test_normalized_fills_empty_slot(self):
        for v in UNSURE_INPUTS:
            for slot in ("power_state", "brand", "model_year", "powertrain"):
                r = run(1, {slot: v}, {})
                self.assertEqual(r[slot], "不确定", (slot, v))

    def test_uncertain_never_overwrites_confirmed(self):
        for v in UNSURE_INPUTS:
            r = run(1, {k: v for k in SLOTS}, FULL_OLD)
            for k in SLOTS:
                expected = FULL_OLD.get(k) or "不确定"
                self.assertEqual(r[k], expected, (k, v))

    def test_old_uncertain_replaced_by_definite(self):
        r = run(1, {"power_state": "能READY"}, {"power_state": "不确定"})
        self.assertEqual(r["power_state"], "能READY")

    def test_old_raw_unknown_normalized(self):
        r = run(1, {}, {"power_state": "unknown", "brand": "不知道"})
        self.assertEqual((r["power_state"], r["brand"]), ("不确定", "不确定"))

    def test_text_containing_word_not_treated_as_unsure(self):
        r = run(1, {"symptom": "不知道为什么早上开不了"}, {})
        self.assertEqual(r["symptom"], "不知道为什么早上开不了")
        r = run(1, {"recent_events": "无"}, {})
        self.assertEqual(r["recent_events"], "无")


class TestPowerState(unittest.TestCase):
    def test_enum_and_aliases(self):
        cases = {"能READY": "能READY", "能 ready": "能READY", "能进入READY": "能READY",
                 "不能READY": "不能READY", "不能 Ready": "不能READY", "进不了READY": "不能READY",
                 "READY不亮": "不能READY", "12V都没电": "12V都没电", "12v没电": "12V都没电",
                 "能正常READY": "能READY", "能正常 READY。": "能READY"}
        for v, exp in cases.items():
            self.assertEqual(run(1, {"power_state": v}, {})["power_state"], exp, v)

    def test_non_enum_becomes_uncertain(self):
        for v in ("屏幕能亮", "黑屏，车门能开", "好像可以", "N/A?", "无"):
            self.assertEqual(run(1, {"power_state": v}, {})["power_state"], "不确定", v)

    def test_non_enum_does_not_overwrite_confirmed(self):
        r = run(1, {"power_state": "黑屏"}, {"power_state": "不能READY"})
        self.assertEqual(r["power_state"], "不能READY")

    def test_definite_change_allowed(self):
        r = run(1, {"power_state": "能READY"}, {"power_state": "不能READY"})
        self.assertEqual(r["power_state"], "能READY")


class TestFaultQuery(unittest.TestCase):
    def test_concat_skips_empty_and_uncertain(self):
        r = run(1, {"brand": "Tesla", "vehicle_model": "Model Y", "power_state": "不知道",
                    "symptom": "中控屏黑屏", "powertrain": ""}, {})
        self.assertEqual(r["fault_query"], "Tesla Model Y 中控屏黑屏")

    def test_full(self):
        r = run(1, {"warning_info": "黄色电池图案", "powertrain": "BEV"}, FULL_OLD)
        self.assertEqual(r["fault_query"], "BYD 比亚迪 海豚 Dolphin BEV 不能READY 早上开不了 黄色电池图案")

    def test_output_keys(self):
        self.assertEqual(sorted(run()), sorted(SLOTS + ["fault_query"]))
        for v in run().values():
            self.assertIsInstance(v, str)


class TestMultiTurn(unittest.TestCase):
    """按 test-cases.md 的多轮用例串起来跑合并逻辑（只模拟 Code 节点，不模拟 LLM）。"""

    @staticmethod
    def step(conv, is_success, new):
        r = run(is_success, new, conv)
        return {k: r[k] for k in SLOTS}, r

    @staticmethod
    def complete(conv):
        # 对应 if_slots：4 个必填项 非空 且 不包含「不确定」
        return all(conv[k] and "不确定" not in conv[k]
                   for k in ("brand", "vehicle_model", "power_state", "symptom"))

    def test_tc02(self):
        conv = {k: "" for k in SLOTS}
        conv, _ = self.step(conv, 1, {"brand": "Tesla", "symptom": "开不了"})
        self.assertFalse(self.complete(conv))
        conv, _ = self.step(conv, 1, {"vehicle_model": "Model Y", "model_year": "2021",
                                      "symptom": "开不了；中控屏黑屏，车门能开",
                                      "power_state": "黑屏，车门能开"})
        self.assertEqual((conv["brand"], conv["power_state"]), ("Tesla", "不确定"))
        self.assertFalse(self.complete(conv))
        conv, r = self.step(conv, 1, {"power_state": "不能READY"})
        self.assertTrue(self.complete(conv))
        self.assertIn("Model Y", r["fault_query"])

    def test_tc02_extraction_failure_mid_conversation(self):
        conv = {k: "" for k in SLOTS}
        conv, _ = self.step(conv, 1, {"brand": "Tesla", "symptom": "开不了"})
        conv, _ = self.step(conv, 0, {})
        self.assertEqual(conv["brand"], "Tesla")

    def test_tc19_user_never_knows(self):
        conv = {k: "" for k in SLOTS}
        conv, _ = self.step(conv, 1, {"brand": "BYD 比亚迪", "vehicle_model": "海豚 Dolphin",
                                      "symptom": "开不了"})
        for ans in ("不知道", "看不懂，不清楚", "unknown", "我也不太清楚呢"):
            conv, _ = self.step(conv, 1, {"power_state": ans})
            self.assertEqual(conv["power_state"], "不确定", ans)
            self.assertFalse(self.complete(conv))

    def test_tc20_confirmed_not_downgraded(self):
        conv = {k: "" for k in SLOTS}
        conv, _ = self.step(conv, 1, {"brand": "Tesla", "vehicle_model": "Model 3",
                                      "power_state": "能READY", "symptom": "不能充电"})
        self.assertTrue(self.complete(conv))
        conv, _ = self.step(conv, 1, {"power_state": "不清楚", "symptom": "不能充电；有异响",
                                      "brand": "Unknown"})
        self.assertEqual((conv["power_state"], conv["brand"]), ("能READY", "Tesla"))
        self.assertEqual(conv["symptom"], "不能充电；有异响")
        self.assertTrue(self.complete(conv))


if __name__ == "__main__":
    unittest.main(verbosity=1)
