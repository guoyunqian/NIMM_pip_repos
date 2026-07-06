#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""计算体感温度的 CLI 示例。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import xarray as xr
import meteva_base as meb

def process(
    temperature_path: str,
    wind_speed_path: str,
    relative_humidity_path: str,
    pressure_path: str,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """根据气温、风速、相对湿度和气压计算体感温度。

    参数
    ----------
    temperature_path : str
        屏幕高度气温场 nc 文件路径。
    wind_speed_path : str
        10 米风速场 nc 文件路径。
    relative_humidity_path : str
        屏幕高度相对湿度场 nc 文件路径。
    pressure_path : str
        气压场 nc 文件路径（海平面气压或地面气压，按单位自动换算）。
    output_path : str, optional
        输出 nc 文件路径；为 None 时不写文件。

    返回
    -------
    xr.DataArray
        体感温度场。
    """
    from feels_like_temperature.src.feels_like_temperature import calculate_feels_like_temperature
    from feels_like_temperature.utils.utils import check_for_meb_griddata, check_for_xy_coordinates
    
    _valid_val = (-np.inf, np.inf, np.nan)
    temperature = check_for_meb_griddata(
        meb.read_griddata_from_nc(temperature_path), valid_val=_valid_val
    )
    wind_speed = check_for_meb_griddata(
        meb.read_griddata_from_nc(wind_speed_path), valid_val=_valid_val
    )
    relative_humidity = check_for_meb_griddata(
        meb.read_griddata_from_nc(relative_humidity_path), valid_val=_valid_val
    )
    pressure = check_for_meb_griddata(
        meb.read_griddata_from_nc(pressure_path), valid_val=_valid_val
    )

    for label, field in (
        ("风速场", wind_speed),
        ("相对湿度场", relative_humidity),
        ("气压场", pressure),
    ):
        if not check_for_xy_coordinates([temperature, field], is_time_match=True):
            raise ValueError(f"{label}与温度场的空间/时效坐标不一致")

    result = calculate_feels_like_temperature(
        temperature=temperature,
        wind_speed=wind_speed,
        relative_humidity=relative_humidity,
        pressure=pressure,
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
        / "feels_like_temp_data"
    )
    cli_input_dir = data_root / "cli_input"
    cli_output_dir = data_root / "cli_output"

    #各输入文件的路径映射
    temperature_path = str(cli_input_dir / "20181121T1200Z-PT0012H00M-temperature_at_screen_level.nc")   #温度场nc文件路径
    wind_speed_path = str(cli_input_dir / "20181121T1200Z-PT0012H00M-wind_speed_at_10m.nc")   #风速场nc文件路径
    relative_humidity_path = str(
        cli_input_dir / "20181121T1200Z-PT0012H00M-relative_humidity_at_screen_level.nc"
    )   #相对湿度场nc文件路径
    pressure_path = str(cli_input_dir / "20181121T1200Z-PT0012H00M-pressure_at_mean_sea_level.nc")   #气压场nc文件路径
    output_path = str(cli_output_dir / "cli_feels_like_temp_result.nc")   #输出nc文件路径

    result = process(
        temperature_path,
        wind_speed_path,
        relative_humidity_path,
        pressure_path,
        output_path=output_path,
    )
