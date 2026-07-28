#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""generate_orographic_smoothing_coefficients CLI 脚本入口。"""

from pathlib import Path


def main() -> None:
    """打印可运行脚本路径。"""
    print(Path(__file__).with_name("anc_generate_orographic_smoothing_coefficients.py"))
