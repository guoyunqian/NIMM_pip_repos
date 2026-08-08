#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""CLI 示例：调用 ManipulateReliabilityTable 整理可靠性表。

用法（仓库根目录，先改脚本底部路径）::

    python probability_reliability_correction/cli/prb_manipulate_reliability_table.py

网格：``output_path`` 为**目录**（按阈值多文件）；站点：为**单个 csv**。
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

import pandas as pd
import xarray as xr


def process(
    reliability_table_path: Union[str, Path],
    *,
    minimum_forecast_count: int = 200,
    point_by_point: bool = False,
    output_path: Optional[Union[str, Path]] = None,
) -> Union[List[xr.Dataset], pd.DataFrame]:
    """读取可靠性表，合并欠采样箱并强制观测频率单调，可选写出。

    参数
    ----------
    reliability_table_path :
        可靠性表路径；
        网格 ``.nc`` 或站点 ``.csv``。
    minimum_forecast_count :
        概率箱最少预报计数；低于该值将尝试与邻箱合并。
    point_by_point :
        是否按空间点 / 站点分别整理。
    output_path :
        网格为输出目录；站点为输出 csv；``None`` 只返回。

    返回
    -------
    list of xr.Dataset 或 pd.DataFrame
        网格按阈值拆开的表列表，或站点一张长表。
    """
    from probability_reliability_correction.cli.io import read_reliability, write_result
    from probability_reliability_correction.src.reliability_calibration import (
        ManipulateReliabilityTable,
    )

    table = read_reliability(reliability_table_path)
    result = ManipulateReliabilityTable(
        minimum_forecast_count=minimum_forecast_count,
        point_by_point=point_by_point,
    ).process(table)
    if output_path is not None:
        written = write_result(result, output_path)
        if written is not None:
            print("已写出", len(written), "个阈值表 ->", Path(output_path))
    return result


if __name__ == "__main__":
    import sys

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    data_root = (
        Path(__file__).resolve().parent.parent
        / "test_data"
        / "manipulate-reliability-table"
        / "basic"
    )
    cli_input = data_root / "cli_input"
    cli_output = data_root / "cli_output" / "mig_cli_cloud_min300"
    table_file = cli_input / "reliability_table_cloud.nc"
    if not table_file.is_file():
        print(
            f"示例输入不存在：{table_file}\n"
            "请补齐 test_data（可先运行 cli/preprocess_test_data.py）后再试，"
            "或在此处改成你自己的输入路径。"
        )
    else:
        cli_output.mkdir(parents=True, exist_ok=True)
        process(
            table_file,
            minimum_forecast_count=300,
            point_by_point=False,
            output_path=cli_output,
        )
