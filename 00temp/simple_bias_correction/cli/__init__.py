#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""simple_bias_correction 模块 CLI 入口。"""

from typing import Optional, Sequence


_CLI_SCRIPTS = (
    "simple_bias_correction/cli/cal_calculate_forecast_bias.py",
    "simple_bias_correction/cli/prb_bias_correction.py",
    "simple_bias_correction/cli/preprocess_test_data.py",
)


def main(argv: Optional[Sequence[str]] = None):
    """列出可直接运行的 CLI 示例脚本。"""
    lines = [
        "simple_bias_correction 模块 CLI 已改为示例脚本，请直接运行：",
        *(f"  python {script}" for script in _CLI_SCRIPTS),
        "",
        "算法脚本输入为预处理后的 meb 六维 .nc。",
        "预处理（官方 Iris 样例 → meb）：",
        "  python simple_bias_correction/cli/preprocess_test_data.py",
        "在脚本底部的 if __name__ == '__main__' 中修改路径与参数后执行。",
    ]
    raise SystemExit("\n".join(lines))
