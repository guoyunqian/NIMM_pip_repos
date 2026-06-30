#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""从 ``pyart.retrieve.echo_class`` 迁移来的回波分类算法。
包括：
- Steiner 层状-对流分类
- 特征识别
- 水凝物分类
- 小波层状-对流分类
对上述算法进行了插件类的封装。
插件类的主要功能是：
- 接收meteva_base的网格数据作为输入
- 调用对应的算法函数进行处理
- 返回处理结果
"""

from __future__ import annotations

from warnings import warn

import numpy as np
import xarray as xr

from ._echo_class import _feature_detection, steiner_class_buff
from ._echo_class_wt import calc_scale_break, wavelet_reclass
from ...plugin_base import BasePlugin
from ..utils.utils import (
    build_griddata_like,
    check_for_meb_griddata,
    check_for_xy_coordinates,
    get_xy_in_meters,
)


class SteinerConvStratPlugin(BasePlugin):
    """Steiner 层状-对流分类插件。"""

    def __init__(
        self,
        dx=None,
        dy=None,
        intense: float = 42.0,
        work_level: float = 3000.0,
        peak_relation: str = "default",
        area_relation: str = "medium",
        bkg_rad: float = 11000.0,
        use_intense: bool = True,
    ) -> None:
        self.kwargs = {
            "dx": dx,
            "dy": dy,
            "intense": intense,
            "work_level": work_level,
            "peak_relation": peak_relation,
            "area_relation": area_relation,
            "bkg_rad": bkg_rad,
            "use_intense": use_intense,
        }

    def process(self, refl: xr.DataArray) -> xr.DataArray:
        """调用 ``steiner_conv_strat``。"""
        return steiner_conv_strat(refl, **self.kwargs)


class FeatureDetectionPlugin(BasePlugin):
    """特征识别插件。"""

    def __init__(
        self,
        dx=None,
        dy=None,
        level_m=None,
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
        dB_averaging: bool = True,
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
    ) -> None:
        self.kwargs = {
            "dx": dx,
            "dy": dy,
            "level_m": level_m,
            "always_core_thres": always_core_thres,
            "bkg_rad_km": bkg_rad_km,
            "use_cosine": use_cosine,
            "max_diff": max_diff,
            "zero_diff_cos_val": zero_diff_cos_val,
            "scalar_diff": scalar_diff,
            "use_addition": use_addition,
            "calc_thres": calc_thres,
            "weak_echo_thres": weak_echo_thres,
            "min_val_used": min_val_used,
            "dB_averaging": dB_averaging,
            "remove_small_objects": remove_small_objects,
            "min_km2_size": min_km2_size,
            "binary_close": binary_close,
            "val_for_max_rad": val_for_max_rad,
            "max_rad_km": max_rad_km,
            "core_val": core_val,
            "nosfcecho": nosfcecho,
            "weakecho": weakecho,
            "bkgd_val": bkgd_val,
            "feat_val": feat_val,
            "estimate_flag": estimate_flag,
            "estimate_offset": estimate_offset,
        }

    def process(
        self,
        field_data: xr.DataArray,
        overest_field: xr.DataArray | None = None,
        underest_field: xr.DataArray | None = None,
    ) -> dict[str, xr.DataArray]:
        """调用 ``feature_detection``。"""
        return feature_detection(
            field_data,
            overest_field=overest_field,
            underest_field=underest_field,
            **self.kwargs,
        )


class HydroclassSemisupervisedPlugin(BasePlugin):
    """半监督水凝物分类插件。"""

    def __init__(
        self,
        hydro_names=("AG", "CR", "LR", "RP", "RN", "VI", "WS", "MH", "IH/HDG"),
        var_names=("Zh", "ZDR", "KDP", "RhoHV", "relH"),
        mass_centers=None,
        weights=np.array([1.0, 1.0, 1.0, 0.75, 0.5]),
        value: float = 50.0,
        lapse_rate: float = -6.5,
        radar_freq=None,
        temp_ref: str = "temperature",
        compute_entropy: bool = False,
        output_distances: bool = False,
        vectorize: bool = False,
    ) -> None:
        self.kwargs = {
            "hydro_names": hydro_names,
            "var_names": var_names,
            "mass_centers": mass_centers,
            "weights": weights,
            "value": value,
            "lapse_rate": lapse_rate,
            "radar_freq": radar_freq,
            "temp_ref": temp_ref,
            "compute_entropy": compute_entropy,
            "output_distances": output_distances,
            "vectorize": vectorize,
        }

    def process(
        self,
        refl: xr.DataArray | None = None,
        zdr: xr.DataArray | None = None,
        rhv: xr.DataArray | None = None,
        kdp: xr.DataArray | None = None,
        temp: xr.DataArray | None = None,
        iso0: xr.DataArray | None = None,
    ) -> dict[str, xr.DataArray]:
        """调用 ``hydroclass_semisupervised``。"""
        return hydroclass_semisupervised(
            refl=refl,
            zdr=zdr,
            rhv=rhv,
            kdp=kdp,
            temp=temp,
            iso0=iso0,
            **self.kwargs,
        )


class ConvStratRautPlugin(BasePlugin):
    """小波层状-对流分类插件。"""

    def __init__(
        self,
        cappi_level: float | int = 0,
        zr_a: float = 200,
        zr_b: float = 1.6,
        core_wt_threshold: float = 5,
        conv_wt_threshold: float = 1.5,
        conv_scale_km: float = 25,
        min_reflectivity: float = 5,
        conv_min_refl: float = 25,
        conv_core_threshold: float = 42,
        override_checks: bool = False,
        dx=None,
        dy=None,
    ) -> None:
        self.kwargs = {
            "cappi_level": cappi_level,
            "zr_a": zr_a,
            "zr_b": zr_b,
            "core_wt_threshold": core_wt_threshold,
            "conv_wt_threshold": conv_wt_threshold,
            "conv_scale_km": conv_scale_km,
            "min_reflectivity": min_reflectivity,
            "conv_min_refl": conv_min_refl,
            "conv_core_threshold": conv_core_threshold,
            "override_checks": override_checks,
            "dx": dx,
            "dy": dy,
        }

    def process(self, refl: xr.DataArray) -> xr.DataArray:
        """调用 ``conv_strat_raut``。"""
        return conv_strat_raut(refl, **self.kwargs)


def steiner_conv_strat(
    refl: xr.DataArray,
    dx=None,
    dy=None,
    intense: float = 42.0,
    work_level: float = 3000.0,
    peak_relation: str = "default",
    area_relation: str = "medium",
    bkg_rad: float = 11000.0,
    use_intense: bool = True,
) -> xr.DataArray:
    """
    使用 Steiner 方法将回波划分为层状和对流。

    参数
    ----
    refl : xr.DataArray
        meteva_base 反射率网格数据，需包含 level 维。
    dx, dy : float, optional
        水平分辨率，单位米。未给定时根据经纬度坐标近似估算。
    intense : float, optional
        强对流回波阈值，单位 dBZ。
    work_level : float, optional
        分类使用的工作高度，单位米。
    peak_relation : str, optional
        峰值关系类型。
    area_relation : str, optional
        对流核心影响半径关系类型。
    bkg_rad : float, optional
        计算背景回波时使用的半径，单位米。
    use_intense : bool, optional
        是否直接使用强回波阈值识别对流核心。

    返回
    ----
    xr.DataArray
        单层回波分类网格。
    """
    refl_grid = _check_single_context(refl, valid_val=(-200.0, 200.0, np.nan))
    x_m, y_m = get_xy_in_meters(refl_grid)
    dx, dy = _get_dx_dy(refl_grid, dx=dx, dy=dy, x_m=x_m, y_m=y_m)
    x = x_m.astype(np.float32)
    y = y_m.astype(np.float32)
    z = np.asarray(refl_grid.level.values, dtype=np.float32)
    ze = np.asarray(refl_grid.values[0, :, 0, 0, :, :], dtype=np.float32)

    # =====================================
    # Steiner 分类入口
    #
    # 这里先从 meteva_base 六维网格中取出
    # member/time/dtime 唯一的三维切片，
    # 再组织成分类需要的三维反射率数据。
    # =====================================
    eclass = steiner_class_buff(
        ze,
        x,
        y,
        z,
        dx=dx,
        dy=dy,
        bkg_rad=bkg_rad,
        work_level=work_level,
        intense=intense,
        peak_relation=peak_relation,
        area_relation=area_relation,
        use_intense=use_intense,
    )

    # 选择与工作高度最接近的垂直层；未指定时默认首层。
    if work_level is None:
        level_index = 0
    else:
        level_index = int(np.argmin(np.abs(z - work_level)))
    template = refl_grid.isel(member=[0], level=[level_index], time=[0], dtime=[0])

    return _build_level_result(
        template,
        eclass.astype(np.int32),
        name="echo_classification",
        long_name="Steiner 回波分类",
        valid_min=0,
        valid_max=2,
        extra_attrs={
            "comment_1": "基于 Steiner et al. (1995) 的对流-层状回波分类方法",
            "comment_2": "0 = 未定义, 1 = 层状, 2 = 对流",
        },
    )


def feature_detection(
    field_data: xr.DataArray,
    dx=None,
    dy=None,
    level_m=None,
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
    dB_averaging: bool = True,
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
    overest_field: xr.DataArray | None = None,
    underest_field: xr.DataArray | None = None,
) -> dict[str, xr.DataArray]:
    """
    使用自适应阈值方法进行回波特征识别。

    参数
    ----
    field_data : xr.DataArray
        meteva_base 网格数据，可为反射率或其他待识别场。
    dx, dy : float, optional
        水平分辨率，单位米。未给定时根据经纬度坐标近似估算。
    level_m : float, optional
        参与分类的高度，单位米。未给定时使用第一层。
    always_core_thres : float, optional
        始终判为核心回波的阈值。
    bkg_rad_km : float, optional
        计算背景场时使用的平均半径，单位千米。
    use_cosine : bool, optional
        是否使用余弦型阈值关系。
    max_diff : float, optional
        与背景场比较时允许的最大差值。
    zero_diff_cos_val : float, optional
        余弦阈值关系中差值为 0 时对应的场值。
    scalar_diff : float, optional
        固定差值关系中的增量。
    use_addition : bool, optional
        是否使用加法形式构造特征判据。
    calc_thres : float, optional
        参与分类计算的最小阈值。
    weak_echo_thres : float, optional
        弱回波阈值。
    min_val_used : float, optional
        参与背景与特征识别的最小场值。
    dB_averaging : bool, optional
        是否在 dB 空间进行背景平均。
    remove_small_objects : bool, optional
        是否移除面积过小的对象。
    min_km2_size : float, optional
        保留对象的最小面积，单位平方千米。
    binary_close : bool, optional
        是否在识别后执行二值闭运算。
    val_for_max_rad : float, optional
        对应最大影响半径的场值。
    max_rad_km : float, optional
        特征识别时允许的最大影响半径，单位千米。
    core_val : int, optional
        输出结果中核心回波的类别编号。
    nosfcecho : int, optional
        输出结果中无地面回波或未定义区域的类别编号。
    weakecho : int, optional
        输出结果中弱回波的类别编号。
    bkgd_val : int, optional
        输出结果中背景回波的类别编号。
    feat_val : int, optional
        输出结果中特征回波的类别编号。
    estimate_flag : bool, optional
        是否计算高估和低估结果。
    estimate_offset : float, optional
        构造高估和低估场时对原场增减的偏移量。
    overest_field, underest_field : xr.DataArray, optional
        显式提供高估和低估输入场。未给定时使用原场加减偏移量。

    返回
    ----
    dict[str, xr.DataArray]
        回波特征分类结果字典，键与原始 Py-ART 接口保持一致。
    """
    if max_rad_km > 5:
        raise ValueError("max_rad_km must be less than or equal to 5")

    grid = _check_single_context(field_data)
    dx, dy = _get_dx_dy(grid, dx=dx, dy=dy)

    if bkg_rad_km * 1000 < 2 * dx or bkg_rad_km * 1000 < 2 * dy:
        raise ValueError("background radius for averaging must be at least 2 times dx and dy")

    levels = np.asarray(grid.level.values, dtype=np.float32)
    # feature_detection 仅在单层上运行；这里选取目标高度最近层。
    if level_m is None:
        level_index = 0
    else:
        level_index = int(np.argmin(np.abs(levels - level_m)))
    template = grid.isel(member=[0], level=[level_index], time=[0], dtime=[0])
    field_2d = np.asarray(template.values[0, 0, 0, 0, :, :], dtype=np.float32)

    # feature_detection 实际只处理一个二维 CAPPI 截面，
    # 因此这里先选定目标层。
    _, _, feature_best = _feature_detection(
        field_2d,
        dx,
        dy,
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
        dB_averaging=dB_averaging,
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
    )

    comment = (
        f"{nosfcecho} = 无地面回波/未定义, "
        f"{bkgd_val} = 背景回波, "
        f"{feat_val} = 特征回波, "
        f"{weakecho} = 弱回波"
    )
    results = {
        "feature_detection": _build_level_result(
            template,
            feature_best,
            name="feature_detection",
            long_name="特征识别",
            valid_min=0,
            valid_max=3,
            extra_attrs={"comment_1": comment},
        )
    }

    if not estimate_flag:
        return results

    # =====================================
    # 高估/低估敏感性试验
    #
    # 若用户没有显式提供 over/under 场，
    # 这里对同一二维场加减 estimate_offset，
    # 再分别运行一次识别算法。
    # =====================================
    if underest_field is None:
        under_field_2d = field_2d - estimate_offset
    else:
        under_grid = _check_single_context(underest_field)
        under_template = under_grid.isel(member=[0], level=[level_index], time=[0], dtime=[0])
        under_field_2d = np.asarray(under_template.values[0, 0, 0, 0, :, :], dtype=np.float32)

    if overest_field is None:
        over_field_2d = field_2d + estimate_offset
    else:
        over_grid = _check_single_context(overest_field)
        over_template = over_grid.isel(member=[0], level=[level_index], time=[0], dtime=[0])
        over_field_2d = np.asarray(over_template.values[0, 0, 0, 0, :, :], dtype=np.float32)

    _, _, feature_under = _feature_detection(
        under_field_2d,
        dx,
        dy,
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
        dB_averaging=dB_averaging,
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
    )

    _, _, feature_over = _feature_detection(
        over_field_2d,
        dx,
        dy,
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
        dB_averaging=dB_averaging,
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
    )

    results["feature_under"] = _build_level_result(
        template,
        feature_under,
        name="feature_detection_under",
        long_name="特征识别（低估场）",
        valid_min=0,
        valid_max=3,
        extra_attrs={"comment_1": comment},
    )
    results["feature_over"] = _build_level_result(
        template,
        feature_over,
        name="feature_detection_over",
        long_name="特征识别（高估场）",
        valid_min=0,
        valid_max=3,
        extra_attrs={"comment_1": comment},
    )

    return results


def conv_strat_yuter(
    refl: xr.DataArray,
    dx=None,
    dy=None,
    level_m=None,
    always_core_thres: float = 42,
    bkg_rad_km: float = 11,
    use_cosine: bool = True,
    max_diff: float = 5,
    zero_diff_cos_val: float = 55,
    scalar_diff: float = 1.5,
    use_addition: bool = True,
    calc_thres: float = 0.75,
    weak_echo_thres: float = 5.0,
    min_dBZ_used: float = 5.0,
    dB_averaging: bool = True,
    remove_small_objects: bool = True,
    min_km2_size: float = 10,
    val_for_max_conv_rad: float = 30,
    max_conv_rad_km: float = 5.0,
    cs_core: int = 3,
    nosfcecho: int = 0,
    weakecho: int = 3,
    sf: int = 1,
    conv: int = 2,
    estimate_flag: bool = True,
    estimate_offset: float = 5,
) -> dict[str, xr.DataArray]:
    """
    使用 Yuter 方法进行层状-对流分类。

    参数
    ----
    refl : xr.DataArray
        meteva_base 反射率网格数据。
    dx, dy : float, optional
        水平分辨率，单位米。未给定时根据经纬度坐标近似估算。
    level_m : float, optional
        参与分类的高度，单位米。
    always_core_thres : float, optional
        始终判为对流核心的阈值。
    bkg_rad_km : float, optional
        背景平均半径，单位千米。
    use_cosine : bool, optional
        是否使用余弦型阈值关系。
    max_diff : float, optional
        与背景场比较时允许的最大差值。
    zero_diff_cos_val : float, optional
        余弦阈值关系中差值为 0 时对应的反射率值。
    scalar_diff : float, optional
        固定差值关系中的增量。
    use_addition : bool, optional
        是否使用加法形式构造特征判据。
    calc_thres : float, optional
        参与分类计算的最小阈值。
    weak_echo_thres : float, optional
        弱回波阈值。
    min_dBZ_used : float, optional
        参与分类计算的最小反射率。
    dB_averaging : bool, optional
        是否在 dB 空间进行背景平均。
    remove_small_objects : bool, optional
        是否移除面积过小的对象。
    min_km2_size : float, optional
        保留对象的最小面积，单位平方千米。
    val_for_max_conv_rad : float, optional
        对应最大对流影响半径的反射率值。
    max_conv_rad_km : float, optional
        最大对流影响半径，单位千米。
    cs_core : int, optional
        输出结果中对流核心的类别编号。
    nosfcecho : int, optional
        输出结果中无地面回波或未定义区域的类别编号。
    weakecho : int, optional
        输出结果中弱回波的类别编号。
    sf : int, optional
        输出结果中层状回波的类别编号。
    conv : int, optional
        输出结果中对流回波的类别编号。
    estimate_flag : bool, optional
        是否计算高估和低估结果。
    estimate_offset : float, optional
        构造高估和低估场时对原场增减的偏移量。

    返回
    ----
    dict[str, xr.DataArray]
        层状-对流分类结果字典。
    """
    warn(
        "This function will be deprecated in Py-ART 2.0. Please use feature_detection function.",
        DeprecationWarning,
    )

    return feature_detection(
        refl,
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
        min_val_used=min_dBZ_used,
        dB_averaging=dB_averaging,
        remove_small_objects=remove_small_objects,
        min_km2_size=min_km2_size,
        binary_close=False,
        val_for_max_rad=val_for_max_conv_rad,
        max_rad_km=max_conv_rad_km,
        core_val=cs_core,
        nosfcecho=nosfcecho,
        weakecho=weakecho,
        bkgd_val=sf,
        feat_val=conv,
        estimate_flag=estimate_flag,
        estimate_offset=estimate_offset,
    )


def hydroclass_semisupervised(
    refl: xr.DataArray | None = None,
    zdr: xr.DataArray | None = None,
    rhv: xr.DataArray | None = None,
    kdp: xr.DataArray | None = None,
    temp: xr.DataArray | None = None,
    iso0: xr.DataArray | None = None,
    hydro_names=("AG", "CR", "LR", "RP", "RN", "VI", "WS", "MH", "IH/HDG"),
    var_names=("Zh", "ZDR", "KDP", "RhoHV", "relH"),
    mass_centers=None,
    weights=np.array([1.0, 1.0, 1.0, 0.75, 0.5]),
    value: float = 50.0,
    lapse_rate: float = -6.5,
    radar_freq=None,
    temp_ref: str = "temperature",
    compute_entropy: bool = False,
    output_distances: bool = False,
    vectorize: bool = False,
) -> dict[str, xr.DataArray]:
    """
    使用半监督方法进行水凝物分类。

    参数
    ----
    refl, zdr, rhv, kdp : xr.DataArray
        meteva_base 偏振量网格数据。
    temp, iso0 : xr.DataArray, optional
        温度场或相对零度层高度场。
    hydro_names : sequence of str, optional
        各水凝物类别的名称列表。
    var_names : sequence of str, optional
        参与分类的变量名称顺序。
    mass_centers : ndarray, optional
        各类别的质心矩阵。未给定时按频段选择默认质心。
    weights : ndarray, optional
        各变量在距离计算中的权重。
    value : float, optional
        将距离转换为比例时使用的衰减控制参数。
    lapse_rate : float, optional
        温度转换为相对零度层高度时使用的温度垂直递减率。
    radar_freq : float, optional
        雷达频率，单位 Hz，用于选择质心。
    temp_ref : str, optional
        温度相关输入的解释方式，可选 temperature 或 height_over_iso0。
    compute_entropy : bool, optional
        是否计算分类熵。
    output_distances : bool, optional
        是否输出各类别比例场。
    vectorize : bool, optional
        是否使用向量化距离分类计算。

    返回
    ----
    dict[str, xr.DataArray]
        水凝物分类及附加结果字典。

    输出字典field_dict包含以下键:

    hydro:字典
        水文气象分类。
            -0:未分类
            1:聚集物
            -2:冰晶
            3:小雨
            4:冰缘颗粒
            5:雨水
            6:垂直定向冰
            7:湿雪
            8:冰雹融化
            9:干雹或高密度雨滴

    如果 compute_entropy为真:
    熵:字典
        水文气象物态解混的香农熵

    如果 output_distances 为 True:
    propX:字典
        给定水文气象类别的极化分解中雷达体积的比例
    """
    input_grids = {}
    grids = []
    for var_name in var_names:
        if var_name == "Zh":
            if refl is None:
                raise ValueError("refl must be provided when 'Zh' is in var_names")
            input_grids[var_name] = _check_single_context(
                refl, valid_val=(-200.0, 200.0, np.nan)
            )
        elif var_name == "ZDR":
            if zdr is None:
                raise ValueError("zdr must be provided when 'ZDR' is in var_names")
            input_grids[var_name] = _check_single_context(
                zdr, valid_val=(-20.0, 20.0, np.nan)
            )
        elif var_name == "KDP":
            if kdp is None:
                raise ValueError("kdp must be provided when 'KDP' is in var_names")
            input_grids[var_name] = _check_single_context(
                kdp, valid_val=(-20.0, 20.0, np.nan)
            )
        elif var_name == "RhoHV":
            if rhv is None:
                raise ValueError("rhv must be provided when 'RhoHV' is in var_names")
            input_grids[var_name] = _check_single_context(
                rhv, valid_val=(0.0, 1.1, np.nan)
            )
        elif var_name == "relH":
            if temp_ref == "temperature":
                if temp is None:
                    raise ValueError("temp must be provided when 'relH' is in var_names")
                input_grids[var_name] = _check_single_context(
                    temp, valid_val=(-200.0, 100.0, np.nan)
                )
            else:
                if iso0 is None:
                    raise ValueError("iso0 must be provided when 'relH' is in var_names")
                input_grids[var_name] = _check_single_context(
                    iso0, valid_val=(-10000.0, 10000.0, np.nan)
                )
        else:
            raise ValueError(
                "Valid variable names for hydrometeor classification are: relH, Zh, ZDR, KDP and RhoHV"
            )
        grids.append(input_grids[var_name])

    template_grid = grids[0]

    #检查多个输入网格的水平和时间坐标是否一致。
    if not check_for_xy_coordinates(grids, is_time_match=True):
        raise ValueError("input grid coordinates must be same")

    if mass_centers is None:
        # 先尝试从输入数据属性读取频率；读取不到再使用显式参数 radar_freq。
        frequency = None
        for grid_item in grids:
            freq_attr = grid_item.attrs.get("frequency")
            if freq_attr is None:
                continue
            try:
                frequency = float(np.asarray(freq_attr).squeeze())
                break
            except Exception:
                continue

        if frequency is None:
            frequency = radar_freq

        if frequency is not None:
            mass_centers = _get_mass_centers(frequency)
        else:
            warn(
                "Radar frequency is unknown. Default coefficients for C band will be applied."
            )
            mass_centers = _mass_centers_table()["C"]

    # =====================================
    # 六维网格转算法扫描面
    #
    # 分类函数按 (nrays, nbins) 形式处理二维扫描数据。
    # 这里把 meteva_base 的六维网格统一展平，
    # 待分类结束后再恢复原形状。
    # =====================================
    fields_dict = {}
    original_shape = template_grid.values.shape
    for var_name in var_names:
        if var_name == "Zh":
            fields_dict[var_name], _ = _flatten_to_scan(input_grids[var_name])
        elif var_name == "ZDR":
            fields_dict[var_name], _ = _flatten_to_scan(input_grids[var_name])
        elif var_name == "KDP":
            fields_dict[var_name], _ = _flatten_to_scan(input_grids[var_name])
        elif var_name == "RhoHV":
            fields_dict[var_name], _ = _flatten_to_scan(input_grids[var_name])
        elif var_name == "relH":
            if temp_ref == "temperature":
                temp_scan, _ = _flatten_to_scan(input_grids[var_name])
                fields_dict[var_name] = temp_scan * (1000.0 / lapse_rate)
            else:
                fields_dict[var_name], _ = _flatten_to_scan(input_grids[var_name])

    # =====================================
    # 标准化与距离分类
    #
    # 每个变量都要先标准化到 [-1, 1]，
    # 再与对应频段的质心做距离比较，
    # 从而得到最终分类结果。
    # =====================================
    mc_std = np.empty(np.shape(mass_centers), dtype=np.float32)
    for i, var_name in enumerate(var_names):
        mc_std[:, i] = _standardize(mass_centers[:, i].copy(), var_name)
        fields_dict[var_name] = _standardize(fields_dict[var_name].copy(), var_name)

    t_vals = None
    if compute_entropy:
        t_vals = _compute_coeff_transform(mc_std, weights=weights, value=value)

    if vectorize:
        hydroclass_data, entropy_data, prop_data = _assign_to_class_scan(
            fields_dict, mc_std, var_names=var_names, weights=weights, t_vals=t_vals
        )
    else:
        hydroclass_data, entropy_data, prop_data = _assign_to_class(
            fields_dict, mc_std, var_names=var_names, weights=weights, t_vals=t_vals
        )

    # 分类结果先恢复为完整六维网格，
    # 再统一封装为 meteva_base.grid_data。
    results = {
        "hydro": _build_full_result(
            template_grid,
            hydroclass_data,
            original_shape,
            name="radar_echo_classification",
            long_name="水凝物分类",
            extra_attrs={
                "labels": ["NC", *hydro_names],
                "ticks": list(range(0, len(hydro_names) + 1)),
                "boundaries": [i - 0.5 for i in range(0, len(hydro_names) + 2)],
            },
        )
    }

    if compute_entropy:
        results["entropy"] = _build_full_result(
            template_grid,
            entropy_data,
            original_shape,
            name="hydroclass_entropy",
            long_name="水凝物分类熵",
        )

        if output_distances and prop_data is not None:
            for i, hydro_name in enumerate(hydro_names):
                field_name = "proportion_" + hydro_name
                results[field_name] = _build_full_result(
                    template_grid,
                    prop_data[:, :, i],
                    original_shape,
                    name=field_name,
                    long_name=field_name,
                )

    return results


def conv_strat_raut(
    refl: xr.DataArray,
    cappi_level: float | int = 0,
    zr_a: float = 200,
    zr_b: float = 1.6,
    core_wt_threshold: float = 5,
    conv_wt_threshold: float = 1.5,
    conv_scale_km: float = 25,
    min_reflectivity: float = 5,
    conv_min_refl: float = 25,
    conv_core_threshold: float = 42,
    override_checks: bool = False,
    dx=None,
    dy=None,
) -> xr.DataArray:
    """
    使用小波多分辨率方法进行层状-对流分类。

    参数
    ----
    refl : xr.DataArray
        meteva_base 反射率网格数据。
    cappi_level : float or int, optional
        分类层，可传高度值或层索引。
    zr_a, zr_b : float, optional
        Z-R 关系式系数。
    core_wt_threshold : float, optional
        对流核心与混合回波之间的小波阈值。
    conv_wt_threshold : float, optional
        对流与层状回波之间的小波阈值。
    conv_scale_km : float, optional
        对流尺度与层状尺度的分割尺度，单位千米。
    min_reflectivity : float, optional
        参与分类的最小反射率阈值。
    conv_min_refl : float, optional
        始终视为非对流的反射率上限。
    conv_core_threshold : float, optional
        判定对流核心的反射率阈值。
    override_checks : bool, optional
        是否跳过参数取值范围检查。
    dx, dy : float, optional
        水平分辨率，单位米。未给定时根据经纬度坐标近似估算。

    返回
    ----
    xr.DataArray
        单层小波分类结果。
    """
    refl_grid = _check_single_context(refl, valid_val=(-200.0, 200.0, np.nan))
    dx, dy = _get_dx_dy(refl_grid, dx=dx, dy=dy)
    if not np.isclose(dx, dy):
        warn(
            "Grid resolution dx and dy should be comparable for correct results.",
            UserWarning,
        )

    levels = np.asarray(refl_grid.level.values, dtype=np.float32)
    if isinstance(cappi_level, (int, np.integer)) and 0 <= int(cappi_level) < levels.size:
        level_index = int(cappi_level)
    else:
        # 当传入高度值而非索引时，选取最接近该高度的层。
        level_index = int(np.argmin(np.abs(levels - float(cappi_level))))

    scale_break = calc_scale_break(res_meters=dx, conv_scale_km=conv_scale_km)
    scale_break_km = (2 ** (scale_break - 1)) * dx / 1000

    if not override_checks:
        conv_core_threshold = max(40, conv_core_threshold)
        core_wt_threshold = max(4, min(core_wt_threshold, 6))
        conv_wt_threshold = max(1, min(conv_wt_threshold, 2))
        conv_scale_km = max(16, min(conv_scale_km, 32))
        min_reflectivity = max(0, min_reflectivity)
        conv_min_refl = max(25, min(conv_min_refl, 30))

    template = refl_grid.isel(member=[0], level=[level_index], time=[0], dtime=[0])
    # 保留缺测掩码，避免缺测点被当作有效值参与小波分类。
    dbz_data = np.ma.masked_invalid(
        np.asanyarray(template.values[0, 0, 0, 0, :, :], dtype=np.float32)
    )

    # =====================================
    # 小波分类主流程
    #
    # 先计算给定尺度分割下的小波和场，
    # 再依据波谱强度与反射率阈值将格点重新标记为
    # 层状、混合或对流。
    # =====================================
    reclass = wavelet_reclass(
        dbz_data=dbz_data,
        zr_a=zr_a,
        zr_b=zr_b,
        core_wt_threshold=core_wt_threshold,
        conv_wt_threshold=conv_wt_threshold,
        scale_break=scale_break,
        min_reflectivity=min_reflectivity,
        conv_min_refl=conv_min_refl,
        conv_core_threshold=conv_core_threshold,
    )

    return _build_level_result(
        template,
        np.ma.asarray(reclass).astype(np.float32).filled(np.nan),
        name="wt_reclass",
        long_name="基于小波的多分辨率雷达回波分类",
        valid_min=0,
        valid_max=3,
        extra_attrs={
            "classification_description": "0: 未分类, 1: 层状, 2: 过渡混合, 3: 对流核心",
            "parameters": {
                "cappi_level": int(level_index),
                "zr_a": zr_a,
                "zr_b": zr_b,
                "core_wt_threshold": core_wt_threshold,
                "conv_wt_threshold": conv_wt_threshold,
                "conv_scale_km": conv_scale_km,
                "scale_break_used": int(scale_break_km),
                "min_reflectivity": min_reflectivity,
                "conv_min_refl": conv_min_refl,
                "conv_core_threshold": conv_core_threshold,
            },
        },
    )


def ma_broadcast_to(array, tup):
    """
    Is used to guarantee that a masked array can be broadcasted without
    loosing the mask

    Parameters
    ----------
    array : Numpy masked array or normal array
    tup : shape as tuple

    Returns
    -------
    broadcasted_array
        The broadcasted numpy array including its mask if available
        otherwise only the broadcasted array is returned

    """
    broadcasted_array = np.broadcast_to(array, tup)

    if np.ma.is_masked(array):
        initial_mask = np.ma.getmask(array)
        initial_fill_value = array.fill_value
        broadcasted_mask = np.broadcast_to(initial_mask, tup)
        return np.ma.array(
            broadcasted_array, mask=broadcasted_mask, fill_value=initial_fill_value
        )

    return broadcasted_array


def _standardize(data, field_name, mx=None, mn=None):
    """
    将雷达变量标准化到 [-1, 1] 区间。

    Parameters
    ----------
    data : array
        雷达变量场。
    field_name : str
        变量名称（relH、Zh、ZDR、KDP 或 RhoHV）。
    mx, mn : floats or None, optional
        数据上下界。未给定时按变量默认阈值表取值。

    Returns
    -------
    field_std : array
        标准化后的变量场。

    """
    if field_name == "relH":
        field_std = 2.0 / (1.0 + np.ma.exp(-0.005 * data)) - 1.0
        return field_std

    if (mx is None) or (mn is None):
        dlimits_dict = _data_limits_table()
        if field_name not in dlimits_dict:
            raise ValueError(
                "Field "
                + field_name
                + " unknown. "
                + "Valid field names for standardizing are: "
                + "relH, Zh, ZDR, KDP and RhoHV"
            )
        mx, mn = dlimits_dict[field_name]

    if field_name == "KDP":
        data[data < -0.5] = -0.5
        data = 10.0 * np.ma.log10(data + 0.6)
    elif field_name == "RhoHV":
        # 避免 log 计算出现无穷值。
        data[data > 1.0] = 1.0
        data = 10.0 * np.ma.log10(1.0000000000001 - data)

    mask = np.ma.getmaskarray(data)
    field_std = 2.0 * (data - mn) / (mx - mn) - 1.0
    field_std[data < mn] = -1.0
    field_std[data > mx] = 1.0
    field_std[mask] = np.ma.masked

    return field_std


def _assign_to_class(
    fields_dict,
    mass_centers,
    var_names=("Zh", "ZDR", "KDP", "RhoHV", "relH"),
    weights=np.array([1.0, 1.0, 1.0, 0.75, 0.5]),
    t_vals=None,
):
    """
    根据变量与质心距离为每个距离库点分配水凝物类别。

    Parameters
    ----------
    fields_dict : dict
        已标准化到 [-1, 1] 的输入变量字典。
    mass_centers : matrix
        已标准化的类别质心矩阵，形状为 (nclasses, nvariables)。
    var_names : array of str
        变量名称列表。
    weights : array
        各变量权重，长度为 nvariables。
    t_vals : array
        距离到比例变换系数，长度为 nclasses。

    Returns
    -------
    hydroclass : int array
        分类结果索引。
    entropy : float array
        分类熵。
    t_dist : float matrix
        当计算熵时返回各类别的变换后距离，
        可视作各水凝物占比的代理量，形状为 (nrays, nbins, nclasses)。

    """
    # 逐条扫描线计算到各类质心的距离，
    # 缺测值不参与距离累加。
    nrays = fields_dict[var_names[0]].shape[0]
    nbins = fields_dict[var_names[0]].shape[1]
    nclasses = mass_centers.shape[0]
    nvariables = mass_centers.shape[1]
    dtype = fields_dict[var_names[0]].dtype

    hydroclass = np.ma.empty((nrays, nbins), dtype=np.uint8)
    entropy = None
    t_dist = None
    if t_vals is not None:
        entropy = np.ma.empty((nrays, nbins), dtype=dtype)
        t_dist = np.ma.masked_all((nrays, nbins, nclasses), dtype=dtype)

    for ray in range(nrays):
        data = []
        for var_name in var_names:
            data.append(fields_dict[var_name][ray, :])
        data = np.ma.array(data, dtype=dtype)
        weights_mat = np.broadcast_to(
            weights.reshape(nvariables, 1), (nvariables, nbins)
        )
        dist = np.ma.zeros((nclasses, nbins), dtype=dtype)

        mask = np.ma.getmaskarray(fields_dict[var_names[0]][ray, :])
        for i in range(nclasses):
            centroids_class = mass_centers[i, :]
            centroids_class = np.broadcast_to(
                centroids_class.reshape(nvariables, 1), (nvariables, nbins)
            )
            dist_ray = np.ma.sqrt(
                np.ma.sum(((centroids_class - data) ** 2.0) * weights_mat, axis=0)
            )
            dist_ray[mask] = np.ma.masked
            dist[i, :] = dist_ray

        # argsort 后第一个类别即最近质心对应的水凝物类型。
        class_vec = dist.argsort(axis=0, fill_value=10e40)
        hydroclass_ray = (class_vec[0, :] + 1).astype(np.uint8)
        hydroclass_ray[mask] = 0
        hydroclass[ray, :] = hydroclass_ray

        if t_vals is None:
            continue

        # 若要求熵，则进一步将距离映射为“相对占比”，
        # 并计算分类熵。
        t_vals_ray = np.ma.masked_where(mask, t_vals[class_vec[0, :]])
        t_vals_ray = ma_broadcast_to(t_vals_ray.reshape(1, nbins), (nclasses, nbins))
        t_dist_ray = np.ma.exp(-t_vals_ray * dist)

        dist_total = np.ma.sum(t_dist_ray, axis=0)
        dist_total = ma_broadcast_to(dist_total.reshape(1, nbins), (nclasses, nbins))
        t_dist_ray /= dist_total

        entropy_ray = -np.ma.sum(
            t_dist_ray * np.ma.log(t_dist_ray) / np.ma.log(nclasses), axis=0
        )
        entropy_ray[mask] = np.ma.masked
        entropy[ray, :] = entropy_ray

        t_dist[ray, :, :] = np.ma.transpose(t_dist_ray)

    if t_vals is not None:
        t_dist *= 100.0

    return hydroclass, entropy, t_dist


def _assign_to_class_scan(
    fields_dict,
    mass_centers,
    var_names=("Zh", "ZDR", "KDP", "RhoHV", "relH"),
    weights=np.array([1.0, 1.0, 1.0, 0.75, 0.5]),
    t_vals=None,
):
    """
    根据变量与质心距离为每个距离库点分配水凝物类别。
    该版本一次性处理整幅扫描数据。

    Parameters
    ----------
    fields_dict : dict
        已标准化到 [-1, 1] 的输入变量字典。
    mass_centers : matrix
        已标准化的类别质心矩阵。
    var_names : array of str
        变量名称列表。
    weights : array
        各变量权重。
    t_vals : matrix
        距离到比例变换系数。

    Returns
    -------
    hydroclass : int array
        分类结果索引。
    entropy : float array
        分类熵。
    t_dist : float matrix
        当计算熵时返回各类别的变换后距离，
        可视作各水凝物占比的代理量，形状为 (nrays, nbins, nclasses)。

    """
    # 向量化版本一次处理整幅扫描数据，
    # 逻辑与 _assign_to_class 相同，
    # 只是把逐条扫描线循环改成了整体矩阵运算。
    nrays = fields_dict[var_names[0]].shape[0]
    nbins = fields_dict[var_names[0]].shape[1]
    nclasses = mass_centers.shape[0]
    nvariables = mass_centers.shape[1]
    dtype = fields_dict[var_names[0]].dtype

    data = []
    for var_name in var_names:
        data.append(fields_dict[var_name])
    data = np.ma.array(data, dtype=dtype)
    weights_mat = np.broadcast_to(
        weights.reshape(nvariables, 1, 1), (nvariables, nrays, nbins)
    )

    mask = np.ma.getmaskarray(fields_dict[var_names[0]])
    dist = np.ma.zeros((nrays, nbins, nclasses), dtype=dtype)
    t_dist = None
    entropy = None
    for i in range(nclasses):
        centroids_class = mass_centers[i, :]
        centroids_class = np.broadcast_to(
            centroids_class.reshape(nvariables, 1, 1), (nvariables, nrays, nbins)
        )
        dist_aux = np.ma.sqrt(
            np.ma.sum(((centroids_class - data) ** 2.0) * weights_mat, axis=0)
        )
        dist_aux[mask] = np.ma.masked
        dist[:, :, i] = dist_aux

    del data
    del weights_mat

    class_vec = dist.argsort(axis=-1, fill_value=10e40)
    hydroclass = np.ma.asarray(class_vec[:, :, 0] + 1, dtype=np.uint8)
    hydroclass[mask] = 0

    if t_vals is not None:
        t_vals_aux = np.ma.masked_where(mask, t_vals[class_vec[:, :, 0]])
        t_vals_aux = ma_broadcast_to(
            t_vals_aux.reshape(nrays, nbins, 1), (nrays, nbins, nclasses)
        )
        t_dist = np.ma.exp(-t_vals_aux * dist)
        del t_vals_aux

        dist_total = np.ma.sum(t_dist, axis=-1)
        dist_total = ma_broadcast_to(
            dist_total.reshape(nrays, nbins, 1), (nrays, nbins, nclasses)
        )
        t_dist /= dist_total
        del dist_total

        entropy = -np.ma.sum(t_dist * np.ma.log(t_dist) / np.ma.log(nclasses), axis=-1)
        entropy[mask] = np.ma.masked

        t_dist *= 100.0

    return hydroclass, entropy, t_dist


def _get_mass_centers(freq):
    """
    获取给定频率对应的水凝物分类质心。

    Parameters
    ----------
    freq : float
        雷达频率，单位 Hz。

    Returns
    -------
    mass_centers : ndarray 2D
        各水凝物类别与变量对应的质心矩阵，
        形状为 (nclasses, nvariables)。

    """
    mass_centers_dict = _mass_centers_table()

    freq_band = get_freq_band(freq)
    if (freq_band is not None) and (freq_band in mass_centers_dict):
        return mass_centers_dict[freq_band]

    if freq < 4e9:
        freq_band_aux = "C"
    elif freq > 12e9:
        freq_band_aux = "X"

    mass_centers = mass_centers_dict[freq_band_aux]
    warn(
        "Radar frequency out of range. "
        + "Centroids only valid for C or X band. "
        + freq_band_aux
        + " band centroids will be applied"
    )

    return mass_centers


def _mass_centers_table():
    """
    定义不同频段对应的水凝物分类质心查找表。

    Returns
    -------
    mass_centers_dict : dict
        频段到质心矩阵的映射字典。

    """
    nclasses = 9
    nvariables = 5
    mass_centers_c = np.zeros((nclasses, nvariables))
    mass_centers_x = np.zeros((nclasses, nvariables))

    mass_centers_dict = dict()
    # C 波段质心（由 MeteoSwiss Albis 雷达样本推导）。
    #                       Zh        ZDR     kdp   RhoHV    delta_Z
    mass_centers_c[0, :] = [13.5829, 0.4063, 0.0497, 0.9868, 1330.3]  # DS
    mass_centers_c[1, :] = [02.8453, 0.2457, 0.0000, 0.9798, 0653.8]  # CR
    mass_centers_c[2, :] = [07.6597, 0.2180, 0.0019, 0.9799, -1426.5]  # LR
    mass_centers_c[3, :] = [31.6815, 0.3926, 0.0828, 0.9978, 0535.3]  # GR
    mass_centers_c[4, :] = [39.4703, 1.0734, 0.4919, 0.9876, -1036.3]  # RN
    mass_centers_c[5, :] = [04.8267, -0.5690, 0.0000, 0.9691, 0869.8]  # VI
    mass_centers_c[6, :] = [30.8613, 0.9819, 0.1998, 0.9845, -0066.1]  # WS
    mass_centers_c[7, :] = [52.3969, 2.1094, 2.4675, 0.9730, -1550.2]  # MH
    mass_centers_c[8, :] = [50.6186, -0.0649, 0.0946, 0.9904, 1179.9]  # IH/HDG

    mass_centers_dict.update({"C": mass_centers_c})

    # X 波段质心（由 MeteoSwiss DX50 雷达样本推导）。
    #                       Zh        ZDR     kdp    RhoHV   delta_Z
    mass_centers_x[0, :] = [19.0770, 0.4139, 0.0099, 0.9841, 1061.7]  # DS
    mass_centers_x[1, :] = [03.9877, 0.5040, 0.0000, 0.9642, 0856.6]  # CR
    mass_centers_x[2, :] = [20.7982, 0.3177, 0.0004, 0.9858, -1375.1]  # LR
    mass_centers_x[3, :] = [34.7124, -0.3748, 0.0988, 0.9828, 1224.2]  # GR
    mass_centers_x[4, :] = [33.0134, 0.6614, 0.0819, 0.9802, -1169.8]  # RN
    mass_centers_x[5, :] = [08.2610, -0.4681, 0.0000, 0.9722, 1100.7]  # VI
    mass_centers_x[6, :] = [35.1801, 1.2830, 0.1322, 0.9162, -0159.8]  # WS
    mass_centers_x[7, :] = [52.4539, 2.3714, 1.1120, 0.9382, -1618.5]  # MH
    mass_centers_x[8, :] = [44.2216, -0.3419, 0.0687, 0.9683, 1272.7]  # IH/HDG

    mass_centers_dict.update({"X": mass_centers_x})

    return mass_centers_dict


def _data_limits_table():
    """
    定义标准化时各变量使用的数据上下界。

    Returns
    -------
    dlimits_dict : dict
        各变量上下界映射字典。

    """
    dlimits_dict = dict()
    dlimits_dict.update({"Zh": (60.0, -10.0)})
    dlimits_dict.update({"ZDR": (5.0, -1.5)})
    dlimits_dict.update({"KDP": (7.0, -10.0)})
    dlimits_dict.update({"RhoHV": (-5.23, -50.0)})
    dlimits_dict.update({"RelH": (5000.0, -5000.0)})

    return dlimits_dict


def get_freq_band(freq):
    """
    根据频率返回频段名称（S、C、X 等）。

    Parameters
    ----------
    freq : float
        雷达频率，单位 Hz。

    Returns
    -------
    freq_band : str
        频段名称。

    """
    if freq >= 2e9 and freq < 4e9:
        return "S"
    if freq >= 4e9 and freq < 8e9:
        return "C"
    if freq >= 8e9 and freq <= 12e9:
        return "X"

    warn("Unknown frequency band")

    return None


def _compute_coeff_transform(
    mass_centers, weights=np.array([1.0, 1.0, 1.0, 0.75, 0.5]), value=50.0
):
    """
    计算距离到比例变换所需系数。

    Parameters
    ----------
    mass_centers : ndarray 2D
        各类别和变量的质心矩阵，形状为 (nclasses, nvariables)。
    weights : array
        各变量权重，长度为 nvariables。
    value : float
        控制距离变换衰减速率的参数。

    Returns
    -------
    t_vals : ndarray 1D
        各类别对应的距离变换系数，长度为 nclasses。

    """
    nclasses, nvariables = np.shape(mass_centers)
    t_vals = np.empty((nclasses, nclasses), dtype=mass_centers.dtype)
    for i in range(nclasses):
        weights_mat = np.broadcast_to(
            weights.reshape(1, nvariables), (nclasses, nvariables)
        )
        centroids_class = mass_centers[i, :]
        centroids_class = np.broadcast_to(
            centroids_class.reshape(1, nvariables), (nclasses, nvariables)
        )
        t_vals[i, :] = np.sqrt(
            np.sum(
                weights_mat * np.power(np.abs(centroids_class - mass_centers), 2.0),
                axis=1,
            )
        )

    # 取每类距离中的次小值（最小值为自身距离 0）。
    t_vals = np.sort(t_vals, axis=-1)[:, 1]
    t_vals = np.log(value) / t_vals

    return t_vals


def _check_single_context(grid_data: xr.DataArray, valid_val=(-1000.0, 1000.0, np.nan)) -> xr.DataArray:
    """检查输入网格是否只有一个 member/time/dtime。"""
    normalized = check_for_meb_griddata(
        grid_data,
        is_single=False,
        valid_val=valid_val,
    )

    if normalized.member.size != 1:
        raise ValueError("griddata member dimension must contain exactly one value")
    if normalized.time.size != 1:
        raise ValueError("griddata time dimension must contain exactly one value")
    if normalized.dtime.size != 1:
        raise ValueError("griddata dtime dimension must contain exactly one value")

    return normalized


def _get_dx_dy(grid_data: xr.DataArray, dx=None, dy=None, x_m=None, y_m=None):
    """获取水平分辨率，单位米。"""
    if x_m is None or y_m is None:
        x_m, y_m = get_xy_in_meters(grid_data)

    if dx is None:
        if x_m.size < 2:
            raise ValueError("x/lon dimension must contain at least two points when dx is None")
        _warn_if_nonuniform_spacing(x_m, axis_name="x/lon")
        dx = np.mean(np.abs(np.diff(x_m)))

    if dy is None:
        if y_m.size < 2:
            raise ValueError("y/lat dimension must contain at least two points when dy is None")
        _warn_if_nonuniform_spacing(y_m, axis_name="y/lat")
        dy = np.mean(np.abs(np.diff(y_m)))

    return float(dx), float(dy)


def _warn_if_nonuniform_spacing(coord_1d: np.ndarray, axis_name: str, rel_tol: float = 0.05):
    """
    对一维坐标做等距性检查。
    原算法默认输入为近似等距笛卡尔网格，若明显不等距则给出告警。
    """
    diffs = np.abs(np.diff(np.asarray(coord_1d, dtype=np.float64)))
    diffs = diffs[np.isfinite(diffs)]
    if diffs.size == 0:
        return
    baseline = float(np.nanmedian(diffs))
    if baseline <= 0.0:
        return
    rel_spread = float(np.nanmax(np.abs(diffs - baseline)) / baseline)
    if rel_spread > rel_tol:
        raise ValueError(
            f"{axis_name} coordinate spacing is non-uniform "
            f"(max relative spread={rel_spread:.3f}); "
            "echo_class algorithms require approximately Cartesian/equidistant grid."
        )


def _build_level_result(
    template: xr.DataArray,
    data_2d: np.ndarray,
    name: str,
    long_name: str,
    valid_min: int,
    valid_max: int,
    extra_attrs=None,
) -> xr.DataArray:
    """将二维分类结果封装为 meteva_base 网格数据。"""
    if extra_attrs is None:
        extra_attrs = {}

    data_6d = np.asarray(data_2d, dtype=np.float32)[None, None, None, None, :, :]
    result = build_griddata_like(template, data_6d)
    result.name = name
    result.attrs["long_name"] = long_name
    result.attrs["valid_min"] = valid_min
    result.attrs["valid_max"] = valid_max
    result.attrs.update(extra_attrs)

    return result


def _flatten_to_scan(grid_data: xr.DataArray):
    """将六维网格展平为算法计算使用的二维数组。"""

    # 最后一维保留为“距离/网格点”方向，
    # 其余维统一压平，便于复用原算法。
    values = np.ma.masked_invalid(np.asarray(grid_data.values, dtype=np.float32))
    original_shape = values.shape
    scan = values.reshape(-1, original_shape[-1])
    return scan, original_shape


def _build_full_result(
    template: xr.DataArray,
    data_scan,
    original_shape,
    name: str,
    long_name: str,
    extra_attrs=None,
):
    """将展平计算结果恢复为完整网格。"""
    if extra_attrs is None:
        extra_attrs = {}

    # 原算法可能返回 masked array，
    # 这里统一转回普通 ndarray + nan，
    # 再恢复为 meteva_base 使用的六维网格形状。
    if np.ma.isMaskedArray(data_scan):
        restored = np.ma.filled(data_scan, np.nan).reshape(original_shape)
    else:
        restored = np.asarray(data_scan).reshape(original_shape)

    result = build_griddata_like(template, restored.astype(np.float32, copy=False))
    result.name = name
    result.attrs["long_name"] = long_name
    result.attrs.update(extra_attrs)

    return result


__all__ = [
    "SteinerConvStratPlugin",
    "FeatureDetectionPlugin",
    "HydroclassSemisupervisedPlugin",
    "ConvStratRautPlugin",
    "steiner_conv_strat",
    "feature_detection",
    "conv_strat_yuter",
    "hydroclass_semisupervised",
    "conv_strat_raut",
]
