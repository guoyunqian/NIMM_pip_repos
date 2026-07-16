#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""echo_class 通用网格辅助函数。"""

from __future__ import annotations

import cf_units
import numpy as np
import xarray as xr

from radar_echo_classification.utils.utils import (
    build_griddata_like,
    check_for_meb_griddata,
)

EARTH_METRES_PER_DEGREE = 111195.0


def _unit_scale_to_meters(unit_value: str | None):
    """根据单位字符串返回到米的缩放系数。"""
    if unit_value is None:
        return None

    try:
        src_unit = cf_units.Unit(str(unit_value).strip())
        dst_unit = cf_units.Unit("m")
        return float(src_unit.convert(1.0, dst_unit))
    except Exception:
        return None


def get_xy_in_meters(grid_data: xr.DataArray):
    """
    获取米制 x/y 坐标：
    1. lon/lat 维坐标本身已是米或千米时直接换算（投影轴仅改名为 lat/lon）。
    2. 若存在 ``grid_mapping_attrs``，则尝试读取附属平面坐标 x/y
       （或 projection_*）。
    3. 否则回退到局地经纬度近似。
    """
    lon = np.asarray(grid_data.lon.values, dtype=np.float64)
    lat = np.asarray(grid_data.lat.values, dtype=np.float64)

    lon_unit = getattr(grid_data.lon, "attrs", {}).get("units")
    lat_unit = getattr(grid_data.lat, "attrs", {}).get("units")
    lon_scale = _unit_scale_to_meters(lon_unit)
    lat_scale = _unit_scale_to_meters(lat_unit)
    if lon_scale is not None and lat_scale is not None:
        return lon * lon_scale, lat * lat_scale

    if grid_data.attrs.get("grid_mapping_attrs"):
        for x_name, y_name in (
            ("x", "y"),
            ("projection_x_coordinate", "projection_y_coordinate"),
        ):
            if x_name in grid_data.coords and y_name in grid_data.coords:
                x_coord = grid_data.coords[x_name]
                y_coord = grid_data.coords[y_name]
                x_scale = _unit_scale_to_meters(getattr(x_coord, "attrs", {}).get("units"))
                y_scale = _unit_scale_to_meters(getattr(y_coord, "attrs", {}).get("units"))
                if x_scale is not None and y_scale is not None:
                    x_m = np.asarray(x_coord.values, dtype=np.float64) * x_scale
                    y_m = np.asarray(y_coord.values, dtype=np.float64) * y_scale
                    return x_m, y_m

    lat_mean = float(np.nanmean(lat))
    x = (lon - lon[0]) * EARTH_METRES_PER_DEGREE * np.cos(np.deg2rad(lat_mean))
    y = (lat - lat[0]) * EARTH_METRES_PER_DEGREE
    return x, y


def _get_dx_dy(grid_data: xr.DataArray, dx=None, dy=None):
    """获取水平分辨率，单位米。"""
    x_m, y_m = get_xy_in_meters(grid_data)

    if dx is None:
        if x_m.size < 2:
            raise ValueError("x/lon dimension must contain at least two points when dx is None")
        _warn_if_nonuniform_spacing(x_m, axis_name="x/lon")
        dx = np.mean(np.abs(np.diff(x_m)))

    if dy is None:
        if y_m.size < 2:
            raise ValueError("y/lat dimension must contain at least two points when dy is None")
        _warn_if_nonuniform_spacing(y_m, axis_name="y/lat")
        dy = np.mean(np.abs(np.diff(y_m)))

    return float(dx), float(dy)


def _warn_if_nonuniform_spacing(coord_1d: np.ndarray, axis_name: str, rel_tol: float = 0.05):
    """
    对一维坐标做等距性检查。
    原算法默认输入为近似等距笛卡尔网格，若明显不等距则给出告警。
    """
    diffs = np.abs(np.diff(np.asarray(coord_1d, dtype=np.float64)))
    diffs = diffs[np.isfinite(diffs)]
    if diffs.size == 0:
        return
    baseline = float(np.nanmedian(diffs))
    if baseline <= 0.0:
        return
    rel_spread = float(np.nanmax(np.abs(diffs - baseline)) / baseline)
    if rel_spread > rel_tol:
        raise ValueError(
            f"{axis_name} coordinate spacing is non-uniform "
            f"(max relative spread={rel_spread:.3f}); "
            "echo_class algorithms require approximately Cartesian/equidistant grid."
        )


def _check_single_context(grid_data: xr.DataArray, valid_val=(-1000.0, 1000.0, np.nan)) -> xr.DataArray:
    """检查输入网格是否只有一个 member/time/dtime。"""
    normalized = check_for_meb_griddata(
        grid_data,
        is_single=False,
        valid_val=valid_val,
    )

    if normalized.member.size != 1:
        raise ValueError("griddata member dimension must contain exactly one value")
    if normalized.time.size != 1:
        raise ValueError("griddata time dimension must contain exactly one value")
    if normalized.dtime.size != 1:
        raise ValueError("griddata dtime dimension must contain exactly one value")

    return normalized


def _build_level_result(
    template: xr.DataArray,
    data_2d: np.ndarray,
    name: str,
    standard_name: str,
    long_name: str,
    valid_min: int,
    valid_max: int,
    extra_attrs=None,
) -> xr.DataArray:
    """将二维分类结果封装为 meteva_base 网格数据。"""
    if extra_attrs is None:
        extra_attrs = {}

    data_6d = np.asarray(data_2d, dtype=np.float32)[None, None, None, None, :, :]
    result = build_griddata_like(template, data_6d)
    result.name = name
    result.attrs["standard_name"] = standard_name
    result.attrs["long_name"] = long_name
    result.attrs["valid_min"] = valid_min
    result.attrs["valid_max"] = valid_max
    result.attrs.update(extra_attrs)

    return result


def _flatten_to_scan(grid_data: xr.DataArray):
    """将六维网格展平为算法计算使用的二维数组。"""

    # 最后一维保留为“距离/网格点”方向，
    # 其余维统一压平，便于复用原算法。
    values = np.ma.masked_invalid(np.asarray(grid_data.values, dtype=np.float32))
    scan = values.reshape(-1, values.shape[-1])
    return scan


def _build_full_result(
    template: xr.DataArray,
    data_scan,
    original_shape,
    name: str,
    long_name: str,
    extra_attrs=None,
):
    """将展平计算结果恢复为完整网格。"""
    if extra_attrs is None:
        extra_attrs = {}

    # 原算法可能返回 masked array，
    # 这里统一转回普通 ndarray + nan，
    # 再恢复为 meteva_base 使用的六维网格形状。
    if np.ma.isMaskedArray(data_scan):
        restored = np.ma.filled(data_scan, np.nan).reshape(original_shape)
    else:
        restored = np.asarray(data_scan).reshape(original_shape)

    result = build_griddata_like(template, restored.astype(np.float32, copy=False))
    result.name = name
    result.attrs["long_name"] = long_name
    result.attrs.update(extra_attrs)

    return result
