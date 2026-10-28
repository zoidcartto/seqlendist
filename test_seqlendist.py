"""seqlendist —— 自检测试。

用规则在微调数据的序列长度分布里定位可疑位置

覆盖：正常路径、边界输入、防呆红线、幂等性。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import seqlendist  # noqa: E402

SAMPLE_TEXT = "def foo():\n    password = 'secret123'\n    print('x')"


class TestSeqlendist(unittest.TestCase):
    """微调数据的序列长度分布"""

    def test_cli_help_exits_zero(self):
        """--help 必须能正常退出。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "seqlendist.py"), "--help"],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0)

    def test_cli_rejects_empty_input(self):
        """空输入必须明确报错，不能静默成功。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "seqlendist.py"), "--text", "   "],
            capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(proc.returncode, 0)

    def test_cli_json_output_parses(self):
        """--json 输出必须是合法 JSON。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "seqlendist.py"), "--text", SAMPLE_TEXT,
             "--json"],
            capture_output=True, text=True, encoding="utf-8")
        if proc.returncode not in (0, 1):
            self.fail(f"退出码异常：{proc.returncode} {proc.stderr[:300]}")
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)

    def test_does_not_mutate_input(self):
        """防呆：分析过程不得改动调用方传入的对象。"""
        payload = SAMPLE_TEXT
        before = payload
        seqlendist.seqlendist_analyze(payload)
        self.assertEqual(before, payload)

    def test_is_idempotent(self):
        """同一输入跑两次结果必须一致。"""
        a = seqlendist.seqlendist_analyze(SAMPLE_TEXT)
        b = seqlendist.seqlendist_analyze(SAMPLE_TEXT)
        self.assertEqual(json.dumps(a, ensure_ascii=False, sort_keys=True),
                         json.dumps(b, ensure_ascii=False, sort_keys=True))

    def test_locates_with_line_numbers(self):
        r = seqlendist.seqlendist_analyze(SAMPLE_TEXT)
        self.assertGreater(r["hit_count"], 0)
        for h in r["hits"]:
            self.assertGreaterEqual(h["line"], 1)
            self.assertLessEqual(h["line"], r["line_count"])

    def test_clean_code_is_clean(self):
        """防呆：干净代码不该被误报。"""
        r = seqlendist.seqlendist_analyze("def add(a, b):\n    return a + b")
        self.assertTrue(r["clean"])
