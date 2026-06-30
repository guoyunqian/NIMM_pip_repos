#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""meteva_base 网格数据适配工具。"""

from __future__ import annotations

from datetime import timedelta
from typing import Sequence

import cf_units
import numpy as np
import xarray as xr
from scipy.interpolate import griddata

import meteva_base as meb

_REQUIRED_DIMS = ("member", "level", "time", "dtime", "lat", "lon")
EARTH_METRES_PER_DEGREE = 111195.0
EARTH_RADIUS_METERS = 6370997.0


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


def build_griddata_like(template: xr.DataArray, data: np.ndarray) -> xr.DataArray:
    """根据模板网格信息重新组装 meteva_base 网格数据。"""
    grid_info = meb.get_grid_of_data(template)
    return meb.grid_data(grid=grid_info, data=data.astype(np.float32, copy=False))


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


def _axis_to_meters(values: np.ndarray, unit_value: str | None):
    """Convert an axis to meters when the unit is known."""
    scale = _unit_scale_to_meters(unit_value)
    if scale is None:
        return None
    return np.asarray(values, dtype=np.float64) * scale


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


def polar_to_lonlat(
    radar_lon: float,
    radar_lat: float,
    azimuth_deg,
    range_m,
    elevation_deg: float = 0.0,
):
    """将极坐标门点位置转换为经纬度门点坐标。

    Notes
    -----
    - 该函数仅执行坐标变换，不做插值或规则网格重采样。
    - 返回结果仍与原始 ``azimuth x range`` 门点拓扑一一对应。
    - 参考 Py-ART 的思路，先计算雷达本地平面坐标，再做球面
      azimuthal equidistant 反算得到经纬度。

    Parameters
    ----------
    radar_lon, radar_lat : float
        雷达站点经纬度，单位为度。
    azimuth_deg : array-like
        方位角序列，单位为度。通常对应当前 ``grid_data`` 的伪 ``lat`` 维。
    range_m : array-like
        径距序列，单位为米。通常对应当前 ``grid_data`` 的伪 ``lon`` 维。
    elevation_deg : float, optional
        仰角，单位为度。当前仅用于将径距投影到地平面；若不关心仰角影响，
        可保持默认值 0.0。

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(gate_lon, gate_lat)``，二者均为 ``(nazimuth, nrange)`` 的二维数组。
    """
    azimuth = np.asarray(azimuth_deg, dtype=np.float64)
    radial_range = np.asarray(range_m, dtype=np.float64)

    if azimuth.ndim != 1:
        raise ValueError("azimuth_deg must be a 1D sequence")
    if radial_range.ndim != 1:
        raise ValueError("range_m must be a 1D sequence")

    azimuth_rad = np.deg2rad(azimuth)
    elevation_rad = np.deg2rad(float(elevation_deg))

    range_2d = np.broadcast_to(radial_range.reshape(1, -1), (azimuth.size, radial_range.size))
    azimuth_2d = np.broadcast_to(azimuth_rad.reshape(-1, 1), range_2d.shape)

    ground_range = range_2d * np.cos(elevation_rad)
    x = ground_range * np.sin(azimuth_2d)
    y = ground_range * np.cos(azimuth_2d)

    lon0 = np.deg2rad(float(radar_lon))
    lat0 = np.deg2rad(float(radar_lat))
    rho = np.sqrt(x * x + y * y)
    c = rho / EARTH_RADIUS_METERS

    sin_c = np.sin(c)
    cos_c = np.cos(c)
    sin_lat0 = np.sin(lat0)
    cos_lat0 = np.cos(lat0)

    gate_lat_rad = np.empty_like(rho, dtype=np.float64)
    gate_lon_rad = np.empty_like(rho, dtype=np.float64)

    zero_mask = rho == 0.0
    nonzero_mask = ~zero_mask

    gate_lat_rad[zero_mask] = lat0
    gate_lon_rad[zero_mask] = lon0

    if np.any(nonzero_mask):
        rho_nz = rho[nonzero_mask]
        x_nz = x[nonzero_mask]
        y_nz = y[nonzero_mask]
        sin_c_nz = sin_c[nonzero_mask]
        cos_c_nz = cos_c[nonzero_mask]

        gate_lat_rad[nonzero_mask] = np.arcsin(
            cos_c_nz * sin_lat0 + (y_nz * sin_c_nz * cos_lat0 / rho_nz)
        )
        gate_lon_rad[nonzero_mask] = lon0 + np.arctan2(
            x_nz * sin_c_nz,
            rho_nz * cos_lat0 * cos_c_nz - y_nz * sin_lat0 * sin_c_nz,
        )

    gate_lon = np.rad2deg(gate_lon_rad)
    gate_lat = np.rad2deg(gate_lat_rad)
    return gate_lon, gate_lat


def attach_gate_lonlat(
    grid_data: xr.DataArray,
    radar_lon: float,
    radar_lat: float,
    azimuth_deg=None,
    range_m=None,
    elevation_deg: float = 0.0,
    gate_lon_name: str = "gate_lon",
    gate_lat_name: str = "gate_lat",
) -> xr.DataArray:
    """为 meteva_base ``grid_data`` 附加真实门点经纬度坐标。

    Parameters
    ----------
    grid_data : xr.DataArray
        输入网格。其最后两个维度仍保持原始极坐标门点拓扑。
    radar_lon, radar_lat : float
        雷达站点经纬度，单位为度。
    azimuth_deg, range_m : array-like or None, optional
        方位角与径距的一维序列。若未传入，则默认分别使用
        ``grid_data.lat`` 与 ``grid_data.lon`` 坐标值。
    elevation_deg : float, optional
        仰角，单位为度。
    gate_lon_name, gate_lat_name : str, optional
        附加到结果中的二维坐标名。

    Returns
    -------
    xr.DataArray
        附加二维 ``gate_lon`` / ``gate_lat`` 坐标后的副本。
    """
    normalized = check_for_meb_griddata(grid_data, is_single=False)
    azimuth = normalized.lat.values if azimuth_deg is None else azimuth_deg
    if range_m is None:
        range_unit = (
            normalized.attrs.get("range_units")
            or getattr(normalized.lon, "attrs", {}).get("units")
            or normalized.attrs.get("lon_units")
        )
        radial_range = _axis_to_meters(normalized.lon.values, range_unit)
        if radial_range is None:
            range_scale = normalized.attrs.get("range_scale_to_m")
            try:
                range_scale = float(range_scale) if range_scale is not None else None
            except (TypeError, ValueError):
                range_scale = None
            if range_scale is not None and np.isfinite(range_scale):
                radial_range = np.asarray(normalized.lon.values, dtype=np.float64) * range_scale
            else:
                radial_range = normalized.lon.values
    else:
        radial_range = range_m

    gate_lon, gate_lat = polar_to_lonlat(
        radar_lon=radar_lon,
        radar_lat=radar_lat,
        azimuth_deg=azimuth,
        range_m=radial_range,
        elevation_deg=elevation_deg,
    )

    attached = normalized.copy()
    attached = attached.assign_coords(
        {
            gate_lon_name: (("lat", "lon"), gate_lon.astype(np.float64, copy=False)),
            gate_lat_name: (("lat", "lon"), gate_lat.astype(np.float64, copy=False)),
        }
    )
    return attached


def remap_gate_data_to_latlon_grid(
    values,
    gate_lon,
    gate_lat,
    target_lon,
    target_lat,
    method: str = "nearest",
    missing_value=None,
    fill_value=np.nan,
) -> np.ndarray:
    """将门点场插值到规则经纬网格。

    Notes
    -----
    - 输入 ``values`` 与 ``gate_lon`` / ``gate_lat`` 必须一一对应。
    - ``target_lon`` 与 ``target_lat`` 需为一维规则坐标轴。
    - 当前封装基于 ``scipy.interpolate.griddata``，适合作为通用后处理。

    Parameters
    ----------
    values : array-like
        原始门点二维数据，形状应与 ``gate_lon`` / ``gate_lat`` 相同。
    gate_lon, gate_lat : array-like
        每个门点对应的二维经纬度坐标。
    target_lon, target_lat : array-like
        目标规则经纬网格的一维经纬度轴。
    method : {"nearest", "linear"}, optional
        插值方法。默认使用 ``nearest``，更稳妥且不易在边界产生缺口。
    fill_value : float, optional
        目标网格超出插值有效范围时的填充值。

    Returns
    -------
    np.ndarray
        插值后的二维规则经纬网格数据，形状为
        ``(len(target_lat), len(target_lon))``。
    """
    supported_methods = {"nearest", "linear"}
    if method not in supported_methods:
        raise ValueError(f"method must be one of {supported_methods}, got {method!r}")

    if np.ma.isMaskedArray(values):
        values_2d = np.asarray(np.ma.filled(values, np.nan), dtype=np.float64)
    else:
        values_2d = np.asarray(values, dtype=np.float64)
    gate_lon_2d = np.asarray(gate_lon, dtype=np.float64)
    gate_lat_2d = np.asarray(gate_lat, dtype=np.float64)
    target_lon_1d = np.asarray(target_lon, dtype=np.float64)
    target_lat_1d = np.asarray(target_lat, dtype=np.float64)

    if values_2d.shape != gate_lon_2d.shape or values_2d.shape != gate_lat_2d.shape:
        raise ValueError("values, gate_lon, and gate_lat must have the same 2D shape")
    if target_lon_1d.ndim != 1 or target_lat_1d.ndim != 1:
        raise ValueError("target_lon and target_lat must be 1D sequences")

    valid_mask = (
        np.isfinite(values_2d)
        & np.isfinite(gate_lon_2d)
        & np.isfinite(gate_lat_2d)
    )
    try:
        fill_value_f = float(fill_value)
    except (TypeError, ValueError):
        fill_value_f = None
    if fill_value_f is not None and np.isfinite(fill_value_f):
        valid_mask &= ~np.isclose(values_2d, fill_value_f)

    try:
        missing_value_f = float(missing_value) if missing_value is not None else None
    except (TypeError, ValueError):
        missing_value_f = None
    if missing_value_f is not None and np.isfinite(missing_value_f):
        valid_mask &= ~np.isclose(values_2d, missing_value_f)
    if not np.any(valid_mask):
        return np.full(
            (target_lat_1d.size, target_lon_1d.size),
            fill_value,
            dtype=np.float32,
        )

    points = np.column_stack((gate_lon_2d[valid_mask], gate_lat_2d[valid_mask]))
    source_values = values_2d[valid_mask]
    target_lon_2d, target_lat_2d = np.meshgrid(target_lon_1d, target_lat_1d)

    remapped = griddata(
        points=points,
        values=source_values,
        xi=(target_lon_2d, target_lat_2d),
        method=method,
        fill_value=fill_value,
    )
    return np.asarray(remapped, dtype=np.float32)


def build_latlon_griddata_from_template(
    template: xr.DataArray,
    data_2d: np.ndarray,
    target_lon,
    target_lat,
    data_name: str | None = None,
) -> xr.DataArray:
    """基于模板的非空间维信息重建规则经纬网格 ``grid_data``。

    Parameters
    ----------
    template : xr.DataArray
        提供 member/level/time/dtime 等元信息的模板网格。
    data_2d : np.ndarray
        目标规则经纬网格上的二维数据，形状必须为
        ``(len(target_lat), len(target_lon))``。
    target_lon, target_lat : array-like
        目标规则经纬坐标轴。
    data_name : str or None, optional
        返回结果的数据名；未传入时继承模板名称。

    Returns
    -------
    xr.DataArray
        新的规则经纬网格 ``grid_data``。
    """
    normalized = check_for_meb_griddata(template, is_single=False)
    lon_axis = np.asarray(target_lon, dtype=np.float64)
    lat_axis = np.asarray(target_lat, dtype=np.float64)
    values_2d = np.asarray(data_2d, dtype=np.float32)

    expected_shape = (lat_axis.size, lon_axis.size)
    if values_2d.shape != expected_shape:
        raise ValueError(
            f"data_2d shape must be {expected_shape}, got {values_2d.shape}"
        )

    coords = {
        "member": normalized.member.values,
        "level": normalized.level.values,
        "time": normalized.time.values,
        "dtime": normalized.dtime.values,
        "lat": lat_axis,
        "lon": lon_axis,
    }
    expanded = values_2d.reshape(1, 1, 1, 1, lat_axis.size, lon_axis.size)
    rebuilt = xr.DataArray(
        expanded,
        coords=coords,
        dims=_REQUIRED_DIMS,
        name=normalized.name if data_name is None else data_name,
        attrs=dict(normalized.attrs),
    )
    return rebuilt


def infer_radar_location_from_attrs(grid_data: xr.DataArray):
    """从 ``grid_data.attrs`` 推断雷达站点经纬度。"""
    attr_pairs = (
        ("radar_lon", "radar_lat"),
        ("site_lon", "site_lat"),
        ("longitude", "latitude"),
    )
    for lon_key, lat_key in attr_pairs:
        if lon_key in grid_data.attrs and lat_key in grid_data.attrs:
            try:
                return float(grid_data.attrs[lon_key]), float(grid_data.attrs[lat_key])
            except (TypeError, ValueError):
                continue
    return None, None


def infer_target_lonlat_grid(
    gate_lon,
    gate_lat,
    target_lon=None,
    target_lat=None,
    geo_resolution_deg: float | None = 0.01,
    geo_nlon: int | None = None,
    geo_nlat: int | None = None,
    default_nlon: int | None = None,
    default_nlat: int | None = None,
):
    """根据门点经纬度范围推导规则经纬网格。"""
    if target_lon is not None and target_lat is not None:
        lon_axis = np.asarray(target_lon, dtype=np.float64)
        lat_axis = np.asarray(target_lat, dtype=np.float64)
        if lon_axis.ndim != 1 or lat_axis.ndim != 1:
            raise ValueError("target_lon and target_lat must be 1D sequences")
        return lon_axis, lat_axis

    gate_lon_2d = np.asarray(gate_lon, dtype=np.float64)
    gate_lat_2d = np.asarray(gate_lat, dtype=np.float64)
    valid_mask = np.isfinite(gate_lon_2d) & np.isfinite(gate_lat_2d)
    if not np.any(valid_mask):
        raise ValueError("gate_lon and gate_lat do not contain any finite points")

    lon_min = float(np.nanmin(gate_lon_2d[valid_mask]))
    lon_max = float(np.nanmax(gate_lon_2d[valid_mask]))
    lat_min = float(np.nanmin(gate_lat_2d[valid_mask]))
    lat_max = float(np.nanmax(gate_lat_2d[valid_mask]))

    if geo_resolution_deg is not None:
        resolution = float(geo_resolution_deg)
        if resolution <= 0.0:
            raise ValueError("geo_resolution_deg must be positive")
        nlon = max(int(np.ceil((lon_max - lon_min) / resolution)) + 1, 2)
        nlat = max(int(np.ceil((lat_max - lat_min) / resolution)) + 1, 2)
    else:
        nlon = int(geo_nlon if geo_nlon is not None else (default_nlon or 2))
        nlat = int(geo_nlat if geo_nlat is not None else (default_nlat or 2))
        if nlon < 2 or nlat < 2:
            raise ValueError("geo_nlon and geo_nlat must be at least 2")

    lon_axis = np.linspace(lon_min, lon_max, nlon, dtype=np.float64)
    lat_axis = np.linspace(lat_min, lat_max, nlat, dtype=np.float64)
    return lon_axis, lat_axis


def _haversine_distance_m(lon1, lat1, lon2, lat2):
    """Return great-circle distance in meters."""
    lon1_rad = np.deg2rad(np.asarray(lon1, dtype=np.float64))
    lat1_rad = np.deg2rad(np.asarray(lat1, dtype=np.float64))
    lon2_rad = np.deg2rad(np.asarray(lon2, dtype=np.float64))
    lat2_rad = np.deg2rad(np.asarray(lat2, dtype=np.float64))

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


def mask_outside_radar_coverage(
    data_2d,
    target_lon,
    target_lat,
    radar_lon: float,
    radar_lat: float,
    gate_lon,
    gate_lat,
    coverage_radius_m: float | None = None,
    fill_value=np.nan,
) -> np.ndarray:
    """Mask remapped lat/lon grid cells outside radar circular coverage."""
    values = np.asarray(data_2d, dtype=np.float32).copy()
    lon_axis = np.asarray(target_lon, dtype=np.float64)
    lat_axis = np.asarray(target_lat, dtype=np.float64)
    gate_lon_2d = np.asarray(gate_lon, dtype=np.float64)
    gate_lat_2d = np.asarray(gate_lat, dtype=np.float64)

    valid_mask = np.isfinite(gate_lon_2d) & np.isfinite(gate_lat_2d)
    if not np.any(valid_mask):
        return values

    if coverage_radius_m is None:
        coverage_radius_m = float(
            np.nanmax(
                _haversine_distance_m(
                    radar_lon,
                    radar_lat,
                    gate_lon_2d[valid_mask],
                    gate_lat_2d[valid_mask],
                )
            )
        )

    target_lon_2d, target_lat_2d = np.meshgrid(lon_axis, lat_axis)
    target_distance_m = _haversine_distance_m(
        radar_lon,
        radar_lat,
        target_lon_2d,
        target_lat_2d,
    )
    values[target_distance_m > coverage_radius_m] = fill_value
    return values
