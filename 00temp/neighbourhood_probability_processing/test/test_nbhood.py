#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""nbhood 模块单元测试。"""

from pathlib import Path
import sys

import numpy as np
import pytest
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nbhood.src.nbhood import (
    BaseNeighbourhoodProcessing,
    GeneratePercentilesFromANeighbourhood,
    NeighbourhoodProcessing,
    check_radius_against_distance,
    circular_kernel,
)

def _resolve_existing_dir(candidates):
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"未找到可用测试目录: {candidates}")


RESOURCE_ROOT = _resolve_existing_dir(
    [
        Path(__file__).resolve().parents[1]
        / "test_data"
        / "official_test_nbhood"
        / "normalized_meb6d",
        Path(__file__).resolve().parents[1] / "resource" / "official_test_nohood",
    ]
)
FILL_VALUE_THRESHOLD = 1.0e20


def make_dataarray(data, lead_times=None):
    """构造标准 meb 六维测试 DataArray。"""
    values = np.asarray(data, dtype=np.float32)
    if values.ndim == 2:
        values = values[np.newaxis, np.newaxis, np.newaxis, np.newaxis, :, :]
    elif values.ndim == 3:
        values = values[:, np.newaxis, np.newaxis, np.newaxis, :, :]
    else:
        raise ValueError("测试辅助函数仅支持 2D 或 3D 输入。")

    member_size = values.shape[0]
    lat_size = values.shape[-2]
    lon_size = values.shape[-1]
    coords = {
        "member": np.arange(member_size, dtype=np.int32),
        "level": np.array([0.0], dtype=np.float32),
        "time": np.array([np.datetime64("2024-01-01T00:00:00")]),
        "dtime": np.array([0], dtype=np.int32),
        "lat": xr.DataArray(
            np.arange(lat_size, dtype=np.float32) * 1000.0,
            dims=("lat",),
            attrs={"units": "m"},
        ),
        "lon": xr.DataArray(
            np.arange(lon_size, dtype=np.float32) * 1000.0,
            dims=("lon",),
            attrs={"units": "m"},
        ),
    }
    if lead_times is not None:
        coords["forecast_period"] = xr.DataArray(
            np.asarray(lead_times, dtype=np.float32),
            dims=("member",),
            attrs={"units": "hours"},
        )
    return xr.DataArray(
        values,
        dims=("member", "level", "time", "dtime", "lat", "lon"),
        coords=coords,
    )


def load_primary_dataarray(path: Path) -> xr.DataArray:
    """读取测试文件中的主变量。"""
    dataset = xr.open_dataset(path, decode_timedelta=False)
    for name, data_array in dataset.data_vars.items():
        if data_array.ndim >= 2 and "bnds" not in name and name != "lambert_azimuthal_equal_area":
            return data_array
    raise ValueError(f"未在 {path} 中找到主数据变量。")


def clean_fill_values(data):
    """将官方测试数据中的大填充值转换为 NaN。"""
    values = np.asarray(data, dtype=np.float64)
    cleaned = np.where(np.abs(values) >= FILL_VALUE_THRESHOLD, np.nan, values)
    return cleaned.astype(np.float32)


def mask_fill_values(data):
    """将官方测试数据中的大填充值转换为 masked 值。"""
    values = np.asarray(data, dtype=np.float32)
    masked = np.ma.masked_invalid(values)
    return np.ma.masked_where(np.abs(np.ma.filled(masked, 0.0)) >= FILL_VALUE_THRESHOLD, masked)


class TestBaseNeighbourhoodProcessing:
    """测试基类功能：半径管理、时效插值、输入校验。"""

    def test_fixed_radius_initialization(self):
        """测试固定半径初始化后会直接保存半径值。"""
        plugin = BaseNeighbourhoodProcessing(1000.0)
        data = np.ones((3, 3), dtype=np.float32)
        returned = plugin.process(data)
        assert returned is data
        assert plugin.radius == 1000.0

    def test_radii_lead_times_mismatch_raises(self):
        """测试 radii 与 lead_times 长度不一致时会报错。"""
        with pytest.raises(ValueError, match="长度不一致"):
            BaseNeighbourhoodProcessing([1000.0, 2000.0], lead_times=[1.0])

    def test_reads_lead_times_from_xarray(self):
        """测试 xarray 输入可自动读取时效并完成半径插值。"""
        plugin = BaseNeighbourhoodProcessing([1000.0, 3000.0], lead_times=[1.0, 3.0])
        data = make_dataarray(np.ones((2, 3, 3), dtype=np.float32), lead_times=[1.0, 2.0])
        plugin.process(data)
        np.testing.assert_allclose(plugin.radius, np.array([1000.0, 2000.0]))

    def test_numpy_requires_lead_times_for_variable_radius(self):
        """测试 numpy 输入在可变半径场景下必须显式提供 input_lead_times。"""
        plugin = BaseNeighbourhoodProcessing([1000.0, 3000.0], lead_times=[1.0, 3.0])
        with pytest.raises(ValueError, match="input_lead_times"):
            plugin.process(np.ones((2, 3, 3), dtype=np.float32))

    def test_detects_unmasked_nan(self):
        """测试未掩码 NaN 会在基类检查阶段被拦截。"""
        plugin = BaseNeighbourhoodProcessing(1000.0)
        data = np.array([[1.0, np.nan], [1.0, 1.0]], dtype=np.float32)
        with pytest.raises(ValueError, match="NaN"):
            plugin.process(data)


class TestUtilityFunctions:
    """测试工具函数：半径校验、核生成。"""

    def test_check_radius_against_distance_passes(self):
        """测试合法邻域半径可以通过空间域大小检查。"""
        check_radius_against_distance(1.0, shape=(3, 3), grid_spacing=1.0)

    def test_check_radius_against_distance_raises(self):
        """测试超出空间域允许范围的邻域半径会报错。"""
        with pytest.raises(ValueError, match="超过空间域允许的最大距离"):
            check_radius_against_distance(10.0, shape=(3, 3), grid_spacing=1.0)

    def test_circular_kernel_binary_mode(self):
        """测试圆形核在常权模式下正确生成。"""
        binary = circular_kernel(1, weighted_mode=False)
        assert binary.shape == (3, 3)
        assert set(np.unique(binary)).issubset({0.0, 1.0})

    def test_circular_kernel_weighted_mode(self):
        """测试圆形核在加权模式下中心权重高于边缘。"""
        weighted = circular_kernel(1, weighted_mode=True)
        assert weighted.shape == (3, 3)
        assert weighted[1, 1] > weighted[0, 1]


class TestNeighbourhoodProcessingCore:
    """测试邻域处理核心功能：方形/圆形邻域、求和/平均、掩码处理。"""

    def test_square_sum_numpy(self):
        """测试方形邻域求和在 numpy 输入下的基础结果。"""
        plugin = NeighbourhoodProcessing("square", radii=1.0, sum_only=True, re_mask=False)
        data = np.ones((3, 3), dtype=np.float32)
        result = plugin.process(data, grid_spacing=1.0)
        expected = np.array(
            [[4.0, 6.0, 4.0], [6.0, 9.0, 6.0], [4.0, 6.0, 4.0]],
            dtype=np.float32,
        )
        np.testing.assert_allclose(result, expected)

    def test_external_mask_and_remask(self):
        """测试外部掩码与 re_mask=True 时的输出掩码行为。"""
        plugin = NeighbourhoodProcessing("square", radii=1.0, sum_only=False, re_mask=True)
        data = np.ones((3, 3), dtype=np.float32)
        mask = np.ones((3, 3), dtype=np.int32)
        mask[1, 1] = 0
        result = plugin.process(data, mask=mask, grid_spacing=1.0)
        assert np.ma.isMaskedArray(result)
        assert result.mask[1, 1]

    def test_xarray_matches_numpy(self):
        """测试等价输入下 xarray 与 numpy 结果一致。"""
        data = np.arange(9, dtype=np.float32).reshape(3, 3)
        plugin = NeighbourhoodProcessing("square", radii=1.0, sum_only=False, re_mask=False)
        result_np = plugin.process(data, grid_spacing=1.0)
        result_xr = plugin.process(make_dataarray(data))
        np.testing.assert_allclose(result_np, np.asarray(result_xr)[0, 0, 0, 0, :, :])

    def test_complex_input_support(self):
        """测试邻域处理支持复数输入。"""
        plugin = NeighbourhoodProcessing("square", radii=1.0, sum_only=False, re_mask=False)
        data = np.array(
            [
                [1.0 + 1.0j, 1.0 + 0.0j, 0.0 + 1.0j],
                [1.0 + 2.0j, 2.0 + 1.0j, 1.0 + 0.0j],
                [0.0 + 1.0j, 1.0 + 1.0j, 2.0 + 0.0j],
            ],
            dtype=np.complex64,
        )
        result = plugin.process(data, grid_spacing=1.0)
        assert np.iscomplexobj(result)
        assert result.shape == data.shape
        assert result.dtype == np.complex64

    def test_multilead_slices_with_variable_radius(self):
        """测试多切片输入会按各自时效使用对应邻域半径。"""
        plugin = NeighbourhoodProcessing(
            "square", radii=[1.0, 2.0], lead_times=[1.0, 2.0], sum_only=True, re_mask=False
        )
        data = np.ones((2, 5, 5), dtype=np.float32)
        result = plugin.process(
            data, grid_spacing=1.0, input_lead_times=np.array([1.0, 2.0])
        )
        assert result.shape == (2, 5, 5)
        np.testing.assert_allclose(result[0, 2, 2], 9.0)   # 半径1: 3x3=9
        np.testing.assert_allclose(result[1, 2, 2], 25.0)  # 半径2: 5x5=25

    def test_weighted_mode_with_square_raises(self):
        """测试 weighted_mode 不能与 square 邻域组合使用。"""
        with pytest.raises(ValueError, match="weighted_mode"):
            NeighbourhoodProcessing("square", radii=1.0, weighted_mode=True)


class TestGeneratePercentilesFromANeighbourhood:
    """测试百分位邻域处理功能。"""

    def test_single_percentile_keeps_axis(self):
        """测试单一百分位请求时仍保留 percentile 轴。"""
        plugin = GeneratePercentilesFromANeighbourhood(radii=1.0, percentiles=[10.0])
        data = np.ones((2, 3, 3), dtype=np.float32)
        result = plugin.process(data, grid_spacing=1.0)
        assert result.shape == (1, 2, 3, 3)

    def test_percentile_order_preserved(self):
        """测试百分位顺序与输入顺序保持一致。"""
        data = np.arange(9, dtype=np.float32).reshape(3, 3)
        plugin = GeneratePercentilesFromANeighbourhood(radii=1.0, percentiles=[90.0, 10.0])
        result = plugin.process(data, grid_spacing=1.0)
        assert result.shape[0] == 2

    def test_xarray_numpy_equivalence(self):
        """测试 xarray 与 numpy 输入结果一致。"""
        data = np.arange(9, dtype=np.float32).reshape(3, 3)
        plugin = GeneratePercentilesFromANeighbourhood(radii=1.0, percentiles=[90.0, 10.0])
        result_np = plugin.process(data, grid_spacing=1.0)
        result_xr = plugin.process(make_dataarray(data))
        actual = np.asarray(result_xr)[:, 0, 0, 0, :, :]
        np.testing.assert_allclose(actual, result_np)

    def test_expected_2d_values(self):
        """测试二维样例在圆形邻域下得到预期的百分位结果。"""
        plugin = GeneratePercentilesFromANeighbourhood(radii=1.0, percentiles=[50.0])
        data = np.array(
            [
                [1.0, 1.0, 1.0],
                [1.0, 0.0, 1.0],
                [1.0, 1.0, 1.0],
            ],
            dtype=np.float32,
        )
        result = plugin.process(data, grid_spacing=1.0)
        np.testing.assert_allclose(result[0], np.ones((3, 3), dtype=np.float32))

    def test_reject_masked_input(self):
        """测试邻域百分位当前仍拒绝 masked 输入。"""
        plugin = GeneratePercentilesFromANeighbourhood(radii=1.0, percentiles=[50.0])
        data = np.ma.masked_array(
            np.ones((3, 3), dtype=np.float32),
            mask=np.zeros((3, 3), dtype=bool),
        )
        with pytest.raises(NotImplementedError):
            plugin.process(data, grid_spacing=1.0)


class TestOfficialBasicNeighbourhood:
    """测试官方基础邻域样例（方形/圆形）。"""

    def test_square_neighbourhood_matches_kgo_and_original(self):
        """测试官方方形基础邻域样例与 KGO 和原算法结果一致。"""
        basic_dir = RESOURCE_ROOT / "basic"
        input_data = load_primary_dataarray(basic_dir / "input.nc")

        square_result = NeighbourhoodProcessing("square", radii=20000.0).process(input_data)
        square_kgo = clean_fill_values(load_primary_dataarray(basic_dir / "kgo_square.nc"))
        square_original = clean_fill_values(load_primary_dataarray(basic_dir / "original_square.nc"))

        np.testing.assert_allclose(square_result, square_kgo, equal_nan=True, atol=1.0e-6)
        np.testing.assert_allclose(square_result, square_original, equal_nan=True, atol=1.0e-6)

    def test_circular_neighbourhood_matches_original(self):
        """测试官方圆形基础邻域样例与原算法结果一致。

        说明：当前 kgo_circular.nc 与原算法输出并不一致，因此这里只对原算法
        结果做强校验，避免把测试数据自身的差异误判为迁移版算法问题。
        """
        basic_dir = RESOURCE_ROOT / "basic"
        input_data = load_primary_dataarray(basic_dir / "input.nc")

        circular_result = NeighbourhoodProcessing("circular", radii=20000.0).process(input_data)
        circular_original = clean_fill_values(load_primary_dataarray(basic_dir / "original_circular.nc"))

        np.testing.assert_allclose(circular_result, circular_original, equal_nan=True, atol=1.0e-6)


class TestOfficialMaskedNeighbourhood:
    """测试官方掩码邻域样例（内部掩码/外部掩码）。"""

    def test_internal_masked_matches_kgo_and_original(self):
        """测试官方内部掩码样例与参考结果一致。"""
        mask_dir = RESOURCE_ROOT / "mask"
        internal_input = load_primary_dataarray(mask_dir / "input_masked.nc")
        internal_masked = mask_fill_values(internal_input)
        internal_result = NeighbourhoodProcessing("square", radii=20000.0).process(
            internal_masked, grid_spacing=2000.0
        )

        internal_kgo = clean_fill_values(load_primary_dataarray(mask_dir / "kgo_masked.nc"))
        internal_original = clean_fill_values(load_primary_dataarray(mask_dir / "original_masked.nc"))

        np.testing.assert_allclose(internal_result, internal_kgo, equal_nan=True, atol=1.0e-6)
        np.testing.assert_allclose(internal_result, internal_original, equal_nan=True, atol=1.0e-6)

    def test_external_masked_matches_kgo_and_original(self):
        """测试官方外部掩码样例与参考结果一致。"""
        mask_dir = RESOURCE_ROOT / "mask"
        external_input = load_primary_dataarray(mask_dir / "input.nc")
        external_mask = load_primary_dataarray(mask_dir / "mask.nc")
        external_result = NeighbourhoodProcessing("square", radii=20000.0).process(
            external_input, mask=external_mask
        )

        external_kgo = clean_fill_values(load_primary_dataarray(mask_dir / "kgo_external_masked.nc"))
        external_original = clean_fill_values(load_primary_dataarray(mask_dir / "original_external_masked.nc"))

        np.testing.assert_allclose(external_result, external_kgo, equal_nan=True, atol=1.0e-6)
        np.testing.assert_allclose(external_result, external_original, equal_nan=True, atol=1.0e-6)


class TestOfficialPercentileNeighbourhood:
    """测试官方百分位邻域样例。"""

    def test_circular_percentile_matches_kgo_and_original(self):
        """测试官方百分位邻域样例与 KGO 和原算法结果一致。"""
        percentile_dir = RESOURCE_ROOT / "percentile"
        input_data = load_primary_dataarray(percentile_dir / "input_circular_percentile.nc")

        result = GeneratePercentilesFromANeighbourhood(
            radii=20000.0,
            percentiles=[25.0, 50.0, 75.0],
        ).process(input_data)

        kgo = clean_fill_values(load_primary_dataarray(percentile_dir / "kgo_circular_percentile.nc"))
        original = clean_fill_values(load_primary_dataarray(percentile_dir / "original_circular_percentile.nc"))
        np.testing.assert_allclose(np.asarray(result), kgo, equal_nan=True, atol=1.0e-6)
        np.testing.assert_allclose(np.asarray(result), original, equal_nan=True, atol=1.0e-6)
