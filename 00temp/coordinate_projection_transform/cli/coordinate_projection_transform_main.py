"""CLI helpers for coordinate projection transform algorithms."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="坐标投影转换算法入口。")
    parser.add_argument(
        "--mode",
        choices=["lonlat-to-equal", "meteva-to-cube", "cube-to-meteva", "summary"],
        default="summary",
        help="选择投影转换能力；summary 仅显示可用能力。",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "summary":
        print("available modes: lonlat-to-equal, meteva-to-cube, cube-to-meteva")
        return 0

    # Delay heavy imports so --help and summary work in lightweight environments.
    if args.mode == "lonlat-to-equal":
        from src.cube_lonlat_to_equal import CubeLonlatToEqual

        print(CubeLonlatToEqual.__name__)
    elif args.mode == "meteva-to-cube":
        from src.cube_base import TransMetevaToCube

        print(TransMetevaToCube.__name__)
    elif args.mode == "cube-to-meteva":
        from src.cube_base import TransCubeToMeteva

        print(TransCubeToMeteva.__name__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
