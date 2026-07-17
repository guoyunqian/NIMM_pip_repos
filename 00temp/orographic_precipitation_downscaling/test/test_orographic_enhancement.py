"""Tests for the migrated orographic enhancement implementation."""

from pathlib import Path
import sys

import numpy as np
import pytest
import xarray as xr

MODULE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = MODULE_ROOT.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from orographic_precipitation_downscaling.src.orographic_enhancement import MetaOrographicEnhancement, OrographicEnhancement

DATA_ROOT = MODULE_ROOT / "test_data" / "orographic_enhancement_data"
CLI_INPUT_DIR = DATA_ROOT / "cli_input"
REFERENCE_DIR = DATA_ROOT
MEB_DIMS = ("member", "level", "time", "dtime", "lat", "lon")


def _as_spatial(values: np.ndarray) -> np.ndarray:
    arr = np.squeeze(np.asarray(values))
    if arr.ndim != 2:
        raise AssertionError(f"expected 2D spatial values, got shape {arr.shape}")
    return arr


def create_test_data():
    """Create small synthetic 2D inputs."""
    shape = (10, 10)
    temperature = np.full(shape, 283.15, dtype=np.float32)
    humidity = np.full(shape, 0.85, dtype=np.float32)
    pressure = np.full(shape, 101325.0, dtype=np.float32)
    uwind = np.full(shape, 5.0, dtype=np.float32)
    vwind = np.full(shape, 3.0, dtype=np.float32)
    topography = np.zeros(shape, dtype=np.float32)
    topography[5:, :] = 50.0
    return temperature, humidity, pressure, uwind, vwind, topography


def create_test_xarray_data():
    """Create small synthetic xarray inputs on a lat/lon grid."""
    temperature, humidity, pressure, uwind, vwind, topography = create_test_data()
    lat = np.linspace(40.0, 50.0, 10, dtype=np.float32)
    lon = np.linspace(-10.0, 0.0, 10, dtype=np.float32)

    coords = [("lat", lat), ("lon", lon)]
    temp_da = xr.DataArray(temperature, coords=coords, dims=["lat", "lon"], attrs={"units": "K"})
    hum_da = xr.DataArray(humidity, coords=coords, dims=["lat", "lon"], attrs={"units": "1"})
    pres_da = xr.DataArray(pressure, coords=coords, dims=["lat", "lon"], attrs={"units": "Pa"})
    uwind_da = xr.DataArray(uwind, coords=coords, dims=["lat", "lon"], attrs={"units": "m s-1"})
    vwind_da = xr.DataArray(vwind, coords=coords, dims=["lat", "lon"], attrs={"units": "m s-1"})
    topo_da = xr.DataArray(topography, coords=coords, dims=["lat", "lon"], attrs={"units": "m"})
    return temp_da, hum_da, pres_da, uwind_da, vwind_da, topo_da


def to_meb6d(data_2d: xr.DataArray) -> xr.DataArray:
    """Wrap a 2D lat/lon field into a singleton 6D MEB-style grid."""
    wrapped = xr.DataArray(
        np.asarray(data_2d.values, dtype=np.float32)[None, None, None, None, :, :],
        dims=MEB_DIMS,
        coords={
            "member": ["data0"],
            "level": [1000.0],
            "time": [np.datetime64("1970-01-01T00:00:00")],
            "dtime": [0],
            "lat": data_2d.coords["lat"].values,
            "lon": data_2d.coords["lon"].values,
        },
        attrs=dict(data_2d.attrs),
        name=data_2d.name,
    )
    wrapped.coords["level"].attrs["units"] = "m"
    return wrapped


def open_resource_dataarray(filename: str, variable_name: str) -> xr.DataArray:
    """Open a resource variable and load it eagerly."""
    search_dirs = [CLI_INPUT_DIR]
    if filename == "original_algorithm_result.nc":
        search_dirs = [REFERENCE_DIR]
    for base_dir in search_dirs:
        path = base_dir / filename
        if not path.exists():
            continue
        dataset = xr.open_dataset(path, decode_timedelta=False)
        try:
            return dataset[variable_name].load()
        finally:
            dataset.close()
    raise FileNotFoundError(f"未找到测试数据: {filename}")


class TestOrographicEnhancement:
    """Unit tests for the migrated implementation."""

    def test_numpy_input(self):
        temperature, humidity, pressure, uwind, vwind, topography = create_test_data()
        result = OrographicEnhancement()(temperature, humidity, pressure, uwind, vwind, topography)

        assert isinstance(result, xr.DataArray)
        assert result.attrs["units"] == "m s-1"
        assert result.attrs["long_name"] == "orographic_enhancement"
        assert result.shape == temperature.shape
        assert result.dtype == np.float32
        assert np.all(result.values >= 0.0)

    def test_xarray_input(self):
        temp_da, hum_da, pres_da, uwind_da, vwind_da, topo_da = create_test_xarray_data()
        result = OrographicEnhancement()(
            to_meb6d(temp_da),
            to_meb6d(hum_da),
            to_meb6d(pres_da),
            to_meb6d(uwind_da),
            to_meb6d(vwind_da),
            to_meb6d(topo_da),
        )

        assert isinstance(result, xr.DataArray)
        assert result.attrs["units"] == "m s-1"
        assert result.attrs["long_name"] == "orographic_enhancement"
        assert result.dims == MEB_DIMS
        assert result.sizes["lat"] == topo_da.sizes["lat"]
        assert result.sizes["lon"] == topo_da.sizes["lon"]
        assert result.shape == (1, 1, 1, 1, *topo_da.shape)

    def test_rejects_two_dimensional_xarray_topography(self):
        temp_da, hum_da, pres_da, uwind_da, vwind_da, topo_da = create_test_xarray_data()
        with pytest.raises(ValueError, match="topography 的 xarray 输入必须是标准六维网格"):
            OrographicEnhancement()(
                to_meb6d(temp_da),
                to_meb6d(hum_da),
                to_meb6d(pres_da),
                to_meb6d(uwind_da),
                to_meb6d(vwind_da),
                topo_da,
            )

    def test_2d_output_inherits_time_from_topography_template(self):
        temp_da, hum_da, pres_da, uwind_da, vwind_da, topo_da = create_test_xarray_data()
        forecast_time = np.datetime64("2023-09-20T06:00:00")
        topo_meb = to_meb6d(topo_da).assign_coords(time=forecast_time)

        result = OrographicEnhancement()(
            to_meb6d(temp_da),
            to_meb6d(hum_da),
            to_meb6d(pres_da),
            to_meb6d(uwind_da),
            to_meb6d(vwind_da),
            topo_meb,
        )

        assert "time" in result.coords
        assert result.coords["time"].values == forecast_time

    def test_output_consistency_between_numpy_and_xarray(self):
        temperature, humidity, pressure, uwind, vwind, topography = create_test_data()
        result_np = OrographicEnhancement()(temperature, humidity, pressure, uwind, vwind, topography)

        temp_da, hum_da, pres_da, uwind_da, vwind_da, topo_da = create_test_xarray_data()
        result_xr = OrographicEnhancement()(
            to_meb6d(temp_da),
            to_meb6d(hum_da),
            to_meb6d(pres_da),
            to_meb6d(uwind_da),
            to_meb6d(vwind_da),
            to_meb6d(topo_da),
        )

        np.testing.assert_allclose(result_np, _as_spatial(result_xr.values), rtol=1e-5)

    def test_zero_wind_case(self):
        temperature, humidity, pressure, uwind, vwind, topography = create_test_data()
        uwind[:] = 0.0
        vwind[:] = 0.0

        result = OrographicEnhancement()(temperature, humidity, pressure, uwind, vwind, topography)

        assert np.allclose(result.values, 0.0, atol=1e-10)

    def test_meta_orographic_enhancement(self):
        temp_da, hum_da, pres_da, uwind_da, vwind_da, topo_da = create_test_xarray_data()

        wind_speed = np.sqrt(uwind_da.values**2 + vwind_da.values**2)
        wind_direction = (np.degrees(np.arctan2(uwind_da.values, vwind_da.values)) + 180.0) % 360.0

        wind_speed_da_2d = xr.DataArray(
            wind_speed,
            coords=uwind_da.coords,
            dims=uwind_da.dims,
            attrs={"units": "m s-1", "standard_name": "wind_speed"},
        )
        wind_dir_da_2d = xr.DataArray(
            wind_direction,
            coords=uwind_da.coords,
            dims=uwind_da.dims,
            attrs={"units": "degrees", "standard_name": "wind_from_direction"},
        )

        result = MetaOrographicEnhancement()(
            to_meb6d(temp_da),
            to_meb6d(hum_da),
            to_meb6d(pres_da),
            to_meb6d(wind_speed_da_2d),
            to_meb6d(wind_dir_da_2d),
            to_meb6d(topo_da),
        )

        assert isinstance(result, xr.DataArray)
        assert result.attrs["units"] == "m s-1"
        assert result.dims == MEB_DIMS
        assert result.shape == (1, 1, 1, 1, *topo_da.shape)

    def test_edge_cases_below_thresholds(self):
        shape = (5, 5)
        temperature = np.full(shape, 283.15, dtype=np.float32)
        humidity = np.full(shape, 0.5, dtype=np.float32)
        pressure = np.full(shape, 101325.0, dtype=np.float32)
        uwind = np.full(shape, 1.0, dtype=np.float32)
        vwind = np.full(shape, 1.0, dtype=np.float32)
        topography = np.full(shape, 5.0, dtype=np.float32)

        result = OrographicEnhancement()(temperature, humidity, pressure, uwind, vwind, topography)

        assert np.allclose(result.values, 0.0, atol=1e-10)

    def test_official_sample_regression(self):
        temperature = open_resource_dataarray("temperature.nc", "air_temperature")
        humidity = open_resource_dataarray("humidity.nc", "relative_humidity")
        pressure = open_resource_dataarray("pressure.nc", "air_pressure")
        wind_speed = open_resource_dataarray("wind_speed.nc", "wind_speed")
        wind_direction = open_resource_dataarray("wind_direction.nc", "wind_from_direction")
        orography = open_resource_dataarray("orography_uk-standard_1km.nc", "surface_altitude")
        expected = open_resource_dataarray("original_algorithm_result.nc", "orographic_enhancement")

        result = MetaOrographicEnhancement()(
            temperature, humidity, pressure, wind_speed, wind_direction, orography
        )

        np.testing.assert_allclose(
            _as_spatial(result.values),
            _as_spatial(expected.values),
            atol=6e-7,
            rtol=0.0,
        )
