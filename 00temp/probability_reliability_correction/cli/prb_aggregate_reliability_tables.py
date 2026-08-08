#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""CLI 示例：调用 AggregateReliabilityCalibrationTables 聚合可靠性表。

用法（仓库根目录，先改脚本底部路径）::

    python probability_reliability_correction/cli/prb_aggregate_reliability_tables.py

输入由后缀决定：``.nc`` 网格表；``.csv`` 站点长表。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Union

import pandas as pd
import xarray as xr


def process(
    reliability_table_paths: Sequence[Union[str, Path]],
    *,
    coordinates: Optional[Sequence[str]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Union[xr.Dataset, pd.DataFrame]:
    """读取一张或多张可靠性表，按坐标求和聚合并可选写出。

    参数
    ----------
    reliability_table_paths :
        可靠性表路径；
        网格 ``.nc`` 或站点 ``.csv`` 路径列表（不可混用）。
    coordinates :
        要求和的坐标，例如网格 ``["lat", "lon"]``、站点 ``["id"]``；
        ``None`` 表示多表合并时不对空间/站点维求和。
    output_path :
        若给出则写出结果；``None`` 只返回。

    返回
    -------
    xr.Dataset 或 pd.DataFrame
        聚合后的可靠性表。
    """
    from probability_reliability_correction.cli.io import read_reliabilities, write_result
    from probability_reliability_correction.src.reliability_calibration import (
        AggregateReliabilityCalibrationTables,
    )

    tables = read_reliabilities(reliability_table_paths)
    result = AggregateReliabilityCalibrationTables().process(
        tables,
        coordinates=None if coordinates is None else list(coordinates),
    )
    if output_path is not None:
        write_result(result, output_path)
    return result


if __name__ == "__main__":
    import sys

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    data_root = (
        Path(__file__).resolve().parent.parent
        / "test_data"
        / "aggregate-reliability-tables"
        / "basic"
    )
    cli_input = data_root / "cli_input"
    cli_output = data_root / "cli_output"
    table_file = cli_input / "reliability_table.nc"
    if not table_file.is_file():
        print(
            f"示例输入不存在：{table_file}\n"
            "请补齐 test_data（可先运行 cli/preprocess_test_data.py）后再试，"
            "或在此处改成你自己的输入路径。"
        )
    else:
        cli_output.mkdir(parents=True, exist_ok=True)
        # 示例 1：对空间 lat/lon 求和（折叠空间）
        process(
            [table_file],
            coordinates=["lat", "lon"],
            output_path=cli_output / "mig_cli_collapsed.nc",
        )
    # 示例 2：多表按 FRT 合并（不空间求和）
    # process(
    #     [
    #         cli_input / "reliability_table.nc",
    #         cli_input / "reliability_table_2.nc",
    #     ],
    #     coordinates=None,
    #     output_path=cli_output / "reliability_table_multi.nc",
    # )
    # 站点示例：process(["table_sta.csv"], coordinates=["id"], output_path="out.csv")
