#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""QPE CLI 测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import meteva_base as meb
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pyart.retrieve.cli.qpe import (
    est_rain_rate_hydro,
    est_rain_rate_kdp,
    est_rain_rate_z,
    est_rain_rate_zkdp,
    est_rain_rate_zpoly,
    qpeplugin,
    ztor,
)
from pyart.retrieve.src.qpe import (
    EstimateRainRateHydro,
    EstimateRainRateKdp,
    EstimateRainRateZ,
    EstimateRainRateZKdp,
    EstimateRainRateZPoly,
    EstimateZtoR,
    QPEPlugin,
    ZtoR,
)

INPUT_DIR = Path(__file__).resolve().parents[1] / "test_data" / "qpe" / "input"
ACHN_REFL = INPUT_DIR / "ACHN_CREF000_20240612_070000.nc"
HYDRO_REFL = INPUT_DIR / "hydro_corrected_reflectivity.nc"
HYDRO_ATT = INPUT_DIR / "hydro_specific_attenuation.nc"
HYDRO_CLASS = INPUT_DIR / "hydro_radar_echo_classification.nc"
Z9010_REFL = INPUT_DIR / "Z9010_20250724192400_refl_volume.nc"
Z9010_KDP = INPUT_DIR / "Z9010_20250724192400_kdp_volume.nc"
KDP_FILE = INPUT_DIR / "Z_RADR_I_Z9600_20260425062420_kdp.nc"


def _require_path(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"test input not found: {path}")
    return path


def _read_result_nc(path: Path) -> np.ndarray:
    data = meb.read_griddata_from_nc(str(path))
    return np.asarray(data.values, dtype=np.float32)


def test_est_rain_rate_z_cli_matches_plugin(tmp_path):
    """est_rain_rate_z CLI 输出应与 EstimateRainRateZ 一致。"""
    refl_path = _require_path(ACHN_REFL)
    out_path = tmp_path / "est_rain_rate_z.nc"

    est_rain_rate_z(str(refl_path), output_path=str(out_path))

    refl = meb.read_griddata_from_nc(str(refl_path))
    expected = EstimateRainRateZ().process(refl)
    actual = _read_result_nc(out_path)
    np.testing.assert_allclose(actual, expected.values.astype(np.float32), equal_nan=True)


def test_est_rain_rate_zpoly_cli_matches_function(tmp_path):
    """est_rain_rate_zpoly CLI 输出应与 est_rain_rate_zpoly 一致。"""
    refl_path = _require_path(ACHN_REFL)
    out_path = tmp_path / "est_rain_rate_zpoly.nc"

    est_rain_rate_zpoly(str(refl_path), output_path=str(out_path))

    refl = meb.read_griddata_from_nc(str(refl_path))
    expected = EstimateRainRateZPoly().process(refl)
    actual = _read_result_nc(out_path)
    np.testing.assert_allclose(actual, expected.values.astype(np.float32), equal_nan=True)


def test_ztor_cli_matches_function(tmp_path):
    """ztor CLI 输出应与 ZtoR 一致。"""
    refl_path = _require_path(ACHN_REFL)
    out_path = tmp_path / "ztor.nc"

    ztor(str(refl_path), a=300.0, b=1.4, output_path=str(out_path))

    refl = meb.read_griddata_from_nc(str(refl_path))
    expected = EstimateZtoR(a=300.0, b=1.4).process(refl)
    actual = _read_result_nc(out_path)
    np.testing.assert_allclose(actual, expected.values.astype(np.float32), equal_nan=True)
    assert ZtoR(refl, a=300.0, b=1.4).name == expected.name


def test_qpeplugin_z_cli_matches_plugin(tmp_path):
    """qpeplugin method=z 应与 QPEPlugin(method='z') 一致。"""
    refl_path = _require_path(ACHN_REFL)
    out_path = tmp_path / "qpeplugin_z.nc"

    qpeplugin("z", refl_path=str(refl_path), output_path=str(out_path))

    refl = meb.read_griddata_from_nc(str(refl_path))
    expected = QPEPlugin(method="z").process(refl=refl)
    actual = _read_result_nc(out_path)
    np.testing.assert_allclose(actual, expected.values.astype(np.float32), equal_nan=True)


def test_est_rain_rate_kdp_cli_matches_plugin(tmp_path):
    """est_rain_rate_kdp CLI 应与 EstimateRainRateKdp 一致。"""
    kdp_path = _require_path(KDP_FILE if KDP_FILE.is_file() else Z9010_KDP)
    out_path = tmp_path / "est_rain_rate_kdp.nc"

    est_rain_rate_kdp(str(kdp_path), output_path=str(out_path))

    kdp = meb.read_griddata_from_nc(str(kdp_path))
    expected = EstimateRainRateKdp().process(kdp)
    actual = _read_result_nc(out_path)
    np.testing.assert_allclose(actual, expected.values.astype(np.float32), equal_nan=True)


def test_est_rain_rate_zkdp_cli_matches_plugin(tmp_path):
    """est_rain_rate_zkdp CLI 应与 EstimateRainRateZKdp 一致。"""
    refl_path = _require_path(Z9010_REFL)
    kdp_path = _require_path(Z9010_KDP)
    out_path = tmp_path / "est_rain_rate_zkdp.nc"

    est_rain_rate_zkdp(
        str(refl_path),
        str(kdp_path),
        thresh=40.0,
        output_path=str(out_path),
    )

    refl = meb.read_griddata_from_nc(str(refl_path))
    kdp = meb.read_griddata_from_nc(str(kdp_path))
    expected = EstimateRainRateZKdp(thresh=40.0, thresh_max=True).process(refl, kdp)
    actual = _read_result_nc(out_path)
    np.testing.assert_allclose(actual, expected.values.astype(np.float32), equal_nan=True)


def test_est_rain_rate_hydro_cli_matches_plugin(tmp_path):
    """est-rain-rate-hydro CLI 应与 EstimateRainRateHydro 一致。"""
    refl_path = _require_path(HYDRO_REFL)
    att_path = _require_path(HYDRO_ATT)
    hydro_path = _require_path(HYDRO_CLASS)
    out_path = tmp_path / "est_rain_rate_hydro.nc"

    est_rain_rate_hydro(
        str(refl_path),
        str(att_path),
        str(hydro_path),
        thresh=0.04,
        output_path=str(out_path),
    )

    refl = meb.read_griddata_from_nc(str(refl_path))
    att = meb.read_griddata_from_nc(str(att_path))
    hydro = meb.read_griddata_from_nc(str(hydro_path))
    expected = EstimateRainRateHydro(thresh=0.04, thresh_max=False).process(
        refl, att, hydro
    )
    actual = _read_result_nc(out_path)
    np.testing.assert_allclose(actual, expected.values.astype(np.float32), equal_nan=True)
