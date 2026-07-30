#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""meteva_base 网格数据适配工具。"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import xarray as xr

import meteva_base as meb


def check_for_meb_griddata(
    grd: xr.DataArray,
    is_single: bool = False,
    valid_val: Sequence[float] = (-1000.0, 1000.0, np.nan),
) -> xr.DataArray:
    """检查 meteva_base 网格数据并统一格式。"""
    if not isinstance(grd, xr.DataArray):
        raise ValueError("ERROR: griddata must be xr.DataArray, please check")
    if set(grd.dims) != {"member", "level", "time", "dtime", "lat", "lon"}:
        raise ValueError(
            "ERROR: griddata dims must be set of "
            "{'member', 'level', 'time', 'dtime', 'lat', 'lon'} , please check"
        )
    if is_single and len(grd.values.squeeze().shape) > 2:
        raise ValueError(
            "ERROR: griddata has more effective coordinates than (lat, lon) , please check"
        )
    grd0 = grd.copy()
    if grd0.dims != ("member", "level", "time", "dtime", "lat", "lon"):
        grd0 = grd0.transpose("member", "level", "time", "dtime", "lat", "lon")
    if grd0.values.dtype == np.float64:
        grd0.values = grd0.values.astype(np.float32)
    if ((grd0.values < valid_val[0]) | (grd0.values > valid_val[1])).any():
        print("WARNING: griddata values exceed VALID_VAL, setting to np.NaN")
        grd0.values[(grd0.values < valid_val[0]) | (grd0.values > valid_val[1])] = (
            valid_val[2]
        )
    return grd0


def rebuild_to_meb_griddata(
    values: np.ndarray,
    template: xr.DataArray,
    *,
    name: str | None = None,
    units: str | None = None,
    dtype=np.float32,
) -> xr.DataArray:
    """按 meteva_base 网格模板重组装输出结果。"""
    if not isinstance(template, xr.DataArray):
        raise TypeError("template 必须为 xarray.DataArray。")

    normalized = check_for_meb_griddata(template, valid_val=(-np.inf, np.inf, np.nan))

    target_shape = tuple(
        normalized.sizes[dim]
        for dim in ("member", "level", "time", "dtime", "lat", "lon")
    )
    value_array = np.asarray(values, dtype=dtype)
    if value_array.shape != target_shape:
        if value_array.size != int(np.prod(target_shape)):
            raise ValueError(
                f"values 形状 {value_array.shape} 无法重组为模板形状 {target_shape}。"
            )
        value_array = value_array.reshape(target_shape)

    grid_info = meb.get_grid_of_data(normalized)
    result = meb.grid_data(grid=grid_info, data=value_array)

    if not isinstance(result, xr.DataArray):
        raise TypeError("meb.grid_data 返回结果不是 xarray.DataArray")
    if result.dims != ("member", "level", "time", "dtime", "lat", "lon"):
        result = result.transpose("member", "level", "time", "dtime", "lat", "lon")

    attrs = {
        "units": units,
        "model": None,
        "dtime_units": "hour",
        "level_type": "isobaric",
        "time_type": "UT",
        "time_bounds": [0, 0],
    }
    attrs.update(dict(normalized.attrs))
    if units is not None:
        attrs["units"] = units
    result.attrs = attrs
    result.name = name if name is not None else normalized.name
    return result


def spatial_coords_match(*arrays: xr.DataArray, atol: float = 1.0e-8) -> bool:
    """判断多个 DataArray 的 lat/lon 空间坐标是否一致。"""
    if not arrays:
        return True
    ref = arrays[0]
    for other in arrays[1:]:
        if ref.sizes.get("lat") != other.sizes.get("lat"):
            return False
        if ref.sizes.get("lon") != other.sizes.get("lon"):
            return False
        if not np.allclose(ref.coords["lat"].values, other.coords["lat"].values, atol=atol):
            return False
        if not np.allclose(ref.coords["lon"].values, other.coords["lon"].values, atol=atol):
            return False
    return True
