"""体扫 level 坐标（仰角 + 高度元数据）测试。"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import meteva_base as meb
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pyart.retrieve.utils.utils import (
    attach_sweep_level_metadata,
    build_sweep_level_coordinates,
    stack_gridded_sweeps,
)


def _mock_radar(elevations_deg, gate_ranges_m, site_alt_m=50.0):
    """最小 Radar 替身，供 build_sweep_level_coordinates 单元测试。"""
    return SimpleNamespace(
        nsweeps=len(elevations_deg),
        fixed_angle={"data": np.asarray(elevations_deg, dtype=np.float64)},
        altitude={"data": np.array([site_alt_m], dtype=np.float64)},
        range={"data": np.asarray(gate_ranges_m, dtype=np.float64)},
    )


def test_build_sweep_level_coordinates_matches_fixed_angle():
    radar = _mock_radar([0.5, 1.5, 2.4], np.linspace(1000.0, 230000.0, 460))
    coords = build_sweep_level_coordinates(radar, range_ref="max")

    assert len(coords["level_list"]) == radar.nsweeps
    np.testing.assert_allclose(coords["elevation_deg"], radar.fixed_angle["data"])
    assert coords["height_m"].shape == coords["elevation_deg"].shape
    assert float(coords["height_m"][0]) > float(coords["site_alt_m"])
    assert coords["range_m_used"] == float(radar.range["data"][-1])
    assert "height_reference" in coords


def test_stack_gridded_sweeps_and_metadata():
    grid0 = meb.grid([100, 101, 1], [30, 31, 1], level_list=[0.5])
    grid1 = meb.grid([100, 101, 1], [30, 31, 1], level_list=[1.5])
    g0 = meb.grid_data(grid0, data=np.ones((1, 1, 1, 1, 2, 2), dtype=np.float32))
    g1 = meb.grid_data(grid1, data=np.full((1, 1, 1, 1, 2, 2), 2.0, dtype=np.float32))
    coords = {
        "level_list": [0.5, 1.5],
        "elevation_deg": np.array([0.5, 1.5], dtype=np.float64),
        "height_m": np.array([1000.0, 2000.0], dtype=np.float64),
        "height_reference": "test",
    }
    volume = stack_gridded_sweeps([g0, g1], coords)

    assert int(volume.sizes["level"]) == 2
    assert volume.attrs["level_coordinate"] == "elevation_deg"
    assert volume.attrs["elevation_deg"] == [0.5, 1.5]
    assert volume.attrs["height_m"] == [1000.0, 2000.0]
    np.testing.assert_allclose(volume.values[0, 0, 0, 0], 1.0)
    np.testing.assert_allclose(volume.values[0, 1, 0, 0], 2.0)

    tagged = attach_sweep_level_metadata(volume, coords)
    assert tagged.attrs["height_m"] == [1000.0, 2000.0]
