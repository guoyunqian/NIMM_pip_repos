#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""echo_class 算法插件命令行入口。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import xarray as xr


def _load_echo_class_cli():
    from . import (
        _dict_to_dataset,
        _read_griddata,
        _read_mass_centers,
        _select_dataarray,
        _write_griddata_to_nc,
        parse_comma_separated_list,
        parse_comma_separated_list_of_float,
    )
    from ..src import echo_class as echo_class_src

    return {
        "_dict_to_dataset": _dict_to_dataset,
        "_read_griddata": _read_griddata,
        "_read_mass_centers": _read_mass_centers,
        "_select_dataarray": _select_dataarray,
        "_write_griddata_to_nc": _write_griddata_to_nc,
        "parse_comma_separated_list": parse_comma_separated_list,
        "parse_comma_separated_list_of_float": parse_comma_separated_list_of_float,
        "echo_class_src": echo_class_src,
    }


def _maybe_write(
    result: xr.DataArray | xr.Dataset,
    output_path: Optional[str],
) -> xr.DataArray | xr.Dataset:
    if output_path is not None:
        cli = _load_echo_class_cli()
        cli["_write_griddata_to_nc"](result, output_path)
    return result


def steiner_conv_strat(
    refl_path: str,
    *,
    dx: float = None,
    dy: float = None,
    intense: float = 42.0,
    work_level: float = 3000.0,
    peak_relation: str = "default",
    area_relation: str = "medium",
    bkg_rad: float = 11000.0,
    use_intense: bool = True,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """Steiner 层状/对流回波分类 CLI 入口。"""
    cli = _load_echo_class_cli()
    refl = cli["_read_griddata"](refl_path)
    plugin = cli["echo_class_src"].SteinerConvStratPlugin(
        dx=dx,
        dy=dy,
        intense=intense,
        work_level=work_level,
        peak_relation=peak_relation,
        area_relation=area_relation,
        bkg_rad=bkg_rad,
        use_intense=use_intense,
    )
    return _maybe_write(plugin(refl), output_path)


def feature_detection(
    field_data_path: str,
    *,
    overest_field_path: str = None,
    underest_field_path: str = None,
    dx: float = None,
    dy: float = None,
    level_m: float = None,
    always_core_thres: float = 42,
    bkg_rad_km: float = 11,
    use_cosine: bool = True,
    max_diff: float = 5,
    zero_diff_cos_val: float = 55,
    scalar_diff: float = 1.5,
    use_addition: bool = True,
    calc_thres: float = 0.75,
    weak_echo_thres: float = 5.0,
    min_val_used: float = 5.0,
    db_averaging: bool = True,
    remove_small_objects: bool = True,
    min_km2_size: float = 10,
    binary_close: bool = False,
    val_for_max_rad: float = 30,
    max_rad_km: float = 5.0,
    core_val: int = 3,
    nosfcecho: int = 0,
    weakecho: int = 3,
    bkgd_val: int = 1,
    feat_val: int = 2,
    estimate_flag: bool = True,
    estimate_offset: float = 5,
    result_key: str = None,
    output_path: Optional[str] = None,
) -> xr.DataArray | xr.Dataset:
    """特征识别（feature_detection）CLI 入口。"""
    cli = _load_echo_class_cli()
    field_data = cli["_read_griddata"](field_data_path)
    overest_field = (
        cli["_read_griddata"](overest_field_path) if overest_field_path is not None else None
    )
    underest_field = (
        cli["_read_griddata"](underest_field_path) if underest_field_path is not None else None
    )
    plugin = cli["echo_class_src"].FeatureDetectionPlugin(
        dx=dx,
        dy=dy,
        level_m=level_m,
        always_core_thres=always_core_thres,
        bkg_rad_km=bkg_rad_km,
        use_cosine=use_cosine,
        max_diff=max_diff,
        zero_diff_cos_val=zero_diff_cos_val,
        scalar_diff=scalar_diff,
        use_addition=use_addition,
        calc_thres=calc_thres,
        weak_echo_thres=weak_echo_thres,
        min_val_used=min_val_used,
        dB_averaging=db_averaging,
        remove_small_objects=remove_small_objects,
        min_km2_size=min_km2_size,
        binary_close=binary_close,
        val_for_max_rad=val_for_max_rad,
        max_rad_km=max_rad_km,
        core_val=core_val,
        nosfcecho=nosfcecho,
        weakecho=weakecho,
        bkgd_val=bkgd_val,
        feat_val=feat_val,
        estimate_flag=estimate_flag,
        estimate_offset=estimate_offset,
    )
    result_dict = plugin(
        field_data,
        overest_field=overest_field,
        underest_field=underest_field,
    )
    if result_key:
        result = cli["_select_dataarray"](result_dict, result_key, "feature_detection")
    else:
        result = cli["_dict_to_dataset"](result_dict, "feature_detection")
    return _maybe_write(result, output_path)


def hydroclass_semisupervised(
    *,
    refl_path: str = None,
    zdr_path: str = None,
    rhv_path: str = None,
    kdp_path: str = None,
    temp_path: str = None,
    iso0_path: str = None,
    hydro_names: Sequence[str] = ("AG", "CR", "LR", "RP", "RN", "VI", "WS", "MH", "IH/HDG"),
    var_names: Sequence[str] = ("Zh", "ZDR", "KDP", "RhoHV", "relH"),
    mass_centers_path: str = None,
    weights: Sequence[float] = (1.0, 1.0, 1.0, 0.75, 0.5),
    value: float = 50.0,
    lapse_rate: float = -6.5,
    radar_freq: float = None,
    temp_ref: str = "temperature",
    compute_entropy: bool = False,
    output_distances: bool = False,
    vectorize: bool = False,
    result_key: str = None,
    output_path: Optional[str] = None,
) -> xr.DataArray | xr.Dataset:
    """半监督水凝物分类（hydroclass_semisupervised）CLI 入口。"""
    cli = _load_echo_class_cli()
    refl = cli["_read_griddata"](refl_path) if refl_path is not None else None
    zdr = cli["_read_griddata"](zdr_path) if zdr_path is not None else None
    rhv = cli["_read_griddata"](rhv_path) if rhv_path is not None else None
    kdp = cli["_read_griddata"](kdp_path) if kdp_path is not None else None
    temp = cli["_read_griddata"](temp_path) if temp_path is not None else None
    iso0 = cli["_read_griddata"](iso0_path) if iso0_path is not None else None
    plugin = cli["echo_class_src"].HydroclassSemisupervisedPlugin(
        hydro_names=tuple(cli["parse_comma_separated_list"](hydro_names)),
        var_names=tuple(cli["parse_comma_separated_list"](var_names)),
        mass_centers=cli["_read_mass_centers"](mass_centers_path),
        weights=np.asarray(cli["parse_comma_separated_list_of_float"](weights), dtype=np.float32),
        value=value,
        lapse_rate=lapse_rate,
        radar_freq=radar_freq,
        temp_ref=temp_ref,
        compute_entropy=compute_entropy,
        output_distances=output_distances,
        vectorize=vectorize,
    )
    result_dict = plugin(
        refl=refl,
        zdr=zdr,
        rhv=rhv,
        kdp=kdp,
        temp=temp,
        iso0=iso0,
    )
    if result_key:
        result = cli["_select_dataarray"](result_dict, result_key, "hydroclass_semisupervised")
    else:
        result = cli["_dict_to_dataset"](result_dict, "hydroclass_semisupervised")
    return _maybe_write(result, output_path)


def conv_strat_raut(
    refl_path: str,
    *,
    cappi_level: float = 0,
    zr_a: float = 200,
    zr_b: float = 1.6,
    core_wt_threshold: float = 5,
    conv_wt_threshold: float = 1.5,
    conv_scale_km: float = 25,
    min_reflectivity: float = 5,
    conv_min_refl: float = 25,
    conv_core_threshold: float = 42,
    override_checks: bool = False,
    dx: float = None,
    dy: float = None,
    output_path: Optional[str] = None,
) -> xr.DataArray:
    """Raut 小波层状/对流分类 CLI 入口。"""
    cli = _load_echo_class_cli()
    refl = cli["_read_griddata"](refl_path)
    plugin = cli["echo_class_src"].ConvStratRautPlugin(
        cappi_level=cappi_level,
        zr_a=zr_a,
        zr_b=zr_b,
        core_wt_threshold=core_wt_threshold,
        conv_wt_threshold=conv_wt_threshold,
        conv_scale_km=conv_scale_km,
        min_reflectivity=min_reflectivity,
        conv_min_refl=conv_min_refl,
        conv_core_threshold=conv_core_threshold,
        override_checks=override_checks,
        dx=dx,
        dy=dy,
    )
    return _maybe_write(plugin(refl), output_path)


if __name__ == "__main__":
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    data_dir = Path(__file__).resolve().parents[1] / "test_data" / "echo_class" / "input"
    refl_path = str(data_dir / "ACHN_CREF000_20240612_070000.nc")
    output_path = str(
        Path(__file__).resolve().parents[1]
        / "test_data"
        / "echo_class"
        / "cli_output"
        / "steiner_cli_run.nc"
    )

    from pyart.retrieve.cli.echo_class import steiner_conv_strat as run_steiner_conv_strat

    run_steiner_conv_strat(refl_path, output_path=output_path)
