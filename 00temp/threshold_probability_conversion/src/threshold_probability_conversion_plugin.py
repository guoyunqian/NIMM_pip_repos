# -*- coding: utf-8 -*-
"""阈值概率转换插件入口。比较和隶属仍在 ``threshold.py``。"""
from __future__ import annotations

from .threshold import Threshold


class ThresholdProbabilityConversionPlugin(Threshold):
    """把诊断量转成相对阈值的 0–1 场。

    硬阈值给出真值，fuzzy 阈值给出线性隶属。
    对集合成员或时间平均后就是概率。计算在 ``Threshold.process``。
    """


__all__ = ["Threshold", "ThresholdProbabilityConversionPlugin"]
