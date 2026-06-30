#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""Common helpers for retrieve CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import xarray as xr


_CLI_SCRIPTS = (
    "pyart/retrieve/cli/qpe.py",
    "pyart/retrieve/cli/echo_class.py",
)


def maybe_coerce_with(func, value):
    """Apply func only when value is a string."""
    return func(value) if isinstance(value, str) else value


def _read_griddata(path: str, value_name: Optional[str] = None) -> xr.DataArray:
    """Read one grid field from NetCDF with meteva_base."""
    try:
        import meteva_base as meb

        data = meb.read_griddata_from_nc(path, value_name=value_name)
        if data is None:
            if value_name:
                raise ValueError(f"Cannot read value_name={value_name!r} from {path}")
            raise ValueError("meteva_base.read_griddata_from_nc returned None")
        return data
    except Exception as exc:
        raise RuntimeError(f"Failed to read input file: {path}") from exc


def _read_mass_centers(path: Optional[str]) -> np.ndarray | None:
    """Read hydroclass mass centers from .npy or text file."""
    if path is None:
        return None

    file_path = Path(path)
    if file_path.suffix.lower() == ".npy":
        return np.load(file_path)

    try:
        return np.loadtxt(file_path, delimiter=",")
    except ValueError:
        return np.loadtxt(file_path)


def _select_dataarray(
    result: dict[str, xr.DataArray],
    result_key: str,
    algorithm_name: str,
) -> xr.DataArray:
    """Select one DataArray from a dict-style algorithm result."""
    if result_key not in result:
        available = ", ".join(sorted(result))
        raise KeyError(
            f"{algorithm_name} result_key={result_key!r} not found. "
            f"Available keys: {available}"
        )

    data = result[result_key]
    if not isinstance(data, xr.DataArray):
        raise TypeError(f"{algorithm_name} result {result_key!r} is not xarray.DataArray")
    return data


def _dict_to_dataset(result: dict[str, xr.DataArray], algorithm_name: str) -> xr.Dataset:
    """Convert dict-style algorithm outputs to one Dataset."""
    if not isinstance(result, dict):
        raise TypeError(f"{algorithm_name} result is not a dict")
    if not result:
        raise ValueError(f"{algorithm_name} result is empty")
    for key, value in result.items():
        if not isinstance(value, xr.DataArray):
            raise TypeError(f"{algorithm_name} result {key!r} is not xarray.DataArray")
    return xr.Dataset(result)


def _write_griddata_to_nc(
    data: xr.DataArray | xr.Dataset,
    path: str,
    compression_level: int = 1,
    least_significant_digit: int = None,
) -> None:
    """Write DataArray or Dataset result to NetCDF."""
    if not isinstance(data, (xr.DataArray, xr.Dataset)):
        raise TypeError("_write_griddata_to_nc only supports xarray.DataArray or xarray.Dataset")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    compression_level = 1 if compression_level is None else int(compression_level)
    if compression_level < 0 or compression_level > 9:
        raise ValueError("compression_level must be between 0 and 9")

    if isinstance(data, xr.DataArray):
        var_name = data.name if data.name else "data"
        dataset = data.to_dataset(name=var_name)
    else:
        dataset = data
        var_name = None

    def _sanitize_attr_value(value):
        if value is None:
            return ""
        if isinstance(value, (bool, np.bool_)):
            return int(value)
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, (list, tuple)):
            if all(isinstance(v, (int, float, np.integer, np.floating, bool, np.bool_)) for v in value):
                return [int(v) if isinstance(v, (bool, np.bool_)) else (v.item() if isinstance(v, np.generic) else v) for v in value]
            return json.dumps(value, ensure_ascii=False)
        return value

    dataset.attrs = {k: _sanitize_attr_value(v) for k, v in dict(dataset.attrs).items()}
    for data_var in dataset.data_vars:
        dataset[data_var].attrs = {
            k: _sanitize_attr_value(v)
            for k, v in dict(dataset[data_var].attrs).items()
        }

    encoding = {}
    if compression_level == 0:
        encoding["zlib"] = False
    else:
        encoding["zlib"] = True
        encoding["complevel"] = compression_level
    encoding["_FillValue"] = None
    if least_significant_digit is not None:
        encoding["least_significant_digit"] = int(least_significant_digit)

    if var_name is not None:
        encoding_map = {var_name: encoding}
    else:
        encoding_map = {data_var: dict(encoding) for data_var in dataset.data_vars}

    try:
        dataset.to_netcdf(path, mode="w", encoding=encoding_map)
    except PermissionError as exc:
        raise PermissionError(
            f"Cannot write output file: {path}. "
            "The file may be open in another process (for example, Jupyter). "
            "Please close dataset handles or use a different output path."
        ) from exc


def parse_comma_separated_list(value) -> list[str]:
    """Convert comma-separated text or sequence to a string list."""
    return maybe_coerce_with(lambda s: s.split(","), value)


def parse_comma_separated_list_of_float(value) -> list[float]:
    """Convert comma-separated text or sequence to a float list."""
    return maybe_coerce_with(
        lambda s: [float(item) for item in s.split(",")],
        value,
    )


def main(argv: Optional[Sequence[str]] = None):
    """列出可直接运行的 CLI 示例脚本。"""
    lines = [
        "pyart.retrieve CLI 已改为示例脚本，请直接运行：",
        *(f"  python {script}" for script in _CLI_SCRIPTS),
        "",
        "在脚本底部的 if __name__ == '__main__' 中修改路径与参数后执行。",
    ]
    raise SystemExit("\n".join(lines))
