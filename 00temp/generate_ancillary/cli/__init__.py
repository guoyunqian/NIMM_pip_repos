#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""generate_ancillary CLI 脚本入口。"""

from pathlib import Path


def main() -> None:
    """打印可运行脚本路径。"""
    print(Path(__file__).with_name("preprocess_test_data.py"))
    print(Path(__file__).with_name("dsc_generate_topography_bands_mask.py"))
    print(Path(__file__).with_name("dsc_generate_topographic_zone_weights.py"))
    print(Path(__file__).with_name("anc_generate_landmask_ancillary.py"))
