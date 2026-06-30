#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""region_dealias 算法命令行入口。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from warnings import warn

import numpy as np
import xarray as xr


def process(
    velocity_path: str,
    *,
    ref_velocity_path: str = None,
    gatefilter_path: str = None,
    refl_path: str = None,
    ncp_path: str = None,
    rhv_path: str = None,
    interval_splits: int = 3,
    interval_limits: Sequence[float] | str = None,
    skip_between_rays: int = 100,
    skip_along_ray: int = 100,
    centered: bool = True,
    nyquist_velocity: float = None,
    min_ncp: float = 0.5,
    min_rhv: float = None,
    min_refl: float = -20.0,
    max_refl: float = 100.0,
    rays_wrap_around: bool = None,
    keep_original: bool = False,
    set_limits: bool = True,
    data_name: str = "corrected_velocity",
    radar_lon: float = None,
    radar_lat: float = None,
    elevation_deg: float = 0.0,
    geo_resolution_deg: float = 0.01,
    geo_nlon: int = None,
    geo_nlat: int = None,
    auto_remap_to_latlon: bool = False,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """执行基于区域连通关系的径向速度退模糊 CLI。"""
    from . import (
        _read_griddata,
        _read_npy_array,
        _write_griddata_to_nc,
        parse_comma_separated_list_of_float,
    )
    from ..src import GridGateFilter
    from ..src.region_dealias import RegionDealiasPlugin

    velocity = _read_griddata(velocity_path)
    ref_velocity = (
        _read_griddata(ref_velocity_path) if ref_velocity_path is not None else None
    )
    gatefilter = (
        _read_npy_array(gatefilter_path) if gatefilter_path is not None else None
    )
    refl = _read_griddata(refl_path) if refl_path is not None else None
    ncp = _read_griddata(ncp_path) if ncp_path is not None else None
    rhv = _read_griddata(rhv_path) if rhv_path is not None else None

    if interval_limits is not None and isinstance(interval_limits, str):
        interval_limits = parse_comma_separated_list_of_float(interval_limits)

    if gatefilter is False:
        gatefilter_arg = False
    elif gatefilter is not None:
        gatefilter_arg = GridGateFilter.from_mask(
            velocity,
            np.asarray(gatefilter, dtype=bool),
        )
    elif any(grid is not None for grid in (refl, ncp, rhv)):
        gatefilter_arg = None
    else:
        warn(
            "No gatefilter or moment fields were provided. "
            "An empty gatefilter will be used.",
            UserWarning,
            stacklevel=2,
        )
        gatefilter_arg = False

    plugin = RegionDealiasPlugin(
        interval_splits=interval_splits,
        interval_limits=interval_limits,
        skip_between_rays=skip_between_rays,
        skip_along_ray=skip_along_ray,
        centered=centered,
        nyquist_velocity=nyquist_velocity,
        gatefilter=gatefilter_arg,
        min_ncp=min_ncp,
        min_rhv=min_rhv,
        min_refl=min_refl,
        max_refl=max_refl,
        rays_wrap_around=rays_wrap_around,
        keep_original=keep_original,
        set_limits=set_limits,
        data_name=data_name,
        radar_lon=radar_lon,
        radar_lat=radar_lat,
        elevation_deg=elevation_deg,
        geo_resolution_deg=geo_resolution_deg,
        geo_nlon=geo_nlon,
        geo_nlat=geo_nlat,
        auto_remap_to_latlon=auto_remap_to_latlon,
    )

    result = plugin.process(
        velocity=velocity,
        ref_velocity=ref_velocity,
        refl=refl,
        ncp=ncp,
        rhv=rhv,
    )
    if not isinstance(result, xr.DataArray):
        raise TypeError("RegionDealiasPlugin.process() must return xarray.DataArray")

    if (
        not np.issubdtype(result.values.dtype, np.floating)
        or result.values.dtype != np.float32
    ):
        result = result.astype(np.float32, copy=False)

    if output_path is not None:
        _write_griddata_to_nc(result, output_path)

    return result


if __name__ == "__main__":
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from pyart.correct.cli.region_dealias import process as run_process

    data_dir = Path(__file__).resolve().parents[1] / "test_data" / "region_dealias" / "input"
    velocity_path = str(data_dir / "velocity_sweep0.nc")
    refl_path = str(data_dir / "reflectivity_sweep0.nc")
    ncp_path = str(data_dir / "ncp_sweep0.nc")
    rhv_path = str(data_dir / "rhv_sweep0.nc")
    output_path = str(
        Path(__file__).resolve().parents[1]
        / "test_data"
        / "region_dealias"
        / "cli_output"
        / "region_dealias_cli_run.nc"
    )

    run_process(
        velocity_path,
        refl_path=refl_path,
        ncp_path=ncp_path,
        rhv_path=rhv_path,
        output_path=output_path,
    )
