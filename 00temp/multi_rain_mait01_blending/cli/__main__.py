# -*- coding: utf-8 -*-
"""
项目根目录执行:

- 预报集成: ``python -m cli --time-inputs=...``
- 检验: ``python -m cli verify ts --h5-file=... --grade-list=... --product-list=...``

等价于直接运行 ``src/mait_1h.py`` 或 ``python -m cli.verify``。
"""
import subprocess
import sys
from pathlib import Path


def _run_verify(argv):
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0], *argv]
        from cli.verify import main as verify_main

        verify_main()
    finally:
        sys.argv = saved_argv


if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    _argv = sys.argv[1:]
    if _argv and _argv[0] == "verify":
        _run_verify(_argv[1:])
    else:
        _script = _root / "src" / "mait_1h.py"
        raise SystemExit(subprocess.call([sys.executable, str(_script), *_argv]))
