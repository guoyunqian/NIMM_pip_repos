# -*- coding: utf-8 -*-
"""
项目根目录执行:

- 集成预报: ``python -m cli --time-inputs=...``
- 检验:       ``python -m cli verify --h5-file=...``
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    args = sys.argv[1:]

    if args and args[0] == "verify":
        _script = _root / "cli" / "verify.py"
        raise SystemExit(subprocess.call([sys.executable, str(_script), *args[1:]]))

    _script = _root / "src" / "mait_24h.py"
    raise SystemExit(subprocess.call([sys.executable, str(_script), *args]))
