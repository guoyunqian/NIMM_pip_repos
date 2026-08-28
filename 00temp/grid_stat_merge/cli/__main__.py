# -*- coding: utf-8 -*-
"""
格站融合 CLI：解析参数后调度 ``runner.process``。

项目根目录执行::

    python -m cli --help
    python -m cli --grid=resource/demo_grid.m4 --sta=resource/demo_sta.m3
    python -m cli --output=resource/output/merge.m4 --R=200
"""
import argparse
import sys
from pathlib import Path


def _bootstrap_paths():
    _root = Path(__file__).resolve().parent.parent
    _src = _root / "src"
    for p in (str(_root), str(_src)):
        if p not in sys.path:
            sys.path.insert(0, p)


_bootstrap_paths()

from runner import process
from utils.util_env import get_resolved_paths, get_merge_params


def _parse_bool(s):
    if s is None:
        return None
    t = str(s).strip().lower()
    if t in ("", "none"):
        return None
    if t in ("1", "true", "yes", "y", "on"):
        return True
    if t in ("0", "false", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError("期望布尔值：true/false/1/0")


def _parse_domain(s):
    if s is None or not str(s).strip():
        return None
    vals = [float(x.strip()) for x in str(s).split(",") if x.strip()]
    if len(vals) != 6:
        raise argparse.ArgumentTypeError("domain 须为 6 个数：sou,nor,wst,est,dlon,dlat")
    return vals


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m cli",
        description=(
            "grid_stat_merge：格站融合（站点偏差高斯订正网格）。\n"
            "未给出的项从 resource/grid_stat_merge.ini 读取。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python -m cli --help\n"
            "  python -m cli\n"
            "  python -m cli --grid=a.m4 --sta=b.m3 --output=out.m4\n"
            "  python -m cli --R=200 --use-heatflux false\n"
        ),
    )
    parser.add_argument("--grid", default=None, metavar="PATH", help="输入格点 Micaps4/NC")
    parser.add_argument("--sta", default=None, metavar="PATH", help="输入站点 Micaps3")
    parser.add_argument("--output", default=None, metavar="PATH", help="输出格点 Micaps4")
    parser.add_argument("--terr", default=None, metavar="PATH", help="可选地形格点")
    parser.add_argument("--R", dest="R", type=float, default=None, help="误差传播半径（默认 ini）")
    parser.add_argument(
        "--domain", type=_parse_domain, default=None,
        metavar="sou,nor,wst,est,dlon,dlat",
        help="业务域；省略则从格点推断或读 ini",
    )
    parser.add_argument(
        "--use-heatflux", type=_parse_bool, default=None, metavar="BOOL",
        help="是否热传导去牛眼",
    )
    parser.add_argument(
        "--hf-iters", type=int, default=None, metavar="N",
        help="热传导迭代次数",
    )
    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    # 触达 ini，便于缺配置时尽早暴露
    get_resolved_paths()
    get_merge_params()
    process(
        grid_path=args.grid,
        sta_path=args.sta,
        output_path=args.output,
        terr_path=args.terr,
        R=args.R,
        domain=args.domain,
        b_use_heatflux_equation=args.use_heatflux,
        hf_eq_iter_nums=args.hf_iters,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
