# -*- coding: utf-8 -*-
"""
项目根目录执行: python -m cli [选项...]
"""
import argparse
import sys
from pathlib import Path


def _bootstrap_paths():
    _root = Path(__file__).resolve().parent.parent
    _src = _root / "src"
    for p in (str(_src), str(_root)):
        if p not in sys.path:
            sys.path.insert(0, p)


_bootstrap_paths()

from correct_tp_24h import mainProcess
from utils.util_env import get_resolved_paths


def main(argv=None):
    parser = argparse.ArgumentParser(description="24 小时降水频率匹配订正")
    parser.add_argument(
        "--plugin",
        default=None,
        help="模式路径配置文件，如 resource/plugin/ecmwf.json；省略时使用 ini 中的 default_plugin",
    )
    args = parser.parse_args(argv)
    plugin = args.plugin or get_resolved_paths()["default_plugin"]
    mainProcess(plugin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
