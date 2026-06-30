#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.

"""
Goff-Gratch 公式准确性验证测试。
参考值来自 WMO 技术文档和已知的饱和水汽压表格。
"""

import functools
import numpy as np
import pytest


# Current implementation functions (copied from feels_like_temperature.py)
ABSOLUTE_ZERO = -273.15
TRIPLE_PT_WATER = 273.16
SVP_T_MIN = 183.15
SVP_T_MAX = 338.25
SVP_T_INCREMENT = 0.1


def _svp_pure_water_goff_gratch(temperature: np.ndarray) -> np.ndarray:
    """
    纯水汽系统下的饱和水汽压（Goff-Gratch 公式，WMO 标准方法），返回 hPa。
    """
    t = temperature.astype(np.float32, copy=False)
    triple_pt = np.float32(TRIPLE_PT_WATER)
    c1 = np.float32(10.79574)
    c2 = np.float32(5.028)
    c3 = np.float32(1.50475e-4)
    c4 = np.float32(-8.2969)
    c5 = np.float32(0.42873e-3)
    c6 = np.float32(4.76955)
    c7 = np.float32(0.78614)
    c8 = np.float32(-9.09685)
    c9 = np.float32(3.56654)
    c10 = np.float32(0.87682)
    c11 = np.float32(0.78614)

    over_triple = t > triple_pt

    n0_w = c1 * (1.0 - triple_pt / t)
    n1_w = c2 * np.log10(t / triple_pt)
    n2_w = c3 * (1.0 - np.power(10.0, (c4 * (t / triple_pt - 1.0))))
    n3_w = c5 * (np.power(10.0, (c6 * (1.0 - triple_pt / t))) - 1.0)
    log_es_w = n0_w - n1_w + n2_w + n3_w + c7
    es_w = np.power(10.0, log_es_w)

    n0_i = c8 * ((triple_pt / t) - 1.0)
    n1_i = c9 * np.log10(triple_pt / t)
    n2_i = c10 * (1.0 - (t / triple_pt))
    log_es_i = n0_i - n1_i + n2_i + c11
    es_i = np.power(10.0, log_es_i)

    return np.where(over_triple, es_w, es_i).astype(np.float32)


@functools.lru_cache()
def _svp_table():
    temperatures = np.arange(
        SVP_T_MIN, SVP_T_MAX + 0.5 * SVP_T_INCREMENT, SVP_T_INCREMENT, dtype=np.float32
    )
    svp_hpa = _svp_pure_water_goff_gratch(temperatures)
    return (svp_hpa * 100.0).astype(np.float32)


def _svp_from_lookup(t_kelvin: np.ndarray) -> np.ndarray:
    t_clipped = np.clip(t_kelvin, SVP_T_MIN, SVP_T_MAX - SVP_T_INCREMENT).astype(
        np.float32
    )

    table_position = (t_clipped - SVP_T_MIN) / SVP_T_INCREMENT
    table_index = table_position.astype(np.int32)
    interpolation_factor = (table_position - table_index).astype(np.float32)
    svp_table_data = _svp_table()
    return (1.0 - interpolation_factor) * svp_table_data[
        table_index
    ] + interpolation_factor * svp_table_data[table_index + 1]


def _calculate_svp_in_air(t_kelvin: np.ndarray, pressure_pa: np.ndarray) -> np.ndarray:
    svp = _svp_from_lookup(t_kelvin.astype(np.float32))
    temp_c = (t_kelvin + ABSOLUTE_ZERO).astype(np.float32)
    correction = 1.0 + 1.0e-8 * pressure_pa.astype(np.float32) * (
        4.5 + 6.0e-4 * temp_c * temp_c
    )
    return (svp * correction.astype(np.float32)).astype(np.float32)


class TestGoffGratchValidation:
    """Test Goff-Gratch formula implementation accuracy."""

    def test_goff_gratch_formula_accuracy(self):
        """Test Goff-Gratch formula against reference values from WMO."""
        # Standard reference values (from WMO and engineering handbooks)
        # Format: [(temperature_K, saturation_vapor_pressure_Pa)]
        REFERENCE_VALUES = [
            (250.0, 76.35),      # -23.15°C
            (273.15, 611.21),     # 0°C (ice point)
            (273.16, 611.657),    # 0.01°C (triple point)
            (293.15, 2338.0),     # 20°C
            (310.0, 6220.0),      # 36.85°C
        ]

        total_error = 0.0
        for temp_k, ref_svp in REFERENCE_VALUES:
            temp_array = np.array([temp_k], dtype=np.float32)
            pressure_array = np.array([101325.0], dtype=np.float32)  # Standard atmospheric pressure

            # Calculate base SVP without pressure correction (Pa)
            base_svp_hpa = _svp_pure_water_goff_gratch(temp_array)
            base_svp_pa = base_svp_hpa * 100.0

            # Compare with reference values (using base SVP as reference values are for pure water vapor system)
            calc_value = base_svp_pa[0]
            rel_error = abs(calc_value - ref_svp) / ref_svp * 100.0
            total_error += rel_error

            # Assert individual relative error is within acceptable tolerance
            # The original validation showed 0.1641% average error, but individual points may vary slightly
            # Allow tolerance of 0.6% for edge cases while maintaining overall accuracy
            assert rel_error < 0.6, f"Relative error {rel_error:.4f}% exceeds 0.6% tolerance at {temp_k}K"

        avg_error = total_error / len(REFERENCE_VALUES)

        # Assert average relative error meets meteorological standard (original validation showed 0.1641%)
        assert avg_error < 0.5, f"Average relative error {avg_error:.4f}% exceeds 0.5% tolerance"

    def test_pressure_correction_functionality(self):
        """Test pressure correction functionality."""
        temp_test = 293.15  # 20°C
        pressures = [101325.0, 90000.0, 110000.0]  # Different pressures

        for p in pressures:
            temp_arr = np.array([temp_test], dtype=np.float32)
            press_arr = np.array([p], dtype=np.float32)
            svp_corrected = _calculate_svp_in_air(temp_arr, press_arr)
            svp_base = _svp_pure_water_goff_gratch(temp_arr) * 100.0
            correction_factor = svp_corrected[0] / svp_base[0]

            # Pressure correction should result in correction factor > 1.0
            assert correction_factor > 1.0, f"Correction factor {correction_factor:.6f} should be > 1.0 at pressure {p} Pa"

            # Correction factor should be reasonable (not too large)
            assert correction_factor < 1.01, f"Correction factor {correction_factor:.6f} should be < 1.01 at pressure {p} Pa"