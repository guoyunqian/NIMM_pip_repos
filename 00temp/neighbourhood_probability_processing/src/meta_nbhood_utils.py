#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""nbhood CLI 编排所需的辅助函数。"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
import xarray as xr


def _as_iterable(
    value: Union[str, float, int, Sequence[Union[str, float, int]]]
) -> List[Union[str, float, int]]:
    """将单值或序列统一转换为列表（字符串按单值处理）。"""
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def radius_by_lead_time(
    radii: Union[float, Sequence[Union[float]]],
    lead_times: Optional[Union[int, Sequence[Union[int]]]] = None,
) -> Tuple[Union[float, List[float]], Optional[List[int]]]:
    """解析 radii / lead_times 参数并执行一致性检查。"""
    radii_list = [float(item) for item in _as_iterable(radii)]
    lead_list = None if lead_times is None else [int(item) for item in _as_iterable(lead_times)]

    if lead_list is None:
        if len(radii_list) != 1:
            raise ValueError("提供多个 radii 时必须同时提供等长的 lead_times。")
        return float(radii_list[0]), None

    if len(radii_list) != len(lead_list):
        raise ValueError("radii 与 lead_times 长度不一致。")
    return radii_list, lead_list


def deg_to_complex(
    angle_deg: Union[np.ndarray, float], radius: Union[np.ndarray, float] = 1.0
) -> Union[np.ndarray, complex]:
    """角度转复数。"""
    angle_rad = np.deg2rad(angle_deg)
    real = radius * np.cos(angle_rad)
    imag = radius * np.sin(angle_rad)
    return real + 1j * imag


def complex_to_deg(complex_in: np.ndarray) -> np.ndarray:
    """复数转角度（范围 [0, 360)）。"""
    if not isinstance(complex_in, np.ndarray):
        raise TypeError(f"输入必须是 numpy.ndarray，当前为 {type(complex_in)}")
    angle = np.angle(complex_in, deg=True)
    return np.mod(np.float32(angle), 360.0).astype(np.float32)


def _distance_unit_scale(unit: Optional[str]) -> float:
    """距离单位转米系数。"""
    text = "" if unit is None else str(unit).strip().lower()
    if text in ("", "m", "metre", "metres", "meter", "meters"):
        return 1.0
    if text in ("km", "kilometre", "kilometres", "kilometer", "kilometers"):
        return 1000.0
    if "degree" in text:
        # 与主算法一致：角度坐标使用局地近似换算，不做重投影重采样。
        return 111195.0
    raise ValueError(f"不支持的空间坐标单位: {unit}")


def _grid_spacing_from_spatial_coords(data: xr.DataArray) -> Tuple[float, float]:
    """从最后两个空间坐标估算网格间距（米）。"""
    if data.ndim < 2:
        raise ValueError("输入至少需要二维空间网格。")
    y_name, x_name = data.dims[-2], data.dims[-1]
    if y_name not in data.coords or x_name not in data.coords:
        raise ValueError("最后两个维度必须有同名一维坐标。")

    y = np.asarray(data.coords[y_name].values, dtype=np.float64)
    x = np.asarray(data.coords[x_name].values, dtype=np.float64)
    if y.size < 2 or x.size < 2:
        raise ValueError("空间坐标长度不足，无法计算网格间距。")

    y_diff = np.abs(np.diff(y))
    x_diff = np.abs(np.diff(x))
    y_step = float(np.mean(y_diff))
    x_step = float(np.mean(x_diff))
    if not np.allclose(y_diff, y_step, rtol=1.0e-5, atol=0.0):
        raise ValueError(f"{y_name} 坐标不是等间距网格。")
    if not np.allclose(x_diff, x_step, rtol=1.0e-5, atol=0.0):
        raise ValueError(f"{x_name} 坐标不是等间距网格。")

    y_unit = data.coords[y_name].attrs.get("units")
    x_unit = data.coords[x_name].attrs.get("units")
    y_scale = _distance_unit_scale(y_unit)
    x_scale = _distance_unit_scale(x_unit)
    y_spacing = y_step * y_scale
    x_spacing = x_step * x_scale
    return y_spacing, x_spacing


def remove_dataarray_halo(data: xr.DataArray, halo_radius: float) -> xr.DataArray:
    """按 halo 半径裁剪 DataArray 外圈网格。"""
    if not isinstance(data, xr.DataArray):
        raise TypeError("remove_dataarray_halo 仅支持 xarray.DataArray 输入。")
    halo_radius = float(halo_radius)
    if halo_radius <= 0:
        raise ValueError("halo_radius 必须为正数。")

    y_spacing, x_spacing = _grid_spacing_from_spatial_coords(data)
    halo_y = int(halo_radius / y_spacing)
    halo_x = int(halo_radius / x_spacing)
    if halo_y <= 0 or halo_x <= 0:
        raise ValueError(
            f"halo_radius={halo_radius}m 对应裁剪网格数为 0（x={halo_x}, y={halo_y}）。"
        )

    y_name, x_name = data.dims[-2], data.dims[-1]
    y_size = data.sizes[y_name]
    x_size = data.sizes[x_name]
    if (2 * halo_y) >= y_size or (2 * halo_x) >= x_size:
        raise ValueError("halo_radius 过大，裁剪后无有效区域。")

    return data.isel(
        {
            y_name: slice(halo_y, y_size - halo_y),
            x_name: slice(halo_x, x_size - halo_x),
        }
    )
