# -*- coding: utf-8 -*-
"""确认 SAMOS 插件文件继承 BasePlugin，并区分训练和订正。"""
import unittest
from pathlib import Path


class PluginEntryTest(unittest.TestCase):
    def test_named_plugin_declares_base_entry(self):
        text = Path(__file__).resolve().parents[1].joinpath(
            "src", "samos_probability_calibration_plugin.py"
        ).read_text(encoding="utf-8")
        self.assertIn("class SamosProbabilityCalibrationPlugin(BasePlugin)", text)
        self.assertIn("标准化异常", text)
        self.assertIn('name == "train"', text)


if __name__ == "__main__":
    unittest.main()
