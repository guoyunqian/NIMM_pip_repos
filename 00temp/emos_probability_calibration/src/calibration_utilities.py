# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of 'IMPROVER' and is released under the BSD 3-Clause license.
# See LICENSE in the root of the repository for full licensing details.
"""
Utilities used by ensemble calibration plugins (xarray, spot-only).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple, Union

import numpy as np
import xarray as xr
from numpy import ndarray
from numpy.ma.core import MaskedArray

from utils.xarray_core import (
    SPOT_DIM,
    TIME_DIM,
    as_dataarray,
    collapsed,
    convert_data_to_2d,
    enforce_coordinate_ordering,
    get_frt_hours,
    is_spot_data,
    pd_timestamp_to_datetime,
)

# Backward-compatible alias used by emos_calibration imports
convert_cube_data_to_2d = convert_data_to_2d


def flatten_ignoring_masked_data(
    data_array: Union[MaskedArray, ndarray], preserve_leading_dimension: bool = False
) -> ndarray:
    if np.ma.is_masked(data_array):
        if data_array.ndim > 2:
            first_slice_mask = data_array[0].mask
            for i in range(1, data_array.shape[0]):
                if not np.all(first_slice_mask == data_array[i].mask):
                    raise ValueError(
                        "The mask on the input array is not the same for "
                        "every slice along the leading dimension."
                    )
        result = data_array[~data_array.mask]
    else:
        result = data_array.flatten()
    if preserve_leading_dimension:
        result = result.reshape((data_array.shape[0], -1))
    return result


def check_predictor(predictor: str) -> str:
    if predictor.lower() not in ["mean", "realizations"]:
        raise ValueError(
            f"The requested value for the predictor {predictor.lower()} is not an "
            "accepted value. Accepted values are 'mean' or 'realizations'"
        )
    return predictor.lower()


def _time_match_key(t) -> datetime:
    return pd_timestamp_to_datetime(t)


def filter_non_matching_cubes(
    historic_forecast: Union[xr.DataArray, xr.Dataset],
    truth: Union[xr.DataArray, xr.Dataset],
) -> Tuple[xr.DataArray, xr.DataArray]:
    """Align historic forecast and truth on matching validity times."""
    hf = as_dataarray(historic_forecast)
    tr = as_dataarray(truth)
    if TIME_DIM not in hf.dims:
        raise ValueError("historic_forecast must have a time dimension")

    hf_slices = []
    tr_slices = []
    truth_times = []

    for t in hf[TIME_DIM].values:
        t_key = _time_match_key(t)
        if TIME_DIM not in tr.dims:
            raise ValueError("truth must have a time dimension")
        if t not in tr[TIME_DIM].values and _time_match_key(t) not in [
            _time_match_key(v) for v in tr[TIME_DIM].values
        ]:
            continue
        tr_at_t = tr.sel({TIME_DIM: t}, drop=False)
        hf_at_t = hf.sel({TIME_DIM: t}, drop=False)
        if np.isnan(hf_at_t.values).all():
            continue
        if t_key in truth_times:
            continue
        truth_times.append(t_key)
        hf_slices.append(hf_at_t)
        tr_slices.append(tr_at_t)

    if not hf_slices:
        raise ValueError(
            "The filtering has found no matches in validity time "
            "between the historic forecasts and the truths."
        )

    hf_out = xr.concat(hf_slices, dim=TIME_DIM)
    tr_out = xr.concat(
        [s.expand_dims(TIME_DIM) if TIME_DIM not in s.dims else s for s in tr_slices],
        dim=TIME_DIM,
    )
    hf_out = enforce_coordinate_ordering(hf_out, list(hf.dims))
    tr_out = enforce_coordinate_ordering(tr_out, list(tr.dims))
    return hf_out, tr_out


def create_unified_frt_coord(historic_forecasts: xr.DataArray) -> xr.DataArray:
    """Scalar forecast_reference_time coordinate for coefficient metadata."""
    frt = historic_forecasts["forecast_reference_time"]
    points = np.atleast_1d(frt.values)
    frt_point = np.max(points)
    return xr.DataArray(
        frt_point,
        attrs=frt.attrs,
        name="forecast_reference_time",
    )


def merge_land_and_sea(
    calibrated_land_only: Union[xr.DataArray, xr.Dataset],
    uncalibrated: Union[xr.DataArray, xr.Dataset],
) -> None:
    from utils.xarray_core import merge_land_and_sea as _merge

    _merge(as_dataarray(calibrated_land_only), as_dataarray(uncalibrated))


def _ceiling_fp(da: xr.DataArray) -> np.ndarray:
    fp = da["forecast_period"]
    values = fp.values

    if not np.issubdtype(values.dtype, np.timedelta64):
        # 探测它代表的是小时还是纳秒。如果数字非常大(比如时间戳级别的纳秒)，转为纳秒再转小时
        if values.size == 1 and values > 10000:
            values = np.array(values, dtype="timedelta64[ns]")
        else:
            # 如果数字很小(比如 12, 15, 24)，说明它本身就是代表小时的整数，直接打包成 [h]
            values = np.array(values, dtype="timedelta64[h]")

        # 3. 此时执行除法，两边都是时间序列，绝对安全
    if hasattr(values, "astype"):
        hours = values / np.timedelta64(1, "h")
        return np.ceil(hours.astype(float))

    return np.ceil(np.atleast_1d(values).astype(float))


def forecast_coords_match(first: Union[xr.DataArray, xr.Dataset], second: Union[xr.DataArray, xr.Dataset]) -> None:
    a = as_dataarray(first)
    b = as_dataarray(second)
    mismatches = []
    if not np.array_equal(_ceiling_fp(a), _ceiling_fp(b)):
        mismatches.append("rounded forecast_period hours")
    if get_frt_hours(a) != get_frt_hours(b):
        mismatches.append("forecast_reference_time hours")
    if mismatches:
        raise ValueError(
            f"The following coordinates of the two inputs do not match: {', '.join(mismatches)}"
        )


def check_forecast_consistency(forecasts: Union[xr.DataArray, xr.Dataset]) -> None:
    fc = as_dataarray(forecasts)
    frt_hours = get_frt_hours(fc)
    if len(frt_hours) != 1:
        raise ValueError(
            f"Forecasts have been provided with differing hours for the "
            f"forecast reference time {frt_hours}"
        )
    fp = fc["forecast_period"]
    fp_vals = np.atleast_1d(fp.values)
    if len(fp_vals) != 1:
        raise ValueError(
            f"Forecasts have been provided with differing forecast periods {fp_vals}"
        )


def broadcast_data_to_time_coord(
    predictors: List[xr.DataArray],
) -> List[ndarray]:
    """Broadcast static predictors along the time dimension."""
    num_times = [
        p.sizes[TIME_DIM]
        for p in predictors
        if TIME_DIM in p.dims
    ]
    broadcasted = []
    for p in predictors:
        data = p.values
        if TIME_DIM not in p.dims and num_times:
            data = np.broadcast_to(data, (num_times[0],) + data.shape)
        broadcasted.append(data)
    return broadcasted


def check_data_sufficiency(
    historic_forecasts: Union[xr.DataArray, xr.Dataset],
    truths: Union[xr.DataArray, xr.Dataset],
    point_by_point: bool,
    proportion_of_nans: float,
) -> None:
    hf = as_dataarray(historic_forecasts)
    tr = as_dataarray(truths)
    if not is_spot_data(hf):
        return

    truths_data = np.broadcast_to(tr.values, hf.shape)
    index = np.isnan(hf.values) & np.isnan(truths_data)

    if point_by_point:
        spot_axis = hf.dims.index(SPOT_DIM)
        non_spot_axes = [i for i in range(hf.ndim) if i != spot_axis]
        detected_proportion = np.count_nonzero(index, axis=tuple(non_spot_axes)) / np.prod(
            np.array(index.shape)[non_spot_axes]
        )
        if np.any(detected_proportion > proportion_of_nans):
            number_of_sites = np.sum(detected_proportion > proportion_of_nans)
            raise ValueError(
                f"{number_of_sites} sites have a proportion of NaNs that is "
                f"higher than the allowable proportion of NaNs within the "
                f"historic forecasts and truth pairs. The allowable proportion is "
                f"{proportion_of_nans}. The maximum proportion of NaNs is "
                f"{np.amax(detected_proportion)}."
            )
    else:
        detected_proportion = np.count_nonzero(index) / index.size
        if detected_proportion > proportion_of_nans:
            raise ValueError(
                f"The proportion of NaNs detected is {detected_proportion}. "
                f"This is higher than the allowable proportion of NaNs within the "
                f"historic forecasts and truth pairs: {proportion_of_nans}."
            )
