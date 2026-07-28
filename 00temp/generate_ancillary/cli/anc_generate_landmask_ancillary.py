#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""海陆掩码二值化 CLI 示例。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import meteva_base as meb
import xarray as xr


def process(landmask_path: str, output_path: Optional[str] = None) -> xr.DataArray:
    """读取海陆掩码并输出 0/1 二值化结果。

    功能逻辑：
    插值后的海陆掩码场中，格点值为 0~1 之间的浮点数，表示该格点为陆地的概率。
    本方法以 0.5 为阈值进行二值化：
    - 格点值 < 0.5：判定为海，置为 0
    - 格点值 >= 0.5：判定为陆，置为 1
    当output_path不为空时，输出结果为float32类型的二值掩码场。

    输入输出均为 meteva_base 标准六维网格数据（member, level, time, dtime, lat, lon），
    维度保持不变，仅修改格点值。

    参数
    ----------
    landmask_path : str
        输入海陆掩码 nc 文件路径。
    output_path : str, optional
        输出 nc 文件路径。为空时仅返回结果，不写盘。

    返回
    -------
    xr.DataArray
        二值化后的海陆掩码，维度保持输入不变。
    """
    from generate_ancillary.src.generate_ancillary import CorrectLandSeaMask
    
    landmask = meb.read_griddata_from_nc(landmask_path)
    result = CorrectLandSeaMask().process(landmask)

    if output_path is not None:
        # 避免 meteva_base 在 int32 + scale_factor 编码时触发类型冲突。
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
        / "generate-landmask"
        / "basic"
    )
    cli_input_root = test_data_root / "cli_inputs"
    cli_output_root = test_data_root / "cli_outputs"

    landmask_path = cli_input_root / "input_landmask_meb.nc"
    output_path = cli_output_root / "cli_landmask_result.nc"

    if not landmask_path.is_file():
        print(
            f"示例输入不存在：{landmask_path}\n"
            "请补充 test_data 后重试，或在此处改为自己的输入/输出路径。"
        )
    else:
        process(landmask_path=str(landmask_path), output_path=str(output_path))
