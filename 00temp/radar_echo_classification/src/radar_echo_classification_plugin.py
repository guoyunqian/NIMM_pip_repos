# -*- coding: utf-8 -*-
"""雷达回波分类插件入口。四类算法仍在 ``echo_class.py``。"""
from __future__ import annotations

from .echo_class import (
    ConvStratRautPlugin,
    FeatureDetectionPlugin,
    HydroclassSemisupervisedPlugin,
    SteinerConvStratPlugin,
)


class RadarEchoClassificationPlugin(SteinerConvStratPlugin):
    """雷达回波分类插件。默认使用 Steiner 对流/层状分类。

    其余入口：``FeatureDetectionPlugin``（特征检测）、
    ``HydroclassSemisupervisedPlugin``（半监督相态）、
    ``ConvStratRautPlugin``（Raut 对流/层状）。
    """


__all__ = [
    "ConvStratRautPlugin",
    "FeatureDetectionPlugin",
    "HydroclassSemisupervisedPlugin",
    "RadarEchoClassificationPlugin",
    "SteinerConvStratPlugin",
]
