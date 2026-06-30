#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""适配 meteva_base 的邻域处理算法。

本模块迁移自 Improver 的 nbhood 算法，实现了面向 ``xarray.DataArray``
与 ``numpy.ndarray`` 的邻域平均、邻域求和和邻域百分位计算。
"""

from typing import Any, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
import xarray as xr
from numpy import ndarray
from scipy.ndimage import correlate
try:
    from cf_units import Unit
except Exception:
    Unit = None
try:
    from pyproj import CRS, Transformer
except Exception:
    CRS = None
    Transformer = None

from ..utils.utils import check_for_meb_griddata, rebuild_to_meb_griddata
from .meta_nbhood_utils import radius_by_lead_time

# 默认百分位序列
DEFAULT_PERCENTILES = (10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0)

__all__ = [
    "BaseNeighbourhoodProcessing",
    "GeneratePercentilesFromANeighbourhood",
    "NeighbourhoodProcessing",
    "check_radius_against_distance",
    "circular_kernel",
]

SUPPORTED_DISTANCE_UNITS = {
    "m": 1.0,
    "metre": 1.0,
    "metres": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "km": 1000.0,
    "kilometre": 1000.0,
    "kilometres": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
}
EARTH_METRES_PER_DEGREE = 111195.0
DEFAULT_OUTPUT_NAME = "neighbourhood_result"

SUPPORTED_TIME_UNITS = {
    "h": 1.0,
    "hr": 1.0,
    "hrs": 1.0,
    "hour": 1.0,
    "hours": 1.0,
    "s": 1.0 / 3600.0,
    "sec": 1.0 / 3600.0,
    "secs": 1.0 / 3600.0,
    "second": 1.0 / 3600.0,
    "seconds": 1.0 / 3600.0,
}
MEB_DIMS = ("member", "level", "time", "dtime", "lat", "lon")


def _normalise_unit(unit: Optional[str]) -> str:
    """统一单位字符串。"""
    if unit is None:
        return ""
    return unit.strip().lower()


def _convert_with_cf_units(
    values: ndarray, from_unit: Optional[str], to_unit: str
) -> Optional[ndarray]:
    """使用 cf_units 做单位转换，失败返回 None。"""
    if Unit is None:
        return None
    if from_unit is None or str(from_unit).strip() == "":
        return None
    try:
        source = Unit(str(from_unit))
        target = Unit(to_unit)
        return np.asarray(source.convert(np.asarray(values, dtype=np.float64), target))
    except Exception:
        return None


def _convert_distance_values(values: ndarray, unit: Optional[str]) -> ndarray:
    """将距离值转换为米。"""
    converted = _convert_with_cf_units(values, unit, "m")
    if converted is not None:
        return converted
    normalised = _normalise_unit(unit)
    if normalised not in SUPPORTED_DISTANCE_UNITS:
        raise ValueError(f"无法识别的空间坐标单位: {unit}")
    return np.asarray(values, dtype=np.float64) * SUPPORTED_DISTANCE_UNITS[normalised]


def _infer_spatial_unit(
    unit: Optional[str], coord_name: str, points: ndarray
) -> Optional[str]:
    """推断空间坐标单位，优先使用显式单位。"""
    normalised = _normalise_unit(unit)
    if normalised:
        return normalised

    lower_name = coord_name.lower()
    if lower_name in ("lat", "latitude"):
        return "degree_north"
    if lower_name in ("lon", "longitude"):
        return "degree_east"

    # 当维度名不标准时，避免盲猜导致空间语义错误。
    # 保留严格行为：让调用方补充单位信息。
    _ = points
    return None


def _convert_time_values_to_hours(values: ndarray, unit: Optional[str]) -> ndarray:
    """将时效值转换为小时。"""
    converted = _convert_with_cf_units(values, unit, "hours")
    if converted is not None:
        return converted
    normalised = _normalise_unit(unit)
    if normalised == "":
        return np.asarray(values, dtype=np.float64)
    if normalised not in SUPPORTED_TIME_UNITS:
        raise ValueError(f"无法识别的时效单位: {unit}")
    return np.asarray(values, dtype=np.float64) * SUPPORTED_TIME_UNITS[normalised]


def _rolling_window(
    input_array: ndarray, shape: Tuple[int, int], writeable: bool = False
) -> ndarray:
    """在最后两个维度上构造滚动窗口视图。"""
    num_window_dims = len(shape)
    num_arr_dims = len(input_array.shape)
    if num_arr_dims < num_window_dims:
        raise ValueError("输入数组维度少于窗口维度")
    out_shape = (
        *input_array.shape[:-num_window_dims],
        *(
            arr_dim - win_dim + 1
            for arr_dim, win_dim in zip(input_array.shape[-num_window_dims:], shape)
        ),
        *shape,
    )
    if any(dim <= 0 for dim in out_shape):
        raise RuntimeError("窗口尺寸大于输入数组尺寸")
    strides = input_array.strides + input_array.strides[-num_window_dims:]
    return np.lib.stride_tricks.as_strided(
        input_array, shape=out_shape, strides=strides, writeable=writeable
    )


def _pad_and_roll(
    input_array: ndarray, shape: Tuple[int, int], **kwargs: Any
) -> ndarray:
    """先 pad 再构造滚动窗口。"""
    writeable = kwargs.pop("writeable", False)
    pad_extent = [(0, 0)] * (input_array.ndim - len(shape))
    pad_extent.extend((dim // 2, dim // 2) for dim in shape)
    padded = np.pad(input_array, pad_extent, **kwargs)
    return _rolling_window(padded, shape, writeable=writeable)


def _pad_boxsum(
    data: ndarray, boxsize: Union[int, Tuple[int, int]], **pad_options: Any
) -> ndarray:
    """为 boxsum 生成所需 padding。"""
    boxsize = np.atleast_1d(boxsize)
    ih, jh = boxsize[0] // 2, boxsize[-1] // 2
    padding = [(0, 0)] * (data.ndim - 2) + [(ih + 1, ih), (jh + 1, jh)]
    return np.pad(data, padding, **pad_options)


def _boxsum(
    data: ndarray,
    boxsize: Union[int, Tuple[int, int]],
    cumsum: bool = True,
    **pad_options: Any,
) -> ndarray:
    """快速计算方形邻域内求和。"""
    boxsize = np.atleast_1d(boxsize)
    if not issubclass(boxsize.dtype.type, np.integer):
        raise ValueError("邻域尺寸必须是整数")
    if not np.all(boxsize % 2):
        raise ValueError("邻域尺寸必须为奇数")
    if pad_options:
        data = _pad_boxsum(data, boxsize, **pad_options)
    if cumsum:
        data = data.cumsum(-2).cumsum(-1)
    i, j = boxsize[0], boxsize[-1]
    m, n = data.shape[-2] - i, data.shape[-1] - j
    return (
        data[..., i : i + m, j : j + n]
        - data[..., :m, j : j + n]
        + data[..., :m, :n]
        - data[..., i : i + m, :n]
    )


def _as_iterable(value: Union[float, Sequence[float]]) -> Iterable[float]:
    """将标量或序列统一为可迭代对象。"""
    if isinstance(value, (list, tuple, np.ndarray)):
        return value
    return [value]


def _extract_data_array(data: Union[xr.DataArray, ndarray]) -> ndarray:
    """提取底层数组。"""
    if isinstance(data, xr.DataArray):
        return np.asanyarray(data.values)
    return np.asanyarray(data)


def _as_plain_array(values: Union[np.ndarray, np.ma.MaskedArray]) -> np.ndarray:
    """将普通数组或掩码数组统一为可重组的普通数组。"""
    if np.ma.isMaskedArray(values):
        return np.asarray(np.ma.filled(values, np.nan), dtype=np.float32)
    return np.asarray(values, dtype=np.float32)


def _rebuild_like_meb_template(
    result_values: Union[np.ndarray, np.ma.MaskedArray],
    template: xr.DataArray,
    *,
    name: Optional[str] = None,
    units: Optional[str] = None,
) -> xr.DataArray:
    """按 meb 六维模板重组输出。"""
    output_name = name if name is not None else template.name
    if output_name is None:
        output_name = DEFAULT_OUTPUT_NAME
    return rebuild_to_meb_griddata(
        _as_plain_array(result_values),
        template,
        name=output_name,
        units=units if units is not None else str(template.attrs.get("units", "")),
    )


def _validate_no_nan(data: ndarray) -> None:
    """检查未掩码数据中是否存在 NaN。"""
    if np.ma.isMaskedArray(data):
        values = np.ma.getdata(data)
        mask = np.ma.getmaskarray(data)
        if np.isnan(values[~mask]).any():
            raise ValueError("输入数据中存在未掩码的 NaN 值。")
    elif np.isnan(data).any():
        raise ValueError("输入数据中存在未掩码的 NaN 值。")


def _broadcast_mask(
    mask: Optional[Union[xr.DataArray, ndarray]], target_shape: Tuple[int, ...]
) -> Optional[ndarray]:
    """将掩码广播到目标形状。"""
    if mask is None:
        return None
    mask_array = _extract_data_array(mask)
    try:
        return np.broadcast_to(mask_array, target_shape)
    except ValueError as exc:
        raise ValueError(
            f"mask 形状 {mask_array.shape} 无法广播到输入数据形状 {target_shape}"
        ) from exc


def _get_xarray_spatial_coords(data: xr.DataArray) -> Tuple[ndarray, ndarray]:
    """获取 xarray 最后两个空间坐标。"""
    if data.ndim < 2:
        raise ValueError("输入数据至少需要两个空间维度")
    y_dim, x_dim = data.dims[-2], data.dims[-1]
    if y_dim not in data.coords or x_dim not in data.coords:
        raise ValueError("xarray 输入最后两个维度必须具有同名一维坐标")
    y_coord = data.coords[y_dim]
    x_coord = data.coords[x_dim]
    if y_coord.ndim != 1 or x_coord.ndim != 1:
        raise ValueError("空间坐标必须为一维")
    return np.asarray(y_coord.values), np.asarray(x_coord.values)


def _calculate_equal_spacing(
    points: ndarray, unit: Optional[str], coord_name: str
) -> float:
    """检查一维坐标是否等间距并返回米制间距。"""
    points_in_metres = _convert_distance_values(points, unit)
    diffs = np.abs(np.diff(points_in_metres))
    if diffs.size == 0:
        raise ValueError(f"{coord_name} 坐标长度不足，无法计算网格间距")
    spacing = float(np.mean(diffs))
    if not np.allclose(diffs, spacing, rtol=1.0e-5, atol=0.0):
        raise ValueError(f"{coord_name} 坐标不是等间距网格")
    return spacing


def _infer_grid_spacing_from_xarray(
    data: xr.DataArray,
) -> Tuple[float, ndarray, ndarray]:
    """从 xarray 自动推断网格间距与空间坐标。"""
    y_dim, x_dim = data.dims[-2], data.dims[-1]
    y_coord = data.coords[y_dim]
    x_coord = data.coords[x_dim]
    y_points, x_points = _get_xarray_spatial_coords(data)
    y_unit = _infer_spatial_unit(y_coord.attrs.get("units"), y_dim, y_points)
    x_unit = _infer_spatial_unit(x_coord.attrs.get("units"), x_dim, x_points)

    if y_unit is None or x_unit is None:
        raise ValueError(
            f"无法识别的空间坐标单位: y={y_coord.attrs.get('units')}, x={x_coord.attrs.get('units')}。"
            "请为坐标补充 units，或使用标准维度名 lat/lon。"
        )

    y_is_degree = "degree" in y_unit
    x_is_degree = "degree" in x_unit

    # 经纬度网格：优先根据 grid_mapping 投影到米制坐标，失败后回退局地近似。
    if y_is_degree and x_is_degree:
        transformed = _project_latlon_to_metres(data, y_points, x_points)
        if transformed is not None:
            y_metres, x_metres = transformed
            y_spacing = _calculate_equal_spacing(y_metres, "m", y_dim)
            x_spacing = _calculate_equal_spacing(x_metres, "m", x_dim)
            if not np.isclose(y_spacing, x_spacing, rtol=5.0e-2, atol=0.0):
                raise ValueError("x 和 y 方向的网格间距必须一致")
            return float((x_spacing + y_spacing) / 2.0), y_metres, x_metres

        y_diffs = np.abs(np.diff(np.asarray(y_points, dtype=np.float64)))
        x_diffs = np.abs(np.diff(np.asarray(x_points, dtype=np.float64)))
        if y_diffs.size == 0 or x_diffs.size == 0:
            raise ValueError("空间坐标长度不足，无法计算网格间距")
        y_step = float(np.mean(y_diffs))
        x_step = float(np.mean(x_diffs))
        if not np.allclose(y_diffs, y_step, rtol=1.0e-5, atol=0.0):
            raise ValueError(f"{y_dim} 坐标不是等间距网格")
        if not np.allclose(x_diffs, x_step, rtol=1.0e-5, atol=0.0):
            raise ValueError(f"{x_dim} 坐标不是等间距网格")

        mean_lat = float(np.mean(np.asarray(y_points, dtype=np.float64)))
        cos_lat = np.cos(np.deg2rad(mean_lat))
        if np.isclose(cos_lat, 0.0):
            raise ValueError("纬度过高导致经向距离换算不稳定")

        y_spacing = y_step * EARTH_METRES_PER_DEGREE
        x_spacing = x_step * EARTH_METRES_PER_DEGREE * cos_lat
        if not np.isclose(y_spacing, x_spacing, rtol=5.0e-2, atol=0.0):
            raise ValueError("x 和 y 方向的网格间距必须一致")

        y0 = float(y_points[0])
        x0 = float(x_points[0])
        y_metres = (np.asarray(y_points, dtype=np.float64) - y0) * EARTH_METRES_PER_DEGREE
        x_metres = (np.asarray(x_points, dtype=np.float64) - x0) * EARTH_METRES_PER_DEGREE * cos_lat
        return float((x_spacing + y_spacing) / 2.0), y_metres, x_metres

    # 投影坐标：要求显式可换算的距离单位（m/km 等）。
    y_spacing = _calculate_equal_spacing(y_points, y_unit, y_dim)
    x_spacing = _calculate_equal_spacing(x_points, x_unit, x_dim)
    if not np.isclose(y_spacing, x_spacing):
        raise ValueError("x 和 y 方向的网格间距必须一致")
    y_metres = _convert_distance_values(y_points, y_unit)
    x_metres = _convert_distance_values(x_points, x_unit)
    return x_spacing, y_metres, x_metres


def _project_latlon_to_metres(
    data: xr.DataArray, y_points: ndarray, x_points: ndarray
) -> Optional[Tuple[ndarray, ndarray]]:
    """若存在可解析的 grid_mapping，则将 lat/lon 投影为米制 x/y。"""
    if CRS is None or Transformer is None:
        return None

    mapping_name = data.attrs.get("grid_mapping")
    if not isinstance(mapping_name, str) or mapping_name == "":
        return None
    if mapping_name not in data.coords:
        return None

    mapping = data.coords[mapping_name]
    mapping_attrs = dict(mapping.attrs)
    if not mapping_attrs:
        return None

    try:
        if "crs_wkt" in mapping_attrs and mapping_attrs["crs_wkt"]:
            target_crs = CRS.from_wkt(mapping_attrs["crs_wkt"])
        else:
            target_crs = CRS.from_cf(mapping_attrs)
    except Exception:
        return None

    try:
        transformer = Transformer.from_crs(CRS.from_epsg(4326), target_crs, always_xy=True)
        lon2d, lat2d = np.meshgrid(
            np.asarray(x_points, dtype=np.float64),
            np.asarray(y_points, dtype=np.float64),
        )
        x_proj, y_proj = transformer.transform(lon2d, lat2d)
        y_m = np.asarray(np.nanmean(y_proj, axis=1), dtype=np.float64)
        x_m = np.asarray(np.nanmean(x_proj, axis=0), dtype=np.float64)
        return y_m, x_m
    except Exception:
        return None


def _parse_grid_spacing(
    grid_spacing: Optional[Union[float, Tuple[float, float]]]
) -> Tuple[float, float]:
    """解析显式传入的网格间距。"""
    if grid_spacing is None:
        raise ValueError("numpy.ndarray 输入必须显式提供 grid_spacing")
    if np.isscalar(grid_spacing):
        spacing = float(grid_spacing)
        if spacing <= 0:
            raise ValueError("grid_spacing 必须为正数")
        return spacing, spacing
    if len(grid_spacing) != 2:
        raise ValueError("grid_spacing 必须是标量或长度为 2 的序列")
    y_spacing = float(grid_spacing[0])
    x_spacing = float(grid_spacing[1])
    if y_spacing <= 0 or x_spacing <= 0:
        raise ValueError("grid_spacing 必须为正数")
    return y_spacing, x_spacing


def _distance_to_number_of_grid_cells(radius: float, grid_spacing: float) -> int:
    """根据半径与网格间距计算网格点数。"""
    if radius <= 0:
        raise ValueError(f"邻域半径必须为正数，当前值为 {radius} 米")
    grid_cells = int(np.ceil(radius / grid_spacing))
    if grid_cells == 0:
        raise ValueError(f"邻域半径 {radius} 米对应的网格范围为 0")
    return grid_cells


def _extract_lead_times_from_xarray(data: xr.DataArray) -> ndarray:
    """自动读取 xarray 中的时效坐标。"""
    coord_candidates = (
        "forecast_period",
        "lead_time",
        "input_lead_times",
        "cube_lead_times",
    )
    for name in coord_candidates:
        if name in data.coords:
            coord = data.coords[name]
            return _convert_time_values_to_hours(coord.values, coord.attrs.get("units"))
    attr_candidates = (
        "forecast_period",
        "lead_time",
        "input_lead_times",
        "cube_lead_times",
    )
    for name in attr_candidates:
        if name in data.attrs:
            values = np.asarray(data.attrs[name])
            units = data.attrs.get(f"{name}_units", "hours")
            return _convert_time_values_to_hours(values, units)
    raise ValueError("xarray 输入未找到可识别的 forecast_period / lead_time 信息")


def _slice_lead_times_for_reshaped_data(
    input_lead_times: ndarray, leading_shape: Tuple[int, ...], y_size: int, x_size: int
) -> Optional[ndarray]:
    """将时效信息整理到前导维。"""
    if input_lead_times is None:
        return None
    input_lead_times = np.asarray(input_lead_times, dtype=np.float64)
    if leading_shape == ():
        if input_lead_times.ndim == 0:
            return input_lead_times.reshape(1)
        if input_lead_times.shape == (1,):
            return input_lead_times
        raise ValueError("input_lead_times 与输入前导维度不匹配")
    if input_lead_times.shape == leading_shape:
        return input_lead_times.reshape(-1)
    if input_lead_times.shape == (*leading_shape, y_size, x_size):
        return input_lead_times.reshape(-1, y_size, x_size)[..., 0, 0]
    raise ValueError("input_lead_times 形状与输入数据不匹配")


def check_radius_against_distance(
    radius: float,
    y_coords: Optional[ndarray] = None,
    x_coords: Optional[ndarray] = None,
    shape: Optional[Tuple[int, int]] = None,
    grid_spacing: Optional[Union[float, Tuple[float, float]]] = None,
) -> None:
    """检查邻域半径不超过空间域尺寸。"""
    if y_coords is not None and x_coords is not None:
        y_extent = float(np.max(y_coords) - np.min(y_coords))
        x_extent = float(np.max(x_coords) - np.min(x_coords))
    elif shape is not None and grid_spacing is not None:
        y_spacing, x_spacing = _parse_grid_spacing(grid_spacing)
        y_extent = (shape[0] - 1) * y_spacing
        x_extent = (shape[1] - 1) * x_spacing
    else:
        raise ValueError("必须提供空间坐标或 shape + grid_spacing")
    max_allowed = np.sqrt(x_extent**2 + y_extent**2) * 0.5
    if radius > max_allowed:
        raise ValueError(f"邻域半径 {radius} 米超过空间域允许的最大距离 {max_allowed} 米")


def circular_kernel(ranges: int, weighted_mode: bool) -> ndarray:
    """构造圆形邻域核。"""
    area = ranges * ranges
    kernel = np.ones((int(1 + ranges * 2), int(1 + ranges * 2)), dtype=np.float64)
    open_grid = np.array(
        np.ogrid[[slice(-x, x + 1) for x in (ranges, ranges)]], dtype=object
    )
    if weighted_mode:
        open_grid_summed_squared = np.sum(open_grid**2.0).astype(float)
        kernel[:] = (area - open_grid_summed_squared) / area
        mask = kernel < 0.0
    else:
        mask = np.reshape(np.sum(open_grid**2) > area, kernel.shape)
    kernel[mask] = 0.0
    return kernel


class BaseNeighbourhoodProcessing:
    """邻域处理基础类。

    负责邻域算法共享的前置逻辑：
      1. 校验半径与时效参数
      2. 检查输入中的未掩码 NaN
      3. 在配置 ``lead_times`` 时按输入时效插值得到当前半径
      4. 在工具可用时校验 xarray 网格格式

    Parameters
    ----------
    radii : float or list[float]
        邻域半径，单位米。
    lead_times : list[int], optional
        与 ``radii`` 对应的时效序列，单位小时。必须与 radii 长度一致。

    Raises
    ------
    ValueError
        当 radii 与 lead_times 长度不一致时。

    Notes
    -----
    本类不执行具体的邻域统计计算，仅为子类提供共享的输入校验和半径插值功能。
    """

    def __init__(
        self, radii: Union[float, List[float]], lead_times: Optional[List[int]] = None
    ) -> None:
        radius_or_radii, parsed_lead_times = radius_by_lead_time(radii, lead_times)
        if isinstance(radius_or_radii, list):
            self.radii = [float(x) for x in radius_or_radii]
        else:
            self.radius = float(radius_or_radii)
            self.radii = [self.radius]
        self.lead_times = parsed_lead_times
        if self.lead_times is not None and len(self.radii) != len(self.lead_times):
            raise ValueError(
                "radii 与 lead_times 的长度不一致，无法继续处理。"
            )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.process(*args, **kwargs)

    def _find_radii(self, input_lead_times: Optional[ndarray] = None) -> Union[float, ndarray]:
        """根据时效插值获取半径。

        参数
        ----------
        input_lead_times : ndarray, optional
            输入数据对应的时效，单位为小时。

        返回值
        -------
        float 或 ndarray
            插值后的邻域半径。
        """
        if input_lead_times is None:
            raise ValueError("设置了 lead_times 时必须提供 input_lead_times")
        return np.interp(input_lead_times, self.lead_times, self.radii)

    def process(
        self,
        data: Union[xr.DataArray, ndarray],
        input_lead_times: Optional[Union[float, ndarray]] = None,
    ) -> Union[xr.DataArray, ndarray]:
        """
        执行基础输入校验并准备当前半径。

        本方法不执行邻域统计，只完成前置处理并原样返回输入对象，
        供子类继续计算。

        参数
        ----------
        data : xr.DataArray 或 ndarray
            输入数据。
        input_lead_times : float 或 ndarray, optional
            输入时效（小时）。当配置 ``lead_times`` 且输入为 ndarray 时，
            必须显式提供。

        返回
        -------
        xr.DataArray 或 ndarray
            原样返回输入对象。
        """
        # 对 xarray 输入做 meteva_base 六维网格强校验，维度缺失直接报错。
        if isinstance(data, xr.DataArray):
            data = check_for_meb_griddata(data)

        values = _extract_data_array(data)
        _validate_no_nan(values)

        if self.lead_times is not None:
            if input_lead_times is None:
                if isinstance(data, xr.DataArray):
                    input_lead_times = _extract_lead_times_from_xarray(data)
                else:
                    raise ValueError(
                        "numpy.ndarray 输入在设置 lead_times 时必须显式提供 "
                        "input_lead_times"
                    )
            lead_values = np.asarray(input_lead_times, dtype=np.float64)
            self.radius = self._find_radii(input_lead_times=lead_values)
        return data


class NeighbourhoodProcessing(BaseNeighbourhoodProcessing):
    """邻域均值/邻域和处理插件。

    以输入最后两维作为空间维 (y, x)，按前导维逐片执行邻域统计。
    支持方形/圆形邻域、可选加权圆核、外部掩码与输出重掩码。

    Parameters
    ----------
    neighbourhood_method : {"square", "circular"}
        邻域形状：
        - "square": 方形邻域
        - "circular": 圆形邻域
    radii : float or list[float]
        邻域半径，单位米。
    lead_times : list[int], optional
        与 radii 对应的时效序列，单位小时。
    weighted_mode : bool, default=False
        是否使用加权圆核，仅在 ``neighbourhood_method="circular"`` 时有效。
    sum_only : bool, default=False
        输出类型控制：
        - True: 输出邻域和
        - False: 输出邻域均值
    re_mask : bool, default=True
        是否在输出中恢复输入无效点掩码。

    Raises
    ------
    ValueError
        1. neighbourhood_method 不是 "square" 或 "circular"
        2. weighted_mode 为 True 但 neighbourhood_method 不是 "circular"
        3. 邻域半径超过空间域允许的最大距离
        4. 空间坐标不是等间距网格
        5. x 和 y 方向的网格间距不一致

    Notes
    -----
    1. 对于 xarray.DataArray 输入，会自动推断网格间距和空间坐标。
    2. 对于 numpy.ndarray 输入，必须显式提供 grid_spacing 参数。
    3. 当输入为标准 meb 六维 xarray.DataArray 时，输出会重组为六维 xarray，
       保持维度顺序为 ("member", "level", "time", "dtime", "lat", "lon")。
    4. 加权圆形邻域核的权重由公式 ``(area - r²)/area`` 计算，其中 r 为到中心点的距离。

    Examples
    --------
    >>> import numpy as np
    >>> from nbhood import NeighbourhoodProcessing
    >>> 
    >>> # 创建示例数据
    >>> data = np.random.rand(10, 20, 30)  # 前导维 + 空间维
    >>> 
    >>> # 圆形邻域均值，半径 2000 米
    >>> processor = NeighbourhoodProcessing(
    ...     neighbourhood_method="circular",
    ...     radii=2000.0
    ... )
    >>> result = processor.process(data, grid_spacing=1000.0)
    """

    def __init__(
        self,
        neighbourhood_method: str,
        radii: Union[float, List[float]],
        lead_times: Optional[List[int]] = None,
        weighted_mode: bool = False,
        sum_only: bool = False,
        re_mask: bool = True,
    ) -> None:
        super().__init__(radii, lead_times=lead_times)
        if neighbourhood_method not in ["square", "circular"]:
            raise ValueError(
                f"neighbourhood_method 仅支持 'square' 或 'circular'，当前为 {neighbourhood_method}。"
            )
        if weighted_mode and neighbourhood_method != "circular":
            raise ValueError(
                "weighted_mode 只能与 circular 邻域配合使用，"
                f"当前 neighbourhood_method 为 {neighbourhood_method}。"
            )
        self.neighbourhood_method = neighbourhood_method
        self.weighted_mode = weighted_mode
        self.sum_only = sum_only
        self.re_mask = re_mask
        self.nb_size = 0
        self.kernel: Optional[ndarray] = None

    def _calculate_neighbourhood(
        self, data: ndarray, mask: Optional[ndarray] = None
    ) -> Union[ndarray, np.ma.MaskedArray]:
        """对单个二维切片执行邻域处理。"""
        is_complex = issubclass(data.dtype.type, np.complexfloating)
        if self.neighbourhood_method == "circular" and is_complex:
            raise ValueError("circular 邻域不支持复数输入。")
        if not self.sum_only and not is_complex:
            if np.ma.isMaskedArray(data):
                raw_values = np.ma.getdata(data)
                raw_mask = np.ma.getmaskarray(data)
                valid_values = raw_values[~raw_mask]
                min_val = np.nanmin(valid_values)
                max_val = np.nanmax(valid_values)
            else:
                min_val = np.nanmin(np.asarray(data))
                max_val = np.nanmax(np.asarray(data))

        data_mask = mask == 0 if mask is not None else np.zeros(data.shape, dtype=bool)
        if isinstance(data, np.ma.MaskedArray):
            data_mask = data_mask | np.ma.getmaskarray(data)
            data = data.data

        if is_complex:
            loc_data_dtype = np.complex128
            out_data_dtype = np.complex64
        else:
            loc_data_dtype = np.float64
            out_data_dtype = np.float32
        data = np.array(data, dtype=loc_data_dtype)

        mask_type = np.float32 if self.neighbourhood_method == "circular" else np.int64
        valid_data_mask = np.ones(data.shape, dtype=mask_type)
        valid_data_mask[data_mask] = 0
        data[data_mask] = 0

        if self.sum_only:
            max_extreme_data = None
        else:
            # 先统计邻域内有效点数量，后续平均值计算要用它做分母。
            area_sum = self._do_nbhood_sum(valid_data_mask)
            max_extreme_data = area_sum.astype(loc_data_dtype)

        data = self._do_nbhood_sum(data, max_extreme=max_extreme_data)

        if not self.sum_only:
            with np.errstate(divide="ignore", invalid="ignore"):
                data = data / area_sum
            data[area_sum == 0] = np.nan
            if not is_complex:
                data = data.clip(min_val, max_val)

        if self.re_mask:
            data = np.ma.masked_array(data, data_mask, copy=False)

        return data.astype(out_data_dtype)

    def _do_nbhood_sum(
        self, data: np.ndarray, max_extreme: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """计算单个二维切片的邻域和。"""
        data_shape = data.shape
        ystart = xstart = 0
        ystop, xstop = data.shape
        size = data.size
        extreme = 0
        fill_value = 0
        half_nb_size = self.nb_size // 2

        for _extreme, _fill_value in {0: 0, 1: max_extreme}.items():
            if _fill_value is None or issubclass(data.dtype.type, np.complexfloating):
                continue
            # 仅在包含有效信号的最小外接窗口上做邻域计算，减少大面积零值场的开销。
            nonextreme_indices = np.argwhere(data != _extreme)
            if nonextreme_indices.size == 0:
                _ystart = _ystop = _xstart = _xstop = 0
            else:
                (_ystart, _xstart), (_ystop, _xstop) = (
                    nonextreme_indices.min(0),
                    nonextreme_indices.max(0) + 1,
                )
                _ystart = max(0, _ystart - half_nb_size)
                _ystop = min(data_shape[0], _ystop + half_nb_size)
                _xstart = max(0, _xstart - half_nb_size)
                _xstop = min(data_shape[1], _xstop + half_nb_size)
            _size = (_ystop - _ystart) * (_xstop - _xstart)
            if _size < size:
                size, extreme, fill_value, ystart, ystop, xstart, xstop = (
                    _size,
                    _extreme,
                    _fill_value,
                    _ystart,
                    _ystop,
                    _xstart,
                    _xstop,
                )

        if size != data.size:
            if isinstance(fill_value, np.ndarray):
                untrimmed = fill_value.astype(data.dtype)
            else:
                untrimmed = np.full(data_shape, fill_value, dtype=data.dtype)

        if size:
            data = data[ystart:ystop, xstart:xstop]
            if self.neighbourhood_method == "square":
                data = _boxsum(data, self.nb_size, mode="constant", constant_values=extreme)
            else:
                data = correlate(data, self.kernel, mode="nearest")
        else:
            data = untrimmed

        if data.shape != data_shape:
            untrimmed[ystart:ystop, xstart:xstop] = data
            data = untrimmed
        return data

    def process(
        self,
        data: Union[xr.DataArray, ndarray],
        mask: Optional[Union[xr.DataArray, ndarray]] = None,
        input_lead_times: Optional[Union[float, ndarray]] = None,
        grid_spacing: Optional[Union[float, Tuple[float, float]]] = None,
    ) -> Union[xr.DataArray, ndarray]:
        """
        执行邻域均值或邻域和计算。

        处理流程：
        1. 基类校验输入并准备半径；
        2. 展平前导维并逐二维切片批处理；
        3. 推断（或读取）网格间距并将半径换算为格点数；
        4. 逐切片执行方形/圆形邻域统计；
        5. 对标准 meb 六维 xarray 输入重组为六维输出。

        参数
        ----------
        data : xr.DataArray 或 ndarray
            输入数据，最后两维视为空间维。
        mask : xr.DataArray 或 ndarray, optional
            外部掩码，值为 0 的位置视为无效点。
        input_lead_times : float 或 ndarray, optional
            输入时效（小时），用于与 ``lead_times`` 联合确定半径。
        grid_spacing : float 或 tuple[float, float], optional
            ndarray 路径使用的网格间距（米）。xarray 路径通常自动推断。

        返回
        -------
        xr.DataArray 或 ndarray
            邻域处理结果。标准 meb 六维 xarray 输入返回六维 xarray，
            其余场景返回数组结果。
        """
        data = super().process(data, input_lead_times=input_lead_times)
        values = _extract_data_array(data)
        if values.ndim < 2:
            raise ValueError("输入数据至少需要二维空间网格")

        y_size, x_size = values.shape[-2], values.shape[-1]
        leading_shape = values.shape[:-2]
        flat_values = values.reshape((-1, y_size, x_size))
        flat_mask = _broadcast_mask(mask, values.shape)
        if flat_mask is not None:
            flat_mask = flat_mask.reshape((-1, y_size, x_size))

        if isinstance(data, xr.DataArray):
            base_spacing, y_coords, x_coords = _infer_grid_spacing_from_xarray(data)
            spacing_y = spacing_x = base_spacing
            check_radius_against_distance(
                float(np.max(np.atleast_1d(self.radius))),
                y_coords=y_coords,
                x_coords=x_coords,
            )
        else:
            spacing_y, spacing_x = _parse_grid_spacing(grid_spacing)
            check_radius_against_distance(
                float(np.max(np.atleast_1d(self.radius))),
                shape=(y_size, x_size),
                grid_spacing=(spacing_y, spacing_x),
            )

        lead_values = None
        if self.lead_times is not None:
            if input_lead_times is None and isinstance(data, xr.DataArray):
                input_lead_times = _extract_lead_times_from_xarray(data)
            lead_values = _slice_lead_times_for_reshaped_data(
                np.asarray(input_lead_times, dtype=np.float64), leading_shape, y_size, x_size
            )

        output_slices = []
        for index, data_slice in enumerate(flat_values):
            if lead_values is not None:
                current_radius = float(self._find_radii(np.asarray([lead_values[index]]))[0])
            else:
                current_radius = float(self.radius)

            # 半径先换算为整格范围，再根据邻域形状构造核或窗口尺寸。
            grid_spacing_for_radius = max(spacing_y, spacing_x)
            grid_cells = _distance_to_number_of_grid_cells(
                current_radius, grid_spacing_for_radius
            )
            if self.neighbourhood_method == "circular":
                self.kernel = circular_kernel(grid_cells, self.weighted_mode)
                self.nb_size = max(self.kernel.shape)
            else:
                self.nb_size = 2 * grid_cells + 1

            mask_slice = None if flat_mask is None else flat_mask[index]
            output_slices.append(self._calculate_neighbourhood(data_slice, mask_slice))

        result = np.ma.stack(output_slices).reshape((*leading_shape, y_size, x_size))

        if isinstance(data, xr.DataArray) and set(data.dims) == set(MEB_DIMS):
            return _rebuild_like_meb_template(
                result,
                data.transpose(*MEB_DIMS),
                name=data.name,
                units=str(data.attrs.get("units", "")),
            )
        return result


class GeneratePercentilesFromANeighbourhood(BaseNeighbourhoodProcessing):
    """圆形邻域百分位处理插件。

    在每个二维空间切片上构造圆形邻域窗口，计算指定百分位序列。

    Parameters
    ----------
    radii : float or list[float]
        邻域半径，单位米。
    lead_times : list[int], optional
        与 radii 对应的时效序列，单位小时。
    percentiles : float or list[float], default=DEFAULT_PERCENTILES
        用于计算的百分位值。默认为 (10.0, 20.0, ..., 90.0)。

    Raises
    ------
    ValueError
        1. 邻域半径超过空间域允许的最大距离
        2. 空间坐标不是等间距网格
        3. x 和 y 方向的网格间距不一致
    NotImplementedError
        输入数据为 masked array 时。

    Notes
    -----
    1. 本插件仅支持圆形邻域，不支持方形邻域。
    2. 当输入为标准 meb 六维 xarray.DataArray 时：
        - 输出会重组为六维 xarray
        - 将 (member, percentile) 合并映射到 member 维
        - 添加辅助坐标 member_input_member 和 member_percentile
        - 在属性中添加 member_is_stacked="True" 标记
    3. 对于 numpy.ndarray 输入，输出数组的首轴为 percentile 维。
    4. 不支持 masked array 输入。

    See Also
    --------
    DEFAULT_PERCENTILES : 默认百分位序列
    NeighbourhoodProcessing : 邻域均值/和计算插件

    Examples
    --------
    >>> import xarray as xr
    >>> import numpy as np
    >>> from nbhood import GeneratePercentilesFromANeighbourhood
    >>> 
    >>> # 创建 meb 格式的示例数据
    >>> data = xr.DataArray(
    ...     np.random.rand(2, 1, 1, 3, 100, 120),  # (member, level, time, dtime, lat, lon)
    ...     dims=("member", "level", "time", "dtime", "lat", "lon")
    ... )
    >>> 
    >>> # 计算 25%、50%、75% 百分位
    >>> processor = GeneratePercentilesFromANeighbourhood(
    ...     radii=3000.0,
    ...     percentiles=[25.0, 50.0, 75.0]
    ... )
    >>> result = processor.process(data)
    >>> print(result.dims)  # 输出: ('member', 'level', 'time', 'dtime', 'lat', 'lon')
    >>> print(result.attrs.get('member_is_stacked', "False"))  # 输出: "True"
    """

    def __init__(
        self,
        radii: Union[float, List[float]],
        lead_times: Optional[List[int]] = None,
        percentiles: Union[float, List[float]] = DEFAULT_PERCENTILES,
    ) -> None:
        super().__init__(radii, lead_times=lead_times)
        self.percentiles = tuple(float(x) for x in _as_iterable(percentiles))

    def _pad_and_unpad_array(self, data_2d: ndarray, kernel: ndarray) -> ndarray:
        """对二维切片计算邻域百分位。"""
        kernel_mask = kernel > 0
        nb_slices = _pad_and_roll(
            data_2d, kernel.shape, mode="mean", stat_length=max(kernel.shape) // 2
        )
        percentiles = np.asarray(self.percentiles, dtype=np.float32)
        result = np.empty((len(percentiles), *data_2d.shape), dtype=np.float32)
        for nb_chunk, output_chunk in zip(nb_slices, result.swapaxes(0, 1)):
            np.percentile(
                nb_chunk[..., kernel_mask],
                percentiles,
                axis=-1,
                out=output_chunk,
                overwrite_input=True,
            )
        return result

    def process(
        self,
        data: Union[xr.DataArray, ndarray],
        input_lead_times: Optional[Union[float, ndarray]] = None,
        grid_spacing: Optional[Union[float, Tuple[float, float]]] = None,
    ) -> Union[xr.DataArray, ndarray]:
        """
        计算邻域百分位结果。

        处理流程：
        1. 基类校验输入并准备半径；
        2. 展平前导维并逐二维切片计算圆形邻域百分位；
        3. ndarray 路径输出首轴为 percentile；
        4. 标准 meb 六维 xarray 路径将 ``(member, percentile)`` 合并映射后，
           返回六维结果。

        参数
        ----------
        data : xr.DataArray 或 ndarray
            输入数据，最后两维视为空间维。
        input_lead_times : float 或 ndarray, optional
            输入时效（小时），用于与 ``lead_times`` 联合确定半径。
        grid_spacing : float 或 tuple[float, float], optional
            ndarray 路径使用的网格间距（米）。xarray 路径通常自动推断。

        返回
        -------
        xr.DataArray 或 ndarray
            邻域百分位结果。ndarray 路径首轴为 percentile；
            标准 meb 六维 xarray 路径返回六维 xarray。
        """
        data = super().process(data, input_lead_times=input_lead_times)
        values = _extract_data_array(data)
        if np.ma.isMaskedArray(values):
            raise NotImplementedError("GeneratePercentilesFromANeighbourhood 暂不支持 masked 输入。")
        if values.ndim < 2:
            raise ValueError("输入数据至少需要二维空间网格")

        y_size, x_size = values.shape[-2], values.shape[-1]
        leading_shape = values.shape[:-2]
        flat_values = values.reshape((-1, y_size, x_size))

        if isinstance(data, xr.DataArray):
            spacing, y_coords, x_coords = _infer_grid_spacing_from_xarray(data)
            check_radius_against_distance(
                float(np.max(np.atleast_1d(self.radius))),
                y_coords=y_coords,
                x_coords=x_coords,
            )
        else:
            spacing_y, spacing_x = _parse_grid_spacing(grid_spacing)
            spacing = max(spacing_y, spacing_x)
            check_radius_against_distance(
                float(np.max(np.atleast_1d(self.radius))),
                shape=(y_size, x_size),
                grid_spacing=(spacing_y, spacing_x),
            )

        lead_values = None
        if self.lead_times is not None:
            if input_lead_times is None and isinstance(data, xr.DataArray):
                input_lead_times = _extract_lead_times_from_xarray(data)
            lead_values = _slice_lead_times_for_reshaped_data(
                np.asarray(input_lead_times, dtype=np.float64), leading_shape, y_size, x_size
            )

        output = np.empty(
            (len(self.percentiles), flat_values.shape[0], y_size, x_size),
            dtype=np.float32,
        )
        for index, data_slice in enumerate(flat_values):
            if lead_values is not None:
                current_radius = float(self._find_radii(np.asarray([lead_values[index]]))[0])
            else:
                current_radius = float(self.radius)
            grid_cells = _distance_to_number_of_grid_cells(current_radius, spacing)
            kernel = circular_kernel(grid_cells, weighted_mode=False)
            output[:, index] = self._pad_and_unpad_array(data_slice, kernel)

        result = output.reshape((len(self.percentiles), *leading_shape, y_size, x_size))

        if isinstance(data, xr.DataArray) and set(data.dims) == set(MEB_DIMS):
            template = data.transpose(*MEB_DIMS)
            result_da = xr.DataArray(
                np.asarray(result, dtype=np.float32),
                dims=("percentile", "member", "level", "time", "dtime", "lat", "lon"),
                coords={
                    "percentile": np.asarray(self.percentiles, dtype=np.float32),
                    "member": template.coords["member"].values,
                    "level": template.coords["level"].values,
                    "time": template.coords["time"].values,
                    "dtime": template.coords["dtime"].values,
                    "lat": template.coords["lat"].values,
                    "lon": template.coords["lon"].values,
                },
                attrs=dict(template.attrs),
                name=data.name if data.name is not None else DEFAULT_OUTPUT_NAME,
            )

            # 将输入 member 与新增 percentile 先合并为联合成员维，
            # 再映射回标准六维中的 member，保证输出结构仍为 meb 六维。
            stacked = result_da.stack(stacked_member=("member", "percentile"))
            member_index = stacked.indexes["stacked_member"]
            input_member = np.asarray(member_index.get_level_values("member"))
            member_percentile = np.asarray(
                member_index.get_level_values("percentile"), dtype=np.float32
            )
            # 清理同名 level 坐标，避免维度重命名冲突。
            drop_names = [name for name in ("member", "percentile") if name in stacked.coords]
            if drop_names:
                stacked = stacked.drop_vars(drop_names)
            stacked = stacked.transpose(
                "stacked_member", "level", "time", "dtime", "lat", "lon"
            ).rename({"stacked_member": "member"})

            merged = stacked.assign_coords(
                member=np.arange(stacked.sizes["member"], dtype=np.int32),
                member_input_member=("member", input_member),
                member_percentile=("member", member_percentile),
            ).transpose(*MEB_DIMS)
            merged.attrs.update(dict(template.attrs))
            merged.attrs["member_is_stacked"] = "True"
            merged.attrs["member_stack_dims"] = "member,percentile"
            merged.attrs["member_units"] = "%"
            if merged.name is None:
                merged = merged.copy()
                merged.name = DEFAULT_OUTPUT_NAME
            return merged

        return result
