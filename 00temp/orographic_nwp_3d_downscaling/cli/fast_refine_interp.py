"""CLI for fast refined interpolation."""

from __future__ import annotations

import argparse

from nimm_g_interp.src.fast_refine_interp_plugin import FastRefineInterpPlugin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行快速精细化插值算法。")
    parser.add_argument("--work-dir", required=True, help="业务运行目录，通常放置 Fast_refine_interp_*.ini。")
    parser.add_argument("--root-path", help="业务根目录，包含 Parameter 和 lib；不传时自动推断。")
    parser.add_argument("--model-region", default="EC_12P5KM", help="模式区域，如 EC_12P5KM。")
    parser.add_argument("--s3-method", default="g_interp", help="结果目录中的算法方法名。")
    parser.add_argument("--para-file", default="Fast_refine_interp_site.ini", help="算法参数文件名。")
    parser.add_argument("--resolution", default="site", choices=["site", "1km", "5km"], help="插值分辨率。")
    parser.add_argument("--operation", default="i", choices=["i", "p", "ip"], help="i=插值，p=求参，ip=两者。")
    parser.add_argument("--begin-date", help="业务时间，格式 YYYYMMDDHH。")
    parser.add_argument("--site-name", default="Station1", help="站点文件名。")
    parser.add_argument("--debug", type=int, default=0, help="调试等级。")
    parser.add_argument("--update", type=int, default=0, help="是否强制更新，0/1。")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    plugin = FastRefineInterpPlugin(
        debug=args.debug,
        update=args.update,
        operation=args.operation,
        begin_date=args.begin_date,
        resolution=args.resolution,
        para_file=args.para_file,
        work_dir=args.work_dir,
        model_region=args.model_region,
        root_path=args.root_path,
        s3_method=args.s3_method,
        site_name=args.site_name,
    )
    return plugin.process()


if __name__ == "__main__":
    main()

