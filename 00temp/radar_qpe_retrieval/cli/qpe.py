#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""QPE 插件命令行入口。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import xarray as xr


def _load_qpe_cli():
    from . import _read_griddata, _write_griddata_to_nc
    from ..src import qpe as qpe_src

    return _read_griddata, _write_griddata_to_nc, qpe_src


def _as_float32_dataarray(result: xr.DataArray) -> xr.DataArray:
    """确保 CLI 返回 float32 降水率网格。"""
    if not isinstance(result, xr.DataArray):
        raise TypeError("QPE plugin process() must return xarray.DataArray")
    if (
        not np.issubdtype(result.values.dtype, np.floating)
        or result.values.dtype != np.float32
    ):
        result = result.astype(np.float32, copy=False)
    return result


def _maybe_write(result: xr.DataArray, output_path: Optional[str]) -> xr.DataArray:
    if output_path is not None:
        _, _write_griddata_to_nc, _ = _load_qpe_cli()
        _write_griddata_to_nc(result, output_path)
    return result


def est_rain_rate_z(
    refl_path: str,
    *,
    alpha: float = 0.0376,
    beta: float = 0.6112,
    rr_field: str = None,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """反射率 Z-R 降水率估算（``EstimateRainRateZ`` / ``est_rain_rate_z``）。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    refl = _read_griddata(refl_path)
    plugin = qpe_src.EstimateRainRateZ(alpha=alpha, beta=beta, rr_field=rr_field)
    return _maybe_write(_as_float32_dataarray(plugin.process(refl)), output_path)


def est_rain_rate_zpoly(
    refl_path: str,
    *,
    rr_field: str = None,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """反射率多项式降水率估算（``EstimateRainRateZPoly`` / ``est_rain_rate_zpoly``）。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    refl = _read_griddata(refl_path)
    plugin = qpe_src.EstimateRainRateZPoly(rr_field=rr_field)
    return _maybe_write(_as_float32_dataarray(plugin.process(refl)), output_path)


def est_rain_rate_kdp(
    kdp_path: str,
    *,
    alpha: float = None,
    beta: float = None,
    rr_field: str = None,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """KDP 降水率估算（``EstimateRainRateKdp`` / ``est_rain_rate_kdp``）。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    kdp = _read_griddata(kdp_path)
    plugin = qpe_src.EstimateRainRateKdp(alpha=alpha, beta=beta, rr_field=rr_field)
    return _maybe_write(_as_float32_dataarray(plugin.process(kdp)), output_path)


def est_rain_rate_a(
    att_path: str,
    *,
    alpha: float = None,
    beta: float = None,
    rr_field: str = None,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """比衰减降水率估算（``EstimateRainRateA`` / ``est_rain_rate_a``）。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    att = _read_griddata(att_path)
    plugin = qpe_src.EstimateRainRateA(alpha=alpha, beta=beta, rr_field=rr_field)
    return _maybe_write(_as_float32_dataarray(plugin.process(att)), output_path)


def est_rain_rate_zkdp(
    refl_path: str,
    kdp_path: str,
    *,
    alphaz: float = 0.0376,
    betaz: float = 0.6112,
    alphakdp: float = None,
    betakdp: float = None,
    rr_field: str = None,
    main_field: str = None,
    thresh: float = None,
    thresh_max: bool = True,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """反射率 + KDP 融合降水率估算（``EstimateRainRateZKdp`` / ``est_rain_rate_zkdp``）。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    refl = _read_griddata(refl_path)
    kdp = _read_griddata(kdp_path)
    plugin = qpe_src.EstimateRainRateZKdp(
        alphaz=alphaz,
        betaz=betaz,
        alphakdp=alphakdp,
        betakdp=betakdp,
        rr_field=rr_field,
        main_field=main_field,
        thresh=thresh,
        thresh_max=thresh_max,
    )
    return _maybe_write(_as_float32_dataarray(plugin.process(refl, kdp)), output_path)


def est_rain_rate_za(
    refl_path: str,
    att_path: str,
    *,
    alphaz: float = 0.0376,
    betaz: float = 0.6112,
    alphaa: float = None,
    betaa: float = None,
    rr_field: str = None,
    main_field: str = None,
    thresh: float = None,
    thresh_max: bool = False,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """反射率 + 比衰减融合降水率估算（``EstimateRainRateZA`` / ``est_rain_rate_za``）。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    refl = _read_griddata(refl_path)
    att = _read_griddata(att_path)
    plugin = qpe_src.EstimateRainRateZA(
        alphaz=alphaz,
        betaz=betaz,
        alphaa=alphaa,
        betaa=betaa,
        rr_field=rr_field,
        main_field=main_field,
        thresh=thresh,
        thresh_max=thresh_max,
    )
    return _maybe_write(_as_float32_dataarray(plugin.process(refl, att)), output_path)


def est_rain_rate_hydro(
    refl_path: str,
    att_path: str,
    hydro_path: str,
    *,
    alphazr: float = 0.0376,
    betazr: float = 0.6112,
    alphazs: float = 0.1,
    betazs: float = 0.5,
    alphaa: float = None,
    betaa: float = None,
    rr_field: str = None,
    mp_factor: float = 0.6,
    main_field: str = None,
    thresh: float = None,
    thresh_max: bool = False,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """水凝物分类降水率估算（``EstimateRainRateHydro`` / ``est_rain_rate_hydro``）。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    refl = _read_griddata(refl_path)
    att = _read_griddata(att_path)
    hydro = _read_griddata(hydro_path)
    plugin = qpe_src.EstimateRainRateHydro(
        alphazr=alphazr,
        betazr=betazr,
        alphazs=alphazs,
        betazs=betazs,
        alphaa=alphaa,
        betaa=betaa,
        rr_field=rr_field,
        mp_factor=mp_factor,
        main_field=main_field,
        thresh=thresh,
        thresh_max=thresh_max,
    )
    return _maybe_write(
        _as_float32_dataarray(plugin.process(refl, att, hydro)),
        output_path,
    )


def ztor(
    refl_path: str,
    *,
    a: float = 300.0,
    b: float = 1.4,
    save_name: str = "NWS_primary_prate",
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """经典 Z = aR^b 降水率转换（``EstimateZtoR`` / ``ZtoR``）。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    refl = _read_griddata(refl_path)
    plugin = qpe_src.EstimateZtoR(a=a, b=b, save_name=save_name)
    return _maybe_write(_as_float32_dataarray(plugin.process(refl)), output_path)


def qpeplugin(
    method: str,
    *,
    refl_path: str = None,
    kdp_path: str = None,
    att_path: str = None,
    hydro_path: str = None,
    z_alpha: float = 0.0376,
    z_beta: float = 0.6112,
    kdp_alpha: float = None,
    kdp_beta: float = None,
    a_alpha: float = None,
    a_beta: float = None,
    snow_alpha: float = 0.1,
    snow_beta: float = 0.5,
    ztor_a: float = 300.0,
    ztor_b: float = 1.4,
    rr_field: str = None,
    main_field: str = None,
    thresh: float = None,
    thresh_max: bool = None,
    mp_factor: float = 0.6,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """QPE 统一入口（``QPEPlugin``），通过 ``method`` 选择算法。"""
    _read_griddata, _, qpe_src = _load_qpe_cli()
    refl = _read_griddata(refl_path) if refl_path is not None else None
    kdp = _read_griddata(kdp_path) if kdp_path is not None else None
    att = _read_griddata(att_path) if att_path is not None else None
    hydro = _read_griddata(hydro_path) if hydro_path is not None else None
    plugin = qpe_src.QPEPlugin(
        method=method,
        z_alpha=z_alpha,
        z_beta=z_beta,
        kdp_alpha=kdp_alpha,
        kdp_beta=kdp_beta,
        a_alpha=a_alpha,
        a_beta=a_beta,
        snow_alpha=snow_alpha,
        snow_beta=snow_beta,
        ztor_a=ztor_a,
        ztor_b=ztor_b,
        rr_field=rr_field,
        main_field=main_field,
        thresh=thresh,
        thresh_max=thresh_max,
        mp_factor=mp_factor,
    )
    return _maybe_write(
        _as_float32_dataarray(
            plugin.process(
                refl=refl,
                kdp=kdp,
                att=att,
                hydro=hydro,
            )
        ),
        output_path,
    )


if __name__ == "__main__":
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    data_dir = Path(__file__).resolve().parents[1] / "test_data" / "qpe" / "input"
    refl_path = str(data_dir / "ACHN_CREF000_20240612_070000.nc")
    output_path = str(
        Path(__file__).resolve().parents[1]
        / "test_data"
        / "qpe"
        / "cli_output"
        / "est_rain_rate_z_cli_run.nc"
    )

    from pyart.retrieve.cli.qpe import est_rain_rate_z as run_est_rain_rate_z

    run_est_rain_rate_z(refl_path, output_path=output_path)
