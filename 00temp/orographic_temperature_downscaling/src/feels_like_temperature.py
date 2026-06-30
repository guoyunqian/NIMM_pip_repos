#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""体感温度计算。

本模块提供体感温度相关的计算工具，支持 ``xarray.DataArray`` 和
``numpy.ndarray`` 两种输入类型。模块包含两个主要能力：

- ``CalculateWindChill``：根据气温和 10 米风速计算风寒温度；
- ``calculate_feels_like_temperature``：综合风寒温度与显温，计算最终体感温度。

对于 ``xarray.DataArray`` 输入，模块会优先从 ``attrs['units']`` 中读取单位；
对于 ``numpy.ndarray`` 输入，则按函数约定的默认单位进行计算。
输入单位字符串须为 ``cf_units`` 可识别的 CF 写法（如 ``degC``、``K``、``m s-1``、``km/h``、``Pa``、``hPa``、``%``、``1``）。

文件结构（算法模板参考）::

    常量
    -> 网格输入校验与输出封装（私有）
    -> 饱和水汽压辅助（私有）
    -> 核心数值算法（私有）
    -> 插件类与对外主入口（公开）
"""

from __future__ import annotations

import functools
from typing import Optional, Tuple, Union

import numpy as np
import xarray as xr

from temperature.utils.utils import (
    assert_xy_match,
    check_for_meb_griddata,
    convert_units,
    rebuild_to_meb_griddata,
)

#: 0 开尔文对应的摄氏温标偏移
ABSOLUTE_ZERO = -273.15

#: 水的三相点温度，单位为 K
TRIPLE_PT_WATER = 273.16

#: 饱和水汽压查表的最低温度，单位为 K
SVP_T_MIN = 183.15

#: 饱和水汽压查表的最高温度，单位为 K
SVP_T_MAX = 338.25

#: 饱和水汽压查表的温度增量，单位为 K
SVP_T_INCREMENT = 0.1


# ---------------------------------------------------------------------------
# 网格输入校验与输出封装
# ---------------------------------------------------------------------------

def _extract_field(
    field: Union[xr.DataArray, np.ndarray],
    *,
    default_units: str,
) -> Tuple[np.ndarray, str, Optional[xr.DataArray]]:
    """从 DataArray 或 ndarray 提取数值数组、单位字符串及可选模板。"""
    if isinstance(field, xr.DataArray):
        normalized = check_for_meb_griddata(field, valid_val=(-np.inf, np.inf, np.nan))
        units = normalized.attrs.get("units") or default_units
        values = normalized.values.astype(np.float32, copy=False)
        return values, units, normalized  # 第三项为输出重组网格时的坐标模板

    values = np.asarray(field, dtype=np.float32)
    return values, default_units, None  # ndarray 无模板，结果也以 ndarray 返回


def _prepare_meb_inputs(
    temperature: Union[xr.DataArray, np.ndarray],
    wind_speed: Union[xr.DataArray, np.ndarray],
    relative_humidity: Union[xr.DataArray, np.ndarray],
    pressure: Union[xr.DataArray, np.ndarray],
) -> Tuple[
    np.ndarray,
    str,
    np.ndarray,
    str,
    np.ndarray,
    str,
    np.ndarray,
    str,
    Optional[xr.DataArray],
]:
    """规范化四路输入并校验与温度场的坐标一致性。"""
    t_values, t_units, t_template = _extract_field(temperature, default_units="degC")
    w_values, w_units, _ = _extract_field(wind_speed, default_units="m s-1")
    rh_values, rh_units, _ = _extract_field(relative_humidity, default_units="1")
    p_values, p_units, _ = _extract_field(pressure, default_units="Pa")

    if t_template is not None:
        # 仅以温度场为参考网格；ndarray 输入无法做坐标比对
        for label, field in (
            ("风速场", wind_speed),
            ("相对湿度场", relative_humidity),
            ("气压场", pressure),
        ):
            if isinstance(field, xr.DataArray):
                assert_xy_match(t_template, field, label)

    return (
        t_values,
        t_units,
        w_values,
        w_units,
        rh_values,
        rh_units,
        p_values,
        p_units,
        t_template,
    )


def _wrap_meb_output(
    values: np.ndarray,
    template: xr.DataArray,
    *,
    name: str,
    units: str,
) -> xr.DataArray:
    """将 numpy 结果重组为标准六维 DataArray。"""
    return rebuild_to_meb_griddata(
        values,
        template=template,
        name=name,
        units=units,
    )


# ---------------------------------------------------------------------------
# 饱和水汽压（显温计算辅助）
# ---------------------------------------------------------------------------

def _svp_pure_water_goff_gratch(temperature: np.ndarray) -> np.ndarray:
    """使用 Goff-Gratch 公式计算纯水系统中的饱和水汽压。

    参数
    ----------
    temperature : np.ndarray
        气温，单位为 K。

    返回
    -------
    np.ndarray
        饱和水汽压，单位为 hPa。
    """
    t = temperature.astype(np.float32, copy=False)
    triple_pt = np.float32(TRIPLE_PT_WATER)
    c1 = np.float32(10.79574)
    c2 = np.float32(5.028)
    c3 = np.float32(1.50475e-4)
    c4 = np.float32(-8.2969)
    c5 = np.float32(0.42873e-3)
    c6 = np.float32(4.76955)
    c7 = np.float32(0.78614)
    c8 = np.float32(-9.09685)
    c9 = np.float32(3.56654)
    c10 = np.float32(0.87682)
    c11 = np.float32(0.78614)

    over_triple = t > triple_pt  # 三相点以上用液态水公式，以下用冰面公式

    # 液态水饱和水汽压（Goff-Gratch，log10 形式）
    n0_w = c1 * (1.0 - triple_pt / t)
    n1_w = c2 * np.log10(t / triple_pt)
    n2_w = c3 * (1.0 - np.power(10.0, (c4 * (t / triple_pt - 1.0))))
    n3_w = c5 * (np.power(10.0, (c6 * (1.0 - triple_pt / t))) - 1.0)
    log_es_w = n0_w - n1_w + n2_w + n3_w + c7
    es_w = np.power(10.0, log_es_w)

    # 冰面饱和水汽压（低温分支）
    n0_i = c8 * ((triple_pt / t) - 1.0)
    n1_i = c9 * np.log10(triple_pt / t)
    n2_i = c10 * (1.0 - (t / triple_pt))
    log_es_i = n0_i - n1_i + n2_i + c11
    es_i = np.power(10.0, log_es_i)

    return np.where(over_triple, es_w, es_i).astype(np.float32)  # 按格点逐元素选分支


@functools.lru_cache(maxsize=1)
def _svp_table() -> tuple[float, ...]:
    """构建饱和水汽压查找表。"""
    svp_data = []
    temperatures = np.arange(
        SVP_T_MIN, SVP_T_MAX + 0.5 * SVP_T_INCREMENT, SVP_T_INCREMENT, dtype=np.float32
    )
    for temp in temperatures:
        svp_data.append(_svp_pure_water_goff_gratch(np.array([temp]))[0])
    # Goff-Gratch 结果为 hPa，查表统一存 Pa（×100）供后续插值
    return tuple(float(value * 100.0) for value in svp_data)


def _svp_from_lookup(temperature: np.ndarray) -> np.ndarray:
    """从查找表中插值得到纯水系统中的饱和水汽压。

    参数
    ----------
    temperature : np.ndarray
        气温，单位为 K。

    返回
    -------
    np.ndarray
        饱和水汽压，单位为 Pa。
    """
    t_clipped = np.clip(temperature, SVP_T_MIN, SVP_T_MAX - SVP_T_INCREMENT)  # 避免插值越界

    # 将温度映射到查表索引，table_index 为下界，interpolation_factor 为区间内小数部分
    table_position = (t_clipped - SVP_T_MIN) / SVP_T_INCREMENT
    table_index = table_position.astype(int)
    interpolation_factor = table_position - table_index
    svp_table_data = np.array(_svp_table(), dtype=np.float32)
    # 相邻两档线性插值（支持任意形状的 temperature 数组）
    return (1.0 - interpolation_factor) * svp_table_data[
        table_index
    ] + interpolation_factor * svp_table_data[table_index + 1]


def _calculate_svp_in_air(temperature: np.ndarray, pressure: np.ndarray) -> np.ndarray:
    """计算空气中的饱和水汽压。

    参数
    ----------
    temperature : np.ndarray
        气温，单位为 K。
    pressure : np.ndarray
        气压，单位为 Pa。

    返回
    -------
    np.ndarray
        空气中的饱和水汽压，单位为 Pa。
    """
    svp = _svp_from_lookup(temperature)
    temp_c = temperature + ABSOLUTE_ZERO  # K -> ℃，用于气压订正项
    # 饱和水汽压随气压与温度的微弱订正（Gill, A4.7）
    correction = 1.0 + 1.0e-8 * pressure * (4.5 + 6.0e-4 * temp_c * temp_c)
    return svp * correction.astype(np.float32)


# ---------------------------------------------------------------------------
# 核心数值算法（纯 numpy，无 I/O 依赖）
# ---------------------------------------------------------------------------

def _calculate_wind_chill(temperature: np.ndarray, wind_speed_kmh: np.ndarray) -> np.ndarray:
    """根据气温和风速计算风寒温度。

    参数
    ----------
    temperature : np.ndarray
        气温，单位为摄氏度。
    wind_speed_kmh : np.ndarray
        风速，单位为千米每小时。

    返回
    -------
    np.ndarray
        风寒温度，单位为摄氏度。
    """
    # 4.824 km/h 为公式适用的最低有效风速（对应文献中的步行风速下限）
    eqn_component = np.clip(wind_speed_kmh, 4.824, None) ** 0.16
    return (
        13.12
        + 0.6215 * temperature
        - 11.37 * eqn_component
        + 0.3965 * temperature * eqn_component
    ).astype(np.float32)


def _calculate_apparent_temperature(
    temperature: np.ndarray,
    wind_speed: np.ndarray,
    relative_humidity: np.ndarray,
    pressure: np.ndarray,
) -> np.ndarray:
    """计算显温。

    参数
    ----------
    temperature : np.ndarray
        气温，单位为摄氏度。
    wind_speed : np.ndarray
        10 米风速，单位为米每秒。
    relative_humidity : np.ndarray
        相对湿度，使用 0 到 1 的分数表示。
    pressure : np.ndarray
        气压，单位为 Pa。

    返回
    -------
    np.ndarray
        显温，单位为摄氏度。
    """
    t_kelvin = temperature + 273.15
    svp = _calculate_svp_in_air(t_kelvin, pressure)  # Pa
    # Steadman 回归式中水汽压单位为 hPa，故 svp(Pa) × RH 后再 ×0.001
    avp = 0.001 * svp * relative_humidity
    return (-2.7 + 1.04 * temperature + 2.0 * avp - 0.65 * wind_speed).astype(np.float32)


def _feels_like_temperature(
    temperature: np.ndarray,
    apparent_temperature: np.ndarray,
    wind_chill: np.ndarray,
) -> np.ndarray:
    """融合显温与风寒温度，得到最终体感温度。

    计算规则如下：

    - 当气温低于 10 摄氏度时，体感温度取风寒温度；
    - 当气温高于 20 摄氏度时，体感温度取显温；
    - 当气温位于 10 到 20 摄氏度之间时，在风寒温度和显温之间进行线性过渡。

    参数
    ----------
    temperature : np.ndarray
        气温，单位为摄氏度。
    apparent_temperature : np.ndarray
        显温，单位为摄氏度。
    wind_chill : np.ndarray
        风寒温度，单位为摄氏度。

    返回
    -------
    np.ndarray
        体感温度，单位为摄氏度。
    """
    feels_like_temperature = np.zeros(temperature.shape, dtype=np.float32)

    # 低温区：直接采用风寒温度
    feels_like_temperature[temperature < 10] = wind_chill[temperature < 10]

    # 过渡区（10–20℃）：按气温线性加权融合显温与风寒温度
    alpha = (temperature - 10.0) / 10.0  # 10℃ 时 alpha=0，20℃ 时 alpha=1
    temp_flt = alpha * apparent_temperature + ((1 - alpha) * wind_chill)
    between = (temperature >= 10) & (temperature <= 20)
    feels_like_temperature[between] = temp_flt[between]

    # 高温区：直接采用显温
    feels_like_temperature[temperature > 20] = apparent_temperature[temperature > 20]

    return feels_like_temperature


def _compute_feels_like_values(
    temperature_c: np.ndarray,
    wind_ms: np.ndarray,
    relative_humidity_frac: np.ndarray,
    pressure_pa: np.ndarray,
) -> np.ndarray:
    """在标准单位下计算体感温度（摄氏度）。"""
    apparent_temperature = _calculate_apparent_temperature(
        temperature_c,
        wind_ms,
        relative_humidity_frac,
        pressure_pa,
    )
    wind_chill = _calculate_wind_chill(
        temperature_c,
        convert_units(wind_ms, "m s-1", "km/h"),  # 风寒公式要求 km/h
    )
    return _feels_like_temperature(temperature_c, apparent_temperature, wind_chill)


# ---------------------------------------------------------------------------
# 插件类
# ---------------------------------------------------------------------------

class CalculateWindChill:
    """计算风寒温度的插件类。

    该类用于根据气温和 10 米风速估算人体在寒冷多风环境下感受到的温度。
    既可以使用 ``process(...)``，也可以直接调用实例 ``plugin(...)``。
    """

    def __call__(
        self,
        temperature_data: Union[xr.DataArray, np.ndarray],
        wind_speed_data: Union[xr.DataArray, np.ndarray],
        temperature_units: str = "degC",
        wind_speed_units: str = "m s-1",
    ) -> Union[xr.DataArray, np.ndarray]:
        """直接调用插件并返回风寒温度结果。"""
        return self.process(
            temperature_data=temperature_data,
            wind_speed_data=wind_speed_data,
            temperature_units=temperature_units,
            wind_speed_units=wind_speed_units,
        )

    def process(
        self,
        temperature_data: Union[xr.DataArray, np.ndarray],
        wind_speed_data: Union[xr.DataArray, np.ndarray],
        temperature_units: str = "degC",
        wind_speed_units: str = "m s-1",
    ) -> Union[xr.DataArray, np.ndarray]:
        """计算风寒温度。

        参数
        ----------
        temperature_data : xr.DataArray or np.ndarray
            气温数据。DataArray 优先使用 ``attrs['units']``；ndarray 使用
            ``temperature_units``。
        wind_speed_data : xr.DataArray or np.ndarray
            10 米风速数据。DataArray 优先使用 ``attrs['units']``；ndarray 使用
            ``wind_speed_units``。
        temperature_units : str, default="degC"
            ndarray 输入时的气温单位。
        wind_speed_units : str, default="m s-1"
            ndarray 输入时的风速单位。

        返回
        -------
        xr.DataArray or np.ndarray
            风寒温度，单位为摄氏度。
        """
        t_values, t_units, t_template = _extract_field(
            temperature_data,
            default_units=temperature_units,
        )
        w_values, w_units, w_template = _extract_field(
            wind_speed_data,
            default_units=wind_speed_units,
        )

        if t_template is not None and w_template is not None:
            assert_xy_match(t_template, w_template, "风速场")

        temp_degc = convert_units(t_values, t_units, "degC")
        wind_kmh = convert_units(w_values, w_units, "km/h")  # 风寒公式要求 km/h
        wind_chill_data = _calculate_wind_chill(temp_degc, wind_kmh)

        if t_template is not None:
            return _wrap_meb_output(
                wind_chill_data,
                t_template,
                name="wind_chill_temperature",
                units="degC",
            )
        return wind_chill_data

    def _calculate_wind_chill(
        self,
        temperature: np.ndarray,
        wind_speed: np.ndarray,
    ) -> np.ndarray:
        """兼容旧调用方式：委托模块级风寒温度计算函数。"""
        return _calculate_wind_chill(temperature, wind_speed)

# ---------------------------------------------------------------------------
# 对外主入口
# ---------------------------------------------------------------------------

def calculate_feels_like_temperature(
    temperature: Union[xr.DataArray, np.ndarray],
    wind_speed: Union[xr.DataArray, np.ndarray],
    relative_humidity: Union[xr.DataArray, np.ndarray],
    pressure: Union[xr.DataArray, np.ndarray],
) -> Union[xr.DataArray, np.ndarray]:
    """计算体感温度。

    该函数综合显温和风寒温度，输出与输入形状一致的体感温度数组。

    单位处理约定如下：

    - ``temperature``：``degC`` 或 ``K``；
    - ``wind_speed``：``m s-1`` 或 ``km/h``；
    - ``relative_humidity``：``1``（分数）或 ``%``；
    - ``pressure``：``Pa``、``hPa`` 或 ``kPa``。
    以上单位字符串须为 ``cf_units`` 可识别的 CF 写法。

    对于 ``xarray.DataArray``，函数会先校验并规范化为标准六维网格，
    并检查各场与温度场的空间/时效坐标是否一致；
    对于 ``numpy.ndarray``，默认假定输入分别为摄氏度、米每秒、相对湿度分数和帕。

    参数
    ----------
    temperature : xr.DataArray or np.ndarray
        气温数据。
    wind_speed : xr.DataArray or np.ndarray
        10 米风速数据。
    relative_humidity : xr.DataArray or np.ndarray
        相对湿度数据。
    pressure : xr.DataArray or np.ndarray
        气压数据。

    返回
    -------
    xr.DataArray or np.ndarray
        若输入为 ``xarray.DataArray``，返回标准六维 ``xarray.DataArray``；
        若输入为 ``numpy.ndarray``，返回 ``numpy.ndarray``。
        输出温度单位与输入温度单位保持一致。
    """
    (
        t_values,
        t_units,
        w_values,
        w_units,
        rh_values,
        rh_units,
        p_values,
        p_units,
        t_template,
    ) = _prepare_meb_inputs(temperature, wind_speed, relative_humidity, pressure)

    # 核心算法在固定单位下计算，最后再换回输入温度的单位
    t_celsius = convert_units(t_values, t_units, "degC")
    w_ms = convert_units(w_values, w_units, "m s-1")
    rh_frac = convert_units(rh_values, rh_units, "1")
    p_pa = convert_units(p_values, p_units, "Pa")

    feels_like_degc = _compute_feels_like_values(t_celsius, w_ms, rh_frac, p_pa)
    out_values = convert_units(feels_like_degc, "degC", t_units)

    if t_template is not None:
        # 输入为 K 时输出也标为 K，否则为 degC
        output_units = "K" if (t_units or "").strip() == "K" else "degC"
        return _wrap_meb_output(
            out_values,
            t_template,
            name="feels_like_temperature",
            units=output_units,
        )
    return out_values
