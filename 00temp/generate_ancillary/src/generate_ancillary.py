#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""地形相关辅助场生成算法。

本模块实现了地形相关辅助场生成算法，包括地形带掩码生成和海陆掩码纠正。

算法面向 xarray.DataArray 与 numpy.ndarray 双输入，同时兼容 meteva_base 常见六维网格（member, level, time, dtime, lat, lon）。

算法不依赖空间坐标的物理数值进行计算，坐标仅参与 xarray 的维度对齐与广播，其值从未被读取或用于数值运算。因此：
- 输入场可以是任意空间坐标系（投影坐标 projection_x/y_coordinate 或地理坐标 lat/lon），不影响计算正确性。
- 若上游数据保留 grid_mapping 属性（如 lambert_azimuthal_equal_area 的投影参数），本模块会将其随输出场透传，供下游消费方按需重建 CRS 并做投影转换。

为避免不必要的投影往返转换带来的精度损失与额外依赖，当前并未实现投影坐标与经纬坐标的转换，并且测试数据在预处理阶段也并未进行坐标转换，投影坐标只是映射到经纬维度。

"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Union

import numpy as np
import xarray as xr
from cf_units import Unit as CfUnit
from numpy import ndarray
from numpy.ma.core import MaskedArray

from generate_ancillary.utils.base_plugin import BasePlugin
from generate_ancillary.utils.utils import check_for_meb_griddata

#以下字典定义了默认的以米为单位的地形高度带
THRESHOLDS_DICT = {
    "bounds": [
        [-500.0, 50.0],
        [50.0, 100.0],
        [100.0, 150.0],
        [150.0, 200.0],
        [200.0, 250.0],
        [250.0, 300.0],
        [300.0, 400.0],
        [400.0, 500.0],
        [500.0, 650.0],
        [650.0, 800.0],
        [800.0, 950.0],
        [950.0, 6000.0],
    ],
    "units": "m",
}

__all__ = [
    "THRESHOLDS_DICT",
    "CorrectLandSeaMask",
    "GenerateOrographyBandAncils",
]


class CorrectLandSeaMask(BasePlugin):
    """将海陆掩码纠正为 0/1 二值场。

    功能逻辑：
    插值后的海陆掩码场中，格点值为 0~1 之间的浮点数，表示该格点为陆地的概率。
    本方法以 0.5 为阈值进行二值化：
    - 格点值 < 0.5：判定为海，置为 0
    - 格点值 >= 0.5：判定为陆，置为 1
    输出为 int8 类型的二值掩码场。

    输入输出均为 meteva_base 标准六维网格数据（member, level, time, dtime, lat, lon），
    维度保持不变，仅修改格点值。
    """

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        """返回插件实例说明。"""
        return "<CorrectLandSeaMask>"

    @staticmethod
    def process(standard_landmask: Union[xr.DataArray, ndarray]) -> Union[xr.DataArray, ndarray]:
        """将插值后的海陆掩码阈值化为 0/1。

        以 0.5 为阈值对海陆掩码进行二值化，小于 0.5 置为 0（海），
        大于等于 0.5 置为 1（陆）。

        Parameters
        ----------
        standard_landmask : xr.DataArray or ndarray
            插值后的海陆掩码场，格点值为 0~1 之间的浮点数。

        Returns
        -------
        xr.DataArray or ndarray
            二值化后的海陆掩码场，取值含义为：0 表示海，1 表示陆，数据类型为 int8。
            输入为 xr.DataArray 时，返回 xr.DataArray，维度与坐标保持不变；
            输入为 ndarray 时，返回 ndarray。
        """
        if isinstance(standard_landmask, xr.DataArray):
            # xarray 输入统一按 meteva_base 六维网格约定检查。
            unbounded = (-np.inf, np.inf, np.nan)
            standard_landmask = check_for_meb_griddata(
                standard_landmask, valid_val=unbounded
            )
            data = np.asarray(standard_landmask.values, dtype=np.float32).copy()
            data[data < 0.5] = 0
            data[data >= 0.5] = 1
            return xr.DataArray(
                data.astype(np.int8),
                dims=standard_landmask.dims,
                coords=standard_landmask.coords,
                attrs=standard_landmask.attrs,
                name="land_binary_mask",
            )

        data = np.asarray(standard_landmask, dtype=np.float32).copy()
        data[data < 0.5] = 0
        data[data >= 0.5] = 1
        return data.astype(np.int8)


class GenerateOrographyBandAncils(BasePlugin):
    """生成地形带掩码辅助场。

    功能逻辑：
    根据地形高度场，将区域按海拔划分为多个连续的地形带（如 -500~50m、50~100m 等），
    每个地形带生成一张二值掩码图，标记哪些格点落在该海拔区间内。

    核心处理流程：
    1. 接收地形高度场、海陆掩码（可选）、阈值配置
    2. 遍历每个地形带区间：
       a. 单位换算（将阈值转换到地形场的单位）
       b. 阈值比较：lower < orog <= upper，生成二值掩码
       c. 海点处理：若提供了海陆掩码，将海点置为 0
       d. 将结果包装为标准六维 DataArray，地形带映射到 level 维
    3. 将所有地形带沿 level 维堆叠，返回完整结果

    输出格式：
    - xarray 输入：返回 xr.DataArray，维度为 (member, level, time, dtime, lat, lon)
      level 维长度为地形带数量，level 坐标值为各地形带的中心值
      level 坐标附带 level_lower_bound 和 level_upper_bound 两个辅助坐标
    - ndarray 输入：返回 ndarray，第一维为地形带索引
    """

    def __repr__(self) -> str:
        """返回插件实例说明。"""
        return "<GenerateOrographyBandAncils>"

    @staticmethod
    def _coerce_threshold_bounds(topographic_bounds: Sequence[float]) -> ndarray:
        """校验并标准化地形带上下界。"""
        if any(item is None for item in topographic_bounds):
            msg = (
                "地形带阈值必须同时提供上下界："
                f"当前 topographic_bounds={topographic_bounds}"
            )
            raise TypeError(msg)
        if len(topographic_bounds) != 2:
            msg = (
                "地形带阈值只能包含上下两个界值："
                f"当前长度为 {len(topographic_bounds)}"
            )
            raise TypeError(msg)
        return np.asarray(topographic_bounds, dtype=np.float32)

    @staticmethod
    def _broadcast_landmask_values(
        landmask_values: ndarray, target_shape: tuple[int, ...]
    ) -> ndarray:
        """将 landmask 广播到与地形场一致的形状。"""
        if landmask_values.shape == target_shape:
            return landmask_values
        try:
            return np.broadcast_to(landmask_values, target_shape)
        except ValueError as exc:
            raise ValueError(
                "海陆掩码形状无法广播到地形场："
                f"{landmask_values.shape} -> {target_shape}"
            ) from exc

    @staticmethod
    def sea_mask(
        landmask: ndarray, orog_band: ndarray, sea_fill_value: Optional[int] = None
    ) -> Union[MaskedArray, ndarray]:
        """将海点从地形带结果中屏蔽或填固定值。

        根据海陆掩码，将海洋区域的格点屏蔽（设为 fill_value）或填充指定值。

        Parameters
        ----------
        landmask : ndarray
            海陆掩码，陆地格点为 1，海洋格点为 0。
        orog_band : ndarray
            地形带二值掩码。
        sea_fill_value : int or None, default=None
            海点的填充值。若为 None，则返回 masked array。

        Returns
        -------
        MaskedArray or ndarray
            海点处理后的地形带掩码。
            当 sea_fill_value 为 None 时，海点被屏蔽并返回 MaskedArray；
            当 sea_fill_value 为整数时，海点被填为该值并返回 ndarray。
        """
        # 找出海洋格点（landmask 为 False 的位置）
        points_to_mask = np.logical_not(landmask)

        if sea_fill_value is None:
            # 返回 masked array，海洋格点被屏蔽
            sea_fill_value = np.ma.default_fill_value(orog_band)
            orog_data = np.array(orog_band, copy=True)
            orog_data[points_to_mask] = sea_fill_value
            return np.ma.masked_array(orog_data, mask=points_to_mask)

        # 返回普通数组，海洋格点填入指定值
        mask_data = np.array(orog_band, copy=True)
        mask_data[points_to_mask] = sea_fill_value
        return mask_data

    def gen_orography_masks(
        self,
        standard_orography: Union[xr.DataArray, ndarray],
        standard_landmask: Optional[Union[xr.DataArray, ndarray]],
        thresholds: Sequence[float],
        units: str = "m",
    ) -> Union[xr.DataArray, ndarray]:
        """针对单个地形带生成掩码。

        功能逻辑：
        对单个地形带区间（如 [50, 100]），在地形高度场上标记所有满足
        lower < orog <= upper 的格点，生成二值掩码。
        若提供了海陆掩码，则将海洋格点置为 0。

        Parameters
        ----------
        standard_orography : xr.DataArray or ndarray
            地形高度场。
        standard_landmask : xr.DataArray or ndarray or None
            海陆掩码，可选。若提供，用于屏蔽海洋格点。
        thresholds : sequence of float
            地形带上下界，如 [lower, upper]。
        units : str, default="m"
            阈值的单位。

        Returns
        -------
        xr.DataArray or ndarray
            单个地形带的二值掩码。
            xarray 输入时返回标准六维 DataArray，level 维长度为 1；
            ndarray 输入时返回 ndarray，第一维长度为 1。
        """
        orography_is_xarray = isinstance(standard_orography, xr.DataArray)

        # 获取地形场的单位
        target_units = (
            standard_orography.attrs.get("units", "m")
            if orography_is_xarray
            else "m"
        )
        # 核心步骤1：单位换算，将阈值转换到地形场的单位
        threshold_values = np.asarray(thresholds, dtype=np.float32)
        converted_thresholds = CfUnit(units).convert(
            threshold_values, CfUnit(target_units)
        )
        lower_threshold, upper_threshold = converted_thresholds

        # 核心步骤2：阈值比较，生成二值掩码（lower < orog <= upper）
        orog_values = (
            np.asarray(standard_orography.values)
            if orography_is_xarray
            else np.asarray(standard_orography)
        )
        orog_band = (
            (orog_values > lower_threshold) & (orog_values <= upper_threshold)
        ).astype(np.int32)

        # 核心步骤3：海点处理，若提供了海陆掩码则将海洋格点置为 0
        if standard_landmask is not None:
            if orography_is_xarray and isinstance(standard_landmask, xr.DataArray):
                # 将海陆掩码广播到与地形场一致的形状
                _, aligned_landmask = xr.broadcast(standard_orography, standard_landmask)
                landmask_values = np.asarray(aligned_landmask.values)
            elif isinstance(standard_landmask, xr.DataArray):
                landmask_values = np.asarray(standard_landmask.values)
            else:
                landmask_values = np.asarray(standard_landmask)
            landmask_values = self._broadcast_landmask_values(
                landmask_values, tuple(orog_values.shape)
            )
            mask_data = self.sea_mask(landmask_values, orog_band, sea_fill_value=0)
            sea_points_included = False
        else:
            mask_data = orog_band
            sea_points_included = True

        # 核心步骤4：包装输出，将地形带映射到 level 维
        if orography_is_xarray:
            # 校验输入 level 维长度为 1（地形带将映射到此维）
            if standard_orography.sizes.get("level", 0) != 1:
                raise ValueError("地形带映射到 level 时要求输入 level 维长度为 1")

            bounds = self._coerce_threshold_bounds(converted_thresholds)
            level_center = np.mean(bounds).astype(np.float32)

            # 先去除 level 维（输入 level 维长度为 1）
            base = xr.DataArray(
                np.asarray(mask_data, dtype=np.int32),
                dims=standard_orography.dims,
                coords=standard_orography.coords,
                name="topography_mask",
                attrs={
                    "units": "1",
                    "topographic_zones_include_seapoints": str(
                        bool(sea_points_included)
                    ),
                },
            ).isel(level=0, drop=True)

            # 用地形带中心值重建 level 维，实现地形带到 level 维的映射
            result = base.expand_dims(
                level=xr.DataArray(
                    np.asarray([level_center], dtype=np.float32),
                    dims=("level",),
                    attrs={"units": str(target_units)},
                )
            )
            result.coords["level"].attrs["units"] = str(target_units)
            # 附加地形带边界信息作为 level 的辅助坐标
            result = result.assign_coords(
                level_lower_bound=(
                    ("level",),
                    np.asarray([bounds[0]], dtype=np.float32),
                ),
                level_upper_bound=(
                    ("level",),
                    np.asarray([bounds[1]], dtype=np.float32),
                ),
            )
            return result.transpose("member", "level", "time", "dtime", "lat", "lon")

        return np.asarray(mask_data, dtype=np.int32)[np.newaxis, ...]

    def process(
        self,
        orography: Union[xr.DataArray, ndarray],
        thresholds_dict: Dict[str, Any],
        landmask: Optional[Union[xr.DataArray, ndarray]] = None,
    ) -> Union[xr.DataArray, ndarray]:
        """针对多个地形带循环生成掩码并堆叠输出。

        功能逻辑：
        遍历 thresholds_dict["bounds"] 中的每个地形带区间，依次调用
        gen_orography_masks 生成单个地形带的掩码，然后将所有地形带
        沿 level 维堆叠，形成完整的地形带掩码场。

        Parameters
        ----------
        orography : xr.DataArray or ndarray
            地形高度场，应为 meteva_base 标准六维网格数据。
        thresholds_dict : dict
            阈值配置字典，包含：
            - "bounds": 由多个 [lower, upper] 组成的区间列表
            - "units": str，阈值单位
        landmask : xr.DataArray or ndarray or None, default=None
            海陆掩码，可选。若提供，用于屏蔽海洋格点。

        Returns
        -------
        xr.DataArray or ndarray
            地形带掩码场。
            xarray 输入时返回 xr.DataArray，维度为
            (member, level, time, dtime, lat, lon)，
            level 维长度为地形带数量；
            ndarray 输入时返回 ndarray，第一维为地形带索引。
        """
        # 在入口统一做一次 xarray 六维校验
        if isinstance(orography, xr.DataArray):
            unbounded = (-np.inf, np.inf, np.nan)
            orography = check_for_meb_griddata(orography, valid_val=unbounded)
            if isinstance(landmask, xr.DataArray):
                landmask = check_for_meb_griddata(landmask, valid_val=unbounded)

        # 校验阈值配置
        if "bounds" not in thresholds_dict or not thresholds_dict["bounds"]:
            raise ValueError("未提供任何地形带阈值。")
        if "units" not in thresholds_dict:
            raise KeyError("thresholds_dict 缺少必需字段: units")

        # 核心循环：遍历每个地形带区间，逐个生成掩码
        band_results = [
            self.gen_orography_masks(
                orography,
                landmask,
                limits,
                thresholds_dict["units"],
            )
            for limits in thresholds_dict["bounds"]
        ]

        if isinstance(orography, xr.DataArray):
            # 核心步骤：将所有地形带沿 level 维堆叠
            # 每个单带结果已是标准六维（level 维长度为 1）
            result = xr.concat(band_results, dim="level")
            result.name = "topography_mask"
            result = result.transpose("member", "level", "time", "dtime", "lat", "lon")
            return result

        return np.concatenate([np.asarray(item) for item in band_results], axis=0)