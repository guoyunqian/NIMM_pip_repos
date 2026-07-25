#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CorrectLandSeaMask 单元测试。"""

from pathlib import Path
import sys

import numpy as np
import pytest
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generate_ancillary.src.generate_ancillary import CorrectLandSeaMask


def make_landmask_dataarray() -> xr.DataArray:
    """构造 meteva_base 六维格式测试海陆掩码。"""
    base = np.array(
        [[0.2, 0.0, 0.0], [0.7, 0.5, 0.05], [1.0, 0.95, 0.7]], dtype=np.float32
    )
    values = base[np.newaxis, np.newaxis, np.newaxis, np.newaxis, :, :]
    return xr.DataArray(
        values,
        dims=("member", "level", "time", "dtime", "lat", "lon"),
        coords={
            "member": xr.DataArray(np.array([0], dtype=np.int32), dims=("member",)),
            "level": xr.DataArray(np.array([0], dtype=np.int32), dims=("level",)),
            "time": xr.DataArray(
                np.array(["2024-01-01T00:00:00"], dtype="datetime64[ns]"),
                dims=("time",),
            ),
            "dtime": xr.DataArray(np.array([0], dtype=np.int32), dims=("dtime",)),
            "lat": xr.DataArray(np.array([0.0, 1.0, 2.0], dtype=np.float32), dims=("lat",)),
            "lon": xr.DataArray(np.array([100.0, 101.0, 102.0], dtype=np.float32), dims=("lon",)),
        },
        name="landmask",
    )


def test_process_binary_landmask_for_numpy():
    """测试 numpy 输入会被阈值化为 int8 二值掩码。"""
    plugin = CorrectLandSeaMask()
    landmask = np.array(
        [[0.2, 0.0, 0.0], [0.7, 0.5, 0.05], [1.0, 0.95, 0.7]],
        dtype=np.float32,
    )

    result = plugin.process(landmask)

    expected = np.array([[0, 0, 0], [1, 1, 0], [1, 1, 1]], dtype=np.int8)
    np.testing.assert_array_equal(result, expected)
    assert result.dtype == np.int8


def test_process_binary_landmask_for_xarray():
    """测试 xarray 输入会保留坐标并统一输出名称。"""
    plugin = CorrectLandSeaMask()
    landmask = make_landmask_dataarray()

    result = plugin.process(landmask)

    expected = np.array([[0, 0, 0], [1, 1, 0], [1, 1, 1]], dtype=np.int8)
    np.testing.assert_array_equal(result.squeeze(drop=True).values, expected)
    assert result.dtype == np.int8
    assert result.name == "land_binary_mask"
    assert result.dims == landmask.dims


def test_call_matches_process_for_landmask():
    """测试 __call__ 与 process 的返回完全一致。"""
    plugin = CorrectLandSeaMask()
    landmask = make_landmask_dataarray()

    result_process = plugin.process(landmask)
    result_call = plugin(landmask)

    xr.testing.assert_identical(result_call, result_process)


def test_process_rejects_non_meb6d_xarray_landmask():
    """测试非六维 xarray 输入会抛出格式异常。"""
    plugin = CorrectLandSeaMask()
    invalid_landmask = xr.DataArray(
        np.array([[0.2, 0.6], [0.4, 1.0]], dtype=np.float32),
        dims=("y", "x"),
    )
    with pytest.raises(ValueError, match="griddata dims must be"):
        plugin.process(invalid_landmask)
