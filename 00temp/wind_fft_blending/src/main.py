# !/usr/bin/python
# -*-coding:utf-8 -*-
"""
多风场 FFT 融合执行模块。

1) 外部模块调用（单任务）::

    from main import process
    process(
        main_uv_path=r"/data/main_uv.m11",
        ass_uv_path=r"/data/ass_uv.m11",
        output_dir=r"/data/out",
        output_prefix="case1",
        is_multi=False,
    )

2) 外部模块调用（多任务，``is_multi`` 控制是否多进程）::

    process(
        main_uv_path=[r".../a1.m11", r".../b1.m11"],
        ass_uv_path=[r".../a2.m11", r".../b2.m11"],
        output_dir=r".../out",
        output_prefix=["sample_a", "sample_b"],
        is_multi=True,
        pro_count=2,
    )

3) 命令行（参数解析在 cli）::

    python -m cli --help
    python -m cli --main-uv ... --ass-uv ... --output-dir ... --output-prefix ...
    python -m cli \\
        --main-uv a1.m11 b1.m11 --ass-uv a2.m11 b2.m11 \\
        --output-prefix sample_a sample_b --output-dir ... \\
        --is-multi --pro-count 2

4) 直接运行本文件（在 ``__main__`` 中给 ``process`` 传参）::

    python src/main.py

样例数据目录（与 ``NIMM_pip_repos`` 同级）::

    NIMM_pip_testdata/multi_wind_fft_blending/test_data/
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Union

from meteva import base as meb

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = Path(_SRC_DIR).resolve().parent
_00TEMP = _PROJECT_ROOT.parent
for _p in (str(_SRC_DIR), str(_00TEMP)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fft_merge  # noqa: E402
from utils.multipro_plugin import SimpleParallelTool  # noqa: E402

_TEST_DATA = (
    _PROJECT_ROOT.parents[1].parent
    / "NIMM_pip_testdata"
    / "multi_wind_fft_blending"
    / "test_data"
)


def _netcdf_encoding(da):
    name = da.name if da.name else "data0"
    return {name: {"dtype": "int32", "scale_factor": 0.001, "_FillValue": -9999, "zlib": True}}


def del_dir_or_file(src_path):
    """删除文件或者文件夹。"""
    try:
        if not os.path.exists(src_path):
            return True
        if os.path.isdir(src_path):
            shutil.rmtree(src_path, ignore_errors=True)
        else:
            os.remove(src_path)
    except Exception:
        pass


def _as_str_list(value: Union[str, os.PathLike, Sequence]) -> List[str]:
    if isinstance(value, (str, os.PathLike)):
        return [os.fspath(value)]
    return [os.fspath(v) for v in value]


def _normalize_cases(
    main_uv_path: Union[str, Sequence[str]],
    ass_uv_path: Union[str, Sequence],
    output_dir: str,
    output_prefix: Union[str, Sequence[str]],
) -> List[Dict[str, Any]]:
    """将入口参数规范为任务列表。"""
    mains = _as_str_list(main_uv_path)
    prefixes = _as_str_list(output_prefix)

    if len(mains) == 1:
        if len(prefixes) != 1:
            raise ValueError("单主场时 output_prefix 只能有一个")
        if isinstance(ass_uv_path, (str, os.PathLike)):
            ass = [os.fspath(ass_uv_path)]
        else:
            ass = [os.fspath(p) for p in ass_uv_path]
        if not ass:
            raise ValueError("ass_uv_path 不能为空")
        return [{
            "main_uv_path": mains[0],
            "ass_uv_path": ass,
            "output_dir": output_dir,
            "output_prefix": prefixes[0],
        }]

    if len(prefixes) != len(mains):
        raise ValueError("多主场时 output_prefix 数量须与 main_uv_path 一致")
    if isinstance(ass_uv_path, (str, os.PathLike)):
        raise ValueError("多主场时 ass_uv_path 须为与主场等长的列表")
    ass_list = list(ass_uv_path)
    if len(ass_list) != len(mains):
        raise ValueError("多主场时 ass_uv_path 数量须与 main_uv_path 一致")

    cases = []
    for main_p, ass_p, prefix in zip(mains, ass_list, prefixes):
        cases.append({
            "main_uv_path": main_p,
            "ass_uv_path": ass_p,
            "output_dir": output_dir,
            "output_prefix": prefix,
        })
    return cases


def _run_one(
    main_uv_path: str,
    ass_uv_path: Union[str, Sequence[str]],
    output_dir: str,
    output_prefix: str,
    feature_border: int = 128,
    max_iterations: int = 1024,
    move_percent: float = 1.0,
    write_linear_compare: bool = True,
) -> bool:
    """执行单次 FFT 融合（内部实现，不含多进程逻辑）。"""
    if isinstance(ass_uv_path, (str, os.PathLike)):
        ass_uv_paths: List[str] = [os.fspath(ass_uv_path)]
    else:
        ass_uv_paths = [os.fspath(p) for p in ass_uv_path]
    if not ass_uv_paths:
        print("ass_uv_path 不能为空")
        return False

    if not os.path.isfile(main_uv_path):
        print(f"主风场不存在: {main_uv_path}")
        return False
    for p in ass_uv_paths:
        if not os.path.isfile(p):
            print(f"辅助风场不存在: {p}")
            return False
    if not (0.0 < float(move_percent) <= 1.0):
        print("move_percent 须满足 (0, 1]")
        return False

    os.makedirs(output_dir, exist_ok=True)
    prefix = str(output_prefix).strip() or "fft_merge"
    print(f"主风场: {main_uv_path}")
    print(f"辅助风场: {ass_uv_paths}")
    print(f"执行结果保存目录：{output_dir}")

    print("******开始读取输入数据")
    uv1_da = meb.read_gridwind_from_micaps11(main_uv_path)
    print(f"读取完成：{main_uv_path}")
    uv2_da_list = []
    for p in ass_uv_paths:
        da = meb.read_gridwind_from_micaps11(p)
        uv2_da_list.append(da)
        print(f"读取完成：{p}")

    muv_path = os.path.join(output_dir, f"{prefix}_fft_uv.nc")
    muv_m11_path = os.path.join(output_dir, f"{prefix}_fft_uv.m11")
    del_dir_or_file(muv_path)
    del_dir_or_file(muv_m11_path)

    print("******开始进行FFT融合")
    s_time = time.time()
    fft_c = fft_merge.FFTMergePlugin()
    muv_da = fft_c(
        uv1_da,
        uv2_da_list,
        feature_border=int(feature_border),
        max_iterations=int(max_iterations),
        move_percent=float(move_percent),
    )
    muv_da.to_netcdf(muv_path, encoding=_netcdf_encoding(muv_da))
    print(f"FFT融合结果保存成功: {muv_path}")
    print(f"FFT融合完成, 耗时：{round(time.time() - s_time, 4)}s")
    meb.write_griddata_to_micaps11(muv_da, muv_m11_path)
    print(f"FFT风速结果micaps11保存成功（为了方便对比结果）:{muv_m11_path}")

    if write_linear_compare:
        luv_path = os.path.join(output_dir, f"{prefix}_line_uv.nc")
        luv_m11_path = os.path.join(output_dir, f"{prefix}_line_uv.m11")
        del_dir_or_file(luv_path)
        del_dir_or_file(luv_m11_path)
        print("******开始进行线性插值")
        s_time = time.time()
        luv_da = uv1_da
        for da in uv2_da_list:
            luv_da = luv_da + da
        luv_da = luv_da / float(1 + len(uv2_da_list))
        luv_da.to_netcdf(luv_path, encoding=_netcdf_encoding(luv_da))
        print(f"线性插值结果保存成功: {luv_path}")
        print(f"线性插值执行完成, 耗时：{round(time.time() - s_time, 4)}s")
        meb.write_griddata_to_micaps11(luv_da, luv_m11_path)
        print(f"线性插值风速micaps11结果保存成功（为了方便对比结果）:{luv_m11_path}")

    print("执行完毕")
    return True


def _process_worker(
    feature_border: int = 128,
    max_iterations: int = 1024,
    move_percent: float = 1.0,
    write_linear_compare: bool = True,
    **params,
) -> bool:
    """多进程 worker：处理 ``params['param']`` 中的单个任务。"""
    case = params["param"]
    return _run_one(
        main_uv_path=case["main_uv_path"],
        ass_uv_path=case["ass_uv_path"],
        output_dir=case["output_dir"],
        output_prefix=case["output_prefix"],
        feature_border=feature_border,
        max_iterations=max_iterations,
        move_percent=move_percent,
        write_linear_compare=write_linear_compare,
    )


def process(
    main_uv_path: Union[str, Sequence[str]],
    ass_uv_path: Union[str, Sequence],
    output_dir: str,
    output_prefix: Union[str, Sequence[str]],
    feature_border: int = 128,
    max_iterations: int = 1024,
    move_percent: float = 1.0,
    write_linear_compare: bool = True,
    is_multi: bool = False,
    pro_count: int = 4,
) -> Union[bool, List[bool]]:
    """
    FFT 融合统一入口。不读配置，参数均由调用方传入。

    Parameters
    ----------
    main_uv_path : str | sequence[str]
        主风场路径。传列表表示多个独立融合任务。
    ass_uv_path : str | sequence
        辅助风场路径。
        - 单主场：一个路径，或路径列表（同一任务的多辅助场）
        - 多主场：与主场等长的列表（每项为一个任务的辅助场路径或路径列表）
    output_dir : str
        输出目录。
    output_prefix : str | sequence[str]
        输出前缀；多主场时数量须与 ``main_uv_path`` 一致。
    feature_border, max_iterations, move_percent, write_linear_compare
        算法参数。
    is_multi : bool, default False
        是否多进程执行。仅当任务数 > 1 时生效：
        ``False`` 串行，``True`` 用进程池并行。
    pro_count : int, default 4
        多进程并行数（``is_multi=True`` 时使用）。

    Returns
    -------
    bool | list[bool]
        单任务返回 ``bool``；多任务返回各任务结果列表。
    """
    cases = _normalize_cases(main_uv_path, ass_uv_path, output_dir, output_prefix)
    common = dict(
        feature_border=feature_border,
        max_iterations=max_iterations,
        move_percent=move_percent,
        write_linear_compare=write_linear_compare,
    )

    if len(cases) == 1:
        return _run_one(**cases[0], **common)

    if not is_multi:
        return [_run_one(**case, **common) for case in cases]

    sw_all = datetime.now()
    parallel_tool = SimpleParallelTool(
        target_func=_process_worker,
        parallel_mode="async",
        with_return=True,
        num_process=pro_count,
        fixed_params=common,
    )
    results = parallel_tool.process({"param": cases})
    print(">>> Time elasped: " + str((datetime.now() - sw_all).total_seconds()))
    return list(results) if results is not None else []


if __name__ == "__main__":
    # 直接运行：在此修改 process 传参即可；命令行请用 python -m cli ...
    _td = str(_TEST_DATA)
    process(
        main_uv_path=os.path.join(_td, "sample_a1_uv.m11"),
        ass_uv_path=os.path.join(_td, "sample_a2_uv.m11"),
        output_dir=_td,
        output_prefix="sample_a",
        feature_border=128,
        max_iterations=1024,
        move_percent=1.0,
        write_linear_compare=True,
        is_multi=False,
        pro_count=4,
    )
