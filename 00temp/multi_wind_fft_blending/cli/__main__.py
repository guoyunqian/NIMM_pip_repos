# -*- coding: utf-8 -*-
"""
项目根目录执行: python -m cli [选项...]

等价于: python cli/fft_merge_cli.py [选项...]
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    _script = _root / "cli" / "fft_merge_cli.py"
    raise SystemExit(subprocess.call([sys.executable, str(_script), *sys.argv[1:]]))
