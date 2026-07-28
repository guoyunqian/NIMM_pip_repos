#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""地方太阳时计算 CLI 示例。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from datetime import datetime

import meteva_base as meb
import xarray as xr


def process(
    target_grid_path: str,
    time: datetime,
    new_title: Optional[str] = None,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """读取目标网格并计算地方太阳时。"""
    from generate_derived_solar_fields.src.generate_derived_solar_fields import GenerateSolarTime

    if not isinstance(time, datetime):
        raise TypeError("time 必须是 datetime。")

    target_grid = meb.read_griddata_from_nc(target_grid_path)
    result = GenerateSolarTime().process(
        target_grid=target_grid,
        time=time,
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
        / "generate-solar-time"
    )
    cli_input_root = test_data_root / "cli_inputs"
    cli_output_root = test_data_root / "cli_outputs"

    # 输入文件路径
    target_grid_path = cli_input_root / "input_target_grid_meb.nc"
    output_path = cli_output_root / "cal_solar_time_result.nc"

    if not target_grid_path.is_file():
        print(
            f"示例输入不存在：{target_grid_path}\n"
            "请补充 test_data 后重试，或在此处配置自己的输入与输出路径。"
        )
    else:
        # 调用算法
        process(
            target_grid_path=str(target_grid_path),
            time=datetime(2022, 6, 7, 0, 0),
            output_path=str(output_path),
        )
