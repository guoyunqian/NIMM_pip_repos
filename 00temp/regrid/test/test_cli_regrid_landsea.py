#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI process() 冒烟与典型路径对照（输入均为 cli_input）。"""

from __future__ import annotations

from pathlib import Path
import sys

import iris
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from regrid.cli.tran_regrid import process
from regrid.test.helpers import to_compare_array

DATA_DIR = Path(__file__).resolve().parents[1] / "test_data"
CLI_INPUT = DATA_DIR / "cli_input"


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        pytest.skip(f"缺 CLI 示例数据（test_data/cli_input），会跳过: {missing}")


def test_cli_bilinear_against_kgo(tmp_path):
    cube = CLI_INPUT / "global_cutout.nc"
    target = CLI_INPUT / "ukvx_grid.nc"
    kgo = DATA_DIR / "basic/kgo.nc"
    _require(cube, target, kgo)

    out = tmp_path / "out.nc"
    result = process(
        str(cube),
        str(target),
        output_path=str(out),
        regrid_mode="bilinear",
        regridded_title="test",
    )
    assert out.exists()
    expected = to_compare_array(iris.load_cube(str(kgo)))
    np.testing.assert_allclose(
        to_compare_array(result), expected, atol=1e-4, rtol=1e-4, equal_nan=True
    )


def test_cli_nearest_with_mask_against_kgo(tmp_path):
    cube = CLI_INPUT / "global_cutout.nc"
    target = CLI_INPUT / "ukvx_landmask.nc"
    mask = CLI_INPUT / "glm_landmask.nc"
    kgo = DATA_DIR / "landmask/kgo.nc"
    _require(cube, target, mask, kgo)

    result = process(
        str(cube),
        str(target),
        land_sea_mask_path=str(mask),
        output_path=str(tmp_path / "nwm.nc"),
        regrid_mode="nearest-with-mask",
        land_sea_mask_vicinity=100000.0,
        regridded_title="test",
    )
    expected = to_compare_array(iris.load_cube(str(kgo)))
    np.testing.assert_allclose(
        to_compare_array(result), expected, atol=1e-4, rtol=1e-4, equal_nan=True
    )


def test_cli_landmask_without_mask_mode_raises():
    cube = CLI_INPUT / "global_cutout.nc"
    target = CLI_INPUT / "ukvx_grid.nc"
    mask = CLI_INPUT / "glm_landmask.nc"
    _require(cube, target, mask)

    with pytest.raises(ValueError, match="Land-mask file supplied"):
        process(
            str(cube),
            str(target),
            land_sea_mask_path=str(mask),
            regrid_mode="bilinear",
        )
