#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""Shared helpers for region-based velocity dealiasing."""

from __future__ import annotations

import numpy as np
import xarray as xr

from ..utils.utils import check_for_meb_griddata, check_for_xy_coordinates
from .grid_gate_filter import GridGateFilter, _as_2d_array


def _parse_nyquist_vel(nyquist_velocity, velocity):
    """Parse nyquist velocity as a scalar or one value per 4D context."""
    slice_shape = velocity.shape[:4]

    if nyquist_velocity is not None:
        nyquist_array = np.asarray(nyquist_velocity, dtype=np.float32)
        if nyquist_array.ndim == 0:
            return np.full(slice_shape, float(nyquist_array), dtype=np.float32)
        if nyquist_array.shape == slice_shape:
            return nyquist_array.astype(np.float32, copy=False)
        if nyquist_array.size == int(np.prod(slice_shape)):
            return nyquist_array.astype(np.float32, copy=False).reshape(slice_shape)
        raise ValueError(
            "nyquist_velocity must be a scalar or match the member/level/time/dtime shape"
        )

    for key in ("nyquist_velocity", "nyquist_vel"):
        if key in velocity.attrs:
            attr_array = np.asarray(velocity.attrs[key], dtype=np.float32)
            if attr_array.ndim == 0:
                return np.full(slice_shape, float(attr_array), dtype=np.float32)
            if attr_array.shape == slice_shape:
                return attr_array.astype(np.float32, copy=False)
            if attr_array.size == int(np.prod(slice_shape)):
                return attr_array.astype(np.float32, copy=False).reshape(slice_shape)
            raise ValueError(
                f"{key} in attrs must be a scalar or match the member/level/time/dtime shape"
            )

    raise ValueError("nyquist_velocity is required when input attrs do not provide it")


def _parse_gatefilter(
    gatefilter,
    velocity,
    refl=None,
    ncp=None,
    rhv=None,
    min_ncp=0.5,
    min_rhv=None,
    min_refl=-20.0,
    max_refl=100.0,
):
    """Resolve the gatefilter argument into a GridGateFilter."""
    if gatefilter is None:
        return _moment_based_gatefilter(
            velocity,
            refl=refl,
            ncp=ncp,
            rhv=rhv,
            min_ncp=min_ncp,
            min_rhv=min_rhv,
            min_refl=min_refl,
            max_refl=max_refl,
        )
    if gatefilter is False:
        return GridGateFilter(velocity)
    if isinstance(gatefilter, GridGateFilter):
        return gatefilter.copy()
    raise TypeError("gatefilter must be None, False, or GridGateFilter")


def _moment_based_gatefilter(
    velocity: xr.DataArray,
    refl: xr.DataArray | None = None,
    ncp: xr.DataArray | None = None,
    rhv: xr.DataArray | None = None,
    min_ncp: float | None = 0.5,
    min_rhv: float | None = None,
    min_refl: float | None = -20.0,
    max_refl: float | None = 100.0,
):
    """Build a GridGateFilter using the main Py-ART moment filtering rules."""
    gatefilter = GridGateFilter(velocity)

    if (min_ncp is not None) and (ncp is not None):
        ncp_grid = check_for_meb_griddata(ncp, is_single=True)
        if not check_for_xy_coordinates([velocity, ncp_grid]):
            raise ValueError("velocity and ncp grid coordinates must be same")
        gatefilter.exclude_below(ncp_grid, min_ncp)
        gatefilter.exclude_masked(ncp_grid)
        gatefilter.exclude_invalid(ncp_grid)

    if (min_rhv is not None) and (rhv is not None):
        rhv_grid = check_for_meb_griddata(rhv, is_single=True)
        if not check_for_xy_coordinates([velocity, rhv_grid]):
            raise ValueError("velocity and rhv grid coordinates must be same")
        gatefilter.exclude_below(rhv_grid, min_rhv)
        gatefilter.exclude_masked(rhv_grid)
        gatefilter.exclude_invalid(rhv_grid)

    if refl is not None and (min_refl is not None or max_refl is not None):
        refl_grid = check_for_meb_griddata(refl, is_single=True)
        if not check_for_xy_coordinates([velocity, refl_grid]):
            raise ValueError("velocity and refl grid coordinates must be same")
        gatefilter.exclude_outside(refl_grid, min_refl, max_refl)
        gatefilter.exclude_masked(refl_grid)
        gatefilter.exclude_invalid(refl_grid)

    return gatefilter


def _parse_rays_wrap_around(rays_wrap_around, velocity):
    """Parse whether the first and last ray should be connected."""
    if rays_wrap_around is not None:
        return bool(rays_wrap_around)

    scan_type = str(velocity.attrs.get("scan_type", "")).strip().lower()
    sweep_mode = str(velocity.attrs.get("sweep_mode", "")).strip().lower()

    if scan_type == "ppi" or "ppi" in sweep_mode:
        return True

    if scan_type in {"rhi", "vpt", "other"}:
        return False

    return False


def _set_limits(data, nyquist_vel, attrs):
    """Set output valid_min/valid_max according to dealiasing result."""
    max_abs_vel = np.ma.max(np.ma.abs(data))
    if max_abs_vel is np.ma.masked:
        return

    max_nyq_vel = np.ma.max(nyquist_vel)
    max_nyq_int = 2.0 * max_nyq_vel
    added_intervals = np.ceil((max_abs_vel - max_nyq_vel) / max_nyq_int)
    max_valid_velocity = max_nyq_vel + added_intervals * max_nyq_int
    attrs["valid_min"] = float(-max_valid_velocity)
    attrs["valid_max"] = float(max_valid_velocity)
