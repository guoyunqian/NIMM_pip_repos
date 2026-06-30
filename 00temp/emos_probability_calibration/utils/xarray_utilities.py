"""xarray utilities for Ensemble Copula Coupling (no iris)."""

from __future__ import annotations

import warnings
from typing import List, Optional, Union

import numpy as np
import xarray as xr
from numpy import ndarray

from utils.constants import BOUNDS_FOR_ECDF

ABSOLUTE_ZERO = 273.15


def concatenate_2d_array_with_2d_array_endpoints(
    array_2d: ndarray, low_endpoint: float, high_endpoint: float
) -> ndarray:
    if array_2d.ndim != 2:
        raise ValueError(f"Expected 2D input, got {array_2d.ndim}D input")
    lower_array = np.full((array_2d.shape[0], 1), low_endpoint, dtype=array_2d.dtype)
    upper_array = np.full((array_2d.shape[0], 1), high_endpoint, dtype=array_2d.dtype)
    return np.concatenate((lower_array, array_2d, upper_array), axis=1)


def choose_set_of_percentiles(no_of_percentiles: int, sampling: str = "quantile") -> List[float]:
    if sampling in ["quantile"]:
        percentiles = np.linspace(
            1 / float(1 + no_of_percentiles),
            no_of_percentiles / float(1 + no_of_percentiles),
            no_of_percentiles,
        ).tolist()
    elif sampling in ["random"]:
        percentiles = sorted(
            list(
                np.random.uniform(
                    1 / float(1 + no_of_percentiles),
                    no_of_percentiles / float(1 + no_of_percentiles),
                    no_of_percentiles,
                )
            )
        )
    else:
        raise ValueError(f"Unrecognised sampling option '{sampling}'")
    return [item * 100 for item in percentiles]


def create_dataarray_with_percentiles(
    percentiles: Union[List[float], ndarray],
    template: xr.DataArray,
    cube_data: ndarray,
    units: Optional[str] = None,
) -> xr.DataArray:
    """Build DataArray with leading percentile dimension."""
    template = template.drop_vars(
        [v for v in (template.name,) if v and v in template.coords],
        errors="ignore",
    )
    for d in ("realization", "percentile"):
        if d in template.dims:
            template = template.isel({d: 0}, drop=True)

    coords = dict(template.coords)
    dims = ["percentile"] + list(template.dims)
    coords["percentile"] = ("percentile", np.asarray(percentiles, dtype=np.float32))
    # print(percentiles)
    attrs = dict(template.attrs)
    if units:
        attrs["units"] = units
    da = xr.DataArray(
        cube_data.astype(np.float32),
        dims=dims,
        coords={k: v for k, v in coords.items() if k in dims},
        attrs=attrs,
        name=template.name or template.attrs.get("standard_name"),
    )
    for k, v in coords.items():
        if (k not in dims) and (getattr(v, "ndim", 0) == 0):
            da.coords[k] = v
    return da


def get_bounds_of_distribution(bounds_pairing_key: str, desired_units: str) -> ndarray:
    try:
        bounds_pairing = BOUNDS_FOR_ECDF[bounds_pairing_key].value
    except KeyError as err:
        raise KeyError(
            f"The bounds_pairing_key: {bounds_pairing_key} is not recognised "
            f"within BOUNDS_FOR_ECDF."
        ) from err
    # Without cf_units/pint: assume bounds already in desired diagnostic units.
    return np.array(bounds_pairing, dtype=np.float32)


def insert_lower_and_upper_endpoint_to_1d_array(
    array_1d: ndarray, low_endpoint: float, high_endpoint: float
) -> ndarray:
    if array_1d.ndim != 1:
        raise ValueError(f"Expected 1D input, got {array_1d.ndim}D input")
    array_1d = np.concatenate(([low_endpoint], array_1d, [high_endpoint]))
    if array_1d.dtype == np.float64:
        array_1d = array_1d.astype(np.float32)
    return array_1d


def restore_non_percentile_dimensions(
    array_to_reshape: ndarray, template: xr.DataArray, n_percentiles: int
) -> ndarray:
    shape = [n_percentiles] + [template.sizes[d] for d in template.dims] if n_percentiles > 1 else list(template.sizes[d] for d in template.dims)
    if n_percentiles <= 1:
        shape = list(template.sizes[d] for d in template.dims)
    else:
        shape = [n_percentiles] + [template.sizes[d] for d in template.dims]
    return array_to_reshape.reshape(shape)


def slow_interp_same_x(x: np.ndarray, xp: np.ndarray, fp: np.ndarray) -> np.ndarray:
    result = np.empty((fp.shape[0], len(x)), np.float32)
    for i in range(fp.shape[0]):
        result[i, :] = np.interp(x, xp, fp[i, :])
    return result


def interpolate_multiple_rows_same_x(*args):
    try:
        import numba  # noqa: F401
        from ensemble_copula_coupling.numba_utilities import fast_interp_same_x

        return fast_interp_same_x(*args)
    except ImportError:
        warnings.warn("Module numba unavailable. ResamplePercentiles will be slower.")
        return slow_interp_same_x(*args)


def slow_interp_same_y(x: np.ndarray, xp: np.ndarray, fp: np.ndarray) -> np.ndarray:
    result = np.empty((xp.shape[0], len(x)), dtype=np.float32)
    for i in range(xp.shape[0]):
        result[i] = np.interp(x, xp[i, :], fp)
    return result


def interpolate_multiple_rows_same_y(*args):
    try:
        import numba  # noqa: F401
        from ensemble_copula_coupling.numba_utilities import fast_interp_same_x as _  # noqa
        from ensemble_copula_coupling.numba_utilities import fast_interp_same_y

        return fast_interp_same_y(*args)
    except ImportError:
        warnings.warn(
            "Module numba unavailable. ConvertProbabilitiesToPercentiles will be slower."
        )
        return slow_interp_same_y(*args)


def choose(index_array: ndarray, array_set: ndarray) -> ndarray:
    """Reorder along leading dimension (from indexing_operations.choose)."""
    if index_array.shape != array_set.shape:
        raise ValueError(
            f"index_array shape {index_array.shape} != array_set shape {array_set.shape}"
        )
    if index_array.max() > array_set.shape[0] - 1:
        raise IndexError(
            f"index max {index_array.max()} exceeds sub-array count {array_set.shape[0]}"
        )
    result = np.array(
        [array_set[index_array[i]][i[1:]] for i in np.ndindex(index_array.shape)]
    ).reshape(index_array.shape)
    return result


def manipulate_n_realizations(da: xr.DataArray, n_realizations: int) -> xr.DataArray:
    if "realization" not in da.dims:
        raise ValueError("Input must contain a realization dimension")
    mpoints = da["realization"].values
    if len(mpoints) == n_realizations:
        return da.copy()
    realization_list = [mpoints[i % len(mpoints)] for i in range(n_realizations)]
    new_numbers = realization_list[0] + np.arange(n_realizations)
    slices = [da.sel(realization=r) for r in realization_list]
    out = xr.concat(slices, dim="realization")
    return out.assign_coords(realization=new_numbers.astype(np.int32))
