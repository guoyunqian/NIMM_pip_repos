#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""Neighbourhood 处理 CLI 示例。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Union

import numpy as np
import xarray as xr
import meteva_base as meb


def process(
    input_data_path: str,
    neighbourhood_output: str,
    radii: Sequence[float],
    mask_path: Optional[str] = None,
    output_path: Optional[str] = None,
    *,
    neighbourhood_shape: str = "square",
    lead_times: Optional[Sequence[int]] = None,
    degrees_as_complex: bool = False,
    weighted_mode: bool = False,
    area_sum: bool = False,
    percentiles: Optional[Sequence[float]] = None,
    halo_radius: Optional[float] = None,
) -> xr.DataArray:
    """执行邻域处理。

    参数
    ----------
    input_data_path : str
        输入网格数据 nc 文件路径。
    neighbourhood_output : str
        邻域输出类型：``probabilities`` 或 ``percentiles``。
    radii : sequence of float
        邻域半径（米），可传单值或多值。
    mask_path : str, optional
        外部掩码 nc 文件路径，仅 ``probabilities`` 模式可用。
    output_path : str, optional
        输出 nc 文件路径；为 None 时不写文件。
    neighbourhood_shape : str, default="square"
        邻域形状，``square`` 或 ``circular``。
    lead_times : sequence of int, optional
        与 ``radii`` 配套的时效（小时）。
    degrees_as_complex : bool, default=False
        是否将输入角度场转为复数后再计算。
    weighted_mode : bool, default=False
        圆形邻域加权模式。
    area_sum : bool, default=False
        是否返回邻域和而非邻域平均。
    percentiles : sequence of float, default=DEFAULT_PERCENTILES
        百分位列表（单位 %），仅 ``percentiles`` 模式使用。
    halo_radius : float, optional
        结果外圈裁剪半径（米）。

    返回
    -------
    xr.DataArray
        邻域处理结果。
    """
    from neighbourhood_probability_processing.src.utils._helpers import (
        complex_to_deg,
        deg_to_complex,
        radius_by_lead_time,
        remove_dataarray_halo,
    )
    from neighbourhood_probability_processing.src.nbhood import (
        DEFAULT_PERCENTILES,
        GeneratePercentilesFromANeighbourhood,
        NeighbourhoodProcessing,
    )
    from neighbourhood_probability_processing.cli.io import read_mask_or_weights_from_nc
    
    if percentiles is None:
        percentiles = DEFAULT_PERCENTILES

    mode = str(neighbourhood_output).strip().lower()
    shape = str(neighbourhood_shape).strip().lower()
    if mode not in ("probabilities", "percentiles"):
        raise ValueError('neighbourhood_output 仅支持 "probabilities" 或 "percentiles"。')
    if shape not in ("square", "circular"):
        raise ValueError('neighbourhood_shape 仅支持 "square" 或 "circular"。')
    if mode == "percentiles" and mask_path is not None:
        raise RuntimeError('neighbourhood_output="percentiles" 时不支持 mask。')
    if mode == "percentiles" and weighted_mode:
        raise RuntimeError('weighted_mode 不能与 neighbourhood_output="percentiles" 同时使用。')
    if degrees_as_complex and mode == "percentiles":
        raise RuntimeError("complex 角度模式不支持 percentiles 输出。")
    if degrees_as_complex and shape == "circular":
        raise RuntimeError("complex 角度模式不支持 circular 邻域。")

    from neighbourhood_probability_processing.utils.utils import check_for_meb_griddata

    input_data = check_for_meb_griddata(meb.read_griddata_from_nc(input_data_path), valid_val=(-np.inf, np.inf, np.nan))
    mask = (
        None
        if mask_path is None
        else read_mask_or_weights_from_nc(mask_path)
    )

    radius_or_radii, parsed_lead_times = radius_by_lead_time(list(radii), lead_times)

    work_input_data = input_data.copy()
    if degrees_as_complex:
        work_input_data = work_input_data.copy(
            data=deg_to_complex(np.asarray(work_input_data.values))
        )

    if mode == "probabilities":
        nbhood = NeighbourhoodProcessing(
            shape,
            radius_or_radii,
            lead_times=parsed_lead_times,
            weighted_mode=bool(weighted_mode),
            sum_only=bool(area_sum),
            re_mask=True,
        )
        # CLI 经 meb 读盘得到普通 DataArray，仅支持外部 mask；内部掩码需 MaskedArray
        # 输入（见 docs/nbhood.md），不在 CLI 场景内。
        result = nbhood.process(work_input_data, mask=mask)
    else:
        result = GeneratePercentilesFromANeighbourhood(
            radius_or_radii,
            lead_times=parsed_lead_times,
            percentiles=list(percentiles),
        ).process(work_input_data)

    if not isinstance(result, xr.DataArray):
        raise TypeError("算法结果不是 xarray.DataArray。")

    if degrees_as_complex:
        result = result.copy(data=complex_to_deg(np.asarray(result.values)))

    if halo_radius is not None:
        result = remove_dataarray_halo(result, halo_radius=float(halo_radius))

    result = result.astype(np.float32, copy=False)

    if output_path is not None:
        # 无效格点已是 NaN，meb 会量化为 int32 哨兵，读回可还原（见 nbs/nbhood.ipynb）。
        meb.write_griddata_to_nc(result, output_path, creat_dir=True)

    return result


if __name__ == "__main__":
    import sys

    #添加项目根目录到系统路径,可直接运行示例脚本
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # 测试数据路径（输入 cli_input，输出 cli_output）
    test_root = Path(__file__).resolve().parent.parent / "test_data" / "official_test_nbhood"
    input_dir = test_root / "cli_input" / "basic"
    output_dir = test_root / "cli_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    #各输入文件的路径映射
    input_data_path = str(input_dir / "input.nc")   #待处理输入场nc文件路径
    mask_path = None   #外部掩码nc文件路径
    output_path = str(output_dir / "cli_nbhood_square_result.nc")   #输出nc文件路径

    neighbourhood_output = "probabilities"   #邻域输出类型
    neighbourhood_shape = "square"   #邻域形状
    radii: List[float] = [20000.0]   #邻域半径（米）
    lead_times = None   #与radii对应的时效（小时）
    degrees_as_complex = False   #是否将输入角度场转为复数后再计算
    weighted_mode = False   #圆形邻域加权模式
    area_sum = False   #是否返回邻域和而非邻域平均
    halo_radius = None   #结果外圈裁剪半径（米）

    result = process(
        input_data_path,
        neighbourhood_output,
        radii,
        mask_path=mask_path,
        output_path=output_path,
        neighbourhood_shape=neighbourhood_shape,
        lead_times=lead_times,
        degrees_as_complex=degrees_as_complex,
        weighted_mode=weighted_mode,
        area_sum=area_sum,
        halo_radius=halo_radius,
    )
