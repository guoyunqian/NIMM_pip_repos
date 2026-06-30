"""cinrad StandardData → meteva_base 网格（不经过 Py-ART Radar）。

本模块只做「极坐标/单层 PPI → 规则经纬度 meteva 网格」的转换；
NetCDF 落盘请用 :func:`~utils.save_meteva_grid_to_netcdf`（float32 + CF 缺测值；
勿用 ``meteva_base.write_griddata_to_nc`` 默认 int32 缩放，否则 NaN 会显示为约 ``-2147483.6``）。

与 :mod:`cinrad_pyart_prep` 的分工：
- ``cinrad_pyart_prep``：cinrad → Py-ART ``Radar``（原算法、门点坐标对比）
- ``cinrad_meb``：cinrad ``get_data`` / ``grid_2d`` / ``quick_cr`` → meteva（迁移插件输入）
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

import meteva_base as meb

import xarray as xr

from cinrad.calc import grid_2d
from .utils import stack_gridded_sweeps


def _same_lat_lon_grid(grid_a: xr.DataArray, grid_b: xr.DataArray, *, atol: float = 0.02) -> bool:
    """检查两幅 meteva 网格的 lat/lon 轴是否一致（忽略 level 等差异）。"""
    if grid_a.shape[-2:] != grid_b.shape[-2:]:
        return False
    return bool(
        np.allclose(grid_a.coords["lat"].values, grid_b.coords["lat"].values, atol=atol)
        and np.allclose(grid_a.coords["lon"].values, grid_b.coords["lon"].values, atol=atol)
    )

_CINRAD_DTYPE_VAR_MAP = {
    "REF": ("REF", "reflectivity", "dBZ"),
    "KDP": ("KDP", "specific_differential_phase", "deg/km"),
    "RHO": ("RHO", "cross_correlation_ratio", "1"),
}


def build_cinrad_level_coords(
    cinrad_file,
    dtype: str,
    *,
    range_km: int = 300,
) -> dict:
    """各仰角索引与 ``level`` 元数据（与 :func:`build_sweep_level_coordinates` 字段一致）。"""
    tilts = list(cinrad_file.available_tilt(dtype))
    if not tilts:
        raise ValueError(f"cinrad 文件中没有 {dtype} 仰角层")
    elevation_deg = np.array([float(cinrad_file.el[nel]) for nel in tilts], dtype=np.float64)
    site_alt = float(getattr(cinrad_file, "radarheight", 0.0))
    ref_range = float(range_km) * 1000.0
    height_m = site_alt + ref_range * np.sin(np.deg2rad(elevation_deg))
    return {
        "tilt_indices": tilts,
        "level_list": [float(v) for v in elevation_deg],
        "elevation_deg": elevation_deg,
        "height_m": height_m.astype(np.float64),
        "height_reference": f"site_alt + {range_km:g}km*sin(elevation)",
        "range_m_used": ref_range,
        "site_alt_m": site_alt,
    }


def _parse_cinrad_scan_time(cinrad_file) -> pd.Timestamp:
    return pd.to_datetime(cinrad_file.scantime)


def _cinrad_site_code(cinrad_file) -> str:
    return str(getattr(cinrad_file, "code", None) or "RADAR")


def cinrad_frequency_hz(cinrad_file) -> float | None:
    """从标准格式基数据站配置读取发射频率（Hz）。

    cinrad 解析头块 ``site_config.frequency``（单位 MHz，见 QX/T 653 站配置），
    并保存为 ``StandardData.wavelength``（厘米）。二者满足
    ``wavelength_cm = 3e8 / (frequency_MHz * 1e4)``。
    """
    wl_cm = getattr(cinrad_file, "wavelength", None)
    if wl_cm is None:
        return None
    wl_cm = float(wl_cm)
    if not np.isfinite(wl_cm) or wl_cm <= 0:
        return None
    return 3e8 / (wl_cm * 0.01)


def _freq_band_from_hz(frequency_hz: float) -> str | None:
    """与 :func:`echo_class.get_freq_band` 一致的 S/C/X 划分（Hz）。"""
    if frequency_hz >= 2e9 and frequency_hz < 4e9:
        return "S"
    if frequency_hz >= 4e9 and frequency_hz < 8e9:
        return "C"
    if frequency_hz >= 8e9 and frequency_hz <= 12e9:
        return "X"
    return None


def _apply_cinrad_grid_attrs(gdata: meb.grid_data, cinrad_file) -> None:
    """写入站点、扫描时间与频率等元数据（供 QPE / 水凝物等读取 ``attrs``）。"""
    gdata.attrs["site_code"] = _cinrad_site_code(cinrad_file)
    gdata.attrs["scan_time"] = str(_parse_cinrad_scan_time(cinrad_file))
    freq_hz = cinrad_frequency_hz(cinrad_file)
    if freq_hz is not None:
        gdata.attrs["frequency"] = float(freq_hz)
        gdata.attrs["frequency_units"] = "Hz"
        band = _freq_band_from_hz(freq_hz)
        if band is not None:
            gdata.attrs["band"] = band
    if getattr(cinrad_file, "name", None):
        gdata.attrs["site_name"] = str(cinrad_file.name)
    lon = getattr(cinrad_file, "stationlon", None)
    lat = getattr(cinrad_file, "stationlat", None)
    if lon is not None:
        gdata.attrs["site_longitude"] = float(lon)
    if lat is not None:
        gdata.attrs["site_latitude"] = float(lat)


def _cinrad_layer_to_meteva(
    data_2d: np.ndarray,
    lon_1d: np.ndarray,
    lat_1d: np.ndarray,
    *,
    field_name: str,
    cinrad_file,
    level: float,
    units: str,
    member: str | None = None,
    time: pd.Timestamp | None = None,
) -> meb.grid_data:
    """单层经纬度规则网格 → meteva ``grid_data``（6 维，level=1）。"""
    if len(lon_1d) < 2 or len(lat_1d) < 2:
        raise ValueError("grid_2d 输出经纬度维度过小")
    dlon = float(lon_1d[1] - lon_1d[0])
    dlat = float(lat_1d[1] - lat_1d[0])
    if time is None:
        time = _parse_cinrad_scan_time(cinrad_file)
    member = member or _cinrad_site_code(cinrad_file)

    grid = meb.grid(
        [float(lon_1d.min()), float(lon_1d.max()), dlon],
        [float(lat_1d.min()), float(lat_1d.max()), dlat],
        gtime=time,
        dtime_list=[0],
        level_list=[float(level)],
        member_list=[member],
    )
    gdata = meb.grid_data(grid, np.asarray(data_2d, dtype=np.float32))
    gdata.name = field_name
    gdata.attrs["units"] = units
    gdata.attrs["var_name"] = field_name
    gdata.attrs["data_name"] = member
    _apply_cinrad_grid_attrs(gdata, cinrad_file)
    return gdata


def cinrad_dtype_to_meteva_volume(
    cinrad_file,
    dtype: str,
    *,
    range_km: int = 300,
    resolution: Sequence[int] = (1000, 1000),
    field_name: str | None = None,
    units: str | None = None,
):
    """逐仰角 ``get_data`` + ``grid_2d``，拼成带 ``level`` 维的 meteva 体扫网格。

    与 ``quick_cr`` 相同，在 cinrad 内完成极坐标 → 经纬度网格，无需 ``standard_data_to_pyart``。
    """
    if dtype not in _CINRAD_DTYPE_VAR_MAP:
        raise ValueError(f"不支持的 dtype: {dtype}")
    cinrad_var, default_name, default_units = _CINRAD_DTYPE_VAR_MAP[dtype]
    field_name = field_name or default_name
    units = units or default_units

    level_coords = build_cinrad_level_coords(cinrad_file, dtype, range_km=range_km)
    x_out = y_out = None
    sweep_grids = []

    for nel, elev in zip(level_coords["tilt_indices"], level_coords["level_list"]):
        ds = cinrad_file.get_data(nel, range_km, dtype)
        data = np.asarray(ds[cinrad_var].values, dtype=np.float32)
        lon = np.asarray(ds["longitude"].values, dtype=np.float64)
        lat = np.asarray(ds["latitude"].values, dtype=np.float64)
        gridded, x_out, y_out = grid_2d(
            data,
            lon,
            lat,
            x_out=x_out,
            y_out=y_out,
            resolution=tuple(resolution),
        )
        sweep_grids.append(
            _cinrad_layer_to_meteva(
                gridded,
                x_out,
                y_out,
                field_name=field_name,
                cinrad_file=cinrad_file,
                level=elev,
                units=units,
            )
        )

    volume = stack_gridded_sweeps(sweep_grids, level_coords)
    volume.name = field_name
    _apply_cinrad_grid_attrs(volume, cinrad_file)
    return volume, sweep_grids


def pick_low_tilt_index(
    cinrad_file,
    dtype: str = "REF",
    *,
    max_elevation_deg: float = 2.0,
) -> int:
    """在 ``available_tilt(dtype)`` 中选取不高于 ``max_elevation_deg`` 的最低仰角索引。"""
    tilts = list(cinrad_file.available_tilt(dtype))
    if not tilts:
        raise ValueError(f"cinrad 文件中没有 {dtype} 仰角层")
    elev = np.asarray([float(cinrad_file.el[nel]) for nel in tilts], dtype=np.float64)
    candidates = np.where(elev <= float(max_elevation_deg))[0]
    if candidates.size == 0:
        return int(np.argmin(elev))
    return int(candidates[np.argmin(elev[candidates])])


def cinrad_tilt_to_meteva_grid_aligned(
    cinrad_file,
    dtype: str,
    tilt_index: int,
    template_grid: xr.DataArray,
    *,
    range_km: int = 300,
    field_name: str | None = None,
    units: str | None = None,
) -> meb.grid_data:
    """将指定仰角单层网格化到与 ``template_grid`` 相同的 lat/lon 网格上。"""
    if dtype not in _CINRAD_DTYPE_VAR_MAP:
        raise ValueError(f"不支持的 dtype: {dtype}")
    cinrad_var, default_name, default_units = _CINRAD_DTYPE_VAR_MAP[dtype]
    field_name = field_name or default_name
    units = units or default_units

    tilts = list(cinrad_file.available_tilt(dtype))
    if not tilts:
        raise ValueError(f"cinrad 文件中没有 {dtype} 仰角层")
    tilt_index = int(tilt_index)
    if tilt_index < 0 or tilt_index >= len(tilts):
        raise ValueError(f"tilt_index {tilt_index} 超出 {dtype} 仰角范围")

    lon_1d = np.asarray(template_grid.coords["lon"].values, dtype=np.float64)
    lat_1d = np.asarray(template_grid.coords["lat"].values, dtype=np.float64)
    resolution = (int(lon_1d.size), int(lat_1d.size))

    nel = tilts[tilt_index]
    elev = float(cinrad_file.el[nel])
    ds = cinrad_file.get_data(nel, range_km, dtype)
    data = np.asarray(ds[cinrad_var].values, dtype=np.float32)
    lon = np.asarray(ds["longitude"].values, dtype=np.float64)
    lat = np.asarray(ds["latitude"].values, dtype=np.float64)
    gridded, _, _ = grid_2d(
        data,
        lon,
        lat,
        x_out=lon_1d,
        y_out=lat_1d,
        resolution=resolution,
    )
    return _cinrad_layer_to_meteva(
        gridded,
        lon_1d,
        lat_1d,
        field_name=field_name,
        cinrad_file=cinrad_file,
        level=elev,
        units=units,
    )


def apply_meteva_gate_mask(
    grid_data: xr.DataArray,
    gate_included: np.ndarray,
) -> xr.DataArray:
    """用 ``gate_included``（2D lat×lon，True 为保留）掩膜 meteva 网格。

    同一 2D 掩膜作用于 **所有** ``member/level/time/dtime`` 层（`values[..., lat, lon]`），
    不是只过滤某一个 ``level``。若只需单层，请先 ``select_grid_level`` 再掩膜。
    """
    included = np.asarray(gate_included, dtype=bool)
    if included.ndim != 2:
        raise ValueError("gate_included must be a 2D (lat, lon) mask")
    out = grid_data.copy()
    values = np.asarray(out.values, dtype=np.float32).copy()
    if values.shape[-2:] != included.shape:
        raise ValueError(
            f"gate_included shape {included.shape} must match grid plane {values.shape[-2:]}"
        )
    values[..., ~included] = np.nan
    out.values = values
    return out


def apply_cref_quality_gatefilter(
    cref_grid: xr.DataArray,
    *,
    refl_low: xr.DataArray | None = None,
    rho_low: xr.DataArray | None = None,
    min_refl_dbz: float = 15.0,
    min_rho: float = 0.85,
    min_cref_dbz: float = 15.0,
    max_dbz: float = 80.0,
):
    """对 CREF 网格应用 ``GridGateFilter``（低仰角 REF + RHO + CR 自身阈值）。

    返回
    ----
    cref_qc, gatefilter, gate_included
        过滤后的 CREF、过滤器对象、2D 保留掩膜。
    """
    from ...correct import GridGateFilter

    cref_grid = xr.DataArray(cref_grid) if not isinstance(cref_grid, xr.DataArray) else cref_grid
    if refl_low is not None and not _same_lat_lon_grid(cref_grid, refl_low):
        raise ValueError("cref_grid and refl_low must share the same lat/lon coordinates")
    if rho_low is not None and not _same_lat_lon_grid(cref_grid, rho_low):
        raise ValueError("cref_grid and rho_low must share the same lat/lon coordinates")

    gatefilter = GridGateFilter(cref_grid)
    gatefilter.exclude_invalid(cref_grid)
    gatefilter.exclude_masked(cref_grid)
    if min_cref_dbz is not None:
        gatefilter.exclude_below(cref_grid, float(min_cref_dbz))
    if max_dbz is not None:
        gatefilter.exclude_outside(cref_grid, 0.0, float(max_dbz))
    if refl_low is not None:
        gatefilter.exclude_invalid(refl_low)
        gatefilter.exclude_masked(refl_low)
        if min_refl_dbz is not None:
            gatefilter.exclude_below(refl_low, float(min_refl_dbz))
    if rho_low is not None:
        gatefilter.exclude_invalid(rho_low)
        gatefilter.exclude_masked(rho_low)
        if min_rho is not None:
            gatefilter.exclude_below(rho_low, float(min_rho))

    gate_included = np.asarray(gatefilter.gate_included, dtype=bool)
    cref_qc = apply_meteva_gate_mask(cref_grid, gate_included)
    cref_qc.attrs = dict(cref_grid.attrs)
    cref_qc.attrs["qc_gatefilter"] = "cref+low_refl+rho"
    return cref_qc, gatefilter, gate_included


def build_cref_qc_aux_grids_from_cinrad(
    cinrad_file,
    cref_grid: xr.DataArray,
    *,
    range_km: int = 300,
    max_low_tilt_deg: float = 2.0,
) -> tuple[meb.grid_data, meb.grid_data, int]:
    """生成与 CREF 对齐的低仰角 REF、RHO 网格，供 :func:`apply_cref_quality_gatefilter` 使用。"""
    low_idx = pick_low_tilt_index(
        cinrad_file, "REF", max_elevation_deg=max_low_tilt_deg,
    )
    refl_low = cinrad_tilt_to_meteva_grid_aligned(
        cinrad_file, "REF", low_idx, cref_grid, range_km=range_km,
    )
    rho_low = None
    if list(cinrad_file.available_tilt("RHO")):
        rho_tilts = list(cinrad_file.available_tilt("RHO"))
        rho_idx = min(low_idx, len(rho_tilts) - 1)
        rho_low = cinrad_tilt_to_meteva_grid_aligned(
            cinrad_file, "RHO", rho_idx, cref_grid, range_km=range_km,
            field_name="cross_correlation_ratio",
        )
    return refl_low, rho_low, low_idx


def apply_cr_dataset_gate_mask(cr_ds, gate_included: np.ndarray):
    """将 2D 掩膜应用到 cinrad ``quick_cr`` 输出的 ``CR`` 场（用于 Py-ART 门点填值）。"""
    included = np.asarray(gate_included, dtype=bool)
    cr = np.asarray(cr_ds["CR"].values, dtype=np.float32).copy()
    if cr.shape != included.shape:
        raise ValueError(f"CR shape {cr.shape} must match gate mask {included.shape}")
    cr[~included] = np.nan
    out = cr_ds.copy(deep=True)
    out["CR"].values = cr
    return out


_DEFAULT_RADAR_MASK_FIELDS = (
    "reflectivity",
    "specific_differential_phase",
    "cross_correlation_ratio",
    "differential_reflectivity",
    "velocity",
    "spectrum_width",
)


def gate_excluded_from_latlon_qc_mask(
    gate_lat: np.ndarray,
    gate_lon: np.ndarray,
    gate_included: np.ndarray,
    lon_1d: np.ndarray,
    lat_1d: np.ndarray,
    target_shape: tuple[int, int],
    *,
    method: str = "nearest",
) -> np.ndarray:
    """在门点经纬度上采样 CREF QC 的 ``gate_included``，得到 ``target_shape`` 的排除掩膜。

    ``True`` 表示该门点应被排除。各雷达场射线数可能略差 1 行，需按各自 ``data.shape`` 切片门点坐标。
    """
    included = np.asarray(gate_included, dtype=bool)
    if included.ndim != 2:
        raise ValueError("gate_included must be a 2D (lat, lon) mask")

    nr, ng = int(target_shape[0]), int(target_shape[1])
    glat = np.asarray(gate_lat, dtype=np.float64)[:nr, :ng]
    glon = np.asarray(gate_lon, dtype=np.float64)[:nr, :ng]
    included_at_gates = sample_latlon_field_at_gates(
        included.astype(np.float32),
        lat_1d,
        lon_1d,
        glat,
        glon,
        method=method,
    )
    keep = np.isfinite(included_at_gates) & (included_at_gates >= 0.5)
    return ~keep


def apply_latlon_mask_to_pyart_radar(
    radar,
    gate_included: np.ndarray,
    lon_1d: np.ndarray,
    lat_1d: np.ndarray,
    field_names: Sequence[str] | None = None,
    *,
    method: str = "nearest",
) -> np.ndarray:
    """将 CREF QC 的 2D ``gate_included`` 掩膜应用到 Py-ART ``Radar`` 各门点场。

    在门点经纬度上对 ``gate_included`` 采样：False / 网格外 → 对应门点置为掩膜。
    与 meteva 网格 ``apply_meteva_gate_mask``、``apply_cr_dataset_gate_mask`` 使用同一掩膜。

    说明：与 ``pyart.filters.GateFilter`` 按阈值逐场过滤不同，此处是**把 CREF 网格上
    已算好的 2D 掩膜**映射到门点，以保证与插件/meteva 路径**逐格一致**。
    若仅需在雷达原生场上做类似阈值 QC，可用 :func:`build_pyart_gatefilter_from_cref_qc_rules`。

    返回
    ----
    np.ndarray
        与 ``radar.gate_longitude`` 同形的 ``gate_excluded``（供可选传入 Py-ART 算法）。
    """
    gate_lon = np.asarray(radar.gate_longitude["data"], dtype=np.float64)
    gate_lat = np.asarray(radar.gate_latitude["data"], dtype=np.float64)
    gate_shape = gate_lat.shape

    if field_names is None:
        field_names = [name for name in _DEFAULT_RADAR_MASK_FIELDS if name in radar.fields]
    if not field_names:
        raise ValueError("no radar fields selected for lat/lon QC mask")

    for fname in field_names:
        if fname not in radar.fields:
            continue
        data = radar.fields[fname]["data"]
        exclude = gate_excluded_from_latlon_qc_mask(
            gate_lat,
            gate_lon,
            gate_included,
            lon_1d,
            lat_1d,
            data.shape,
            method=method,
        )
        if not isinstance(data, np.ma.MaskedArray):
            data = np.ma.asarray(data)
        else:
            data = data.copy()
        data.mask = np.logical_or(np.asarray(data.mask), exclude)
        radar.fields[fname]["data"] = data

    return gate_excluded_from_latlon_qc_mask(
        gate_lat,
        gate_lon,
        gate_included,
        lon_1d,
        lat_1d,
        gate_shape,
        method=method,
    )


def build_pyart_gatefilter_from_cref_qc_rules(
    radar,
    *,
    min_refl_dbz: float = 15.0,
    min_rho: float = 0.85,
    max_dbz: float = 80.0,
    refl_field: str = "reflectivity",
    rho_field: str = "cross_correlation_ratio",
):
    """用与 CREF QC 相近的**门点阈值规则**构造 Py-ART ``GateFilter``（非网格掩膜复刻）。

    各场射线数不一致时仍按门点坐标过滤；与 :func:`apply_latlon_mask_to_pyart_radar`
    使用的 ``gate_included`` 网格掩膜**不必逐门相同**（尤其 composite 与 quick_cr 路径）。
    """
    import pyart

    gatefilter = pyart.filters.GateFilter(radar)
    gatefilter.exclude_transition()
    if refl_field in radar.fields:
        gatefilter.exclude_invalid(refl_field)
        gatefilter.exclude_outside(refl_field, 0.0, max_dbz)
        gatefilter.exclude_below(refl_field, min_refl_dbz)
    if rho_field in radar.fields and min_rho is not None:
        gatefilter.exclude_invalid(rho_field)
        gatefilter.exclude_below(rho_field, min_rho)
    return gatefilter


def cinrad_cr_to_meteva_grid(
    cr_ds,
    field_name: str = "composite_reflectivity",
    member: str | None = None,
    time=None,
    dtime: int = 0,
    level: float = 0.0,
    cinrad_file=None,
):
    """``quick_cr`` 的 Dataset → meteva ``grid_data``。"""
    data = np.asarray(cr_ds["CR"].values, dtype=np.float32)
    lat = np.asarray(cr_ds["latitude"].values, dtype=np.float64)
    lon = np.asarray(cr_ds["longitude"].values, dtype=np.float64)
    if lat.ndim != 1 or lon.ndim != 1:
        raise ValueError("quick_cr 需要 1D latitude/longitude 坐标")
    dlon = float(lon[1] - lon[0]) if len(lon) > 1 else 0.01
    dlat = float(lat[1] - lat[0]) if len(lat) > 1 else 0.01
    if time is None:
        time = pd.to_datetime(cr_ds.attrs.get("scan_time"))
    elif isinstance(time, str):
        time = pd.to_datetime(time)
    member = member or str(cr_ds.attrs.get("site_code", "RADAR"))
    grid = meb.grid(
        [float(lon.min()), float(lon.max()), dlon],
        [float(lat.min()), float(lat.max()), dlat],
        gtime=time,
        dtime_list=[int(dtime)],
        level_list=[float(level)],
        member_list=[member],
    )
    gdata = meb.grid_data(grid, data)
    gdata.name = field_name
    gdata.attrs["units"] = "dBZ"
    gdata.attrs["var_name"] = field_name
    gdata.attrs["data_name"] = member
    for key in (
        "site_code",
        "site_name",
        "site_longitude",
        "site_latitude",
        "scan_time",
        "elevation",
        "frequency",
        "frequency_units",
        "band",
    ):
        if key in cr_ds.attrs:
            gdata.attrs[key] = cr_ds.attrs[key]
    if cinrad_file is not None:
        _apply_cinrad_grid_attrs(gdata, cinrad_file)
    return gdata


def sample_latlon_field_at_gates(
    field_2d,
    lat_1d,
    lon_1d,
    gate_lat,
    gate_lon,
    *,
    method: str = "nearest",
):
    """在规则经纬度网格上对雷达门点坐标采样（与 qpe notebook 一致）。"""
    from scipy.interpolate import RegularGridInterpolator

    values = np.asarray(field_2d, dtype=np.float64)
    lat_axis = np.asarray(lat_1d, dtype=np.float64)
    lon_axis = np.asarray(lon_1d, dtype=np.float64)
    if lat_axis.size > 1 and lat_axis[0] > lat_axis[-1]:
        lat_axis = lat_axis[::-1]
        values = values[::-1, :]
    if lon_axis.size > 1 and lon_axis[0] > lon_axis[-1]:
        lon_axis = lon_axis[::-1]
        values = values[:, ::-1]
    interp = RegularGridInterpolator(
        (lat_axis, lon_axis),
        values,
        method=method,
        bounds_error=False,
        fill_value=np.nan,
    )
    sample_points = np.column_stack(
        [np.asarray(gate_lat, dtype=np.float64).ravel(), np.asarray(gate_lon, dtype=np.float64).ravel()]
    )
    return interp(sample_points).reshape(np.asarray(gate_lat).shape).astype(np.float32)


def fill_pyart_radar_from_quick_cr(
    cr_ds,
    radar,
    field_name: str = "composite_reflectivity",
    sweep_index: int = 0,
    *,
    method: str = "nearest",
):
    """用 ``quick_cr`` 的 CR(dBZ) 覆盖 Py-ART ``Radar`` 指定场（保持门点几何不变）。

    仅替换反射率数值，不转回极坐标；原算法 ``est_rain_rate_*`` 仍在门点经纬度上
    使用与插件相同的 cinrad 组合反射率输入。
    """
    if field_name not in radar.fields:
        raise KeyError(f"radar has no field {field_name!r}")

    sweep_index = int(sweep_index)
    start = int(radar.sweep_start_ray_index["data"][sweep_index])
    end = int(radar.sweep_end_ray_index["data"][sweep_index])
    sweep_slice = slice(start, end + 1)

    gate_lon = np.asarray(radar.gate_longitude["data"], dtype=np.float64)
    gate_lat = np.asarray(radar.gate_latitude["data"], dtype=np.float64)
    if gate_lon.ndim > 1:
        gate_lon = gate_lon[sweep_slice]
        gate_lat = gate_lat[sweep_slice]

    cr = np.asarray(cr_ds["CR"].values, dtype=np.float64)
    lat = np.asarray(cr_ds["latitude"].values, dtype=np.float64)
    lon = np.asarray(cr_ds["longitude"].values, dtype=np.float64)
    dbz = sample_latlon_field_at_gates(
        cr, lat, lon, gate_lat, gate_lon, method=method,
    )

    field = radar.fields[field_name]
    target = field["data"][sweep_slice]
    dbz_2d = np.asarray(dbz, dtype=target.dtype).reshape(target.shape)
    field["data"][sweep_slice] = np.ma.masked_invalid(dbz_2d)
    return radar


def gate_reflectivity_matches_masked_cr(
    radar,
    cr_ds,
    field_name: str = "composite_reflectivity",
    sweep_index: int = 0,
    *,
    atol_dbz: float = 0.05,
) -> dict:
    """对比门点反射率与掩膜后 CR 网格采样是否一致（调试用）。

    返回 valid 门点的 max/mean abs diff 等统计。
    """
    sweep_index = int(sweep_index)
    start = int(radar.sweep_start_ray_index["data"][sweep_index])
    end = int(radar.sweep_end_ray_index["data"][sweep_index])
    sweep_slice = slice(start, end + 1)

    gate_lon = np.asarray(radar.gate_longitude["data"], dtype=np.float64)
    gate_lat = np.asarray(radar.gate_latitude["data"], dtype=np.float64)
    if gate_lon.ndim > 1:
        gate_lon = gate_lon[sweep_slice]
        gate_lat = gate_lat[sweep_slice]

    cr = np.asarray(cr_ds["CR"].values, dtype=np.float64)
    lat = np.asarray(cr_ds["latitude"].values, dtype=np.float64)
    lon = np.asarray(cr_ds["longitude"].values, dtype=np.float64)
    cr_at_gates = sample_latlon_field_at_gates(cr, lat, lon, gate_lat, gate_lon)

    radar_dbz = np.ma.filled(
        np.ma.asarray(radar.fields[field_name]["data"][sweep_slice], dtype=np.float64),
        np.nan,
    )
    valid = np.isfinite(cr_at_gates) & np.isfinite(radar_dbz)
    if not np.any(valid):
        return {"n_valid": 0}
    diff = np.abs(np.ma.filled(radar_dbz, np.nan) - cr_at_gates)
    diff_valid = diff[valid]
    return {
        "n_valid": int(valid.sum()),
        "max_abs_diff": float(np.nanmax(diff_valid)),
        "mean_abs_diff": float(np.nanmean(diff_valid)),
        "within_atol": bool(np.nanmax(diff_valid) <= atol_dbz),
    }


def meteva_grid_plot_arrays(meteva_grid):
    """从 meteva 网格得到 ``build_latlon_plot_arrays`` 兼容的 lon/lat 与二维场。"""
    lon = np.asarray(meteva_grid.coords["lon"].values, dtype=np.float64)
    lat = np.asarray(meteva_grid.coords["lat"].values, dtype=np.float64)
    lon_2d, lat_2d = np.meshgrid(lon, lat)
    data_2d = np.asarray(meteva_grid.values, dtype=np.float32).squeeze()
    return data_2d, lon_2d, lat_2d, lon, lat
