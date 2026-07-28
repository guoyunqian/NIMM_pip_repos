#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""晴空太阳辐射累计计算 CLI 示例。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import meteva_base as meb
import xarray as xr


def process(
    target_grid_path: str,
    time: datetime,
    accumulation_period: int,
    surface_altitude_path: Optional[str] = None,
    linke_turbidity_path: Optional[str] = None,
    temporal_spacing: int = 30,
    new_title: Optional[str] = None,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """读取输入并计算累计晴空太阳辐射。"""
    from generate_derived_solar_fields.src.generate_derived_solar_fields import (
        GenerateClearskySolarRadiation,
    )

    if not isinstance(time, datetime):
        raise TypeError("time 必须是 datetime。")

    target_grid = meb.read_griddata_from_nc(target_grid_path)
    surface_altitude = (
        meb.read_griddata_from_nc(surface_altitude_path)
        if surface_altitude_path is not None
        else None
    )
    linke_turbidity = (
        meb.read_griddata_from_nc(linke_turbidity_path)
        if linke_turbidity_path is not None
        else None
    )

    result = GenerateClearskySolarRadiation().process(
        target_grid=target_grid,
        time=time,
        accumulation_period=accumulation_period,
        surface_altitude=surface_altitude,
        linke_turbidity=linke_turbidity,
        temporal_spacing=temporal_spacing,
        new_title=new_title,
    )

    if output_path is not None:
        meb.write_griddata_to_nc(result.astype("float32"), output_path, creat_dir=True)
    return result


if __name__ == "__main__":
    import sys

    # 添加项目根目录到系统路径,可直接运行示例脚本
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # 测试数据根目录
    test_data_root = (
        Path(__file__).resolve().parents[1]
        / "test_data"
        / "generate-clearsky-solar-radiation"
    )
    cli_input_root = test_data_root / "cli_inputs"
    cli_output_root = test_data_root / "cli_outputs"

    # 输入文件路径
    surface_altitude_path = cli_input_root / "input_surface_altitude_meb.nc"
    target_grid_path = surface_altitude_path
    linke_turbidity_path = cli_input_root / "input_linke_turbidity_meb.nc"
    output_path = cli_output_root / "cal_clearsky_solar_radiation_result.nc"

    if not surface_altitude_path.is_file():
        print(
            f"示例输入不存在：{surface_altitude_path}\n"
            "请补充 test_data 后重试，或在此处配置自己的输入与输出路径。"
        )
    else:
        # 调用算法
        process(
            target_grid_path=str(target_grid_path),
            time=datetime(2022, 5, 6, 0, 0),
            accumulation_period=24,
            surface_altitude_path=str(surface_altitude_path),
            linke_turbidity_path=str(linke_turbidity_path) if linke_turbidity_path.is_file() else None,
            output_path=str(output_path),
        )
