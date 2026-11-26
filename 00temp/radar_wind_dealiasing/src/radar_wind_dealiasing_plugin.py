# -*- coding: utf-8 -*-
"""雷达径向速度退模糊插件入口。区域展开仍在 ``region_dealias.py``。"""
from __future__ import annotations

from .region_dealias import RegionDealiasPlugin


class RadarWindDealiasingPlugin(RegionDealiasPlugin):
    """雷达速度退模糊插件。

    在奈奎斯特速度（Nyquist velocity，不模糊速度）间隔内展开折叠的径向速度。
    连通域求解仍由 ``RegionDealiasPlugin.process`` 完成。
    """


__all__ = ["RadarWindDealiasingPlugin", "RegionDealiasPlugin"]
