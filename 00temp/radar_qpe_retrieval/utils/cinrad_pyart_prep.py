"""cinrad StandardData → Py-ART Radar 预处理（sweep 修正、方位去重）。"""

from __future__ import annotations

import numpy as np

from .cinrad_meb import cinrad_frequency_hz


def _reinit_ray_geometry(radar):
    """Reset lazy gate geometry after ray/sweep layout changes."""
    radar.nrays = len(radar.azimuth["data"])
    radar.init_rays_per_sweep()
    radar.init_gate_x_y_z()
    radar.init_gate_longitude_latitude()
    radar.init_gate_altitude()


def _sync_sweep_metadata(radar, tilt_indices=None):
    """使 sweep 维元数据长度与 ``radar.nsweeps`` 一致（write_cfradial 需要）。"""
    n = radar.nsweeps
    if tilt_indices is not None:
        sel = np.asarray(list(tilt_indices), dtype=int)
    else:
        sel = np.arange(n)

    def _subset(dic):
        data = np.asarray(dic["data"])
        if data.shape[0] == n:
            return
        dic["data"] = data[sel]

    if radar.sweep_mode is not None:
        _subset(radar.sweep_mode)
    if radar.target_scan_rate is not None:
        _subset(radar.target_scan_rate)
    if radar.antenna_transition is not None:
        _subset(radar.antenna_transition)
    if radar.instrument_parameters:
        for key in ("nyquist_velocity", "unambiguous_range"):
            if key in radar.instrument_parameters:
                _subset(radar.instrument_parameters[key])


def _sync_time_length(radar):
    t = np.asarray(radar.time["data"])
    n = len(radar.azimuth["data"])
    if len(t) == n:
        return
    if len(t) > n:
        radar.time["data"] = t[:n]
    else:
        radar.time["data"] = np.pad(t, (0, n - len(t)), mode="edge")


def _attach_radar_frequency(radar, cinrad_file):
    """确保 Py-ART ``Radar`` 带有 ``instrument_parameters['frequency']``（Hz）。

    ``standard_data_to_pyart`` 生成的对象在某些 cinrad 数据上可能没有频率字段；
    迁移后的 meteva 链路会从 ``attrs['frequency']`` 自动选默认系数。为避免
    原算法链和插件/CLI 链因默认频段系数不同而偏离，这里统一从 cinrad 文件
    回填频率到 Py-ART ``Radar``。
    """
    freq_hz = cinrad_frequency_hz(cinrad_file)
    if freq_hz is None or not np.isfinite(freq_hz):
        return radar

    if radar.instrument_parameters is None:
        radar.instrument_parameters = {}

    existing = radar.instrument_parameters.get("frequency")
    if existing is not None:
        try:
            existing_data = np.asarray(existing.get("data"), dtype=np.float64).ravel()
        except Exception:
            existing_data = np.array([], dtype=np.float64)
        if existing_data.size and np.isfinite(existing_data[0]):
            return radar

    radar.instrument_parameters["frequency"] = {
        "data": np.array([freq_hz], dtype=np.float32),
        "units": "Hz",
        "long_name": "radar transmit frequency",
    }
    return radar


def repair_cinrad_pyart_sweep_indices(cinrad_file, radar, *, radius: int = 460):
    """修正 ``standard_data_to_pyart`` 的 sweep 索引，使其与 REF 各仰角射线数一致。"""
    tilts = list(cinrad_file.available_tilt("REF"))
    if not tilts:
        raise ValueError("cinrad 文件中没有 REF 仰角层")

    starts, ends = [], []
    offset = 0
    for nel in tilts:
        raw = cinrad_file.get_raw(nel, radius, "REF")
        arr = raw[0] if isinstance(raw, tuple) else raw
        n_ray = int(np.asarray(arr).shape[0])
        starts.append(offset)
        ends.append(offset + n_ray - 1)
        offset += n_ray

    radar.nsweeps = len(tilts)
    radar.sweep_start_ray_index["data"] = np.array(starts, dtype="int32")
    radar.sweep_end_ray_index["data"] = np.array(ends, dtype="int32")
    radar.sweep_number["data"] = np.arange(len(tilts), dtype="int32")
    radar.fixed_angle["data"] = np.array(
        [cinrad_file.el[nel] for nel in tilts], dtype="float32"
    )
    radar.azimuth["data"] = np.hstack(
        [cinrad_file.aux[nel]["azimuth"] for nel in tilts]
    )
    radar.elevation["data"] = np.hstack(
        [cinrad_file.aux[nel]["elevation"] for nel in tilts]
    )
    _sync_time_length(radar)
    _sync_sweep_metadata(radar, tilts)
    _reinit_ray_geometry(radar)
    return radar


def dedupe_sweep_azimuths(radar, *, atol: float = 1e-6):
    """按 sweep 去除重复方位角，满足 ``composite_reflectivity`` 对严格递增 az 的要求。"""
    field_names = [
        k
        for k, v in radar.fields.items()
        if v["data"].ndim >= 1 and v["data"].shape[0] == radar.nrays
    ]

    new_starts, new_ends, fixed_angles = [], [], []
    az_chunks, el_chunks, t_chunks = [], [], []
    f_chunks = {k: [] for k in field_names}
    offset = 0

    for sw in range(radar.nsweeps):
        s = int(radar.sweep_start_ray_index["data"][sw])
        e = int(radar.sweep_end_ray_index["data"][sw])
        sl = slice(s, e + 1)
        az = np.asarray(radar.azimuth["data"][sl], dtype=float)
        n_eff = len(az)
        if "reflectivity" in radar.fields:
            n_eff = min(n_eff, int(radar.fields["reflectivity"]["data"][sl].shape[0]))
        if n_eff == 0:
            continue

        az = az[:n_eff]
        order = np.argsort(az, kind="mergesort")
        az_sorted = az[order]
        keep = np.ones(n_eff, dtype=bool)
        if n_eff > 1:
            keep[1:] = np.diff(az_sorted) > atol
        idx = order[keep]
        n = len(idx)

        new_starts.append(offset)
        new_ends.append(offset + n - 1)
        fixed_angles.append(float(radar.fixed_angle["data"][sw]))
        offset += n

        az_chunks.append(radar.azimuth["data"][sl][:n_eff][idx])
        el_chunks.append(radar.elevation["data"][sl][:n_eff][idx])
        t_chunks.append(radar.time["data"][sl][:n_eff][idx])
        for k in field_names:
            chunk = radar.fields[k]["data"][sl][:n_eff][idx]
            if not isinstance(chunk, np.ma.MaskedArray):
                chunk = np.ma.asarray(chunk)
            f_chunks[k].append(chunk)

    radar.nsweeps = len(new_starts)
    radar.sweep_start_ray_index["data"] = np.array(new_starts, dtype="int32")
    radar.sweep_end_ray_index["data"] = np.array(new_ends, dtype="int32")
    radar.sweep_number["data"] = np.arange(len(new_starts), dtype="int32")
    radar.fixed_angle["data"] = np.array(fixed_angles, dtype="float32")
    radar.azimuth["data"] = np.hstack(az_chunks)
    radar.elevation["data"] = np.hstack(el_chunks)
    radar.time["data"] = np.hstack(t_chunks)
    for k in field_names:
        radar.fields[k]["data"] = np.ma.vstack(f_chunks[k])

    _sync_sweep_metadata(radar)
    _reinit_ray_geometry(radar)
    return radar


def needs_cinrad_sweep_repair(cinrad_file, radar) -> bool:
    tilts = list(cinrad_file.available_tilt("REF"))
    if len(tilts) != radar.nsweeps:
        return True
    if int(radar.fields["reflectivity"]["data"].shape[0]) != radar.nrays:
        return True
    for sw in range(radar.nsweeps):
        sl = slice(
            int(radar.sweep_start_ray_index["data"][sw]),
            int(radar.sweep_end_ray_index["data"][sw]) + 1,
        )
        z = radar.fields["reflectivity"]["data"][sl]
        az = radar.azimuth["data"][sl]
        if z.shape[0] != len(az):
            return True
    return False


def prepare_radar_for_composite_reflectivity(
    radar, cinrad_file=None, *, radius: int = 460, dedupe: bool = True
):
    """修正 sweep（若需要）并去重方位角，再调用 ``composite_reflectivity``。"""
    if cinrad_file is not None and needs_cinrad_sweep_repair(cinrad_file, radar):
        repair_cinrad_pyart_sweep_indices(cinrad_file, radar, radius=radius)
    if dedupe:
        dedupe_sweep_azimuths(radar)
    return radar


def load_cinrad_pyart_radar(path, *, radius: int = 460, prepare: bool = True, dedupe: bool = True):
    """从 cinrad 基数据读取并转为已预处理的 Py-ART ``Radar``。"""
    import cinrad
    from cinrad.io.export import standard_data_to_pyart

    cinrad_file = cinrad.io.StandardData(str(path))
    radar = standard_data_to_pyart(cinrad_file, radius=radius)
    if prepare:
        radar = prepare_radar_for_composite_reflectivity(
            radar, cinrad_file=cinrad_file, radius=radius, dedupe=dedupe
        )
    radar = _attach_radar_frequency(radar, cinrad_file)
    return cinrad_file, radar
