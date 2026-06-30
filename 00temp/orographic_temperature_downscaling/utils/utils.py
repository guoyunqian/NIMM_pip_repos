#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""meteva_base 网格数据适配工具。"""

from __future__ import annotations

from datetime import timedelta
from typing import Sequence

import numpy as np
import xarray as xr
from cf_units import Unit

import meteva_base as meb

_REQUIRED_DIMS = ("member", "level", "time", "dtime", "lat", "lon")
_DEFAULT_GRID_ATTRS = {
    "units": None,
    "model": None,
    "dtime_units": "hour",
    "level_type": "isobaric",
    "time_type": "UT",
    "time_bounds": [0, 0],
}


def check_for_meb_griddata(
    grid_data: xr.DataArray,
    is_single: bool = False,
    valid_val: Sequence[float] = (-1000.0, 1000.0, np.nan),
) -> xr.DataArray:
    """检查 meteva_base 网格数据并统一格式。

    Parameters
    ----------
    grid_data : xr.DataArray
        meteva_base 格式的输入网格数据。
    is_single : bool, optional
        若为 True，要求有效数据维度压缩后仅包含 `(lat, lon)`。
    valid_val : sequence of float, optional
        合理取值范围的下限、上限以及越界后的替代值。

    Returns
    -------
    xr.DataArray
        经过检查后的网格数据副本，维度顺序已统一，数据类型为 `float32`。
    """
    if not isinstance(grid_data, xr.DataArray):
        raise ValueError("griddata must be xr.DataArray")

    if set(grid_data.dims) != set(_REQUIRED_DIMS):
        raise ValueError(
            "griddata dims must be "
            f"{set(_REQUIRED_DIMS)}, got {set(grid_data.dims)}"
        )

    if is_single and len(grid_data.values.squeeze().shape) > 2:
        raise ValueError("griddata must be a single field over lat/lon")

    normalized = grid_data.copy()
    if normalized.dims != _REQUIRED_DIMS:
        normalized = normalized.transpose(*_REQUIRED_DIMS)

    if normalized.values.dtype != np.float32:
        normalized.values = normalized.values.astype(np.float32)

    lower, upper, fill_value = valid_val
    invalid = (normalized.values < lower) | (normalized.values > upper)
    if invalid.any():
        normalized.values[invalid] = fill_value

    return normalized


def rebuild_to_meb_griddata(
    values: np.ndarray,
    template: xr.DataArray,
    *,
    name: str | None = None,
    units: str | None = None,
    dtype=np.float32,
) -> xr.DataArray:
    """按 meteva_base 网格模板重组装输出结果。

    参数
    ----------
    values : np.ndarray
        待重组装的数值数组。
    template : xr.DataArray
        模板网格数据，用于继承维度顺序、坐标和属性信息。
    name : str, optional
        输出变量名；未指定时继承模板名。
    units : str, optional
        输出单位；未指定时继承模板单位。
    dtype : data-type, default=np.float32
        输出数据类型。

    返回
    -------
    xr.DataArray
        维度顺序为 ``member, level, time, dtime, lat, lon`` 的网格数据。
    """
    if not isinstance(template, xr.DataArray):
        raise TypeError("template 必须为 xarray.DataArray。")

    # 模板必须是完整六维网格，禁止自动补维。
    normalized = check_for_meb_griddata(template)

    target_shape = tuple(normalized.sizes[dim] for dim in _REQUIRED_DIMS)
    value_array = np.asarray(values, dtype=dtype)
    if value_array.shape != target_shape:
        if value_array.size != int(np.prod(target_shape)):
            raise ValueError(
                f"values 形状 {value_array.shape} 无法重组为模板形状 {target_shape}。"
            )
        value_array = value_array.reshape(target_shape)

    # 通过 meteva_base 网格对象组装，避免手工补维和坐标构造误差。
    grid_info = meb.get_grid_of_data(normalized)
    result = meb.grid_data(grid=grid_info, data=value_array)

    if not isinstance(result, xr.DataArray):
        raise TypeError("meb.grid_data 返回结果不是 xarray.DataArray")
    if result.dims != _REQUIRED_DIMS:
        result = result.transpose(*_REQUIRED_DIMS)

    attrs = dict(_DEFAULT_GRID_ATTRS)
    attrs.update(dict(normalized.attrs))
    if units is not None:
        attrs["units"] = units
    result.attrs = attrs
    result.name = name if name is not None else normalized.name
    return result


def check_for_xy_coordinates(grd_list=[], is_time_match=False):
    """检查网格数据列表中的坐标是否一致。"""
    ref = grd_list[0]
    match = True
    for grd in grd_list[1:]:
        if is_time_match is False:
            match = (
                (grd.member.values == ref.member.values).all()
                and (grd.level.values == ref.level.values).all()
                and np.allclose(grd.lat.values, ref.lat.values, atol=0.001)
                and np.allclose(grd.lon.values, ref.lon.values, atol=0.001)
                and match
            )
        else:
            match = (
                (grd.member.values == ref.member.values).all()
                and (grd.level.values == ref.level.values).all()
                and np.allclose(grd.lat.values, ref.lat.values, atol=0.001)
                and np.allclose(grd.lon.values, ref.lon.values, atol=0.001)
                and (
                    (
                        (grd.time.values == ref.time.values).all()
                        and (grd.dtime.values == ref.dtime.values).all()
                    )
                    or _check_time_dtime_same(
                        grd.time.values,
                        grd.dtime.values,
                        ref.time.values,
                        ref.dtime.values,
                    )
                )
                and match
            )
    return match


def _check_time_dtime_same(times0, dtimes0, times1, dtimes1):
    """检查两组 time+dtime 对应的时刻是否一致。"""
    try:
        _ = len(times0)
    except Exception:
        times0 = [times0]
    try:
        _ = len(dtimes0)
    except Exception:
        dtimes0 = [dtimes0]
    try:
        _ = len(times1)
    except Exception:
        times1 = [times1]
    try:
        _ = len(dtimes1)
    except Exception:
        dtimes1 = [dtimes1]

    times0 = [meb.tool.all_type_time_to_datetime(fn) for fn in times0]
    times1 = [meb.tool.all_type_time_to_datetime(fn) for fn in times1]

    alltimes0 = []
    for time0 in times0:
        for dtime0 in dtimes0:
            alltimes0.append(time0 + timedelta(hours=int(dtime0)))

    alltimes1 = []
    for time1 in times1:
        for dtime1 in dtimes1:
            alltimes1.append(time1 + timedelta(hours=int(dtime1)))

    alltimes0 = set(alltimes0)
    alltimes1 = set(alltimes1)
    return alltimes0 & alltimes1 == alltimes0


def convert_units(values: np.ndarray, from_unit: str, to_unit: str) -> np.ndarray:
    """使用 cf_units 进行单位换算；from_unit 与 to_unit 须为 CF 标准写法。"""
    from_unit = (from_unit or "").strip()
    to_unit = (to_unit or "").strip()
    if from_unit == to_unit:
        return np.asarray(values, dtype=np.float32)

    values_f64 = np.asarray(values, dtype=np.float64)
    source_unit = Unit(from_unit)
    target_unit = Unit(to_unit)
    converted = source_unit.convert(values_f64, target_unit)
    return converted.astype(np.float32)


def assert_xy_match(
    reference: xr.DataArray,
    candidate: xr.DataArray,
    candidate_name: str,
) -> None:
    """校验候选场与参考场的空间/时效坐标是否一致。"""
    try:
        matched = check_for_xy_coordinates([reference, candidate], is_time_match=True)
    except Exception as exc:
        raise ValueError(f"{candidate_name}与参考场的坐标一致性检查失败: {exc}") from exc
    if not matched:
        raise ValueError(f"{candidate_name}与参考场的空间/时效坐标不一致")
