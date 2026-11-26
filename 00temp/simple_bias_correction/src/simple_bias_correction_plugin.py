# -*- coding: utf-8 -*-
"""简单偏差订正插件入口。估计和订正仍在 ``simple_bias_correction.py``。"""
from __future__ import annotations

from .simple_bias_correction import ApplyBiasCorrection, CalculateForecastBias


class SimpleBiasCorrectionPlugin(ApplyBiasCorrection):
    """简单偏差订正插件。预报减去历史偏差场。

    偏差场由 ``CalculateForecastBias.process`` 从历史预报和实况估计。
    """


__all__ = [
    "ApplyBiasCorrection",
    "CalculateForecastBias",
    "SimpleBiasCorrectionPlugin",
]
