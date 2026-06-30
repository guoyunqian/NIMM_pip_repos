"""Shared xarray helpers for EMOS calibration (spot data, no iris)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import xarray as xr
from numpy import ndarray
from numpy.ma.core import MaskedArray

MANDATORY_ATTRIBUTE_DEFAULTS = {
    "title": "unknown",
    "source": "IMPROVER",
    "institution": "unknown",
}

MANDATORY_ATTRIBUTES = [x for x in MANDATORY_ATTRIBUTE_DEFAULTS.keys()]

SPOT_DIM = "spot_index"
REALIZATION_DIM = "realization"
TIME_DIM = "time"


class CoordinateNotFoundError(KeyError):
    """Raised when an expected coordinate is missing."""


def as_dataarray(
    obj: Union[xr.DataArray, xr.Dataset],
    var_name: Optional[str] = None,
) -> xr.DataArray:
    """Extract a single diagnostic DataArray from a Dataset or pass through."""
    if isinstance(obj, xr.DataArray):
        return obj
    if not isinstance(obj, xr.Dataset):
        raise TypeError(f"Expected DataArray or Dataset, got {type(obj)}")
    if var_name is not None:
        if var_name not in obj.data_vars:
            raise KeyError(f"Variable {var_name!r} not in dataset")
        return obj[var_name]
    if len(obj.data_vars) == 1:
        return next(iter(obj.data_vars.values()))
    for name, da in obj.data_vars.items():
        if da.attrs.get("standard_name"):
            return da
    raise ValueError(
        "Dataset has multiple data variables; specify var_name or use a "
        f"single-variable dataset. Variables: {list(obj.data_vars)}"
    )


def as_dataset(obj: Union[xr.DataArray, xr.Dataset]) -> xr.Dataset:
    """Wrap a DataArray as a single-variable Dataset or return Dataset unchanged."""
    if isinstance(obj, xr.Dataset):
        return obj
    if isinstance(obj, xr.DataArray):
        if obj.name is None:
            name = obj.attrs.get("standard_name", "unknown")
            return obj.to_dataset(name=name)
        return obj.to_dataset()
    raise TypeError(f"Expected DataArray or Dataset, got {type(obj)}")


def get_diagnostic_name(da: xr.DataArray) -> str:
    """Return standard_name, long_name, or variable name."""
    if da.attrs.get("standard_name"):
        return da.attrs["standard_name"]
    if da.attrs.get("long_name"):
        return da.attrs["long_name"]
    if da.name:
        return da.name
    return "unknown"


def is_spot_data(da: xr.DataArray) -> bool:
    """True if data uses spot_index as a dimension coordinate."""
    return SPOT_DIM in da.dims


def has_coord(da: xr.DataArray, name: str) -> bool:
    return name in da.coords or name in da.dims


def dim_names(da: xr.DataArray) -> List[str]:
    return list(da.dims)


def enforce_coordinate_ordering(
    da: xr.DataArray,
    coord_names: Union[List[str], str],
    anchor_start: bool = True,
) -> xr.DataArray:
    """Reorder dimensions so listed coords appear first (or last)."""
    if isinstance(coord_names, str):
        coord_names = [coord_names]
    present = [c for c in coord_names if c in da.dims]
    if not present:
        return da
    other = [d for d in da.dims if d not in present]
    new_order = present + other if anchor_start else other + present
    return da.transpose(*new_order)


def collapsed(
    da: xr.DataArray,
    dim: Union[str, Sequence[str]],
    how: str,
) -> xr.DataArray:
    """Collapse dimension(s) with mean or variance (spot-only EMOS usage)."""
    if isinstance(dim, str):
        dim = [dim]
    if how == "mean":
        return da.mean(dim=dim, keep_attrs=True)
    if how == "var":
        return da.var(dim=dim, keep_attrs=True)
    raise ValueError(f"Unsupported collapse method: {how}")


def convert_data_to_2d(
    da: xr.DataArray,
    coord: str = REALIZATION_DIM,
    transpose: bool = True,
) -> ndarray:
    """Reshape so *coord* is the second dimension (or first if transpose=False)."""
    data = da.values
    if np.ma.is_masked(data):
        data = np.ma.filled(data, np.nan)
    if coord not in da.dims:
        flat = data.flatten()
        result = flat.reshape(-1, 1) if transpose else flat.reshape(1, -1)
        return np.array(result)

    da_ord = enforce_coordinate_ordering(da, coord)
    other_dims = [d for d in da_ord.dims if d != coord]
    stacked = da_ord.transpose(coord, *other_dims)
    forecast_data = stacked.values.reshape(stacked.sizes[coord], -1)
    if transpose:
        forecast_data = forecast_data.T
    return np.array(forecast_data)


def time_coord_to_datetime(
    da: xr.DataArray,
    coord_name: str = TIME_DIM,
    point_or_bound: str = "point",
) -> List:
    """Convert xarray time coordinate to python datetime(s)."""
    if coord_name not in da.coords:
        raise CoordinateNotFoundError(coord_name)
    coord = da[coord_name]
    values = coord.values
    if point_or_bound == "point":
        return [np.datetime_as_string(v, unit="s").astype("datetime64[s]").astype(object)
                if not isinstance(v, datetime) else v
                for v in np.atleast_1d(values)]
    # bounds not used in current sample data; extend if needed
    raise NotImplementedError("time bounds matching not implemented for xarray path")


def _numpy_datetime_to_py(dt) -> datetime:
    if isinstance(dt, datetime):
        return dt
    return pd_timestamp_to_datetime(dt)


def pd_timestamp_to_datetime(dt) -> datetime:
    import pandas as pd

    return pd.Timestamp(dt).to_pydatetime()


def get_frt_hours(da: xr.DataArray) -> set:
    """Hour component of forecast_reference_time coordinate."""
    if "forecast_reference_time" not in da.coords:
        raise CoordinateNotFoundError("forecast_reference_time")
    frt = da["forecast_reference_time"].values
    hours = set()
    for v in np.atleast_1d(frt):
        t = pd_timestamp_to_datetime(v)
        hours.add(int(t.hour))
    return hours


def create_unified_frt_coord(da: xr.DataArray) -> Dict[str, Any]:
    """Build scalar forecast_reference_time metadata for coefficient output."""
    frt = da["forecast_reference_time"]
    points = np.atleast_1d(frt.values)
    frt_point = np.max(points)
    frt_bounds_min = np.min(points)
    frt_bounds_max = frt_point
    return {
        "forecast_reference_time": frt_point,
        "forecast_reference_time_bounds": (frt_bounds_min, frt_bounds_max),
    }


def generate_mandatory_attributes(
    diagnostic_arrays: List[xr.DataArray],
    model_id_attr: Optional[str] = None,
) -> Dict[str, str]:
    """Merge mandatory attrs from input diagnostics."""
    missing_value = object()
    attr_dicts = [da.attrs for da in diagnostic_arrays]
    required_attributes = [model_id_attr] if model_id_attr else []
    attributes = MANDATORY_ATTRIBUTE_DEFAULTS.copy()
    for attr in MANDATORY_ATTRIBUTES + required_attributes:
        unique_values = {d.get(attr, missing_value) for d in attr_dicts}
        if len(unique_values) == 1 and missing_value not in unique_values:
            (attributes[attr],) = unique_values
        elif attr in required_attributes:
            raise ValueError(
                f'Required attribute "{attr}" is missing or not the same on all inputs'
            )
    return attributes


def create_new_diagnostic_dataarray(
    name: str,
    units: str,
    template: xr.DataArray,
    mandatory_attributes: Dict[str, str],
    optional_attributes: Optional[Dict[str, Any]] = None,
    data: Optional[Union[MaskedArray, ndarray]] = None,
    dtype: type = np.float32,
) -> xr.DataArray:
    """Create output DataArray copying coords/attrs from template."""
    attributes = dict(mandatory_attributes)
    if optional_attributes:
        attributes.update(optional_attributes)
    for attr in MANDATORY_ATTRIBUTES:
        if attr not in attributes:
            raise ValueError(f"{attr} attribute is required")

    drop = [REALIZATION_DIM, "percentile"]
    coords = {
        k: v
        for k, v in template.coords.items()
        if k not in drop and (k in template.dims or k not in template.dims)
    }
    # Keep non-dimension coords whose dimension is still present
    dims = list(template.dims)
    for d in drop:
        if d in dims:
            dims.remove(d)

    if data is None:
        shape = tuple(template.sizes[d] for d in dims) if dims else ()
        data = np.zeros(shape, dtype=dtype)
    else:
        data = np.asarray(data, dtype=dtype)

    da = xr.DataArray(
        data,
        dims=dims,
        coords={k: v for k, v in coords.items() if k in dims or k not in dims},
        attrs={**template.attrs, **attributes, "units": units},
        name=name,
    )
    if "standard_name" in attributes:
        da.attrs["standard_name"] = attributes["standard_name"]
    elif name not in ("location_parameter", "scale_parameter") and not name.startswith(
        "emos_coefficient"
    ):
        da.attrs["standard_name"] = name
    return da


def extract_coefficient(ds: xr.Dataset, coeff_name: str) -> xr.DataArray:
    """Get one EMOS coefficient variable from a coefficients Dataset."""
    if coeff_name in ds.data_vars:
        return ds[coeff_name]
    prefixed = f"emos_coefficient_{coeff_name.replace('emos_coefficient_', '')}"
    if prefixed in ds.data_vars:
        return ds[prefixed]
    raise KeyError(f"Coefficient {coeff_name!r} not found in dataset")


def get_dataset_attribute(ds: xr.Dataset, name: str, optional: bool = False) -> Any:
    """Read attribute from dataset or coefficient variables consistently."""
    values = []
    for var in ds.data_vars:
        if name in ds[var].attrs:
            values.append(str(ds[var].attrs[name]))
    if name in ds.attrs:
        values.append(str(ds.attrs[name]))
    if not values and optional:
        return None
    if not values:
        raise AttributeError(f"The {name} attribute must be specified on coefficients.")
    if len(set(values)) == 1:
        raw = values[0]
        if name == "shape_parameters":
            return np.array(eval(raw)) if raw.startswith("[") else ds[list(ds.data_vars)[0]].attrs[name]
        return ds[list(ds.data_vars)[0]].attrs.get(name, raw)
    raise AttributeError(f"Coefficients must share the same {name} attribute: {values}")


def mask_dataarray(da: xr.DataArray, landsea_mask: xr.DataArray) -> xr.DataArray:
    """Mask sea points with NaN (land=1, sea=0)."""
    mask_da = as_dataarray(landsea_mask)
    land = mask_da.values.astype(bool)
    data = da.values.copy()
    try:
        data[..., ~land] = np.nan
    except IndexError as err:
        raise IndexError(
            f"DataArray and landsea_mask shapes are not compatible. {err}"
        ) from err
    return da.copy(data=np.ma.masked_invalid(data))


def merge_land_and_sea(
    calibrated_land_only: xr.DataArray,
    uncalibrated: xr.DataArray,
) -> None:
    """Fill masked sea points in calibrated output from uncalibrated data (in place)."""
    cal = as_dataarray(calibrated_land_only)
    unc = as_dataarray(uncalibrated)
    if cal.dims != unc.dims:
        raise ValueError("Input arrays do not have the same dimension names")
    if np.ma.is_masked(cal.values):
        new_data = cal.values.data.copy()
        mask = cal.values.mask
        new_data[mask] = unc.values[mask]
        calibrated_land_only.values[:] = new_data


def merge_coords_from_template(
    result: xr.DataArray, template: xr.DataArray, prob_dim: Optional[str] = None
) -> xr.DataArray:
    """Copy non-probabilistic coords from template onto result."""
    drop = {REALIZATION_DIM, "percentile", prob_dim} - {None}
    for c in template.coords:
        if c in drop or c in result.coords:
            continue
        if c in template.dims and c not in result.dims:
            continue
        result = result.assign_coords({c: template[c]})
    result.attrs = {**template.attrs, **result.attrs}
    return result


def to_output_dataset(da: xr.DataArray) -> xr.Dataset:
    """Return single-variable result as Dataset."""
    return as_dataset(da)


def copy_dataset_attrs(source: xr.Dataset, target: xr.Dataset) -> xr.Dataset:
    target.attrs = deepcopy(source.attrs)
    return target
