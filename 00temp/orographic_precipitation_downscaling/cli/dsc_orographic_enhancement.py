#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""地形增强 CLI 示例。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import xarray as xr
import meteva_base as meb
import numpy as np

def process(
    temperature_path: str,
    humidity_path: str,
    pressure_path: str,
    wind_speed_path: str,
    wind_direction_path: str,
    orography_path: str,
    output_path: Optional[str] = None,
    *,
    boundary_height: float = 1000.0,
    boundary_height_units: str = "m",
) -> xr.DataArray:
    """地形增强处理流程。

    参数
    ----------
    temperature_path : str
        温度输入场 nc 文件路径。
    humidity_path : str
        相对湿度输入场 nc 文件路径。
    pressure_path : str
        气压输入场 nc 文件路径。
    wind_speed_path : str
        风速输入场 nc 文件路径。
    wind_direction_path : str
        风向输入场 nc 文件路径（相对真北角度）。
    orography_path : str
        目标地形网格场 nc 文件路径。
    output_path : str, optional
        输出 nc 文件路径；为 None 时不写文件。
    boundary_height : float, default=1000.0
        边界层代表高度。
    boundary_height_units : str, default="m"
        边界层代表高度单位。

    返回
    -------
    xr.DataArray
        地形增强结果，单位 ``m s-1``。
    """
    from orographic_enhancement.src.orographic_enhancement import MetaOrographicEnhancement
    from orographic_enhancement.utils.utils import check_for_meb_griddata, check_for_xy_coordinates

    _unbounded = (-np.inf, np.inf, np.nan)

    temperature = check_for_meb_griddata(
        meb.read_griddata_from_nc(temperature_path), valid_val=_unbounded
    )
    humidity = check_for_meb_griddata(
        meb.read_griddata_from_nc(humidity_path), valid_val=_unbounded
    )
    pressure = check_for_meb_griddata(
        meb.read_griddata_from_nc(pressure_path), valid_val=_unbounded
    )
    wind_speed = check_for_meb_griddata(
        meb.read_griddata_from_nc(wind_speed_path), valid_val=_unbounded
    )
    wind_direction = check_for_meb_griddata(
        meb.read_griddata_from_nc(wind_direction_path), valid_val=_unbounded
    )
    orography = check_for_meb_griddata(
        meb.read_griddata_from_nc(orography_path),
        is_single=True,
        valid_val=_unbounded,
    )

    for label, field in (
        ("相对湿度场", humidity),
        ("气压场", pressure),
        ("风速场", wind_speed),
        ("风向场", wind_direction),
    ):
        if not check_for_xy_coordinates([temperature, field], is_time_match=True):
            raise ValueError(f"{label}与温度场的空间/时效坐标不一致")

    plugin = MetaOrographicEnhancement(
        boundary_height=boundary_height,
        boundary_height_units=boundary_height_units,
    )
    result = plugin(
        temperature,
        humidity,
        pressure,
        wind_speed,
        wind_direction,
        orography,
    )

    if output_path is not None:
        # meb.write_griddata_to_nc 对 ~1e-6 m/s 量级结果会量化成 0，改用 xarray 直写。
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        var_name = result.name if result.name else "orographic_enhancement"
        result.to_dataset(name=var_name).to_netcdf(output_file, mode="w")

    return result


if __name__ == "__main__":
    import sys

    #添加项目根目录到系统路径,可直接运行示例脚本
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
        
    #测试数据路径
    data_dir = (
        Path(__file__).resolve().parent.parent
        / "test_data"
        / "orographic_enhancement_data"
        / "normalized_meb6d"
    )

    #各输入文件的路径映射
    temperature_path = str(data_dir / "temperature.nc")   #温度场nc文件路径
    humidity_path = str(data_dir / "humidity.nc")   #相对湿度场nc文件路径
    pressure_path = str(data_dir / "pressure.nc")   #气压场nc文件路径
    wind_speed_path = str(data_dir / "wind_speed.nc")   #风速场nc文件路径
    wind_direction_path = str(data_dir / "wind_direction.nc")   #风向场nc文件路径
    orography_path = str(data_dir / "orography_uk-standard_1km.nc")   #地形场nc文件路径
    output_path = str(data_dir / "cli_test_result.nc")   #输出nc文件路径

    boundary_height = 1000.0   #边界层代表高度  
    boundary_height_units = "m"   #边界层代表高度单位

    result = process(
        temperature_path,
        humidity_path,
        pressure_path,
        wind_speed_path,
        wind_direction_path,
        orography_path,
        output_path=output_path,
        boundary_height=boundary_height,
        boundary_height_units=boundary_height_units,
    )
