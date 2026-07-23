# -*- coding: utf-8 -*-
"""
多风场 FFT 融合 CLI（``python -m cli`` → ``main.process``）。

项目根目录执行
--------------
::

    python -m cli --help
    python -m cli \\
        --main-uv <主风场.m11> \\
        --ass-uv <辅助风场.m11> [更多辅助场...] \\
        --output-dir <输出目录> \\
        --output-prefix <输出前缀>
    python -m cli \\
        --main-uv a1.m11 b1.m11 --ass-uv a2.m11 b2.m11 \\
        --output-prefix sample_a sample_b --output-dir <输出目录> \\
        --is-multi --pro-count 2

模块调用::

    from main import process
    process(..., is_multi=True, pro_count=2)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
_00TEMP = _ROOT.parent
for _p in (str(_SRC), str(_00TEMP)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_TEST_DATA = (
    _ROOT.parents[1].parent
    / "NIMM_pip_testdata"
    / "multi_wind_fft_blending"
    / "test_data"
)


def _build_arg_parser() -> argparse.ArgumentParser:
    test_data = str(_TEST_DATA)
    parser = argparse.ArgumentParser(
        prog="cli",
        description="多风场 FFT 融合执行入口。不读配置，全部参数由命令行传入。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "样例数据目录（与 NIMM_pip_repos 同级）:\n"
            f"  {test_data}\n\n"
            "单任务示例:\n"
            "  python -m cli \\\n"
            f"    --main-uv {test_data}/sample_a1_uv.m11 \\\n"
            f"    --ass-uv {test_data}/sample_a2_uv.m11 \\\n"
            f"    --output-dir {test_data} \\\n"
            "    --output-prefix sample_a\n\n"
            "多任务 + 多进程示例:\n"
            "  python -m cli \\\n"
            f"    --main-uv {test_data}/sample_a1_uv.m11 {test_data}/sample_b1_uv.m11 \\\n"
            f"    --ass-uv {test_data}/sample_a2_uv.m11 {test_data}/sample_b2_uv.m11 \\\n"
            "    --output-prefix sample_a sample_b \\\n"
            f"    --output-dir {test_data} \\\n"
            "    --is-multi --pro-count 2\n"
        ),
    )
    parser.add_argument(
        "--main-uv",
        required=True,
        nargs="+",
        help="主风场 Micaps11；可传多个表示多个任务",
    )
    parser.add_argument(
        "--ass-uv",
        required=True,
        nargs="+",
        help="辅助风场 Micaps11；单主场时可多个辅助场，多主场时数量须与主场一致",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="输出目录",
    )
    parser.add_argument(
        "--output-prefix",
        required=True,
        nargs="+",
        help="输出文件名前缀；多主场时数量须与主场一致",
    )
    parser.add_argument(
        "--feature-border",
        type=int,
        default=128,
        help="FFT 特征匹配网格边长",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=1024,
        help="位移场求解最大迭代次数",
    )
    parser.add_argument(
        "--move-percent",
        type=float,
        default=1.0,
        help="主场向辅助场移动比例 (0, 1]",
    )
    parser.add_argument(
        "--write-linear-compare",
        dest="write_linear_compare",
        action="store_true",
        default=True,
        help="写出线性平均对比结果（默认开启）",
    )
    parser.add_argument(
        "--no-write-linear-compare",
        dest="write_linear_compare",
        action="store_false",
        help="不写出线性平均对比结果",
    )
    parser.add_argument(
        "--is-multi",
        dest="is_multi",
        action="store_true",
        default=False,
        help="多任务时是否多进程执行（默认关闭，串行）",
    )
    parser.add_argument(
        "--no-is-multi",
        dest="is_multi",
        action="store_false",
        help="多任务时串行执行",
    )
    parser.add_argument(
        "--pro-count",
        type=int,
        default=4,
        help="多进程并行数（--is-multi 时生效）",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """解析命令行并调用 ``main.process``。"""
    from main import process

    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    main_uv = args.main_uv[0] if len(args.main_uv) == 1 else args.main_uv
    output_prefix = (
        args.output_prefix[0] if len(args.output_prefix) == 1 else args.output_prefix
    )
    ass_uv = args.ass_uv

    try:
        result = process(
            main_uv_path=main_uv,
            ass_uv_path=ass_uv,
            output_dir=args.output_dir,
            output_prefix=output_prefix,
            feature_border=args.feature_border,
            max_iterations=args.max_iterations,
            move_percent=args.move_percent,
            write_linear_compare=args.write_linear_compare,
            is_multi=args.is_multi,
            pro_count=args.pro_count,
        )
    except Exception as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        return 1

    if isinstance(result, list):
        return 0 if result and all(result) else 1
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
