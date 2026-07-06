#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""feels_like_temperature 模块 CLI 入口。"""

from typing import Optional, Sequence


_CLI_SCRIPTS = (
    "feels_like_temperature/cli/der_feel_like_temp.py",
)


def main(argv: Optional[Sequence[str]] = None):
    """列出可直接运行的 CLI 示例脚本。"""
    lines = [
        "feels_like_temperature 模块 CLI 已改为示例脚本，请直接运行：",
        *(f"  python {script}" for script in _CLI_SCRIPTS),
        "",
        "在脚本底部的 if __name__ == '__main__' 中修改路径与参数后执行。",
    ]
    raise SystemExit("\n".join(lines))
