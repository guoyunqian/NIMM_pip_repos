# -*- coding: utf-8 -*-
"""概率可靠性订正插件入口。计算仍在 ``reliability_calibration.py``。"""
from __future__ import annotations

from .reliability_calibration import (
    AggregateReliabilityCalibrationTables,
    ApplyReliabilityCalibration,
    ConstructReliabilityCalibrationTables,
    ManipulateReliabilityTable,
)


class ProbabilityReliabilityCorrectionPlugin(ApplyReliabilityCalibration):
    """可靠性订正插件。把预报概率按可靠性表改到更接近观测频率。

    建表、多表汇总和改表分别是
    ``ConstructReliabilityCalibrationTables``、
    ``AggregateReliabilityCalibrationTables``、
    ``ManipulateReliabilityTable``。
    """


__all__ = [
    "AggregateReliabilityCalibrationTables",
    "ApplyReliabilityCalibration",
    "ConstructReliabilityCalibrationTables",
    "ManipulateReliabilityTable",
    "ProbabilityReliabilityCorrectionPlugin",
]
