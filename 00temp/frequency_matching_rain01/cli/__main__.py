# -*- coding: utf-8 -*-
"""
逐1小时降水频率匹配订正 — CLI 入口。

项目根目录执行::

    python -m cli
    python -m cli ecmwf 202604081130
    python -m cli ecmwf 202604081130 202604081800

等价于::

    python src/runner.py [选项...]
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    _script = _root / "src" / "runner.py"
    raise SystemExit(subprocess.call([sys.executable, str(_script), *sys.argv[1:]]))
