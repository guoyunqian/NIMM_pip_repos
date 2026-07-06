#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""应用层结递减率进行温度地形订正的 CLI 示例。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np
import xarray as xr
import meteva_base as meb

def process(
    temperature_path: str,
    lapse_rate_path: str,
    source_orography_path: str,
    target_orography_path: str,
    output_path: Optional[str] = None,
) -> Union[xr.DataArray, np.ndarray]:
    """将已计算的层结递减率应用到温度场。

    参数
    ----------
    temperature_path : str
        输入温度场 nc 文件路径。
    lapse_rate_path : str
        层结递减率场 nc 文件路径，单位通常为 ``K m-1``。
    source_orography_path : str
        温度原始网格对应的源地形高度场 nc 文件路径。
    target_orography_path : str
        目标地形高度场 nc 文件路径。
    output_path : str, optional
        输出 nc 文件路径；为 None 时不写文件，仅返回结果。

    返回
    -------
    xr.DataArray or np.ndarray
        地形订正后的温度场。
    """
    from orographic_temperature_downscaling.src.lapse_rate import ApplyGriddedLapseRate
    from orographic_temperature_downscaling.utils.utils import check_for_meb_griddata, check_for_xy_coordinates
    
    _unbounded = (-np.inf, np.inf, np.nan)

    temperature = meb.read_griddata_from_nc(temperature_path)
    lapse_rate = meb.read_griddata_from_nc(lapse_rate_path)
    source_orography = meb.read_griddata_from_nc(source_orography_path)
    target_orography = meb.read_griddata_from_nc(target_orography_path)

    temperature = check_for_meb_griddata(temperature, valid_val=_unbounded)
    lapse_rate = check_for_meb_griddata(lapse_rate)
    source_orography = check_for_meb_griddata(source_orography, valid_val=_unbounded)
    target_orography = check_for_meb_griddata(target_orography, valid_val=_unbounded)

    if not check_for_xy_coordinates([temperature, lapse_rate], is_time_match=True):
        raise ValueError("层结递减率场与温度场的空间/时效坐标不一致")
    if not check_for_xy_coordinates([temperature, source_orography], is_time_match=False):
        raise ValueError("源地形高度场与温度场的坐标不一致")
    if not check_for_xy_coordinates([temperature, target_orography], is_time_match=False):
        raise ValueError("目标地形高度场与温度场的坐标不一致")

    result = ApplyGriddedLapseRate()(
        temperature,
        lapse_rate,
        source_orography,
        target_orography,
    )

    if output_path is not None:
        meb.write_griddata_to_nc(result, output_path, creat_dir=True)

    return result


if __name__ == "__main__":
    import sys

    #添加项目根目录到系统路径,可直接运行示例脚本
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    #测试数据路径
    data_root = (
        Path(__file__).resolve().parent.parent
        / "test_data"
        / "apply_lapse_rate_data"
    )
    cli_input_dir = data_root / "cli_input"
    cli_output_dir = data_root / "cli_output"

    temperature_path = str(cli_input_dir / "ukvx_temperature.nc")    #温度场nc文件路径
    lapse_rate_path = str(cli_input_dir / "ukvx_lapse_rate.nc")    #层结递减率场nc文件路径
    source_orography_path = str(cli_input_dir / "ukvx_orography.nc")    #源地形高度场nc文件路径
    target_orography_path = str(cli_input_dir / "highres_orog.nc")    #目标地形高度场nc文件路径
    output_path = str(cli_output_dir / "cli_apply_lapse_rate_result.nc")#地形订正后温度场nc文件路径

    result = process(temperature_path, lapse_rate_path, source_orography_path, target_orography_path, output_path=output_path)