# -*- coding: utf-8 -*-
"""EMOS 概率订正插件入口。系数估计和分布订正在 ``emos_core.py``。"""
from __future__ import annotations

from .emos_core import (
    ApplyEMOS,
    CalibratedForecastDistributionParameters,
    EstimateCoefficientsForEnsembleCalibration,
)


class EmosProbabilityCalibrationPlugin(ApplyEMOS):
    """EMOS 订正插件。

    EMOS（Ensemble Model Output Statistics，集合模式输出统计）
    用 CRPS（Continuous Ranked Probability Score，连续等级概率评分）
    最小化估计位置和尺度系数，再生成集合、概率或分位数。
    ``EstimateCoefficientsForEnsembleCalibration`` 负责估系数。
    """


__all__ = [
    "ApplyEMOS",
    "CalibratedForecastDistributionParameters",
    "EmosProbabilityCalibrationPlugin",
    "EstimateCoefficientsForEnsembleCalibration",
]
