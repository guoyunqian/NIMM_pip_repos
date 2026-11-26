# -*- coding: utf-8 -*-
"""雷达定量降水估计插件入口。Z-R 等关系仍在 ``qpe.py``。"""
from __future__ import annotations

from .qpe import (
    EstimateRainRateA,
    EstimateRainRateHydro,
    EstimateRainRateKdp,
    EstimateRainRateZ,
    EstimateRainRateZA,
    EstimateRainRateZKdp,
    EstimateRainRateZPoly,
    EstimateZtoR,
    QPEPlugin,
)


class RadarQpeRetrievalPlugin(QPEPlugin):
    """雷达定量降水估计插件。按 ``method`` 选择 Z、Kdp、衰减或相态关系。

    QPE（Quantitative Precipitation Estimation，定量降水估计）
    把反射率等雷达量换成雨强。
    """


__all__ = [
    "EstimateRainRateA",
    "EstimateRainRateHydro",
    "EstimateRainRateKdp",
    "EstimateRainRateZ",
    "EstimateRainRateZA",
    "EstimateRainRateZKdp",
    "EstimateRainRateZPoly",
    "EstimateZtoR",
    "QPEPlugin",
    "RadarQpeRetrievalPlugin",
]
