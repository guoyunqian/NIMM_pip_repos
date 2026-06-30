#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""meteva_base 网格数据适配工具。"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Sequence

import cf_units
import numpy as np
import xarray as xr

import meteva_base as meb

_REQUIRED_DIMS = ("member", "level", "time", "dtime", "lat", "lon")
EARTH_METRES_PER_DEGREE = 111195.0
# CF 惯例缺测填充值；避免 meteva ``write_griddata_to_nc`` 的 int32 缩放把 NaN 写成约 -2147483.6
_CF_NETCDF_FILL = np.float32(9.969209968386869e36)


def check_for_meb_griddata(
    grid_data: xr.DataArray,
    is_single: bool = False,
    allow_multi_level: bool = False,
    valid_val: Sequence[float] = (-1000.0, 1000.0, np.nan),
) -> xr.DataArray:
    """检查 meteva_base 网格数据并统一格式。

    Parameters
    ----------
    grid_data : xr.DataArray
        meteva_base 格式的输入网格数据。
    is_single : bool, optional
        若为 True，要求有效数据维度压缩后仅包含 `(lat, lon)`。
    allow_multi_level : bool, optional
        若为 True，允许 ``level`` 维大于 1（多层仰角叠在同一 lat/lon 网格），
        要求 ``member`` 维长度为 1。
    valid_val : sequence of float, optional
        合理取值范围的下限、上限以及越界后的替代值。

    Returns
    -------
    xr.DataArray
        经过检查后的网格数据副本，维度顺序已统一，数据类型为 `float32`。
    """
    if not isinstance(grid_data, xr.DataArray):
        raise ValueError("griddata must be xr.DataArray")

    if is_single and allow_multi_level:
        raise ValueError("is_single and allow_multi_level cannot both be True")

    if set(grid_data.dims) != set(_REQUIRED_DIMS):
        raise ValueError(
            "griddata dims must be "
            f"{set(_REQUIRED_DIMS)}, got {set(grid_data.dims)}"
        )

    if is_single and len(grid_data.values.squeeze().shape) > 2:
        raise ValueError("griddata must be a single field over lat/lon")

    if allow_multi_level:
        if int(grid_data.sizes.get("member", 0)) != 1:
            raise ValueError("multi-level grid must have member dimension size 1")
        if int(grid_data.sizes.get("level", 0)) < 1:
            raise ValueError("multi-level grid must have at least one level")
        if int(grid_data.sizes.get("lat", 0)) < 1 or int(grid_data.sizes.get("lon", 0)) < 1:
            raise ValueError("grid must have lat and lon coordinates")

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


def _check_same_horiz_coordinates(grd_list: list[xr.DataArray]) -> bool:
    """检查多层网格的水平坐标是否一致（不比较 ``level``）。

    用于体扫拼接：各仰角单层网格的 ``level`` 为各自仰角，本就不相同；
    完整维一致性仍由 :func:`check_for_xy_coordinates` 负责（如 QPE 多输入对齐）。
    """
    if not grd_list:
        return False
    ref = grd_list[0]
    for grd in grd_list[1:]:
        if not (
            (grd.member.values == ref.member.values).all()
            and np.allclose(grd.lat.values, ref.lat.values, atol=0.001)
            and np.allclose(grd.lon.values, ref.lon.values, atol=0.001)
        ):
            return False
    return True


def build_griddata_like(template: xr.DataArray, data: np.ndarray) -> xr.DataArray:
    """根据模板网格信息重新组装 meteva_base 网格数据。"""
    grid_info = meb.get_grid_of_data(template)
    return meb.grid_data(grid=grid_info, data=data.astype(np.float32, copy=False))


def build_sweep_level_coordinates(
    radar,
    *,
    range_ref: str = "max",
    range_m: float | None = None,
) -> dict:
    """为体扫各仰角构建 meteva ``level`` 坐标及元数据。

    ``level_list`` 使用真实仰角（度，来自 ``fixed_angle``）；``height_m`` 为每层
    在参考距离处的标称波束高度（米，海拔）。

    Parameters
    ----------
    radar : Radar
        Py-ART 雷达对象。
    range_ref : str, optional
        标称高度所用距离：``max``（最大库）、``mid``（中间库）。
    range_m : float or None, optional
        若给定，则所有仰角共用该距离（米），忽略 ``range_ref``。

    Returns
    -------
    dict
        ``level_list``：供 ``meb.grid(..., level_list=...)``；
        ``elevation_deg``、``height_m``：长度 ``nsweeps`` 的数组；
        ``height_reference``：高度公式说明。
    """
    nsweeps = int(radar.nsweeps)
    fixed = np.asarray(radar.fixed_angle["data"], dtype=np.float64).ravel()
    if fixed.size != nsweeps:
        fixed = np.array(
            [float(np.mean(radar.get_elevation(i))) for i in range(nsweeps)],
            dtype=np.float64,
        )

    site_alt = float(np.asarray(radar.altitude["data"], dtype=np.float64).ravel()[0])
    gate_ranges = np.asarray(radar.range["data"], dtype=np.float64)
    if gate_ranges.size == 0:
        raise ValueError("radar.range is empty")

    if range_m is not None:
        ref_range = float(range_m)
        height_reference = f"site_alt + {ref_range:g}*sin(elevation), range_m fixed"
    elif range_ref == "max":
        ref_range = float(gate_ranges[-1])
        height_reference = "site_alt + max_range*sin(elevation)"
    elif range_ref == "mid":
        ref_range = float(gate_ranges[gate_ranges.size // 2])
        height_reference = "site_alt + mid_range*sin(elevation)"
    else:
        raise ValueError("range_ref must be 'max' or 'mid' when range_m is None")

    elevation_deg = fixed.astype(np.float64, copy=False)
    height_m = site_alt + ref_range * np.sin(np.deg2rad(elevation_deg))

    return {
        "level_list": [float(v) for v in elevation_deg],
        "elevation_deg": elevation_deg,
        "height_m": height_m.astype(np.float64),
        "height_reference": height_reference,
        "range_m_used": ref_range,
        "site_alt_m": site_alt,
    }


def attach_sweep_level_metadata(
    grid_data: xr.DataArray,
    level_coords: dict,
) -> xr.DataArray:
    """在多层 meteva 网格上写入仰角/高度元数据（``level`` 坐标为仰角，度）。"""
    normalized = check_for_meb_griddata(grid_data, allow_multi_level=True)
    elevation_deg = np.asarray(level_coords["elevation_deg"], dtype=np.float64).ravel()
    height_m = np.asarray(level_coords["height_m"], dtype=np.float64).ravel()
    if elevation_deg.size != int(normalized.sizes["level"]):
        raise ValueError(
            "elevation_deg length must match grid level size: "
            f"{elevation_deg.size} vs {int(normalized.sizes['level'])}"
        )
    if height_m.size != elevation_deg.size:
        raise ValueError("height_m must have the same length as elevation_deg")

    out = normalized.copy()
    out.attrs["level_coordinate"] = "elevation_deg"
    out.attrs["elevation_deg"] = [float(v) for v in elevation_deg]
    out.attrs["height_m"] = [float(v) for v in height_m]
    if "height_reference" in level_coords:
        out.attrs["height_reference"] = str(level_coords["height_reference"])
    if "range_m_used" in level_coords:
        out.attrs["range_m_used"] = float(level_coords["range_m_used"])
    if "site_alt_m" in level_coords:
        out.attrs["site_alt_m"] = float(level_coords["site_alt_m"])

    if "level" in out.coords:
        out.coords["level"].attrs["units"] = "degrees"
        out.coords["level"].attrs["standard_name"] = "elevation_angle"
        out.coords["level"].attrs["long_name"] = "radar fixed angle"
    return out


def _sanitize_grid_values_for_nc(values: np.ndarray) -> np.ndarray:
    """将 NaN/异常极值统一为 NetCDF 缺测填充值（float32）。"""
    arr = np.asarray(values, dtype=np.float32).copy()
    invalid = ~np.isfinite(arr)
    invalid |= np.abs(arr) >= np.float32(1e19)
    invalid |= arr <= np.float32(-1e6)
    # 读回 meb int32 缩放文件时常见的伪缺测
    invalid |= np.abs(arr + 2147483.648) < np.float32(1.0)
    arr[invalid] = _CF_NETCDF_FILL
    return arr


def save_meteva_grid_to_netcdf(
    grid_data: xr.DataArray,
    output_path=None,
    *,
    save_path=None,
    compression: bool = True,
    show: bool = False,
) -> Path:
    """保存 meteva 网格为 NetCDF（float32 + CF ``_FillValue``）。

    不使用 ``meteva_base.write_griddata_to_nc`` 默认的 int32×scale_factor 编码，
    否则 NaN 会变成 ``-2147483648``，Panoply 等工具显示为约 ``-2147483.6``。
    """
    if output_path is None:
        output_path = save_path
    if output_path is None:
        raise TypeError("save_meteva_grid_to_netcdf requires output_path or save_path")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    normalized = check_for_meb_griddata(grid_data, allow_multi_level=True)
    var_name = normalized.name or "data0"
    out = normalized.copy()
    out.values = _sanitize_grid_values_for_nc(out.values)
    if not out.attrs.get("units"):
        out.attrs["units"] = ""
    out.attrs.pop("_FillValue", None)
    out.attrs.pop("missing_value", None)

    ds = out.to_dataset(name=var_name)
    encoding: dict = {}
    for v in ds.data_vars:
        ds[v].attrs.pop("_FillValue", None)
        ds[v].attrs.pop("missing_value", None)
        enc = {
            "dtype": "float32",
            "_FillValue": _CF_NETCDF_FILL,
            "missing_value": _CF_NETCDF_FILL,
        }
        if compression:
            enc["zlib"] = True
            enc["complevel"] = 4
        encoding[v] = enc

    ds.to_netcdf(str(output_path), encoding=encoding)
    if show:
        print(f"saved {output_path}")
    return output_path


def stack_gridded_sweeps(
    sweep_grids: list[xr.DataArray],
    level_coords: dict,
) -> xr.DataArray:
    """将各仰角单层 meteva 网格沿 ``level`` 维拼成体扫网格。"""
    if not sweep_grids:
        raise ValueError("sweep_grids must not be empty")
    if not _check_same_horiz_coordinates(sweep_grids):
        raise ValueError(
            "sweep_grids must share the same member/lat/lon coordinates "
            "(level may differ per sweep before stacking)"
        )

    nlevel = len(sweep_grids)
    if nlevel != len(level_coords["level_list"]):
        raise ValueError("sweep_grids length must match level_list length")

    parts = []
    for grid in sweep_grids:
        part = check_for_meb_griddata(grid, allow_multi_level=True)
        if int(part.sizes["level"]) != 1:
            raise ValueError("each sweep grid must have level dimension size 1")
        parts.append(part.values.astype(np.float32, copy=False))

    stacked_values = np.concatenate(parts, axis=1)
    template = check_for_meb_griddata(sweep_grids[0], allow_multi_level=True)
    base_grid = meb.get_grid_of_data(template)
    dtime_list = getattr(base_grid, "dtime_list", None)
    if dtime_list is None:
        dtime_list = list(base_grid.dtimes)
    member_list = getattr(base_grid, "member_list", None)
    if member_list is None:
        member_list = list(base_grid.members)

    volume_grid = meb.grid(
        base_grid.glon,
        base_grid.glat,
        gtime=base_grid.gtime,
        dtime_list=dtime_list,
        level_list=list(level_coords["level_list"]),
        member_list=member_list,
        level_type_attr="elevation",
    )
    volume = meb.grid_data(volume_grid, data=stacked_values)
    return attach_sweep_level_metadata(volume, level_coords)


def select_grid_level(grid_data: xr.DataArray, level_index: int = 0) -> xr.DataArray:
    """从 meteva 网格中取出指定 ``level`` 层（例如某一仰角 PPI）。

    多层体扫可先各仰角网格化并写入 ``level`` 维，QPE 对全体层计算后，
    用本函数取单层结果与 Py-ART 单扫门点产品对比。
    """
    normalized = check_for_meb_griddata(grid_data, allow_multi_level=True)
    nlevel = int(normalized.sizes["level"])
    idx = int(level_index)
    if idx < 0 or idx >= nlevel:
        raise IndexError(f"level_index {idx} out of range for level size {nlevel}")
    return normalized.isel(level=[idx])


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
    1. lon/lat 已是米或千米时直接换算。
    2. 若存在 grid_mapping，则尝试读取投影平面坐标。
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

    if grid_data.attrs.get("grid_mapping"):
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