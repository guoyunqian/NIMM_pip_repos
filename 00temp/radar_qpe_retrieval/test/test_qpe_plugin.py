#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""QPE 插件测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import meteva_base as meb
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pyart.retrieve.src.qpe import (
    QPEPlugin,
    ZtoR,
    est_rain_rate_a,
    est_rain_rate_hydro,
    est_rain_rate_z,
)


def test_qpe_plugin_dispatches_z_method():
    """z 方法应分发到反射率降水率估算函数。"""
    grid = meb.grid([100, 101, 1], [30, 31, 1])
    refl = meb.grid_data(
        grid,
        data=np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32),
    )

    plugin = QPEPlugin(method="z")
    result = plugin.process(refl=refl)
    expected = est_rain_rate_z(refl)

    np.testing.assert_allclose(result.values, expected.values)


def test_qpe_plugin_uses_compressed_z_coefficients():
    """z_alpha 和 z_beta 应映射为 z 方法的 alpha 和 beta。"""
    grid = meb.grid([100, 101, 1], [30, 31, 1])
    refl = meb.grid_data(
        grid,
        data=np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32),
    )

    plugin = QPEPlugin(method="z", z_alpha=0.1, z_beta=0.5)
    result = plugin.process(refl=refl)
    expected = est_rain_rate_z(refl, alpha=0.1, beta=0.5)

    np.testing.assert_allclose(result.values, expected.values)


def test_qpe_plugin_uses_dedicated_ztor_coefficients():
    """ztor_a 和 ztor_b 应只映射到 ZtoR 的 a 和 b。"""
    grid = meb.grid([100, 101, 1], [30, 31, 1])
    refl = meb.grid_data(
        grid,
        data=np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32),
    )

    plugin = QPEPlugin(
        method="ztor",
        z_alpha=0.1,
        z_beta=0.5,
        ztor_a=200.0,
        ztor_b=1.6,
        rr_field="ztor_rain_rate",
    )
    result = plugin.process(refl=refl)
    expected = ZtoR(refl, a=200.0, b=1.6, save_name="ztor_rain_rate")

    np.testing.assert_allclose(result.values, expected.values)
    assert result.name == "ztor_rain_rate"


def test_qpe_plugin_dispatches_a_method():
    """a 方法应分发到比衰减降水率估算函数。"""
    grid = meb.grid([100, 101, 1], [30, 31, 1])
    att = meb.grid_data(
        grid,
        data=np.array([[0.01, 0.05], [0.10, 0.20]], dtype=np.float32),
    )

    plugin = QPEPlugin(method="a")
    result = plugin.process(att=att)
    expected = est_rain_rate_a(att)

    np.testing.assert_allclose(result.values, expected.values)


def test_qpe_plugin_dispatches_hydro_method():
    """hydro 方法应分发到水凝物分类降水率估算函数。"""
    grid = meb.grid([100, 101, 1], [30, 31, 1])
    refl = meb.grid_data(
        grid,
        data=np.array([[20.0, 30.0], [40.0, 50.0]], dtype=np.float32),
    )
    att = meb.grid_data(
        grid,
        data=np.array([[0.01, 0.05], [0.10, 0.20]], dtype=np.float32),
    )
    hydro = meb.grid_data(
        grid,
        data=np.array([[1.0, 3.0], [7.0, 5.0]], dtype=np.float32),
    )

    plugin = QPEPlugin(
        method="hydro",
        thresh=0.04,
        thresh_max=False,
    )
    result = plugin.process(refl=refl, att=att, hydro=hydro)
    expected = est_rain_rate_hydro(refl, att, hydro, thresh=0.04, thresh_max=False)

    np.testing.assert_allclose(result.values, expected.values, equal_nan=True)


def test_qpe_plugin_requires_expected_inputs():
    """不同方法缺少必要输入时应报错。"""
    plugin = QPEPlugin(method="zkdp")

    with pytest.raises(ValueError, match="kdp"):
        plugin.process(refl="dummy")


def test_qpe_plugin_rejects_unknown_method():
    """未知方法名应直接报错。"""
    with pytest.raises(ValueError, match="Unsupported QPE method"):
        QPEPlugin(method="unknown")
