#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""neighbourhood_probability_processing CLI 示例脚本的 nc 读取辅助。"""

from __future__ import annotations

import xarray as xr


def read_mask_or_weights_from_nc(path: str) -> xr.DataArray:
    """读取掩码或权重 nc 文件中的主变量（支持非六维数据）。"""
    try:
        dataset = xr.open_dataset(path, decode_timedelta=False)
    except Exception as exc:
        raise RuntimeError(f"Failed to read input file: {path}") from exc

    for name, data_array in dataset.data_vars.items():
        if (
            data_array.ndim >= 2
            and "bnds" not in name
            and name != "lambert_azimuthal_equal_area"
        ):
            return data_array

    raise ValueError(f"No usable mask/weights variable found in {path}")
