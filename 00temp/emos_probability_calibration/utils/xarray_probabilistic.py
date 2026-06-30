"""Probabilistic metadata helpers for xarray (no iris)."""

from __future__ import annotations

import re
from typing import Match, Optional, Union

import xarray as xr

from utils.xarray_core import CoordinateNotFoundError, as_dataarray, get_diagnostic_name


def probability_cube_name_regex(cube_name: str) -> Optional[Match]:
    regex = re.compile(
        "(probability_of_)"
        "(?P<diag>.*?)"
        "(?P<vicinity>_in_vicinity|_in_variable_vicinity)?"
        "(?P<thresh>_above_threshold|_below_threshold|_between_thresholds|$)"
    )
    return regex.match(cube_name)


def find_percentile_coordinate(da: xr.DataArray) -> str:
    """Return name of percentile coordinate."""
    da = as_dataarray(da)
    name = get_diagnostic_name(da)
    found = []
    for c in da.coords:
        if "percentile" in c:
            found.append(c)
    if not found:
        raise CoordinateNotFoundError(f"No percentile coord found on {name} data")
    if len(found) > 1:
        raise ValueError(f"Too many percentile coords found on {name} data")
    return found[0]


def find_threshold_coordinate(da: xr.DataArray) -> str:
    """Return name of threshold coordinate."""
    da = as_dataarray(da)
    name = get_diagnostic_name(da)
    if "threshold" in da.coords:
        return "threshold"
    for c in da.coords:
        if da[c].attrs.get("var_name") == "threshold":
            return c
    raise CoordinateNotFoundError(f"No threshold coord found on {name} data")


def get_threshold_coord_name_from_probability_name(cube_name: str) -> str:
    regex = probability_cube_name_regex(cube_name)
    return regex.groupdict()["diag"]


def get_diagnostic_cube_name_from_probability_name(cube_name: str) -> str:
    regex = probability_cube_name_regex(cube_name)
    gd = regex.groupdict()
    diag = gd["diag"]
    if gd.get("vicinity"):
        diag += gd["vicinity"]
    return diag


def probability_is_above_or_below(da: xr.DataArray) -> str:
    da = as_dataarray(da)
    thresh = find_threshold_coordinate(da)
    relation = da[thresh].attrs.get("spp__relative_to_threshold")
    if relation in ("above", "below"):
        return relation
    name = get_diagnostic_name(da)
    if "_above_threshold" in name:
        return "above"
    if "_below_threshold" in name:
        return "below"
    raise NotImplementedError(
        f"Cannot determine threshold relation for {name}"
    )


def get_forecast_type(forecast: Union[xr.DataArray, xr.Dataset]) -> str:
    """Return 'probabilities', 'percentiles', or 'realizations'."""
    da = as_dataarray(forecast)
    try:
        find_percentile_coordinate(da)
    except CoordinateNotFoundError:
        name = get_diagnostic_name(da)
        if name.startswith("probability_of"):
            return "probabilities"
        return "realizations"
    else:
        return "percentiles"
