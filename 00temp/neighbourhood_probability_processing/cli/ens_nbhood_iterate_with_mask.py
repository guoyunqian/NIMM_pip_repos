#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""按掩码分层迭代的邻域处理 CLI 示例。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np
import xarray as xr
import meteva_base as meb


def process(
    input_data_path: str,
    mask_path: str,
    coord_for_masking: str,
    radii: Sequence[float],
    weights_path: Optional[str] = None,
    output_path: Optional[str] = None,
    *,
    neighbourhood_shape: str = "square",
    lead_times: Optional[Sequence[int]] = None,
    area_sum: bool = False,
) -> xr.DataArray:
    """执行“按掩码层迭代”的邻域处理。

    参数
    ----------
    input_data_path : str
        待处理输入场 nc 文件路径。
    mask_path : str
        掩码分层数据 nc 文件路径，需包含 ``coord_for_masking`` 维。
    coord_for_masking : str
        掩码分层维名称，例如 ``topographic_zone``。
    radii : sequence of float
        邻域半径（米），可单值或多值。
    weights_path : str, optional
        掩码维折叠权重 nc 文件路径。
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
        邻域处理结果。
    """
    from neighbourhood_probability_processing.src.utils._helpers import radius_by_lead_time
    from neighbourhood_probability_processing.src.use_nbhood import ApplyNeighbourhoodProcessingWithAMask
    from neighbourhood_probability_processing.cli.io import read_mask_or_weights_from_nc
    from neighbourhood_probability_processing.utils.utils import check_for_meb_griddata


    input_data = check_for_meb_griddata(meb.read_griddata_from_nc(input_data_path), valid_val=(-np.inf, np.inf, np.nan))
    mask = read_mask_or_weights_from_nc(mask_path)
    if coord_for_masking not in mask.dims:
        raise ValueError(f"mask 中缺少分层维 {coord_for_masking}")
    weights = (
        None
        if weights_path is None
        else read_mask_or_weights_from_nc(weights_path)
    )

    radius_or_radii, parsed_lead_times = radius_by_lead_time(list(radii), lead_times)
    result = ApplyNeighbourhoodProcessingWithAMask(
        coord_for_masking=coord_for_masking,
        neighbourhood_method=neighbourhood_shape,
        radii=radius_or_radii,
        lead_times=parsed_lead_times,
        collapse_weights=weights,
        sum_only=area_sum,
    ).process(input_data, mask)

    if output_path is not None:
        if result.name is None:
            result = result.copy()
            result.name = "neighbourhood_result"
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
        / "iterate_with_mask"
    )
    input_dir = scenario_dir / "cli_input"
    output_dir = scenario_dir / "cli_output"

    #各输入文件的路径映射
    input_data_path = str(input_dir / "thresholded_input.nc")   #待处理输入场
    mask_path = str(input_dir / "orographic_bands_mask.nc")   #掩码分层数据
    weights_path = str(input_dir / "orographic_bands_weights.nc")   #掩码维折叠权重
    output_path = str(output_dir / "cli_iterated_result.nc")   #带权重折叠输出nc文件路径

    coord_for_masking = "topographic_zone"   #掩码分层维名称
    neighbourhood_shape = "square"   #邻域形状
    radii: List[float] = [10000.0]   #邻域半径（米），折叠场景与官方 KGO 对齐
    lead_times = None   #与radii对应的时效（小时）
    area_sum = False   #是否输出邻域和（True）而非邻域平均（False）

    result = process(
        input_data_path,
        mask_path,
        coord_for_masking,
        radii,
        weights_path=weights_path,
        output_path=output_path,
        neighbourhood_shape=neighbourhood_shape,
        lead_times=lead_times,
        area_sum=area_sum,
    )
