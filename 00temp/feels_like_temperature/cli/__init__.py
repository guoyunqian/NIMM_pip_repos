#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""feels_like_temperature 模块 CLI 入口。

包根目录执行::

    python -m cli
"""


def main() -> None:
    """转发到 ``der_feel_like_temp.main``（在 main 内定义路径并调用 process）。"""
    from .der_feel_like_temp import main as run_cli

    run_cli()
