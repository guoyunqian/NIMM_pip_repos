#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""generate_derived_solar_fields CLI 脚本入口。"""

from pathlib import Path


def main() -> None:
    """打印可运行脚本路径。"""
    print(Path(__file__).with_name("cal_generate_solar_time.py"))
    print(Path(__file__).with_name("cal_generate_clearsky_solar_radiation.py"))
