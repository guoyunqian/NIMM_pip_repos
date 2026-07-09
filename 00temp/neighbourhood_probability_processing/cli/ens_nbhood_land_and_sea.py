#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""陆地/海洋分区邻域处理 CLI 示例。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np
import xarray as xr
import meteva_base as meb


def process(
    input_data_path: str,
    mask_path: str,
    radii: Sequence[float],
    weights_path: Optional[str] = None,
    output_path: Optional[str] = None,
    *,
    neighbourhood_shape: str = "square",
    lead_times: Optional[Sequence[int]] = None,
    area_sum: bool = False,
) -> xr.DataArray:
    """执行陆地/海洋分区邻域处理并合并输出。

    参数
    ----------
    input_data_path : str
        待处理输入场 nc 文件路径。
    mask_path : str
        陆地/海洋或地形带掩码 nc 文件路径。
    radii : sequence of float
        邻域半径（米）。
    weights_path : str, optional
        地形带折叠权重 nc 文件路径；``topographic_zone`` 掩码时必填。
    output_path : str, optional
        输出 nc 文件路径；为 None 时不写文件。
    neighbourhood_shape : str, default="square"
        邻域形状，``square`` / ``circular``。
    lead_times : sequence of int, optional
        与 ``radii`` 对应的时效（小时）。
    area_sum : bool, default=False
        是否输出邻域和（True）而非邻域平均（False）。

    返回
    -------
    xr.DataArray
        陆海合并后的邻域处理结果。
    """
    from neighbourhood_probability_processing.src.utils._helpers import radius_by_lead_time
    from neighbourhood_probability_processing.src.nbhood import NeighbourhoodProcessing
    from neighbourhood_probability_processing.src.use_nbhood import ApplyNeighbourhoodProcessingWithAMask
    from neighbourhood_probability_processing.cli.io import read_mask_or_weights_from_nc
    from neighbourhood_probability_processing.utils.utils import check_for_meb_griddata

    input_data = check_for_meb_griddata(meb.read_griddata_from_nc(input_data_path), valid_val=(-np.inf, np.inf, np.nan))
    mask = read_mask_or_weights_from_nc(mask_path)
    weights = (
        None
        if weights_path is None
        else read_mask_or_weights_from_nc(weights_path)
    )

    radius_or_radii, parsed_lead_times = radius_by_lead_time(list(radii), lead_times)

    has_topographic_zone = "topographic_zone" in mask.dims
    if has_topographic_zone:
        if mask.attrs.get("topographic_zones_include_seapoints") == "True":
            raise ValueError(
                "topographic_zone 掩码必须排除海点：topographic_zones_include_seapoints 不能为 True。"
            )
        if weights is None:
            raise TypeError(
                "使用 topographic_zone 掩码时必须提供 weights_path（用于折叠分层维）。"
            )
        if weights.attrs.get("topographic_zones_include_seapoints") == "True":
            raise ValueError(
                "weights 必须排除海点：topographic_zones_include_seapoints 不能为 True。"
            )

        # 原算法语义：优先使用首层权重的 mask 识别海点；
        # 若读取路径未保留显式 mask，则退化为“非有限值视为海点”。
        layer0 = weights.isel({"topographic_zone": 0})
        layer0_values = np.asanyarray(layer0.values)
        if np.ma.isMaskedArray(layer0_values):
            sea_mask_bool = np.ma.getmaskarray(layer0_values)
        else:
            sea_mask_bool = ~np.isfinite(np.asarray(layer0_values, dtype=np.float64))

        sea_only = xr.DataArray(
            sea_mask_bool.astype(np.int8),
            dims=layer0.dims,
            coords=layer0.coords,
            attrs=dict(layer0.attrs),
            name="sea_binary_mask",
        )
        land_only = xr.DataArray(
            np.logical_not(sea_mask_bool).astype(np.int8),
            dims=layer0.dims,
            coords=layer0.coords,
            attrs=dict(layer0.attrs),
            name="land_binary_mask",
        )
    else:
        if weights is not None:
            raise TypeError("当前 mask 不含 topographic_zone，传入 weights 不会被使用。")
        # 输入约定：land=1, sea=0
        land_only = xr.where(mask > 0, 1, 0).astype(np.int8).rename("land_binary_mask")
        sea_only = xr.where(mask > 0, 0, 1).astype(np.int8).rename("sea_binary_mask")

    result_land = None
    result_sea = None

    # 用于处理陆地邻域部分
    if float(np.nanmax(land_only.values)) > 0.0:
        if has_topographic_zone:
            result_land = ApplyNeighbourhoodProcessingWithAMask(
                coord_for_masking="topographic_zone",
                neighbourhood_method=neighbourhood_shape,
                radii=radius_or_radii,
                lead_times=parsed_lead_times,
                collapse_weights=weights,
                sum_only=area_sum,
            ).process(input_data, mask)
        else:
            result_land = NeighbourhoodProcessing(
                neighbourhood_shape,
                radius_or_radii,
                lead_times=parsed_lead_times,
                sum_only=area_sum,
                re_mask=True,
            ).process(input_data, land_only)

    # 用于处理海点的邻域部分
    if float(np.nanmax(sea_only.values)) > 0.0:
        result_sea = NeighbourhoodProcessing(
            neighbourhood_shape,
            radius_or_radii,
            lead_times=parsed_lead_times,
            sum_only=area_sum,
            re_mask=True,
        ).process(input_data, sea_only)

    if result_land is None and result_sea is None:
        raise RuntimeError("陆地和海洋区域均为空，无法执行邻域处理。")
    if result_land is None:
        result = result_sea
    elif result_sea is None:
        result = result_land
    else:
        land_values = np.asarray(result_land.values, dtype=np.float32)
        sea_values = np.asarray(result_sea.values, dtype=np.float32)
        combined = np.nan_to_num(land_values, nan=0.0) + np.nan_to_num(sea_values, nan=0.0)
        result = xr.DataArray(
            combined.astype(np.float32, copy=False),
            dims=result_land.dims,
            coords=result_land.coords,
            attrs=dict(result_land.attrs),
            name=result_land.name,
        )

    if output_path is not None:
        # 无效格点已是 NaN，meb 会量化为 int32 哨兵，读回可还原。
        meb.write_griddata_to_nc(result, output_path, creat_dir=True)

    return result


if __name__ == "__main__":
    import sys

    #添加项目根目录到系统路径,可直接运行示例脚本
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
        
    #测试数据路径：输入取自 cli_input，结果写到 cli_output
    scenario_dir = (
        Path(__file__).resolve().parent.parent
        / "test_data"
        / "official_test_use_nbhood"
        / "land_and_sea"
    )
    input_dir = scenario_dir / "cli_input"
    output_dir = scenario_dir / "cli_output"

    #各输入文件的路径映射
    input_data_path = str(input_dir / "input.nc")   #待处理输入场nc文件路径
    mask_path = str(input_dir / "ukvx_landmask.nc")   #陆地/海洋掩码nc文件路径
    weights_path = None   #地形带折叠权重nc文件路径
    output_path = str(output_dir / "cli_land_sea_result.nc")   #输出nc文件路径

    neighbourhood_shape = "square"   #邻域形状
    radii: List[float] = [20000.0]   #邻域半径（米）
    lead_times = None   #与radii对应的时效（小时）
    area_sum = False   #是否输出邻域和（True）而非邻域平均（False）

    result = process(
        input_data_path,
        mask_path,
        radii,
        weights_path=weights_path,
        output_path=output_path,
        neighbourhood_shape=neighbourhood_shape,
        lead_times=lead_times,
        area_sum=area_sum,
    )
