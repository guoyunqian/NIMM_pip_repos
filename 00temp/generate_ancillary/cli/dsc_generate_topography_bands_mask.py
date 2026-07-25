#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""地形带辅助场生成 CLI 示例。"""

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
    """读取输入数据并生成地形带掩码辅助场。

    功能逻辑：
    根据地形高度场，将区域按海拔划分为多个连续的地形带（如 -500~50m、50~100m 等），
    每个地形带生成一张二值掩码图，标记哪些格点落在该海拔区间内。

    核心处理流程：
    1. 接收地形高度场、海陆掩码（可选）、阈值配置
    2. 遍历每个地形带区间：
       a. 单位换算（将阈值转换到地形场的单位）
       b. 阈值比较：lower < orog <= upper，生成二值掩码
       c. 海点处理：若提供了海陆掩码，将海点置为 0
       d. 将结果包装为标准六维 DataArray，地形带映射到 level 维
    3. 将所有地形带沿 level 维堆叠，返回完整结果

    当output_path不为空时，输出结果为float32类型的地形带掩码场。

    参数
    ----------
    orography_path : str
        地形高度场 nc 文件路径。
    landmask_path : str, optional
        海陆掩码 nc 文件路径。为空时，输出包含海点。
    thresholds_path : str, optional
        地形带阈值 JSON 文件路径。为空时使用默认阈值 ``THRESHOLDS_DICT``。
    output_path : str, optional
        输出 nc 文件路径。为空时仅返回结果，不写盘。

    返回
    -------
    xr.DataArray
        沿 ``level`` 维堆叠的地形带掩码。
    """
    from generate_ancillary.src.generate_ancillary import (
        THRESHOLDS_DICT,
        GenerateOrographyBandAncils,
    )

    orography = meb.read_griddata_from_nc(orography_path)
    
    if thresholds_path is None:
        thresholds_dict = THRESHOLDS_DICT
    else:
        with open(thresholds_path, "r") as input_file:
            thresholds_dict = json.load(input_file)

    landmask = meb.read_griddata_from_nc(landmask_path) if landmask_path is not None else None

    result = GenerateOrographyBandAncils().process(
        orography=orography,
        thresholds_dict=thresholds_dict,
        landmask=landmask,
    )

    if output_path is not None:
        # meteva_base 写盘默认使用 scale_factor + int32 编码；
        # 对 int32 掩码直接写盘会触发 xarray 编码阶段的 dtype 冲突。
        meb.write_griddata_to_nc(result.astype("float32"), output_path, creat_dir=True)
    return result


if __name__ == "__main__":
    import sys

    # 添加项目根目录到系统路径，可直接运行示例脚本
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Notebook 预处理后、可被 meb.read_griddata_from_nc 直接读取的数据
    test_data_root = (
        Path(__file__).resolve().parents[1]
        / "test_data"
        / "official_test_generate_ancillary"
    )
    cli_input_root = test_data_root / "basic" / "cli_inputs"
    cli_output_root = test_data_root / "basic" / "cli_outputs"

    orography_path = cli_input_root / "input_orog_meb.nc"
    landmask_path = cli_input_root / "input_land_meb.nc"
    thresholds_path = test_data_root / "basic" / "bounds.json"
    output_path = cli_output_root / "cli_topography_bands_mask_result.nc"

    if not orography_path.is_file():
        print(
            f"示例输入不存在：{orography_path}\n"
            "请补充 test_data 后重试，或在此处配置自己的输入与输出路径。"
        )
    else:
        process(
            orography_path=str(orography_path),
            landmask_path=str(landmask_path) if landmask_path.is_file() else None,
            thresholds_path=str(thresholds_path) if thresholds_path.is_file() else None,
            output_path=str(output_path),
        )
