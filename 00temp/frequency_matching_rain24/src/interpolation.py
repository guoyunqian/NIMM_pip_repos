# -*- coding: utf-8 -*-
"""度制 GressMan / 双线性。

``GressManInterpolation``、``mesh_val`` 来自 ``interpolation_station_grid.src.gressman_plugin``。
``bilinear_interp`` 来自本包 ``interpolation_gg_linear``。
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TEMP = os.path.normpath(os.path.join(_HERE, "..", ".."))
_CRESS_SRC = os.path.join(_TEMP, "interpolation_station_grid", "src")
_CRESS_ROOT = os.path.join(_TEMP, "interpolation_station_grid")
for _p in (_CRESS_SRC, _CRESS_ROOT):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.append(_p)

from gressman_plugin import GressManInterpolation, mesh_val  # noqa: E402
from interpolation_gg_linear import bilinear_interp  # noqa: E402

__all__ = ["GressManInterpolation", "bilinear_interp", "mesh_val"]
