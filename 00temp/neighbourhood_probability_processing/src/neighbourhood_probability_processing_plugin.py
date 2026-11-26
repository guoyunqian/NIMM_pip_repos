# -*- coding: utf-8 -*-
"""邻域概率插件入口。

计算在 ``nbhood.py`` 与 ``use_nbhood.py``。本模块按规范命名导出，
并提供默认插件类。
"""
from __future__ import annotations

from .nbhood import (
    BaseNeighbourhoodProcessing,
    GeneratePercentilesFromANeighbourhood,
    NeighbourhoodProcessing,
)
from .use_nbhood import ApplyNeighbourhoodProcessingWithAMask


class NeighbourhoodProbabilityProcessingPlugin(NeighbourhoodProcessing):
    """邻域概率处理插件。半径内的概率或百分位统计沿用 ``NeighbourhoodProcessing.process``。

    带掩码的迭代见 ``ApplyNeighbourhoodProcessingWithAMask``。
    """


__all__ = [
    "ApplyNeighbourhoodProcessingWithAMask",
    "BaseNeighbourhoodProcessing",
    "GeneratePercentilesFromANeighbourhood",
    "NeighbourhoodProbabilityProcessingPlugin",
    "NeighbourhoodProcessing",
]
