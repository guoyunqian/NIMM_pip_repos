#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""generate_ancillary CLI 脚本入口。"""

from pathlib import Path


def main() -> None:
    """打印可运行脚本路径。"""
    print(Path(__file__).with_name("dsc_generate_topography_bands_mask.py"))
    print(Path(__file__).with_name("anc_generate_landmask_ancillary.py"))


if __name__ == "__main__":
    main()
