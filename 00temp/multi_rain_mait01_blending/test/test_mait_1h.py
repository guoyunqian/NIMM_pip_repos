# -*- coding: UTF-8 -*-
"""从仓库根运行时可导入 src 下模块（与 test_run_context.py、mait_1h_cli._bootstrap_paths 一致）。"""
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO, "src")
for _p in (_SRC, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import mait_1h_cli

if __name__ == "__main__":
    mait_1h_cli.process(
        time_inputs=["202605260000"],
        predict_valid_list=[1, 2, 3],
        para_path=os.path.join(_REPO, "resource", "para.ini"),
        is_multi=False,
    )
