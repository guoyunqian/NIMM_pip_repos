#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""threshold_probability_conversion 模块 CLI 入口。"""

from pathlib import Path


def main() -> None:
    """打印可运行脚本路径。"""
    print(Path(__file__).with_name("preprocess_test_data.py"))
    print(Path(__file__).with_name("prb_threshold.py"))
