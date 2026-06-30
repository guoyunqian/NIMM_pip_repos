#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""地形增强算法。

本模块实现并迁移了 IMPROVER 地形增强核心流程，支持
``xarray.DataArray`` 与 ``numpy.ndarray`` 输入。整体计算链路为：

1. 在元插件中提取边界层代表高度的温湿压与风场；
2. 将风速风向解析为目标网格坐标系下的 ``u/v`` 风分量；
3. 在主插件中计算迎风抬升项 ``v·gradZ``、格点增强与上游贡献；
4. 输出地形增强结果（单位 ``m s-1``），并在可用时重组为标准六维网格。
"""
from __future__ import annotations

import functools
from typing import Optional, Tuple, Union

import numpy as np
import xarray as xr
from cf_units import Unit
from pyproj import CRS, Transformer
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import convolve, uniform_filter1d


from orographic_enhancement.utils.utils import (
    check_for_meb_griddata,
    rebuild_to_meb_griddata,
)


ArrayLike = Union[xr.DataArray, np.ndarray]
_MEB_REQUIRED_DIMS = ("member", "level", "time", "dtime", "lat", "lon")

R_WATER_VAPOUR = 461.6  # 水汽气体常数，单位 J K-1 kg-1
ABSOLUTE_ZERO = -273.15 # 绝对零度，单位 °C
TRIPLE_PT_WATER = 273.16    # 水的三相点温度，单位 K
SVP_T_MIN = 183.15  # 饱和水汽压查表的最低温度，单位 K
SVP_T_MAX = 338.25  # 饱和水汽压查表的最高温度，单位 K
SVP_T_INCREMENT = 0.1   # 饱和水汽压查表的温度增量，单位 K
EARTH_RADIUS_M = 6378137.0  # 地球半径，单位 m


def _norm_unit(unit: Optional[str]) -> str:
    """规范化单位字符串。"""
    return (unit or "").strip().lower()


def _convert_units(values: np.ndarray, from_unit: str, to_unit: str) -> np.ndarray:
    """使用 cf_units 进行通用单位转换。"""
    vals = np.asarray(values, dtype=np.float64)
    return Unit(from_unit).convert(vals, Unit(to_unit))


def _get_spatial_coord_names(data: xr.DataArray) -> Tuple[str, str]:
    """识别数据中的 y、x 空间坐标名称。"""
    x_name = None
    y_name = None
    for name, coord in data.coords.items():
        axis = str(coord.attrs.get("axis", "")).upper()
        standard_name = _norm_unit(coord.attrs.get("standard_name"))
        if axis == "X" or standard_name in {"projection_x_coordinate", "longitude", "grid_longitude"}:
            x_name = name
        if axis == "Y" or standard_name in {"projection_y_coordinate", "latitude", "grid_latitude"}:
            y_name = name
    if x_name is None or y_name is None:
        dims = list(data.dims)
        if len(dims) < 2:
            raise ValueError("需要至少两个空间维度")
        y_name, x_name = dims[-2], dims[-1]
    return y_name, x_name


def _sort_spatial_dataarray(data: xr.DataArray) -> xr.DataArray:
    """按空间坐标升序排列二维场。"""
    y_name, x_name = _get_spatial_coord_names(data)
    return data.sortby(y_name).sortby(x_name)


def _normalize_to_2d_field(data: ArrayLike, name: str) -> ArrayLike:
    """将输入约束为二维单场。

    支持普通二维场、前四维长度为 1 的标准六维单场以及 numpy 二维数组。
    六维分支处理集合预报入口场景，普通二维场直接走 squeeze 路径。
    """
    if isinstance(data, xr.DataArray):
        if set(data.dims) == set(_MEB_REQUIRED_DIMS):
            normalized = data.transpose(*_MEB_REQUIRED_DIMS)
            for dim in ("member", "level", "time", "dtime"):
                if normalized.sizes[dim] != 1:
                    raise ValueError(
                        f"{name} 仅支持二维场，或前四维(member/level/time/dtime)长度均为1的六维单场；"
                        f"当前 {dim} 维长度为 {normalized.sizes[dim]}"
                    )
            squeezed = normalized.isel(member=0, level=0, time=0, dtime=0, drop=True)
            if squeezed.ndim != 2:
                raise ValueError(f"{name} 六维单场压缩后不是二维")
            return _sort_spatial_dataarray(squeezed)
        squeezed = data.squeeze(drop=True)
        if squeezed.ndim != 2:
            raise ValueError(
                f"{name} 必须是二维场，或前四维(member/level/time/dtime)长度均为1的标准六维单场"
            )
        return _sort_spatial_dataarray(squeezed)
    squeezed = np.asarray(data).squeeze()
    if squeezed.ndim != 2:
        raise ValueError(f"{name} 必须是二维场，或前四维长度均为1的六维单场")
    return squeezed


def _prepare_input(data: ArrayLike, default_unit: str) -> Tuple[np.ndarray, str, Optional[xr.DataArray]]:
    """统一输入数据的数组值、单位和坐标信息。

    参数
    ----------
    data : ArrayLike
        输入数据，可以是 ``xarray.DataArray`` 或 ``numpy.ndarray`` 。
    default_unit : str
        当输入为 ``numpy.ndarray`` 时使用的默认单位。

    返回值
    -------
    tuple
        - 数值数组
        - 规范化后的单位字符串
        - 原始 ``xarray.DataArray``，若输入不是 xarray 则返回 ``None``
    """
    if isinstance(data, xr.DataArray):
        data = _sort_spatial_dataarray(data) if data.ndim >= 2 else data
        return np.asarray(data.values, dtype=np.float64), (data.attrs.get("units") or "").strip(), data
    return np.asarray(np.asarray(data), dtype=np.float64), (default_unit or "").strip(), None


@functools.lru_cache(maxsize=32)
def _load_grid_mapping_attrs(source_path: str, grid_mapping_name: str) -> Tuple[Tuple[str, object], ...]:
    """从源文件中读取网格映射属性并缓存。

    参数
    ----------
    source_path : str
        源文件路径。
    grid_mapping_name : str
        网格映射变量名。

    返回值
    -------
    tuple
        排序后的网格映射属性键值对。
    """
    dataset = xr.open_dataset(source_path, decode_timedelta=False)
    try:
        if grid_mapping_name not in dataset.variables:
            return tuple()
        return tuple(sorted(dict(dataset[grid_mapping_name].attrs).items()))
    finally:
        dataset.close()


def _get_grid_mapping_attrs(data: xr.DataArray) -> dict:
    """提取数据中的网格映射属性。"""
    grid_mapping_name = data.attrs.get("grid_mapping")
    if not grid_mapping_name:
        return {}
    if grid_mapping_name in data.coords:
        return dict(data.coords[grid_mapping_name].attrs)
    source_path = data.encoding.get("source")
    if source_path:
        attrs = dict(_load_grid_mapping_attrs(source_path, grid_mapping_name))
        if attrs:
            return attrs
    return {}


def _get_data_crs(data: Optional[xr.DataArray]) -> Optional[CRS]:
    """推断数据对应的坐标参考系。

    参数
    ----------
    data : xr.DataArray 或 None
        待识别坐标系的数据场。

    返回值
    -------
    CRS 或 None
        识别到的坐标参考系；若无法识别则返回 ``None`` 。
    """
    if data is None or not isinstance(data, xr.DataArray):
        return None
    if "grid_mapping_attrs" in data.attrs:
        try:
            return CRS.from_cf(dict(data.attrs["grid_mapping_attrs"]))
        except Exception:
            pass
    mapping_attrs = _get_grid_mapping_attrs(data)
    if mapping_attrs:
        try:
            return CRS.from_cf(mapping_attrs)
        except Exception:
            pass
    y_name, x_name = _get_spatial_coord_names(data)
    x_coord = data.coords[x_name]
    y_coord = data.coords[y_name]
    x_units = _norm_unit(x_coord.attrs.get("units"))
    y_units = _norm_unit(y_coord.attrs.get("units"))
    x_standard = _norm_unit(x_coord.attrs.get("standard_name"))
    y_standard = _norm_unit(y_coord.attrs.get("standard_name"))
    if (
        x_units in {"degrees", "degree", "degrees_east", "degree_east"}
        and y_units in {"degrees", "degree", "degrees_north", "degree_north"}
    ) or (x_standard == "longitude" and y_standard == "latitude"):
        return CRS.from_epsg(4326)
    return None


def _coord_values_for_crs(coord: xr.DataArray, crs: Optional[CRS]) -> np.ndarray:
    """按坐标系要求返回可用于计算的坐标值。"""
    values = np.asarray(coord.values, dtype=np.float64)
    units = _norm_unit(coord.attrs.get("units"))
    if crs is not None and crs.is_geographic:
        if units in {"radian", "radians", "rad"}:
            return np.rad2deg(values)
        return values
    if units in {"km", "kilometer", "kilometre"}:
        return values * 1000.0
    return values


def _estimate_grid_spacing_meters(data: ArrayLike) -> float:
    """估算网格的平均空间分辨率。

    参数
    ----------
    data : ArrayLike
        输入网格数据。

    返回值
    -------
    float
        平均网格间距，单位为米。
    """
    if not isinstance(data, xr.DataArray):
        return 1000.0
    y_name, x_name = _get_spatial_coord_names(data)
    y_coord = data.coords[y_name]
    x_coord = data.coords[x_name]
    y_values = np.asarray(y_coord.values, dtype=np.float64)
    x_values = np.asarray(x_coord.values, dtype=np.float64)
    if len(y_values) < 2 or len(x_values) < 2:
        return 1000.0
    y_units = _norm_unit(y_coord.attrs.get("units"))
    x_units = _norm_unit(x_coord.attrs.get("units"))
    if y_units in {"m", "metre", "meter", "km", "kilometer", "kilometre"} and x_units in {"m", "metre", "meter", "km", "kilometer", "kilometre"}:
        y_m = _convert_units(y_values, y_units, "m")
        x_m = _convert_units(x_values, x_units, "m")
        return float((np.mean(np.abs(np.diff(y_m))) + np.mean(np.abs(np.diff(x_m)))) / 2.0)
    crs = _get_data_crs(data)
    if crs is not None and crs.is_geographic:
        mean_lat_rad = np.deg2rad(float(np.mean(y_values)))
        dy = np.mean(np.abs(np.diff(y_values))) * np.pi / 180.0 * EARTH_RADIUS_M
        dx = np.mean(np.abs(np.diff(x_values))) * np.pi / 180.0 * EARTH_RADIUS_M * np.cos(mean_lat_rad)
        return float((dx + dy) / 2.0)
    return 1000.0


def _grid_spacings_meters(data: ArrayLike) -> Tuple[float, float]:
    """分别计算 y、x 方向的网格间距。

    参数
    ----------
    data : ArrayLike
        输入网格数据。

    返回值
    -------
    tuple
        - y 方向网格间距，单位为米
        - x 方向网格间距，单位为米
    """
    if not isinstance(data, xr.DataArray):
        return 1000.0, 1000.0
    y_name, x_name = _get_spatial_coord_names(data)
    y_coord = data.coords[y_name]
    x_coord = data.coords[x_name]
    y_values = np.asarray(y_coord.values, dtype=np.float64)
    x_values = np.asarray(x_coord.values, dtype=np.float64)
    if len(y_values) < 2 or len(x_values) < 2:
        spacing = _estimate_grid_spacing_meters(data)
        return spacing, spacing
    y_units = _norm_unit(y_coord.attrs.get("units"))
    x_units = _norm_unit(x_coord.attrs.get("units"))
    if y_units in {"m", "metre", "meter", "km", "kilometer", "kilometre"}:
        y_spacing = float(np.mean(np.abs(np.diff(_convert_units(y_values, y_units, "m")))))
    else:
        y_spacing = _estimate_grid_spacing_meters(data)
    if x_units in {"m", "metre", "meter", "km", "kilometer", "kilometre"}:
        x_spacing = float(np.mean(np.abs(np.diff(_convert_units(x_values, x_units, "m")))))
    else:
        x_spacing = _estimate_grid_spacing_meters(data)
    return y_spacing, x_spacing


def _needs_regridding(source: xr.DataArray, target: xr.DataArray) -> bool:
    """判断源场是否需要重采样到目标网格。"""
    source = _sort_spatial_dataarray(source)
    target = _sort_spatial_dataarray(target)
    source_y, source_x = _get_spatial_coord_names(source)
    target_y, target_x = _get_spatial_coord_names(target)
    if source.shape != target.shape:
        return True
    if not np.array_equal(source.coords[source_y], target.coords[target_y]):
        return True
    if not np.array_equal(source.coords[source_x], target.coords[target_x]):
        return True
    return False


def _regrid_scalar_field(source: xr.DataArray, target: xr.DataArray) -> xr.DataArray:
    """将标量场线性插值到目标网格。

    参数
    ----------
    source : xr.DataArray
        源网格上的标量场。
    target : xr.DataArray
        目标网格模板。

    返回值
    -------
    xr.DataArray
        重采样后的二维标量场。
    """
    source = _sort_spatial_dataarray(source)
    target = _sort_spatial_dataarray(target)
    source_y, source_x = _get_spatial_coord_names(source)
    target_y, target_x = _get_spatial_coord_names(target)
    source_crs = _get_data_crs(source)
    target_crs = _get_data_crs(target)
    source_y_values = _coord_values_for_crs(source.coords[source_y], source_crs)
    source_x_values = _coord_values_for_crs(source.coords[source_x], source_crs)
    target_y_values = _coord_values_for_crs(target.coords[target_y], target_crs)
    target_x_values = _coord_values_for_crs(target.coords[target_x], target_crs)
    target_x_mesh, target_y_mesh = np.meshgrid(target_x_values, target_y_values)
    sample_x = target_x_mesh
    sample_y = target_y_mesh
    # 若无法识别 CRS，则只能按“同一坐标系”假设直接插值；
    # 为避免网格完全不重叠时发生无约束外推，这里做范围检查并显式报错。
    if source_crs is None and target_crs is None:
        y_overlap = (np.max(source_y_values) >= np.min(target_y_values)) and (
            np.max(target_y_values) >= np.min(source_y_values)
        )
        x_overlap = (np.max(source_x_values) >= np.min(target_x_values)) and (
            np.max(target_x_values) >= np.min(source_x_values)
        )
        if not (y_overlap and x_overlap):
            raise ValueError(
                "源网格与目标网格坐标范围不重叠，且缺少 CRS 信息，无法安全重采样。"
            )
    # 投影不一致时，先把目标点反算到源投影，再在源网格上插值。
    if source_crs is not None and target_crs is not None and not source_crs.equals(target_crs):
        transformer = Transformer.from_crs(target_crs, source_crs, always_xy=True)
        sample_x, sample_y = transformer.transform(target_x_mesh, target_y_mesh)
    interpolator = RegularGridInterpolator(
        (source_y_values, source_x_values),
        np.asarray(source.values, dtype=np.float32),
        method="linear",
        bounds_error=False,
        fill_value=np.nan,
    )
    sample_points = np.column_stack([sample_y.ravel(), sample_x.ravel()])
    regridded = interpolator(sample_points).reshape(target.shape).astype(np.float32)
    return xr.DataArray(
        regridded,
        coords={target_y: target.coords[target_y], target_x: target.coords[target_x]},
        dims=(target_y, target_x),
        attrs=source.attrs.copy(),
    )


def _make_field_on_target(values: np.ndarray, units: str, target: xr.DataArray, source_attrs: Optional[dict] = None) -> xr.DataArray:
    """基于目标网格构造新的二维数据场。

    参数
    ----------
    values : np.ndarray
        待写入的数据值。
    units : str
        输出数据单位。
    target : xr.DataArray
        目标网格模板。
    source_attrs : dict, optional
        需要继承的属性字典。

    返回值
    -------
    xr.DataArray
        与目标网格坐标一致的新二维场。
    """
    y_name, x_name = _get_spatial_coord_names(target)
    attrs = dict(source_attrs or {})
    attrs["units"] = units
    if "grid_mapping_attrs" not in attrs:
        mapping_attrs = _get_grid_mapping_attrs(target)
        if mapping_attrs:
            attrs["grid_mapping_attrs"] = mapping_attrs
    return xr.DataArray(
        np.asarray(values, dtype=np.float32),
        coords={y_name: target.coords[y_name], x_name: target.coords[x_name]},
        dims=(y_name, x_name),
        attrs=attrs,
    )


def _regridded_adjacent_gradient(values: np.ndarray, spacing_m: float, axis: int) -> np.ndarray:
    """按原算法思路计算相邻格点梯度并线性回插到原网格。

    参数
    ----------
    values : np.ndarray
        输入二维场。
    spacing_m : float
        梯度方向的网格间距，单位为米。
    axis : int
        计算梯度的轴索引。

    返回值
    -------
    np.ndarray
        回插到原网格后的梯度场。
    """
    values = np.asarray(values, dtype=np.float64)
    diffs = np.diff(values, axis=axis) / spacing_m
    output = np.empty_like(values, dtype=np.float64)
    axis_length = values.shape[axis]
    if axis_length == 1:
        output[...] = 0.0
        return output
    if axis_length == 2:
        first = [slice(None)] * values.ndim
        second = [slice(None)] * values.ndim
        first[axis] = 0
        second[axis] = 1
        diff_index = [slice(None)] * values.ndim
        diff_index[axis] = 0
        output[tuple(first)] = diffs[tuple(diff_index)]
        output[tuple(second)] = diffs[tuple(diff_index)]
        return output
    first = [slice(None)] * values.ndim
    second = [slice(None)] * values.ndim
    interior = [slice(None)] * values.ndim
    left = [slice(None)] * values.ndim
    right = [slice(None)] * values.ndim
    diff0 = [slice(None)] * values.ndim
    diff1 = [slice(None)] * values.ndim
    difflast = [slice(None)] * values.ndim
    diffprev = [slice(None)] * values.ndim
    first[axis] = 0
    second[axis] = axis_length - 1
    interior[axis] = slice(1, axis_length - 1)
    left[axis] = slice(0, axis_length - 2)
    right[axis] = slice(1, axis_length - 1)
    diff0[axis] = 0
    diff1[axis] = 1
    difflast[axis] = -1
    diffprev[axis] = -2
    output[tuple(first)] = 1.5 * diffs[tuple(diff0)] - 0.5 * diffs[tuple(diff1)]
    output[tuple(interior)] = 0.5 * (diffs[tuple(left)] + diffs[tuple(right)])
    output[tuple(second)] = 1.5 * diffs[tuple(difflast)] - 0.5 * diffs[tuple(diffprev)]
    return output


def _square_neighbourhood_mean(values: np.ndarray, size: int) -> np.ndarray:
    """按有效邻域格点数计算方形邻域均值。

    参数
    ----------
    values : np.ndarray
        输入二维场。
    size : int
        方形邻域边长。

    返回值
    -------
    np.ndarray
        邻域均值场。
    """
    values = np.asarray(values, dtype=np.float64)
    kernel = np.ones((size, size), dtype=np.float64)
    summed = convolve(values, kernel, mode="constant", cval=0.0)
    counts = convolve(np.ones(values.shape, dtype=np.float64), kernel, mode="constant", cval=0.0)
    return summed / counts


def _svp_pure_water_goff_gratch(temperature: np.ndarray) -> np.ndarray:
    """按 Goff-Gratch 公式计算纯水体系饱和水汽压。"""
    t = np.asarray(temperature, dtype=np.float64)
    triple_pt = float(TRIPLE_PT_WATER)
    over_triple = t > triple_pt
    n0_w = 10.79574 * (1.0 - triple_pt / t)
    n1_w = 5.028 * np.log10(t / triple_pt)
    n2_w = 1.50475e-4 * (1.0 - np.power(10.0, -8.2969 * (t / triple_pt - 1.0)))
    n3_w = 0.42873e-3 * (np.power(10.0, 4.76955 * (1.0 - triple_pt / t)) - 1.0)
    log_es_w = n0_w - n1_w + n2_w + n3_w + 0.78614
    es_w = np.power(10.0, log_es_w)
    n0_i = -9.09685 * (triple_pt / t - 1.0)
    n1_i = 3.56654 * np.log10(triple_pt / t)
    n2_i = 0.87682 * (1.0 - t / triple_pt)
    log_es_i = n0_i - n1_i + n2_i + 0.78614
    es_i = np.power(10.0, log_es_i)
    return np.where(over_triple, es_w, es_i)


@functools.lru_cache(maxsize=1)
def _svp_table() -> np.ndarray:
    """生成并缓存饱和水汽压查找表。"""
    temperatures = np.arange(SVP_T_MIN, SVP_T_MAX + 0.5 * SVP_T_INCREMENT, SVP_T_INCREMENT, dtype=np.float64)
    return _svp_pure_water_goff_gratch(temperatures) * 100.0


def _svp_from_lookup(temperature: np.ndarray) -> np.ndarray:
    """通过查表和线性插值得到饱和水汽压。

    参数
    ----------
    temperature : np.ndarray
        温度数组，单位为开尔文。

    返回值
    -------
    np.ndarray
        饱和水汽压，单位为帕。
    """
    # 用查表加线性插值近似饱和水汽压，避免逐点重复计算经验公式。
    t_clipped = np.clip(temperature, SVP_T_MIN, SVP_T_MAX - SVP_T_INCREMENT)
    t_clipped = np.nan_to_num(
        t_clipped,
        nan=SVP_T_MIN,
        posinf=SVP_T_MAX - SVP_T_INCREMENT,
        neginf=SVP_T_MIN,
    )
    table_position = (t_clipped - SVP_T_MIN) / SVP_T_INCREMENT
    table_index = table_position.astype(int)
    interpolation_factor = table_position - table_index
    svp_table = _svp_table()
    table_index = np.clip(table_index, 0, len(svp_table) - 2)
    return (1.0 - interpolation_factor) * svp_table[table_index] + interpolation_factor * svp_table[table_index + 1]


def calculate_svp_in_air(temperature: np.ndarray, pressure: np.ndarray) -> np.ndarray:
    """计算湿空气中的饱和水汽压。

    参数
    ----------
    temperature : np.ndarray
        温度数组，单位为开尔文。
    pressure : np.ndarray
        气压数组，单位为帕。

    返回值
    -------
    np.ndarray
        湿空气中的饱和水汽压，单位为帕。
    """
    # 先求纯水饱和水汽压，再按气压做湿空气修正。
    svp = _svp_from_lookup(temperature)
    temp_c = temperature + ABSOLUTE_ZERO
    correction = 1.0 + 1.0e-8 * pressure * (4.5 + 6.0e-4 * temp_c * temp_c)
    return svp * correction.astype(np.float32)


class ResolveWindComponents:
    """风场分量解析插件。

    该插件对应原算法中“先解风分量再计算地形增强”的步骤，负责把
    ``wind_speed + wind_direction`` 转换为目标网格坐标系下的 ``u/v`` 分量。
    主要处理链路如下：

    1. 统一风速单位到 ``m s-1``，统一风向角度到弧度计算。
    2. 根据风向约定（from/to）确定风矢量指向。
    3. 若输入为投影网格，计算真北与网格北夹角并进行方向修正。
    4. 若源网格与目标网格投影不一致，执行分量旋转与重采样。
    5. 输出与目标网格对齐的风分量，供地形增强主算法直接使用。

    输入支持 ``xarray.DataArray`` 与 ``numpy.ndarray``：
    - DataArray 路径尽量保留坐标与属性；
    - ndarray 路径返回纯数组分量。

    说明
    ----------
    该插件内部计算核心基于二维场。若输入是标准六维且前四维长度为 1，
    会在入口自动压缩到二维计算，并在返回时尽量保持与目标网格一致的坐标语义。
    """

    @staticmethod
    def _bearing_radians(
        lat1_deg: np.ndarray, lon1_deg: np.ndarray, lat2_deg: np.ndarray, lon2_deg: np.ndarray
    ) -> np.ndarray:
        """计算两组经纬度点之间的方位角。"""
        lat1 = np.deg2rad(lat1_deg)
        lon1 = np.deg2rad(lon1_deg)
        lat2 = np.deg2rad(lat2_deg)
        lon2 = np.deg2rad(lon2_deg)
        dlon = lon2 - lon1
        numerator = np.sin(dlon) * np.cos(lat2)
        denominator = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        return np.arctan2(numerator, denominator)

    @staticmethod
    def _calculate_true_north_offset(target: ArrayLike) -> np.ndarray:
        """计算目标网格上真北与网格北的夹角。"""
        target_values = np.asarray(target)
        if not isinstance(target, xr.DataArray):
            return np.zeros(target_values.shape, dtype=np.float32)
        target = _sort_spatial_dataarray(target)
        crs = _get_data_crs(target)
        if crs is None or crs.is_geographic:
            return np.zeros(target.shape, dtype=np.float32)
        y_name, x_name = _get_spatial_coord_names(target)
        x_values = _coord_values_for_crs(target.coords[x_name], crs)
        y_values = _coord_values_for_crs(target.coords[y_name], crs)
        x_mesh, y_mesh = np.meshgrid(x_values, y_values)
        delta = _estimate_grid_spacing_meters(target)
        transformer = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
        lon0, lat0 = transformer.transform(x_mesh, y_mesh)
        lon1, lat1 = transformer.transform(x_mesh, y_mesh + delta)
        return (-ResolveWindComponents._bearing_radians(lat0, lon0, lat1, lon1)).astype(np.float32)

    @staticmethod
    def _calculate_true_north_offset_for_points(
        crs: Optional[CRS], x_points: np.ndarray, y_points: np.ndarray, delta_m: float
    ) -> np.ndarray:
        """计算指定投影坐标点上的真北偏角。"""
        if crs is None or crs.is_geographic:
            return np.zeros(np.asarray(x_points).shape, dtype=np.float32)
        transformer = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
        lon0, lat0 = transformer.transform(x_points, y_points)
        lon1, lat1 = transformer.transform(x_points, y_points + delta_m)
        return (-ResolveWindComponents._bearing_radians(lat0, lon0, lat1, lon1)).astype(np.float32)

    @staticmethod
    def _wind_direction_is_from(data: ArrayLike) -> bool:
        """判断风向字段使用的是 from 还是 to 约定。"""
        if not isinstance(data, xr.DataArray):
            return True
        candidates = [
            str(data.name or ""),
            str(data.attrs.get("standard_name", "")),
            str(data.attrs.get("long_name", "")),
            str(data.attrs.get("direction_convention", "")),
        ]
        if any("from" in item.lower() for item in candidates):
            return True
        if any("to" in item.lower() for item in candidates):
            return False
        return True

    @staticmethod
    def _rotate_grid_components(
        uwind: np.ndarray, vwind: np.ndarray, angle_adjustment: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """旋转已有网格风分量以适配另一套网格方向。"""
        rotated_u = uwind * np.cos(angle_adjustment) + vwind * np.sin(angle_adjustment)
        rotated_v = vwind * np.cos(angle_adjustment) - uwind * np.sin(angle_adjustment)
        return rotated_u.astype(np.float32), rotated_v.astype(np.float32)

    def __call__(self, wind_speed: ArrayLike, wind_direction: ArrayLike, target_grid: ArrayLike) -> Tuple[ArrayLike, ArrayLike]:
        """保持插件可调用接口，等价于 :meth:`process`。"""
        return self.process(wind_speed, wind_direction, target_grid)

    def process(self, wind_speed: ArrayLike, wind_direction: ArrayLike, target_grid: ArrayLike) -> Tuple[ArrayLike, ArrayLike]:
        """将风速风向解析为网格风分量。

        参数
        ----------
        wind_speed : ArrayLike
            风速场。
        wind_direction : ArrayLike
            风向场（相对真北角度）。
        target_grid : ArrayLike
            目标网格模板（通常为地形网格）。

        返回值
        -------
        tuple
            ``(uwind, vwind)``，类型与输入数据结构一致：
            - xarray 输入返回 ``xr.DataArray``；
            - numpy 输入返回 ``np.ndarray``。
        """
        wind_speed = _normalize_to_2d_field(wind_speed, "wind_speed")
        wind_direction = _normalize_to_2d_field(wind_direction, "wind_direction")
        target_grid = _normalize_to_2d_field(target_grid, "target_grid")

        if isinstance(target_grid, xr.DataArray):
            target_grid = _sort_spatial_dataarray(target_grid)
        speed_values, speed_units, speed_da = _prepare_input(wind_speed, "m s-1")
        direction_values, _, direction_da = _prepare_input(wind_direction, "degrees")
        speed_values = _convert_units(speed_values, speed_units, "m s-1").astype(np.float64)
        direction_reference = direction_da if direction_da is not None else wind_direction

        if isinstance(speed_da, xr.DataArray) and isinstance(target_grid, xr.DataArray):
            source_adjustment = self._calculate_true_north_offset(speed_da).astype(np.float64)
            angle = np.deg2rad(direction_values.astype(np.float64)) + source_adjustment
            if self._wind_direction_is_from(direction_reference):
                angle = angle + np.pi
            source_uwind = (speed_values * np.sin(angle)).astype(np.float32)
            source_vwind = (speed_values * np.cos(angle)).astype(np.float32)
            source_crs = _get_data_crs(speed_da)
            target_crs = _get_data_crs(target_grid)
            if source_crs is not None and target_crs is not None and not source_crs.equals(target_crs):
                source_y_name, source_x_name = _get_spatial_coord_names(speed_da)
                source_x_values = _coord_values_for_crs(speed_da.coords[source_x_name], source_crs)
                source_y_values = _coord_values_for_crs(speed_da.coords[source_y_name], source_crs)
                source_x_mesh, source_y_mesh = np.meshgrid(source_x_values, source_y_values)
                transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
                target_x_on_source, target_y_on_source = transformer.transform(source_x_mesh, source_y_mesh)
                target_adjustment = self._calculate_true_north_offset_for_points(
                    target_crs,
                    target_x_on_source,
                    target_y_on_source,
                    _estimate_grid_spacing_meters(target_grid),
                ).astype(np.float64)
                rotation = target_adjustment - source_adjustment
                source_uwind, source_vwind = self._rotate_grid_components(source_uwind, source_vwind, rotation)
            uwind_da = _make_field_on_target(source_uwind, "m s-1", speed_da, speed_da.attrs.copy())
            vwind_da = _make_field_on_target(source_vwind, "m s-1", speed_da, speed_da.attrs.copy())
            if _needs_regridding(uwind_da, target_grid):
                uwind_da = _regrid_scalar_field(uwind_da, target_grid)
            if _needs_regridding(vwind_da, target_grid):
                vwind_da = _regrid_scalar_field(vwind_da, target_grid)
            uwind_values = uwind_da.values
            vwind_values = vwind_da.values
            uwind = _make_field_on_target(uwind_values, "m s-1", target_grid)
            vwind = _make_field_on_target(vwind_values, "m s-1", target_grid)
            return uwind, vwind

        source_adjustment = np.zeros(speed_values.shape, dtype=np.float64)
        angle = np.deg2rad(direction_values.astype(np.float64)) + source_adjustment
        if self._wind_direction_is_from(direction_reference):
            angle = angle + np.pi
        uwind = (speed_values * np.sin(angle)).astype(np.float32)
        vwind = (speed_values * np.cos(angle)).astype(np.float32)
        return uwind, vwind


class MetaOrographicEnhancement:
    """地形增强元插件（前处理与流程编排）。

    该类不直接计算增强值，而是负责组织输入并调度子插件。核心职责包括：

    1. 从多层温湿压/风场中提取边界层代表高度二维切片；
    2. 调用 :class:`ResolveWindComponents` 生成 ``u/v`` 风分量；
    3. 调用 :class:`OrographicEnhancement` 计算最终地形增强。

    设计上将“风场解析”和“增强计算”解耦，便于后续独立校验两个阶段。
    气象场选层后为二维；地形保持原始维度传入主算法，由
    :class:`OrographicEnhancement` 内部压维计算并按地形模板重组六维输出。
    """

    def __init__(self, boundary_height: float = 1000.0, boundary_height_units: str = "m"):
        self.boundary_height = boundary_height
        self.boundary_height_units = boundary_height_units

    def __call__(self, temperature: ArrayLike, humidity: ArrayLike, pressure: ArrayLike, wind_speed: ArrayLike, wind_direction: ArrayLike, orography: ArrayLike) -> xr.DataArray:
        """保持插件可调用接口，等价于 :meth:`process`。"""
        return self.process(temperature, humidity, pressure, wind_speed, wind_direction, orography)

    @staticmethod
    def _extract_height_level(data: ArrayLike, boundary_height: float, boundary_height_units: str) -> ArrayLike:
        """从输入场中提取边界层代表高度对应的二维切片。

        参数
        ----------
        data : ArrayLike
            输入场，可以是二维场，也可以是带 ``height`` 或 ``level`` 坐标的多层场。
        boundary_height : float
            目标边界层代表高度。
        boundary_height_units : str
            目标边界层高度对应的单位。

        返回值
        -------
        ArrayLike
            提取后的二维场；若输入本身已经是二维，则直接返回排序后的原场。
        """
        # 按边界层代表高度选取最接近的一层，保持与原算法一致的选层语义。
        if not isinstance(data, xr.DataArray):
            if np.asarray(data).ndim > 2:
                raise ValueError("numpy 输入包含垂直维时，必须改用带 height/level 坐标的 xarray 输入")
            return data
        if data.ndim <= 2:
            return _sort_spatial_dataarray(data)
        vertical_coord_name = "height" if "height" in data.coords else ("level" if "level" in data.coords else None)
        if vertical_coord_name is None:
            raise ValueError("xarray 输入包含超过二维的数据时，必须提供 height 或 level 坐标")
        height_coord = data.coords[vertical_coord_name]
        height_units = (height_coord.attrs.get("units") or "m").strip()
        height_values = _convert_units(height_coord.values, height_units, boundary_height_units)
        index = int(np.argmin(np.abs(height_values - boundary_height)))
        if abs(float(height_values[index]) - boundary_height) > 0.1:
            raise ValueError(f"未找到高度 {boundary_height}{boundary_height_units} 附近的层次")
        result = data.isel({height_coord.dims[0]: index}, drop=True).squeeze(drop=True)
        if result.ndim != 2:
            raise ValueError("提取高度层后仍不是二维场")
        return _sort_spatial_dataarray(result)

    def process(self, temperature: ArrayLike, humidity: ArrayLike, pressure: ArrayLike, wind_speed: ArrayLike, wind_direction: ArrayLike, orography: ArrayLike) -> xr.DataArray:
        """提取边界层输入并组织地形增强主流程。

        功能说明
        ----------
        从多层输入中提取边界层代表高度的二维温湿压和风场，完成风向解析、
        投影方向修正及必要的重采样，然后调用地形增强主算法。

        参数
        ----------
        temperature : ArrayLike
            温度场，可以是二维场，也可以是带 ``height`` 或 ``level`` 坐标的多层场。
        humidity : ArrayLike
            相对湿度场，可以是二维场，也可以是带 ``height`` 或 ``level`` 坐标的多层场。
        pressure : ArrayLike
            气压场，可以是二维场，也可以是带 ``height`` 或 ``level`` 坐标的多层场。
        wind_speed : ArrayLike
            风速场，可以是二维场，也可以是带 ``height`` 或 ``level`` 坐标的多层场。
        wind_direction : ArrayLike
            风向场，约定为相对真北的角度。
        orography : ArrayLike
            地形高度场，作为目标输出网格。

        返回值
        -------
        xr.DataArray
            地形增强结果，单位为 ``m s-1``。
            六维输出重组由 :class:`OrographicEnhancement` 根据地形维度完成。
        """
        # 入口阶段对 xarray 输入执行严格六维校验，避免隐式兼容改变语义。
        if check_for_meb_griddata is None and any(
            isinstance(item, xr.DataArray)
            for item in (temperature, humidity, pressure, wind_speed, wind_direction, orography)
        ):
            raise ValueError("输入包含 xarray.DataArray，但未找到 check_for_meb_griddata，无法进行六维网格校验。")

        input_fields = {
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
        }
        for name, field in input_fields.items():
            if isinstance(field, xr.DataArray):
                # 不做值域裁剪，避免气压/地形等高值被误置无效。
                input_fields[name] = check_for_meb_griddata(
                    field,
                    is_single=False,
                    valid_val=(-np.inf, np.inf, np.nan),
                )
        temperature = input_fields["temperature"]
        humidity = input_fields["humidity"]
        pressure = input_fields["pressure"]
        wind_speed = input_fields["wind_speed"]
        wind_direction = input_fields["wind_direction"]

        # 约化为边界层代表高度上的二维场，直接传入主算法。
        temperature = self._extract_height_level(temperature, self.boundary_height, self.boundary_height_units)
        humidity = self._extract_height_level(humidity, self.boundary_height, self.boundary_height_units)
        pressure = self._extract_height_level(pressure, self.boundary_height, self.boundary_height_units)
        wind_speed = self._extract_height_level(wind_speed, self.boundary_height, self.boundary_height_units)
        wind_direction = self._extract_height_level(wind_direction, self.boundary_height, self.boundary_height_units)

        if isinstance(orography, xr.DataArray):
            orography = check_for_meb_griddata(
                orography,
                is_single=True,
                valid_val=(-np.inf, np.inf, np.nan),
            )
        elif np.asarray(orography).ndim != 2:
            raise ValueError("orography 必须是二维单场")

        uwind, vwind = ResolveWindComponents()(wind_speed, wind_direction, orography)
        return OrographicEnhancement()(temperature, humidity, pressure, uwind, vwind, orography)


class OrographicEnhancement:
    """地形增强主算法插件。

    该类实现地形增强的数值核心，输入支持二维或前四维为1的标准六维单场
    与网格风分量 ``uwind/vwind``，在目标地形网格上计算增强结果，计算内核仍是二维。
    主要步骤如下：

    1. 单位统一与网格对齐（必要时重采样到地形网格）；
    2. 计算地形梯度并得到迎风抬升项 ``v·gradZ``；
    3. 基于阈值条件生成掩码（地形高度、湿度、抬升强度）；
    4. 计算格点地形增强贡献（``mm h-1``）；
    5. 按风向回溯上游贡献并高斯加权叠加；
    6. 转换到 ``m s-1``，构造带坐标输出。

    参数阈值（地形、湿度、抬升、上游影响距离、云寿命、效率系数）
    与原算法保持一致，便于与官方结果对照验证。

    说明
    ----------
    该类是数值计算核心。即使输入为六维单场，也会先压缩到二维完成计算，
    再按模板重组输出，避免在三维/六维上重复实现同一套二维物理逻辑。
    """

    def __init__(self) -> None:
        self.orog_thresh_m = 20.0
        self.rh_thresh_ratio = 0.8
        self.vgradz_thresh_ms = 0.0005

        self.upstream_range_of_influence_km = 15.0
        self.cloud_lifetime_s = 102.0
        self.efficiency_factor = 0.23265

        #初始化类成员以存储重采样变量用于水汽增强计算
        self.temperature = None
        self.humidity = None
        self.pressure = None
        self.uwind = None
        self.vwind = None
        self.topography = None
        self.grid_spacing_km = None

    def __repr__(self) -> str:
        return "<OrographicEnhancement()>"

    def __call__(self, temperature: ArrayLike, humidity: ArrayLike, pressure: ArrayLike, uwind: ArrayLike, vwind: ArrayLike, topography: ArrayLike) -> xr.DataArray:
        """保持插件可调用接口，等价于 :meth:`process`。"""
        return self.process(temperature, humidity, pressure, uwind, vwind, topography)

    def _prepare_field(self, data: ArrayLike, default_unit: str, target: Optional[xr.DataArray] = None) -> Tuple[np.ndarray, Optional[xr.DataArray], str]:
        """统一单个输入场的单位、数组和值域网格。

        参数
        ----------
        data : ArrayLike
            输入场。
        default_unit : str
            默认单位。
        target : xr.DataArray, optional
            目标网格模板。

        返回值
        -------
        tuple
            - 数值数组
            - 可选的 xarray 数据场
            - 规范化后的单位字符串
        """
        values, units, data_array = _prepare_input(data, default_unit)
        if data_array is not None and target is not None and _needs_regridding(data_array, target):
            data_array = _regrid_scalar_field(data_array, target)
            values = np.asarray(data_array.values, dtype=np.float32)
        return values, data_array, units

    def _calculate_vgradz(self, uwind: np.ndarray, vwind: np.ndarray, topography: np.ndarray, y_spacing_m: float, x_spacing_m: float) -> np.ndarray:
        """计算迎风抬升项 ``v·gradZ`` 。

        参数
        ----------
        uwind : np.ndarray
            x 方向风分量。
        vwind : np.ndarray
            y 方向风分量。
        topography : np.ndarray
            地形高度场。
        y_spacing_m : float
            y 方向网格间距，单位为米。
        x_spacing_m : float
            x 方向网格间距，单位为米。

        返回值
        -------
        np.ndarray
            迎风抬升项数组。
        """
        # 先做与梯度方向垂直的三点平滑，再求地形梯度并与风矢量点乘。
        topo_for_gradx = uniform_filter1d(topography, 3, axis=0, mode="nearest")
        topo_for_grady = uniform_filter1d(topography, 3, axis=1, mode="nearest")
        grad_x = _regridded_adjacent_gradient(topo_for_gradx, x_spacing_m, axis=1)
        grad_y = _regridded_adjacent_gradient(topo_for_grady, y_spacing_m, axis=0)
        return (uwind * grad_x + vwind * grad_y).astype(np.float32)

    def _generate_mask(self, topography: np.ndarray, humidity: np.ndarray, vgradz: np.ndarray) -> np.ndarray:
        """生成不参与地形增强计算的掩码。

        参数
        ----------
        topography : np.ndarray
            地形高度场。
        humidity : np.ndarray
            相对湿度场。
        vgradz : np.ndarray
            迎风抬升项。

        返回值
        -------
        np.ndarray
            布尔掩码数组，``True`` 表示该点不参与计算。
        """
        # 只在地形、湿度和抬升条件都满足时，才计算地形增强。
        topo_nbhood = _square_neighbourhood_mean(topography, size=3)
        mask = np.full(topography.shape, False, dtype=bool)
        mask = np.where(topo_nbhood < self.orog_thresh_m, True, mask)
        mask = np.where(humidity < self.rh_thresh_ratio, True, mask)
        mask = np.where(np.abs(vgradz) < self.vgradz_thresh_ms, True, mask)
        mask = np.where(~np.isfinite(humidity), True, mask)
        mask = np.where(~np.isfinite(vgradz), True, mask)
        return mask

    def _point_orogenh(self, temperature: np.ndarray, humidity: np.ndarray, svp: np.ndarray, vgradz: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """计算格点尺度的地形增强贡献。

        参数
        ----------
        temperature : np.ndarray
            温度场。
        humidity : np.ndarray
            相对湿度场。
        svp : np.ndarray
            饱和水汽压场。
        vgradz : np.ndarray
            迎风抬升项。
        mask : np.ndarray
            计算掩码。

        返回值
        -------
        np.ndarray
            格点地形增强贡献，单位为 ``mm h-1`` 。
        """
        point_orogenh = np.zeros(temperature.shape, dtype=np.float32)
        valid_mask = np.logical_not(mask)
        if np.any(valid_mask):
            # 格点增强沿用原始经验公式，结果单位为 mm h-1。
            prefactor = 3600.0 / R_WATER_VAPOUR
            numerator = humidity[valid_mask] * svp[valid_mask] * vgradz[valid_mask]
            point_orogenh[valid_mask] = prefactor * numerator / temperature[valid_mask]
        return np.where(point_orogenh > 0, point_orogenh, 0).astype(np.float32)

    def _add_upstream_component(self, point_orogenh: np.ndarray) -> np.ndarray:
        """叠加上游格点对当前格点的增强贡献。

        参数
        ----------
        point_orogenh : np.ndarray
            格点地形增强贡献，单位为 ``mm h-1`` 。

        返回值
        -------
        np.ndarray
            叠加上游贡献后的地形增强结果，单位为 ``mm h-1`` 。
        """
        # 沿风向回溯有限距离，对上游格点增强做高斯加权平均。
        uwind = np.nan_to_num(self.uwind, nan=0.0).astype(np.float32)
        vwind = np.nan_to_num(self.vwind, nan=0.0).astype(np.float32)
        wind_speed = np.sqrt(np.square(uwind) + np.square(vwind)).astype(np.float32)
        moving_mask = np.logical_not(np.isclose(wind_speed, 0.0))
        sin_wind_dir = np.zeros(wind_speed.shape, dtype=np.float32)
        cos_wind_dir = np.zeros(wind_speed.shape, dtype=np.float32)
        sin_wind_dir[moving_mask] = uwind[moving_mask] / wind_speed[moving_mask]
        cos_wind_dir[moving_mask] = vwind[moving_mask] / wind_speed[moving_mask]
        max_sin_cos = np.where(np.abs(sin_wind_dir) > np.abs(cos_wind_dir), np.abs(sin_wind_dir), np.abs(cos_wind_dir))
        upstream_roi = self.upstream_range_of_influence_km / self.grid_spacing_km
        max_roi = (upstream_roi * max_sin_cos).astype(int)
        if np.max(max_roi) <= 0:
            return point_orogenh.astype(np.float32)
        length = int(np.max(max_roi))
        distance = np.full((length, wind_speed.shape[0], wind_speed.shape[1]), np.nan, dtype=np.float32)
        for y_index in range(distance.shape[1]):
            for x_index in range(distance.shape[2]):
                if max_roi[y_index, x_index] > 0:
                    distance[: max_roi[y_index, x_index], y_index, x_index] = np.arange(max_roi[y_index, x_index], dtype=np.float32) / max_sin_cos[y_index, x_index]
        xpos, ypos = np.meshgrid(np.arange(wind_speed.shape[1]), np.arange(wind_speed.shape[0]))
        # 把回溯距离换成上游源点索引，并限制在网格范围内。
        x_source = np.around(
            np.where(np.isfinite(distance), xpos - distance * sin_wind_dir, xpos)
        ).astype(int)
        y_source = np.around(
            np.where(np.isfinite(distance), ypos - distance * cos_wind_dir, ypos)
        ).astype(int)
        x_source = np.clip(x_source, 0, wind_speed.shape[1] - 1)
        y_source = np.clip(y_source, 0, wind_speed.shape[0] - 1)
        source_values = point_orogenh[y_source, x_source]
        grid_spacing_m = 1000.0 * self.grid_spacing_km
        # 扩散尺度由风速和云寿命共同决定，二者越大，上游影响越远。
        stddev = (wind_speed * self.cloud_lifetime_s / grid_spacing_m).astype(np.float32)
        variance = np.square(stddev)
        value_weight = np.where(np.isfinite(distance) & (variance > 0), np.exp((-0.5 * np.square(distance)) / variance), 0.0)
        sum_of_weights = np.sum(value_weight, axis=0)
        weighted_values = np.sum(source_values * value_weight, axis=0).astype(np.float32)
        valid_mask = moving_mask & (sum_of_weights > 0)
        weighted_values[valid_mask] = self.efficiency_factor * (weighted_values[valid_mask] / sum_of_weights[valid_mask])
        return weighted_values.astype(np.float32)

    @staticmethod
    def _append_scalar_aux_coords(
        coords: dict,
        field: Optional[xr.DataArray],
        coord_names: Tuple[str, ...] = ("time", "forecast_reference_time", "forecast_period"),
    ) -> None:
        """将场上的标量或单元素辅助坐标写入输出坐标字典。"""
        if field is None:
            return
        for coord_name in coord_names:
            if coord_name in coords or coord_name not in field.coords:
                continue
            coord_value = field.coords[coord_name]
            coord_arr = np.asarray(coord_value.values)
            if coord_arr.ndim == 0:
                coords[coord_name] = coord_value
            elif coord_arr.ndim == 1 and coord_arr.size == 1:
                coords[coord_name] = coord_arr.reshape(())

    @staticmethod
    def _build_output_dataarray(
        values: np.ndarray,
        topography_2d: ArrayLike,
        *,
        topography_template_6d: Optional[xr.DataArray] = None,
        aux_coord_source: Optional[xr.DataArray] = None,
    ) -> xr.DataArray:
        """构造输出结果并在可用时重组为标准六维网格。

        计算内核输出为二维 ``numpy`` 数组，其空间尺寸与压维后地形一致。

        - 六维重组：仅使用压维前保存的 ``topography_template_6d``；
        - 二维输出：空间坐标来自 ``topography_2d``；
        - 时间类辅助坐标：优先地形，其次六维地形模板，最后 ``aux_coord_source``
          （通常为已对齐到地形网格的气象场，如 ``temperature_da``）。
        """
        attrs = {"units": "m s-1", "long_name": "orographic_enhancement"}
        value_array = np.asarray(values, dtype=np.float32)

        if (
            isinstance(topography_template_6d, xr.DataArray)
            and set(topography_template_6d.dims) == set(_MEB_REQUIRED_DIMS)
            and rebuild_to_meb_griddata is not None
        ):
            template_6d = topography_template_6d.transpose(*_MEB_REQUIRED_DIMS)
            try:
                rebuilt = rebuild_to_meb_griddata(
                    value_array,
                    template_6d,
                    name="orographic_enhancement",
                    units="m s-1",
                )
                rebuilt.attrs.pop("standard_name", None)
                rebuilt.attrs["long_name"] = "orographic_enhancement"
                return rebuilt
            except Exception as exc:
                raise RuntimeError(
                    "六维重组失败："
                    f"template_shape={tuple(np.asarray(template_6d).shape)}, "
                    f"output_shape={tuple(value_array.shape)}"
                ) from exc

        if isinstance(topography_2d, xr.DataArray):
            topography_2d = _sort_spatial_dataarray(topography_2d)
            y_name, x_name = _get_spatial_coord_names(topography_2d)
            coords = {
                y_name: topography_2d.coords[y_name],
                x_name: topography_2d.coords[x_name],
            }
            OrographicEnhancement._append_scalar_aux_coords(coords, topography_2d)
            OrographicEnhancement._append_scalar_aux_coords(coords, topography_template_6d)
            OrographicEnhancement._append_scalar_aux_coords(coords, aux_coord_source)

            if "grid_mapping" in topography_2d.attrs:
                attrs["grid_mapping"] = topography_2d.attrs["grid_mapping"]
            return xr.DataArray(
                value_array,
                coords=coords,
                dims=(y_name, x_name),
                attrs=attrs,
                name="orographic_enhancement",
            )
        return xr.DataArray(value_array, attrs=attrs)

    def process(self, temperature: ArrayLike, humidity: ArrayLike, pressure: ArrayLike, uwind: ArrayLike, vwind: ArrayLike, topography: ArrayLike) -> xr.DataArray:
        """在目标地形网格上计算地形增强结果。

        功能说明
        ----------
        统一输入单位和网格后，计算迎风抬升、格点增强与上游贡献，
        最终输出地形增强场。

        参数
        ----------
        temperature : ArrayLike
            温度场。
        humidity : ArrayLike
            相对湿度场。
        pressure : ArrayLike
            气压场。
        uwind : ArrayLike
            网格 x 方向风分量。
        vwind : ArrayLike
            网格 y 方向风分量。
        topography : ArrayLike
            地形高度场，也是目标输出网格。

        返回值
        -------
        xr.DataArray
            地形增强结果，单位为 ``m s-1``。
            若地形为六维单场，输出重组为标准六维网格；否则输出二维场。
        """
        # 主流程依次完成单位统一、迎风抬升计算、格点增强和上游贡献叠加。
        # 计算结果与地形 lat/lon 一致；六维模板仅取自压维前的地形场。
        topography_template_6d: Optional[xr.DataArray] = None
        if isinstance(topography, xr.DataArray) and set(topography.dims) == set(_MEB_REQUIRED_DIMS):
            topography_template_6d = topography.transpose(*_MEB_REQUIRED_DIMS)
        temperature = _normalize_to_2d_field(temperature, "temperature")
        humidity = _normalize_to_2d_field(humidity, "humidity")
        pressure = _normalize_to_2d_field(pressure, "pressure")
        uwind = _normalize_to_2d_field(uwind, "uwind")
        vwind = _normalize_to_2d_field(vwind, "vwind")
        topography = _normalize_to_2d_field(topography, "topography")
        topography_values, topography_units, topography_da = _prepare_input(topography, "m")
        if topography_values.ndim != 2:
            raise ValueError("topography 必须是二维场")
        topography_values = _convert_units(topography_values, topography_units, "m").astype(np.float32)
        target_grid = topography_da if isinstance(topography_da, xr.DataArray) else None
        temperature_values, temperature_da, temperature_units = self._prepare_field(temperature, "K", target_grid)
        humidity_values, _, humidity_units = self._prepare_field(humidity, "1", target_grid)
        pressure_values, _, pressure_units = self._prepare_field(pressure, "Pa", target_grid)
        uwind_values, _, uwind_units = self._prepare_field(uwind, "m s-1", target_grid)
        vwind_values, _, vwind_units = self._prepare_field(vwind, "m s-1", target_grid)
        for name, values in {"temperature": temperature_values, "humidity": humidity_values, "pressure": pressure_values, "uwind": uwind_values, "vwind": vwind_values}.items():
            if values.ndim != 2:
                raise ValueError(f"{name} 必须是二维场")
            if values.shape != topography_values.shape:
                raise ValueError(f"{name} 与 topography 的形状不一致")
        temperature_values = _convert_units(temperature_values, temperature_units, "K").astype(np.float32)
        humidity_values = _convert_units(humidity_values, humidity_units, "1").astype(np.float32)
        pressure_values = _convert_units(pressure_values, pressure_units, "Pa").astype(np.float32)
        uwind_values = _convert_units(uwind_values, uwind_units, "m s-1").astype(np.float32)
        vwind_values = _convert_units(vwind_values, vwind_units, "m s-1").astype(np.float32)
        if target_grid is not None:
            y_spacing_m, x_spacing_m = _grid_spacings_meters(target_grid)
        else:
            y_spacing_m, x_spacing_m = 1000.0, 1000.0
        self.temperature = temperature_values
        self.humidity = humidity_values
        self.pressure = pressure_values
        self.uwind = uwind_values
        self.vwind = vwind_values
        self.topography = topography_values
        self.grid_spacing_km = float((x_spacing_m + y_spacing_m) / 2.0 / 1000.0)
        vgradz = self._calculate_vgradz(self.uwind, self.vwind, self.topography, y_spacing_m, x_spacing_m)
        mask = self._generate_mask(self.topography, self.humidity, vgradz)
        svp = calculate_svp_in_air(self.temperature, self.pressure)
        point_orogenh = self._point_orogenh(self.temperature, self.humidity, svp, vgradz, mask)
        orogenh_mmh = self._add_upstream_component(point_orogenh)
        orogenh_ms = (orogenh_mmh / 3600000.0).astype(np.float32)
        return self._build_output_dataarray(
            orogenh_ms,
            topography,
            topography_template_6d=topography_template_6d,
            aux_coord_source=temperature_da,
        )
