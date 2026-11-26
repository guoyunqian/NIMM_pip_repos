# -*- coding: utf-8 -*-
"""确认 EMOS 插件文件按规范继承订正类。"""
import unittest
from pathlib import Path


class PluginEntryTest(unittest.TestCase):
    def test_named_plugin_declares_apply_entry(self):
        text = Path(__file__).resolve().parents[1].joinpath(
            "src", "emos_probability_calibration_plugin.py"
        ).read_text(encoding="utf-8")
        self.assertIn("class EmosProbabilityCalibrationPlugin(ApplyEMOS)", text)
        self.assertIn("连续等级概率评分", text)


if __name__ == "__main__":
    unittest.main()
