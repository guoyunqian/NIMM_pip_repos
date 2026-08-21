#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""地形带权重辅助场生成 CLI 示例。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import meteva_base as meb
import xarray as xr


def process(
    orography_path: str,
    landmask_path: Optional[str] = None,
    thresholds_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """读取输入数据并生成地形带折叠权重。

    读取地形高度与可选海陆掩码，生成各地形带权重：格点在带中心时该带权重为 1.0；
    在带边界时上下带各为 0.5；其余在中心与边界之间线性变化。

    参数
    ----------
    orography_path : str
        标准网格地形高度场 nc 路径。
    landmask_path : str, optional
        标准网格海陆掩码 nc 路径（陆=1，海=0）。若提供则屏蔽海点；
        为空时对陆点与海点均生成权重。
    thresholds_path : str, optional
        地形带配置 JSON 路径。字典格式示例::

            {"bounds": [[0, 50], [50, 200]], "units": "m"}

        为空时使用默认 ``THRESHOLDS_DICT``，形如::

            {
                "bounds": [
                    [-500.0, 50.0], [50.0, 100.0], [100.0, 150.0],
                    [150.0, 200.0], [200.0, 250.0], [250.0, 300.0],
                    [300.0, 400.0], [400.0, 500.0], [500.0, 650.0],
                    [650.0, 800.0], [800.0, 950.0], [950.0, 6000.0],
                ],
                "units": "m",
            }

    output_path : str, optional
        输出 nc 路径；为空时仅返回结果。

    返回
    -------
    xr.DataArray
        沿 ``level`` 维堆叠的地形带权重（meteva_base 六维）。
    """
    from generate_ancillary.src.generate_ancillary import THRESHOLDS_DICT
    from generate_ancillary.src.generate_topographic_zone_weights import (
        GenerateTopographicZoneWeights,
    )

    orography = meb.read_griddata_from_nc(orography_path)

    if thresholds_path is None:
        thresholds_dict = THRESHOLDS_DICT
    else:
        with open(thresholds_path, "r", encoding="utf-8") as input_file:
            thresholds_dict = json.load(input_file)

    landmask = (
        meb.read_griddata_from_nc(landmask_path) if landmask_path is not None else None
    )

    result = GenerateTopographicZoneWeights().process(
        orography=orography,
        thresholds_dict=thresholds_dict,
        landmask=landmask,
    )

    if output_path is not None:
        meb.write_griddata_to_nc(result.astype("float32"), output_path, creat_dir=True)
    return result


if __name__ == "__main__":
    import sys

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # 复用地形带权重官方样例输入
    test_data_root = (
        Path(__file__).resolve().parents[1]
        / "test_data"
        / "generate-topography-bands-weights"
    )
    cli_input_root = test_data_root / "basic" / "cli_inputs"
    cli_output_root = test_data_root / "basic" / "cli_outputs"

    orography_path = cli_input_root / "input_orog_meb.nc"
    landmask_path = cli_input_root / "input_land_meb.nc"
    thresholds_path = test_data_root / "basic" / "bounds.json"
    output_path = cli_output_root / "cli_topographic_zone_weights_result.nc"

    if not orography_path.is_file():
        print(
            f"示例输入不存在：{orography_path}\n"
            "请补充 test_data 后重试，或在此处改为自己的输入/输出路径。"
        )
    else:
        process(
            orography_path=str(orography_path),
            landmask_path=str(landmask_path) if landmask_path.is_file() else None,
            thresholds_path=str(thresholds_path) if thresholds_path.is_file() else None,
            output_path=str(output_path),
        )
