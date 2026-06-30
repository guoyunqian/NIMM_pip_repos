#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""迁移版 echo_class 函数测试。"""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr
from pyart.retrieve._echo_class import _feature_detection, steiner_class_buff
from pyart.retrieve._echo_class_wt import calc_scale_break, conv_wavelet_sum, label_classes
from pyart.retrieve.echo_class import (
    _assign_to_class,
    _compute_coeff_transform,
    _get_mass_centers,
    _standardize,
)

from pyart.retrieve.src.echo_class import (
    conv_strat_raut,
    conv_strat_yuter,
    feature_detection,
    hydroclass_semisupervised,
    steiner_conv_strat,
)


def _make_refl_grid():
    levels = np.array([1000.0, 3000.0, 5000.0], dtype=np.float32)
    lat = np.array([30.00, 30.01, 30.02, 30.03, 30.04], dtype=np.float32)
    lon = np.array([100.00, 100.01, 100.02, 100.03, 100.04], dtype=np.float32)

    data = np.full((1, 3, 1, 1, 5, 5), 18.0, dtype=np.float32)
    data[0, 1, 0, 0, 2, 2] = 45.0
    data[0, 1, 0, 0, 1:4, 1:4] += 10.0
    data[0, 2, 0, 0, 2, 2] = 35.0

    return xr.DataArray(
        data,
        dims=("member", "level", "time", "dtime", "lat", "lon"),
        coords={
            "member": [0],
            "level": levels,
            "time": [np.datetime64("2024-01-01T00:00:00")],
            "dtime": [0],
            "lat": lat,
            "lon": lon,
        },
        name="reflectivity",
    )


def _make_hydro_inputs():
    refl = _make_refl_grid()
    zdr = xr.full_like(refl, 0.5)
    rhv = xr.full_like(refl, 0.98)
    kdp = xr.full_like(refl, 0.3)
    temp = xr.full_like(refl, -5.0)

    zdr.values[0, 1, 0, 0, 2, 2] = 2.0
    kdp.values[0, 1, 0, 0, 2, 2] = 1.5
    temp.values[0, 0, 0, 0, :, :] = 2.0
    temp.values[0, 1, 0, 0, :, :] = -2.0
    temp.values[0, 2, 0, 0, :, :] = -10.0

    return refl, zdr, rhv, kdp, temp


def _get_xy_and_resolutions(grid):
    lon = grid.lon.values.astype(np.float64)
    lat = grid.lat.values.astype(np.float64)
    lat_mean = float(np.nanmean(lat))
    x = (lon - lon[0]) * 111000.0 * np.cos(np.deg2rad(lat_mean))
    y = (lat - lat[0]) * 111000.0
    dx = float(np.mean(np.abs(np.diff(x))))
    dy = float(np.mean(np.abs(np.diff(y))))
    return x.astype(np.float32), y.astype(np.float32), dx, dy


def test_steiner_conv_strat_matches_pyart_core():
    """Steiner 分类结果应与底层 Py-ART 实现一致。"""
    refl = _make_refl_grid()
    x, y, dx, dy = _get_xy_and_resolutions(refl)
    z = refl.level.values.astype(np.float32)
    volume = refl.values[0, :, 0, 0, :, :]

    result = steiner_conv_strat(refl, dx=dx, dy=dy, work_level=3000.0)
    expected = steiner_class_buff(
        volume,
        x,
        y,
        z,
        dx=dx,
        dy=dy,
        bkg_rad=11000.0,
        work_level=3000.0,
        intense=42.0,
        peak_relation="default",
        area_relation="medium",
        use_intense=True,
    )

    assert result.shape[-2:] == expected.shape
    assert result.name == "echo_classification"
    np.testing.assert_array_equal(result.values[0, 0, 0, 0, :, :], expected.astype(np.float32))


def test_feature_detection_returns_expected_keys_and_values():
    """feature_detection 应返回主结果及高估低估结果。"""
    refl = _make_refl_grid()
    _, _, dx, dy = _get_xy_and_resolutions(refl)
    field_2d = refl.values[0, 1, 0, 0, :, :]

    result = feature_detection(refl, dx=dx, dy=dy, level_m=3000.0, estimate_flag=True)
    _, _, expected = _feature_detection(field_2d, dx, dy)

    assert set(result.keys()) == {"feature_detection", "feature_under", "feature_over"}
    assert result["feature_detection"].name == "feature_detection"
    np.testing.assert_array_equal(
        result["feature_detection"].values[0, 0, 0, 0, :, :],
        expected.astype(np.float32),
    )


def test_conv_strat_yuter_wraps_feature_detection():
    """conv_strat_yuter 应与 feature_detection 主结果一致。"""
    refl = _make_refl_grid()
    _, _, dx, dy = _get_xy_and_resolutions(refl)

    with pytest.deprecated_call():
        yuter_result = conv_strat_yuter(
            refl,
            dx=dx,
            dy=dy,
            level_m=3000.0,
            estimate_flag=False,
        )

    feature_result = feature_detection(
        refl,
        dx=dx,
        dy=dy,
        level_m=3000.0,
        estimate_flag=False,
    )

    np.testing.assert_array_equal(
        yuter_result["feature_detection"].values,
        feature_result["feature_detection"].values,
    )


def test_hydroclass_semisupervised_returns_hydro_grid():
    """水凝物分类应返回与输入同形状的分类网格。"""
    refl, zdr, rhv, kdp, temp = _make_hydro_inputs()

    result = hydroclass_semisupervised(
        refl,
        zdr,
        rhv,
        kdp,
        temp=temp,
        radar_freq=5.6e9,
        compute_entropy=False,
        vectorize=False,
    )

    assert set(result.keys()) == {"hydro"}
    assert result["hydro"].shape == refl.shape
    assert result["hydro"].name == "radar_echo_classification"
    assert np.nanmax(result["hydro"].values) <= 9
    assert np.nanmin(result["hydro"].values) >= 0


def test_hydroclass_semisupervised_four_variable_mode_runs():
    """4变量模式（无 relH）应可正常运行并返回 hydro 字段。"""
    refl, zdr, rhv, kdp, _ = _make_hydro_inputs()
    mass_centers = _get_mass_centers(5.6e9)[:, :4]
    weights = np.array([1.0, 1.0, 1.0, 0.75], dtype=np.float32)

    result = hydroclass_semisupervised(
        refl,
        zdr,
        rhv,
        kdp,
        var_names=("Zh", "ZDR", "KDP", "RhoHV"),
        mass_centers=mass_centers,
        weights=weights,
        radar_freq=5.6e9,
        compute_entropy=False,
        vectorize=True,
    )

    assert set(result.keys()) == {"hydro"}
    assert result["hydro"].shape == refl.shape


def test_hydroclass_semisupervised_entropy_matches_internal_logic():
    """水凝物分类熵结果应与内部分类逻辑一致。"""
    refl, zdr, rhv, kdp, temp = _make_hydro_inputs()

    result = hydroclass_semisupervised(
        refl,
        zdr,
        rhv,
        kdp,
        temp=temp,
        radar_freq=5.6e9,
        compute_entropy=True,
        output_distances=False,
        vectorize=False,
    )

    scan_refl = np.ma.masked_invalid(refl.values.astype(np.float32).reshape(-1, refl.shape[-1]))
    scan_zdr = np.ma.masked_invalid(zdr.values.astype(np.float32).reshape(-1, zdr.shape[-1]))
    scan_rhv = np.ma.masked_invalid(rhv.values.astype(np.float32).reshape(-1, rhv.shape[-1]))
    scan_kdp = np.ma.masked_invalid(kdp.values.astype(np.float32).reshape(-1, kdp.shape[-1]))
    scan_temp = np.ma.masked_invalid(temp.values.astype(np.float32).reshape(-1, temp.shape[-1]))

    mass_centers = _get_mass_centers(5.6e9)
    fields_dict = {
        "Zh": _standardize(scan_refl.copy(), "Zh"),
        "ZDR": _standardize(scan_zdr.copy(), "ZDR"),
        "KDP": _standardize(scan_kdp.copy(), "KDP"),
        "RhoHV": _standardize(scan_rhv.copy(), "RhoHV"),
        "relH": _standardize((scan_temp * (1000.0 / -6.5)).copy(), "relH"),
    }
    mc_std = np.empty_like(mass_centers, dtype=np.float32)
    for i, name in enumerate(("Zh", "ZDR", "KDP", "RhoHV", "relH")):
        mc_std[:, i] = _standardize(mass_centers[:, i].copy(), name)
    t_vals = _compute_coeff_transform(mc_std, weights=np.array([1.0, 1.0, 1.0, 0.75, 0.5]), value=50.0)
    _, entropy_expected, _ = _assign_to_class(fields_dict, mc_std, weights=np.array([1.0, 1.0, 1.0, 0.75, 0.5]), t_vals=t_vals)

    np.testing.assert_allclose(
        result["entropy"].values,
        np.ma.filled(entropy_expected, np.nan).reshape(refl.shape).astype(np.float32),
        equal_nan=True,
    )


def test_conv_strat_raut_matches_wavelet_components():
    """Raut 小波分类应与底层波レット分类逻辑一致。"""
    refl = _make_refl_grid()
    _, _, dx, _ = _get_xy_and_resolutions(refl)
    field_2d = refl.values[0, 0, 0, 0, :, :]

    result = conv_strat_raut(refl, cappi_level=0, dx=dx, dy=dx)

    scale_break = calc_scale_break(res_meters=dx, conv_scale_km=25)
    wt_sum = conv_wavelet_sum(field_2d.copy(), 200, 1.6, scale_break)
    expected = label_classes(wt_sum, field_2d, 5, 1.5, 5, 25, 42)

    np.testing.assert_allclose(
        result.values[0, 0, 0, 0, :, :],
        np.asarray(expected, dtype=np.float32),
        equal_nan=True,
    )
