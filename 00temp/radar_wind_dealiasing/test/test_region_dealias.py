#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""迁移版 region_dealias 算法测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import meteva_base as meb
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from pyart.correct import GridGateFilter, RegionDealiasPlugin, dealias_region_based
from pyart.correct.src._common_dealias import _parse_rays_wrap_around


def _build_velocity_grid(data: np.ndarray):
    """构造带 Nyquist 速度属性的测试网格。"""
    grid = meb.grid([100, 103, 1], [30, 31, 1])
    velocity = meb.grid_data(grid=grid, data=data.astype(np.float32))
    velocity.attrs["nyquist_velocity"] = 5.0
    velocity.attrs["units"] = "m/s"
    velocity.name = "velocity"
    return velocity


def _build_named_grid(data: np.ndarray, name: str):
    """构造带名称的单时次单层测试网格。"""
    grid = _build_velocity_grid(data)
    grid.name = name
    return grid


def _build_gatefilter(velocity: np.ndarray, mask: np.ndarray) -> GridGateFilter:
    """构造与速度场对齐的布尔掩码过滤器。"""
    velocity_grid = _build_velocity_grid(velocity)
    return GridGateFilter.from_mask(velocity_grid, mask)


def _build_polar_like_velocity_grid(data: np.ndarray, name: str = "velocity"):
    """构造更接近单个 sweep 的极坐标风格测试网格。"""
    grid = meb.grid([0, 2000, 1000], [0, 90, 90])
    velocity = meb.grid_data(grid=grid, data=data.astype(np.float32))
    velocity.attrs["nyquist_velocity"] = 5.0
    velocity.attrs["units"] = "m/s"
    velocity.attrs["radar_lon"] = 116.0
    velocity.attrs["radar_lat"] = 40.0
    velocity.attrs["range_units"] = "m"
    velocity.attrs["azimuth_units"] = "degree"
    velocity.name = name
    return velocity


def test_dealias_region_based_returns_griddata():
    """退模糊结果应保持 meteva_base 网格结构。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )

    result = dealias_region_based(velocity, centered=False)

    expected = np.array(
        [[-6.0, -6.0, -4.0, -4.0], [-6.0, -6.0, -4.0, -4.0]],
        dtype=np.float32,
    )

    assert result.dims == velocity.dims
    assert result.shape == velocity.shape
    assert result.name == "corrected_velocity"
    assert result.attrs["units"] == "m/s"
    np.testing.assert_allclose(result.values.squeeze(), expected)


def test_dealias_region_based_can_anchor_to_reference_velocity():
    """提供参考速度后应将结果锚定到参考场附近。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )
    reference_velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, 6.0, 6.0], [4.0, 4.0, 6.0, 6.0]],
            dtype=np.float32,
        )
    )

    result = dealias_region_based(
        velocity,
        ref_velocity=reference_velocity,
        centered=False,
    )

    np.testing.assert_allclose(result.values.squeeze(), reference_velocity.values.squeeze())


def test_dealias_region_based_respects_gatefilter_keep_original():
    """过滤格点在 keep_original=True 时应保留原值。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )
    gatefilter = _build_gatefilter(
        velocity.values.squeeze(),
        np.array(
            [[False, False, True, True], [False, False, True, True]],
            dtype=bool,
        ),
    )

    result = dealias_region_based(
        velocity,
        gatefilter=gatefilter,
        keep_original=True,
        centered=False,
    )

    expected = np.array(
        [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
        dtype=np.float32,
    )
    np.testing.assert_allclose(result.values.squeeze(), expected)


def test_dealias_region_based_masks_filtered_gates_by_default():
    """过滤格点在 keep_original=False 时应在结果中保持为缺测值。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )
    gatefilter = _build_gatefilter(
        velocity.values.squeeze(),
        np.array(
            [[False, False, True, True], [False, False, True, True]],
            dtype=bool,
        ),
    )

    result = dealias_region_based(
        velocity,
        gatefilter=gatefilter,
        centered=False,
    )

    values = result.values.squeeze()
    fill_value = result.attrs["_FillValue"]
    np.testing.assert_allclose(
        values[:, :2],
        np.array([[4.0, 4.0], [4.0, 4.0]], dtype=np.float32),
    )
    assert np.allclose(values[:, 2:], fill_value)


def test_dealias_region_based_builds_gatefilter_when_none():
    """gatefilter=None 时应可基于矩场阈值自动构造过滤器。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )
    reflectivity = _build_named_grid(
        np.array(
            [[10.0, 10.0, -30.0, -30.0], [10.0, 10.0, -30.0, -30.0]],
            dtype=np.float32,
        ),
        "reflectivity",
    )

    result = dealias_region_based(
        velocity,
        gatefilter=None,
        refl=reflectivity,
        centered=False,
    )

    values = result.values.squeeze()
    fill_value = result.attrs["_FillValue"]
    np.testing.assert_allclose(
        values[:, :2],
        np.array([[4.0, 4.0], [4.0, 4.0]], dtype=np.float32),
    )
    assert np.allclose(values[:, 2:], fill_value)


def test_dealias_region_based_false_gatefilter_disables_auto_filtering():
    """gatefilter=False 时即使提供矩场也不应自动过滤。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )
    reflectivity = _build_named_grid(
        np.array(
            [[10.0, 10.0, -30.0, -30.0], [10.0, 10.0, -30.0, -30.0]],
            dtype=np.float32,
        ),
        "reflectivity",
    )

    result = dealias_region_based(
        velocity,
        gatefilter=False,
        refl=reflectivity,
        centered=False,
    )

    expected = np.array(
        [[-6.0, -6.0, -4.0, -4.0], [-6.0, -6.0, -4.0, -4.0]],
        dtype=np.float32,
    )
    np.testing.assert_allclose(result.values.squeeze(), expected)


def test_dealias_region_based_processes_each_level_independently():
    """多层输入应按 level 切片分别退模糊。"""
    grid = meb.grid(
        [100, 103, 1],
        [30, 31, 1],
        gtime=["2020010100"],
        dtime_list=[0],
        level_list=[1000, 850],
        member_list=["m"],
    )
    data = np.array(
        [
            [
                [
                    [
                        [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
                        [[1.0, 1.0, 2.0, 2.0], [1.0, 1.0, 2.0, 2.0]],
                    ]
                ]
            ]
        ],
        dtype=np.float32,
    )
    velocity = meb.grid_data(grid=grid, data=data)
    velocity.attrs["nyquist_velocity"] = np.array([[[[5.0]], [[5.0]]]], dtype=np.float32)
    velocity.attrs["units"] = "m/s"
    velocity.name = "velocity"

    result = dealias_region_based(velocity, centered=False)

    expected_level0 = np.array(
        [[-6.0, -6.0, -4.0, -4.0], [-6.0, -6.0, -4.0, -4.0]],
        dtype=np.float32,
    )
    expected_level1 = np.array(
        [[1.0, 1.0, 2.0, 2.0], [1.0, 1.0, 2.0, 2.0]],
        dtype=np.float32,
    )
    np.testing.assert_allclose(result.values[0, 0, 0, 0], expected_level0)
    np.testing.assert_allclose(result.values[0, 1, 0, 0], expected_level1)


def test_parse_rays_wrap_around_uses_scan_type_when_none():
    """rays_wrap_around=None 时应优先参考 attrs 中的 scan_type。"""
    velocity = _build_velocity_grid(
        np.array(
            [[1.0, 1.0, 2.0, 2.0], [1.0, 1.0, 2.0, 2.0]],
            dtype=np.float32,
        )
    )
    velocity.attrs["scan_type"] = "ppi"

    assert _parse_rays_wrap_around(None, velocity) is True


def test_parse_rays_wrap_around_explicit_value_overrides_scan_type():
    """显式传入 rays_wrap_around 时应优先使用参数值。"""
    velocity = _build_velocity_grid(
        np.array(
            [[1.0, 1.0, 2.0, 2.0], [1.0, 1.0, 2.0, 2.0]],
            dtype=np.float32,
        )
    )
    velocity.attrs["scan_type"] = "ppi"

    assert _parse_rays_wrap_around(False, velocity) is False


def test_region_dealias_plugin_process_forwards_to_algorithm():
    """插件调用应与直接函数调用保持一致。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )
    plugin = RegionDealiasPlugin(centered=False)

    plugin_result = plugin.process(velocity=velocity)
    func_result = dealias_region_based(velocity=velocity, centered=False)

    np.testing.assert_allclose(plugin_result.values, func_result.values)


def test_region_dealias_plugin_attaches_gate_lonlat_when_radar_location_given():
    """提供雷达站点经纬度后，插件结果应附加真实门点经纬度坐标。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )
    plugin = RegionDealiasPlugin(
        centered=False,
        radar_lon=116.0,
        radar_lat=40.0,
    )
    result = plugin.process(velocity=velocity)

    assert "gate_lon" in result.coords
    assert "gate_lat" in result.coords
    assert result.coords["gate_lon"].dims == ("lat", "lon")
    assert result.coords["gate_lat"].dims == ("lat", "lon")
    assert result.coords["gate_lon"].shape == velocity.shape[-2:]
    assert result.coords["gate_lat"].shape == velocity.shape[-2:]


def test_region_dealias_plugin_can_output_regular_latlon_grid():
    """提供目标经纬网格后，插件应输出规则经纬网格结果。"""
    velocity = _build_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0, -4.0], [4.0, 4.0, -4.0, -4.0]],
            dtype=np.float32,
        )
    )
    target_lon = np.array([116.00, 116.01, 116.02], dtype=np.float64)
    target_lat = np.array([40.00, 40.01], dtype=np.float64)
    plugin = RegionDealiasPlugin(
        centered=False,
        radar_lon=116.0,
        radar_lat=40.0,
        target_lon=target_lon,
        target_lat=target_lat,
    )
    result = plugin.process(velocity=velocity)

    assert result.dims == velocity.dims
    assert result.shape[-2:] == (target_lat.size, target_lon.size)
    np.testing.assert_allclose(result.lon.values, target_lon)
    np.testing.assert_allclose(result.lat.values, target_lat)


def test_region_dealias_plugin_can_auto_remap_from_attrs():
    """雷达站点写在 attrs 中时，插件应支持自动生成规则经纬网格输出。"""
    velocity = _build_polar_like_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0], [4.0, 4.0, -4.0]],
            dtype=np.float32,
        )
    )
    plugin = RegionDealiasPlugin(
        centered=False,
        auto_remap_to_latlon=True,
        geo_resolution_deg=None,
        geo_nlon=3,
        geo_nlat=2,
    )
    result = plugin.process(velocity=velocity)
    assert result.dims == velocity.dims
    assert result.shape[-2:] == (2, 3)


def test_region_dealias_plugin_masks_outside_radar_coverage_when_remapping():
    """启用地理重映射时，雷达覆盖范围外的格点应保持缺测。"""
    velocity = _build_polar_like_velocity_grid(
        np.array(
            [[4.0, 4.0, -4.0], [4.0, 4.0, -4.0]],
            dtype=np.float32,
        )
    )
    plugin = RegionDealiasPlugin(
        centered=False,
        radar_lon=116.0,
        radar_lat=40.0,
        target_lon=np.array([115.99, 116.0, 116.03], dtype=np.float64),
        target_lat=np.array([39.99, 40.0, 40.03], dtype=np.float64),
    )

    result = plugin.process(velocity=velocity)
    values = result.values
    fill_value = result.attrs["_FillValue"]

    assert np.any(~np.isclose(values, fill_value))
    assert np.any(np.isclose(values, fill_value))
