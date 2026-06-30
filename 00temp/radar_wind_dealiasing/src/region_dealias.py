#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""基于连通区域合并的速度退模糊算法。"""

from __future__ import annotations

import warnings

import numpy as np
import scipy.ndimage as ndimage
import xarray as xr
from scipy.optimize import fmin_l_bfgs_b

from ...plugin_base import BasePlugin
from ..utils.utils import (
    attach_gate_lonlat,
    build_latlon_griddata_from_template,
    build_griddata_like,
    check_for_meb_griddata,
    check_for_xy_coordinates,
    infer_radar_location_from_attrs,
    infer_target_lonlat_grid,
    mask_outside_radar_coverage,
    remap_gate_data_to_latlon_grid,
)

from ._common_dealias import (
    _as_2d_array,
    _parse_gatefilter,
    _parse_nyquist_vel,
    _parse_rays_wrap_around,
    _set_limits,
)
from ._fast_edge_finder import _fast_edge_finder
from .grid_gate_filter import GridGateFilter


class RegionDealiasPlugin(BasePlugin):
    """`dealias_region_based` 的插件封装。

    插件层只负责参数收口、输入转发和地理后处理，不重复实现核心
    退模糊逻辑。核心连通域展开、分段合并、参考速度锚定等步骤都
    仍然保留在 :func:`dealias_region_based` 中。

    插件额外提供的能力主要有两类：
    1. 统一接收 ``meteva_base`` 网格输入，并将过滤器与辅助参数转发给核心算法。
    2. 在需要时为结果补充经纬度信息，并重映射到规则经纬网格。
    """

    def __init__(
        self,
        interval_splits: int = 3,
        interval_limits=None,
        skip_between_rays: int = 100,
        skip_along_ray: int = 100,
        centered: bool = True,
        nyquist_velocity=None,
        gatefilter=False,
        min_ncp: float | None = 0.5,
        min_rhv: float | None = None,
        min_refl: float | None = -20.0,
        max_refl: float | None = 100.0,
        rays_wrap_around: bool | None = None,
        keep_original: bool = False,
        set_limits: bool = True,
        data_name: str = "corrected_velocity",
        attrs: dict | None = None,
        radar_lon: float | None = None,
        radar_lat: float | None = None,
        elevation_deg: float = 0.0,
        azimuth_deg=None,
        range_m=None,
        target_lon=None,
        target_lat=None,
        geo_method: str = "nearest",
        geo_resolution_deg: float | None = 0.01,
        geo_nlon: int | None = None,
        geo_nlat: int | None = None,
        auto_remap_to_latlon: bool = False,
    ) -> None:
        """初始化区域退模糊插件。

        参数
        ----
        interval_splits : int, optional
            Nyquist 区间划分数量。值越大，速度分段越细。
        interval_limits : array-like or None, optional
            自定义速度分段边界。若为 ``None``，则由 Nyquist 速度自动生成。
        skip_between_rays, skip_along_ray : int, optional
            区域连通判定时允许跨越的方位向和径向格点数。
        centered : bool, optional
            是否将最终圈数整体平移到以 0 为中心。
        nyquist_velocity : float, array-like or None, optional
            Nyquist 速度。可以是标量，也可以是与输入前四维一致的数组。
        gatefilter : None, False or GridGateFilter, optional
            门限过滤器配置。
            ``False`` 表示不使用过滤器；
            ``None`` 表示由 ``refl``、``ncp``、``rhv`` 和阈值参数在内部构建；
            ``GridGateFilter`` 表示直接使用外部已构建好的过滤器。
        min_ncp, min_rhv, min_refl, max_refl : float or None, optional
            当 ``gatefilter=None`` 时，用于构建过滤器的阈值参数。
        rays_wrap_around : bool or None, optional
            方位向是否首尾相接。未指定时由输入网格属性自动判断。
        keep_original : bool, optional
            对于被过滤的格点，是否保留原始输入值。
        set_limits : bool, optional
            是否在结果属性中写入 ``valid_min`` 和 ``valid_max``。
        data_name : str, optional
            输出结果的数据名称。
        attrs : dict or None, optional
            需要附加到输出结果中的额外属性。
        radar_lon, radar_lat : float or None, optional
            雷达站点经纬度，用于后续地理重映射。
        elevation_deg : float, optional
            仰角，用于构造地理坐标时的局地几何近似。
        azimuth_deg : array-like or None, optional
            方位角坐标。若给定，可用于更精确地重建地理位置。
        range_m : array-like or None, optional
            径向距离坐标。单位应为米；若输入已有单位属性，也会按属性转换。
        target_lon, target_lat : array-like or None, optional
            目标经纬网格范围，用于指定重映射区域。
        geo_method : str, optional
            地理重映射方法，当前通常使用 ``nearest`` 或相近策略。
        geo_resolution_deg : float or None, optional
            目标经纬网格分辨率。若同时提供 ``geo_nlon`` / ``geo_nlat``，
            该参数可不使用。
        geo_nlon, geo_nlat : int or None, optional
            目标经纬网格的经向和纬向格点数。
        auto_remap_to_latlon : bool, optional
            是否在插件返回前自动重映射到规则经纬网格。
        """
        self.kwargs = {
            "interval_splits": interval_splits,
            "interval_limits": interval_limits,
            "skip_between_rays": skip_between_rays,
            "skip_along_ray": skip_along_ray,
            "centered": centered,
            "nyquist_velocity": nyquist_velocity,
            "gatefilter": gatefilter,
            "min_ncp": min_ncp,
            "min_rhv": min_rhv,
            "min_refl": min_refl,
            "max_refl": max_refl,
            "rays_wrap_around": rays_wrap_around,
            "keep_original": keep_original,
            "set_limits": set_limits,
            "data_name": data_name,
            "attrs": attrs,
            "radar_lon": radar_lon,
            "radar_lat": radar_lat,
            "elevation_deg": elevation_deg,
            "azimuth_deg": azimuth_deg,
            "range_m": range_m,
            "target_lon": target_lon,
            "target_lat": target_lat,
            "geo_method": geo_method,
            "geo_resolution_deg": geo_resolution_deg,
            "geo_nlon": geo_nlon,
            "geo_nlat": geo_nlat,
            "auto_remap_to_latlon": auto_remap_to_latlon,
        }

    def process(
        self,
        velocity: xr.DataArray,
        ref_velocity: xr.DataArray | None = None,
        refl: xr.DataArray | None = None,
        ncp: xr.DataArray | None = None,
        rhv: xr.DataArray | None = None,
    ) -> xr.DataArray:
        """执行退模糊并按需完成地理后处理。

        参数
        ----
        velocity : xr.DataArray
            待退模糊的速度场。
        ref_velocity : xr.DataArray or None, optional
            参考速度场，用于区域合并后的结果锚定。
        refl, ncp, rhv : xr.DataArray or None, optional
            用于构建网格过滤器的辅助物理量。

        返回
        ----
        xr.DataArray
            退模糊后的结果；如果开启了地理重映射，则返回规则经纬网格。
        """
        result = dealias_region_based(
            velocity=velocity,
            ref_velocity=ref_velocity,
            interval_splits=self.kwargs["interval_splits"],
            interval_limits=self.kwargs["interval_limits"],
            skip_between_rays=self.kwargs["skip_between_rays"],
            skip_along_ray=self.kwargs["skip_along_ray"],
            centered=self.kwargs["centered"],
            nyquist_velocity=self.kwargs["nyquist_velocity"],
            gatefilter=self.kwargs["gatefilter"],
            refl=refl,
            ncp=ncp,
            rhv=rhv,
            min_ncp=self.kwargs["min_ncp"],
            min_rhv=self.kwargs["min_rhv"],
            min_refl=self.kwargs["min_refl"],
            max_refl=self.kwargs["max_refl"],
            rays_wrap_around=self.kwargs["rays_wrap_around"],
            keep_original=self.kwargs["keep_original"],
            set_limits=self.kwargs["set_limits"],
            data_name=self.kwargs["data_name"],
            attrs=self.kwargs["attrs"],
        )
        return self._post_process_geo(result, source_grid=velocity)

    def _post_process_geo(self, result: xr.DataArray, source_grid: xr.DataArray | None = None) -> xr.DataArray:
        """为退模糊结果补充地理元信息，并按需重映射到经纬网格。"""
        radar_lon = self.kwargs["radar_lon"]
        radar_lat = self.kwargs["radar_lat"]
        geo_source = result.copy(deep=True)
        if source_grid is not None:
            enriched_attrs = dict(geo_source.attrs)
            for key in (
                "grid_axis_type",
                "azimuth_units",
                "range_units",
                "range_scale_to_m",
                "radar_lon",
                "radar_lat",
                "site_lon",
                "site_lat",
                "longitude",
                "latitude",
            ):
                if key in source_grid.attrs and key not in enriched_attrs:
                    enriched_attrs[key] = source_grid.attrs[key]
            geo_source.attrs = enriched_attrs
            for coord_name in ("lon", "lat"):
                if coord_name in source_grid.coords:
                    geo_source.coords[coord_name].attrs.update(
                        dict(getattr(source_grid.coords[coord_name], "attrs", {}))
                    )
        if radar_lon is None or radar_lat is None:
            inferred_lon, inferred_lat = infer_radar_location_from_attrs(geo_source)
            if (inferred_lon is None or inferred_lat is None) and source_grid is not None:
                source_like = xr.DataArray(
                    np.empty((1, 1, 1, 1, 1, 1), dtype=np.float32),
                    dims=("member", "level", "time", "dtime", "lat", "lon"),
                    coords={
                        "member": [0],
                        "level": [0],
                        "time": [0],
                        "dtime": [0],
                        "lat": [0],
                        "lon": [0],
                    },
                    attrs=dict(source_grid.attrs),
                )
                inferred_lon, inferred_lat = infer_radar_location_from_attrs(source_like)
            if radar_lon is None:
                radar_lon = inferred_lon
            if radar_lat is None:
                radar_lat = inferred_lat

        if radar_lon is None or radar_lat is None:
            return result

        attached = attach_gate_lonlat(
            geo_source,
            radar_lon=float(radar_lon),
            radar_lat=float(radar_lat),
            azimuth_deg=self.kwargs["azimuth_deg"],
            range_m=self.kwargs["range_m"],
            elevation_deg=self.kwargs["elevation_deg"],
        )

        if not (
            self.kwargs["auto_remap_to_latlon"]
            or (
                self.kwargs["target_lon"] is not None
                and self.kwargs["target_lat"] is not None
            )
        ):
            return attached

        resolved_target_lon, resolved_target_lat = infer_target_lonlat_grid(
            gate_lon=attached.coords["gate_lon"].values,
            gate_lat=attached.coords["gate_lat"].values,
            target_lon=self.kwargs["target_lon"],
            target_lat=self.kwargs["target_lat"],
            geo_resolution_deg=self.kwargs["geo_resolution_deg"],
            geo_nlon=self.kwargs["geo_nlon"],
            geo_nlat=self.kwargs["geo_nlat"],
        )
        remapped_values = remap_gate_data_to_latlon_grid(
            values=attached.values.squeeze(),
            gate_lon=attached.coords["gate_lon"].values,
            gate_lat=attached.coords["gate_lat"].values,
            target_lon=resolved_target_lon,
            target_lat=resolved_target_lat,
            method=self.kwargs["geo_method"],
            missing_value=result.attrs.get("missing_value"),
            fill_value=result.attrs.get("_FillValue", np.nan),
        )
        remapped_values = mask_outside_radar_coverage(
            remapped_values,
            target_lon=resolved_target_lon,
            target_lat=resolved_target_lat,
            radar_lon=float(radar_lon),
            radar_lat=float(radar_lat),
            gate_lon=attached.coords["gate_lon"].values,
            gate_lat=attached.coords["gate_lat"].values,
            fill_value=result.attrs.get("_FillValue", np.nan),
        )
        remapped = build_latlon_griddata_from_template(
            attached,
            data_2d=remapped_values,
            target_lon=resolved_target_lon,
            target_lat=resolved_target_lat,
            data_name=attached.name,
        )
        remapped.attrs.update(dict(attached.attrs))
        return remapped


def dealias_region_based(
    velocity: xr.DataArray,
    ref_velocity: xr.DataArray | None = None,
    interval_splits: int = 3,
    interval_limits=None,
    skip_between_rays: int = 100,
    skip_along_ray: int = 100,
    centered: bool = True,
    nyquist_velocity=None,
    gatefilter=False,
    refl: xr.DataArray | None = None,
    ncp: xr.DataArray | None = None,
    rhv: xr.DataArray | None = None,
    min_ncp: float | None = 0.5,
    min_rhv: float | None = None,
    min_refl: float | None = -20.0,
    max_refl: float | None = 100.0,
    rays_wrap_around: bool | None = None,
    keep_original: bool = False,
    set_limits: bool = True,
    data_name: str = "corrected_velocity",
    attrs: dict | None = None,
):
    """基于 meteva_base 网格数据的基于区域雷达速度退模糊实现。

    参数
    ----
    velocity : xr.DataArray
        待退模糊速度场。输入应为 meteva_base 的 ``grid_data``，
        维度前四项为 ``member/level/time/dtime``，后两项为 ``lat/lon``。
    ref_velocity : xr.DataArray or None, optional
        参考速度场。可用于在参考场存在时进行全局或分区锚定。
    interval_splits : int, optional
        Nyquist 区间划分数量。
    interval_limits : array-like or None, optional
        自定义速度分段边界。未给定时由 Nyquist 速度自动生成。
    skip_between_rays, skip_along_ray : int, optional
        区域连通判定时允许跳过的方位向与径向间隔。
    centered : bool, optional
        是否在最终结果中将各分段圈数整体居中到 0。
    nyquist_velocity : float, array-like or None, optional
        Nyquist 速度。若为数组，其形状应与 ``velocity.shape[:4]`` 一致。
    gatefilter : None, False or GridGateFilter, optional
        输入门限过滤器。
        ``False`` 表示不使用过滤器；
        ``None`` 表示在函数内部根据 ``refl``、``ncp``、``rhv`` 等场构建；
        ``GridGateFilter`` 表示直接使用外部已构建好的过滤器。
    refl, ncp, rhv : xr.DataArray or None, optional
        当 ``gatefilter=None`` 时用于构建过滤器的辅助场。
    min_ncp, min_rhv, min_refl, max_refl : float or None, optional
        当 ``gatefilter=None`` 时用于构建过滤器的阈值。
    rays_wrap_around : bool or None, optional
        方位角是否首尾相接。未指定时由输入网格属性判断。
    keep_original : bool, optional
        对于被过滤的格点，是否保留原始输入值。
    set_limits : bool, optional
        是否在结果属性中写入 ``valid_min`` 与 ``valid_max``。
    data_name : str, optional
        输出数据名称。
    attrs : dict or None, optional
        需要附加到输出结果中的属性字典。

    返回
    ----
    xr.DataArray
        退模糊后的 meteva_base 网格数据。
    """
    # =====================================
    # 输入预处理
    #
    # 先规范输入网格，再统一处理缺测和填充值，避免这些元信息在
    # 后续分段展开时被误当成有效速度参与计算。
    # =====================================
    velocity_grid = check_for_meb_griddata(velocity, is_single=False)
    fill_value = float(np.float32(-9999.0))
    for key in ("_FillValue", "missing_value"):
        if key not in velocity_grid.attrs:
            continue
        try:
            fill_value = float(velocity_grid.attrs[key])
            break
        except (TypeError, ValueError):
            continue
    ref_velocity_grid = _normalize_optional_grid(ref_velocity, velocity_grid, "ref_velocity")
    refl_grid = _normalize_optional_grid(refl, velocity_grid, "refl")
    ncp_grid = _normalize_optional_grid(ncp, velocity_grid, "ncp")
    rhv_grid = _normalize_optional_grid(rhv, velocity_grid, "rhv")

    rays_wrap_around = _parse_rays_wrap_around(rays_wrap_around, velocity_grid)
    nyquist_vel = _parse_nyquist_vel(
        nyquist_velocity,
        velocity_grid,
    )

    # 前四维用于区分不同切片，真正参与退模糊的是每个切片上的二维
    # lat/lon 平面。
    corrected_values = np.array(velocity_grid.values, dtype=np.float32, copy=True)
    # 前四维用于区分不同切片，真正参与退模糊的是每个切片上的二维 lat/lon 平面。
    slice_shape = velocity_grid.shape[:4]

    # =====================================
    # 按前四维逐个切片处理。
    # 同一套退模糊逻辑会分别作用于每个 sweep / 时次组合。
    # =====================================
    for slice_index in np.ndindex(slice_shape):
        velocity_slice = _slice_griddata(velocity_grid, slice_index)
        ref_slice = _slice_griddata(ref_velocity_grid, slice_index)
        refl_slice = _slice_griddata(refl_grid, slice_index)
        ncp_slice = _slice_griddata(ncp_grid, slice_index)
        rhv_slice = _slice_griddata(rhv_grid, slice_index)
        gatefilter_slice = _slice_gatefilter_input(
            gatefilter,
            slice_index,
            velocity_grid.shape,
            velocity_slice,
        )

        parsed_gatefilter = _parse_gatefilter(
            gatefilter_slice,
            velocity_slice,
            refl=refl_slice,
            ncp=ncp_slice,
            rhv=rhv_slice,
            min_ncp=min_ncp,
            min_rhv=min_rhv,
            min_refl=min_refl,
            max_refl=max_refl,
        )

        corrected_slice = _dealias_region_based_2d(
            velocity_slice=velocity_slice,
            gatefilter=parsed_gatefilter,
            nyquist_vel=float(nyquist_vel[slice_index]),
            ref_velocity=ref_slice,
            interval_splits=interval_splits,
            interval_limits=interval_limits,
            skip_between_rays=skip_between_rays,
            skip_along_ray=skip_along_ray,
            centered=centered,
            rays_wrap_around=rays_wrap_around,
            keep_original=keep_original,
        )
        corrected_values[slice_index] = corrected_slice

    # 将无效值重新回填为缺测标记，便于后续写出 NetCDF。
    valid_for_limits = np.ma.masked_invalid(corrected_values)
    output_values = np.array(corrected_values, dtype=np.float32, copy=True)
    invalid_mask = ~np.isfinite(output_values)
    if np.any(invalid_mask):
        output_values[invalid_mask] = fill_value

    corrected = build_griddata_like(velocity_grid, output_values)
    corrected.name = data_name

    # Nyquist 速度属性如果在所有切片中一致，直接写成标量更简洁。
    if np.allclose(nyquist_vel, nyquist_vel.flat[0]):
        nyquist_attr: float | np.ndarray = float(nyquist_vel.flat[0])
    else:
        # 若不同切片使用不同 Nyquist，则保留四维数组，避免属性信息丢失。
        nyquist_attr = np.array(nyquist_vel, dtype=np.float32, copy=True)

    result_attrs = {
        "long_name": "dealiased velocity",
        "units": velocity_grid.attrs.get("units", ""),
        "nyquist_velocity": nyquist_attr,
        "_FillValue": fill_value,
    }
    if attrs is not None:
        result_attrs.update(attrs)
    if set_limits:
        _set_limits(valid_for_limits, nyquist_vel, result_attrs)
    corrected.attrs.update(result_attrs)

    return corrected


def _normalize_optional_grid(
    grid_data: xr.DataArray | None,
    velocity_grid: xr.DataArray,
    field_name: str,
) -> xr.DataArray | None:
    """将可选辅助场规范为与速度场对齐的网格数据。"""
    if grid_data is None:
        return None

    normalized = check_for_meb_griddata(grid_data, is_single=False)
    # 辅助场虽然不直接参与展开求解，但必须与速度场严格共网格。
    if not check_for_xy_coordinates([velocity_grid, normalized], is_time_match=True):
        raise ValueError(f"velocity and {field_name} grid coordinates must be same")
    return normalized


def _slice_griddata(
    grid_data: xr.DataArray | None,
    slice_index: tuple[int, int, int, int],
) -> xr.DataArray | None:
    """按前四维切片辅助场；若未提供则保持 ``None``。"""
    if grid_data is None:
        return None

    member_idx, level_idx, time_idx, dtime_idx = slice_index
    return grid_data.isel(
        member=slice(member_idx, member_idx + 1),
        level=slice(level_idx, level_idx + 1),
        time=slice(time_idx, time_idx + 1),
        dtime=slice(dtime_idx, dtime_idx + 1),
    )


def _slice_gatefilter_input(gatefilter, slice_index, template_shape, velocity_slice):
    """按当前 2D 切片构建或裁剪 gatefilter。"""
    if gatefilter is None or gatefilter is False:
        return gatefilter

    if isinstance(gatefilter, GridGateFilter):
        gate_excluded = np.asarray(gatefilter.gate_excluded, dtype=bool)
        if gate_excluded.shape == template_shape[-2:]:
            return GridGateFilter(
                velocity_slice,
                gate_excluded=gate_excluded,
            )
        if gate_excluded.shape == template_shape:
            return GridGateFilter(
                _slice_griddata(gatefilter.velocity, slice_index),
                gate_excluded=np.asarray(gate_excluded[slice_index], dtype=bool),
            )
        raise ValueError(
            "gatefilter.gate_excluded must match the 2D plane or full velocity shape"
        )

    raise TypeError("gatefilter must be None, False, or GridGateFilter")


def _dealias_region_based_2d(
    velocity_slice: xr.DataArray,
    gatefilter,
    nyquist_vel: float,
    ref_velocity: xr.DataArray | None,
    interval_splits: int,
    interval_limits,
    skip_between_rays: int,
    skip_along_ray: int,
    centered: bool,
    rays_wrap_around: bool,
    keep_original: bool,
) -> np.ndarray:
    """对单个 2D 切片执行区域退模糊。"""
    # 先把输入里的 NaN / Inf / 掩码值写入 gatefilter，
    # 这样后续的区域连通与边界统计都不会把无效点算进去。
    gatefilter.exclude_masked(velocity_slice)
    gatefilter.exclude_invalid(velocity_slice)
    vdata = _as_2d_array(velocity_slice).view(np.ndarray)
    gfilter = gatefilter.gate_excluded
    # 再补一层对 `_FillValue` / `missing_value` 的显式识别，
    # 避免由输入文件哨兵值转成的普通数值参与计算。
    fillvalue_mask = np.zeros(vdata.shape, dtype=bool)
    for key in ("_FillValue", "missing_value"):
        if key not in velocity_slice.attrs:
            continue
        try:
            fill_val = float(velocity_slice.attrs[key])
        except (TypeError, ValueError):
            continue
        if np.isfinite(fill_val):
            fillvalue_mask |= np.isclose(vdata, fill_val, rtol=0.0, atol=0.0)
    gfilter |= fillvalue_mask
    ref_vdata = None if ref_velocity is None else _as_2d_array(ref_velocity).view(np.ndarray)
    data = vdata.copy()

    nyquist_interval = nyquist_vel * 2.0
    if interval_limits is None:
        valid_sdata = vdata[~gfilter]
        s_interval_limits = _find_sweep_interval_splits(
            nyquist_vel,
            interval_splits,
            valid_sdata,
            0,
        )
    else:
        s_interval_limits = interval_limits

    # 根据当前速度分段找连通区域，再统计相邻区域之间的候选边。
    labels, nfeatures = _find_regions(vdata, gfilter, s_interval_limits)
    if nfeatures >= 2:
        bincount = np.bincount(labels.ravel())
        num_masked_gates = bincount[0]
        region_sizes = bincount[1:]

        indices, edge_count, velos = _edge_sum_and_count(
            labels,
            num_masked_gates,
            vdata,
            rays_wrap_around,
            skip_between_rays,
            skip_along_ray,
        )

        if len(edge_count) != 0:
            region_tracker = _RegionTracker(region_sizes)
            edge_tracker = _EdgeTracker(
                indices,
                edge_count,
                velos,
                nyquist_interval,
                nfeatures + 1,
            )
            while True:
                if _combine_regions(region_tracker, edge_tracker):
                    break

            # 如果要求中心化，则把整幅切片的平均圈数偏移拉回到 0 附近。
            if centered:
                gates_dealiased = region_sizes.sum()
                total_folds = np.sum(region_sizes * region_tracker.unwrap_number[1:])
                sweep_offset = int(round(float(total_folds) / gates_dealiased))
                if sweep_offset != 0:
                    region_tracker.unwrap_number -= sweep_offset

            nwrap = np.take(region_tracker.unwrap_number, labels)
            data += nwrap * nyquist_interval

            # =====================================
            # 若提供参考速度场，则进一步做全局或分区锚定。
            # 这一步会尽量让退模糊结果与参考场在整体上对齐。
            # =====================================
            if ref_vdata is not None:
                gfold = (ref_vdata - data).mean() / nyquist_interval
                gfold = round(gfold)

                new_interval_limits = np.linspace(data.min(), data.max(), 10)
                labels_corr, nfeatures_corr = _find_regions(
                    data,
                    gfilter,
                    new_interval_limits,
                )

                if nfeatures_corr < 2:
                    data = data + gfold * nyquist_interval
                else:
                    bounds_list = [
                        (x, y)
                        for (x, y) in zip(
                            -6 * np.ones(nfeatures_corr),
                            5 * np.ones(nfeatures_corr),
                        )
                    ]
                    data_means = np.zeros(nfeatures_corr)
                    ref_means = np.zeros(nfeatures_corr)
                    for reg in range(1, nfeatures_corr + 1):
                        data_means[reg - 1] = np.ma.mean(data[labels_corr == reg])
                        ref_means[reg - 1] = np.ma.mean(ref_vdata[labels_corr == reg])

                    def cost_function(x):
                        return _cost_function(
                            x,
                            data_means,
                            ref_means,
                            nyquist_interval,
                            nfeatures_corr,
                        )

                    def gradient(x):
                        return _gradient(
                            x,
                            data_means,
                            ref_means,
                            nyquist_interval,
                            nfeatures_corr,
                        )

                    nyq_adjustments = fmin_l_bfgs_b(
                        cost_function,
                        gfold * np.ones(nfeatures_corr),
                        disp=False,
                        fprime=gradient,
                        bounds=bounds_list,
                        maxiter=200,
                        pgtol=nyquist_interval,
                    )

                    i = 0
                    for reg in range(1, nfeatures_corr):
                        # 将优化得到的整数圈数偏移回写到对应区域。
                        data[labels == reg] += nyquist_interval * np.round(
                            nyq_adjustments[0][i]
                        )
                        i += 1

    # =====================================
    # 过滤结果回填
    #
    # keep_original=False: 过滤格点输出缺测值。
    # keep_original=True : 过滤格点保留原始输入值。
    # =====================================
    if np.any(gfilter):
        data = np.ma.array(data, mask=gfilter, fill_value=np.nan)

    if keep_original:
        data[gfilter] = vdata[gfilter]

    values = np.ma.asarray(data, dtype=np.float32)
    if np.ma.isMaskedArray(values):
        return values.filled(np.nan)
    return np.asarray(values, dtype=np.float32)


def _find_sweep_interval_splits(nyquist, interval_splits, velocities, nsweep):
    """根据当前 sweep 的速度范围，决定是否需要扩展 Nyquist 分段。"""
    add_start = add_end = 0
    interval = (2.0 * nyquist) / interval_splits
    if len(velocities) != 0:
        max_vel = velocities.max()
        min_vel = velocities.min()
        if max_vel > nyquist or min_vel < -nyquist:
            msg = f"Velocities outside of the Nyquist interval found in sweep {nsweep}."
            warnings.warn(msg, UserWarning)

            # 输入偶尔可能已经部分越过当前 Nyquist 区间，需临时扩展分段范围以免漏标。
            add_start = int(np.ceil((max_vel - nyquist) / interval))
            add_end = int(np.ceil(-(min_vel + nyquist) / interval))

    start = -nyquist - add_start * interval
    end = nyquist + add_end * interval
    num = interval_splits + 1 + add_start + add_end
    return np.linspace(start, end, num, endpoint=True)


def _find_regions(vel, gfilter, limits):
    """根据速度分段和门限掩码提取 2D 连通区域。"""
    mask = ~gfilter
    label = np.zeros(vel.shape, dtype=np.int32)
    nfeatures = 0
    for lmin, lmax in zip(limits[:-1], limits[1:]):
        # 仅在当前速度分段内做连通域标记，再累计到全局标签空间。
        inp = (lmin <= vel) & (vel < lmax) & mask
        limit_label, limit_nfeatures = ndimage.label(inp)
        limit_label[np.nonzero(limit_label)] += nfeatures
        label += limit_label
        nfeatures += limit_nfeatures

    return label, nfeatures


def _edge_sum_and_count(
    labels,
    num_masked_gates,
    data,
    rays_wrap_around,
    max_gap_x,
    max_gap_y,
):
    """统计候选边的数量和对应速度和。"""
    total_nodes = labels.shape[0] * labels.shape[1] - num_masked_gates
    if rays_wrap_around:
        total_nodes += labels.shape[0] * 2

    indices, velocities = _fast_edge_finder(
        labels.astype("int32"),
        data.astype("float32"),
        rays_wrap_around,
        max_gap_x,
        max_gap_y,
        total_nodes,
    )
    index1, index2 = indices
    vel1, vel2 = velocities
    count = np.ones_like(vel1, dtype=np.int32)

    if len(vel1) == 0:
        return ([], []), [], ([], [])

    # 快速边查找可能返回重复边，这里统一排序并合并。
    order = np.lexsort((index1, index2))
    index1 = index1[order]
    index2 = index2[order]
    vel1 = vel1[order]
    vel2 = vel2[order]
    count = count[order]

    unique_mask = (index1[1:] != index1[:-1]) | (index2[1:] != index2[:-1])
    unique_mask = np.append(True, unique_mask)
    index1 = index1[unique_mask]
    index2 = index2[unique_mask]

    (unique_inds,) = np.nonzero(unique_mask)
    vel1 = np.add.reduceat(vel1, unique_inds, dtype=vel1.dtype)
    vel2 = np.add.reduceat(vel2, unique_inds, dtype=vel2.dtype)
    count = np.add.reduceat(count, unique_inds, dtype=count.dtype)

    return (index1, index2), count, (vel1, vel2)


def _combine_regions(region_tracker, edge_tracker):
    """尝试根据当前最优边继续合并区域。"""
    status, extra = edge_tracker.pop_edge()
    if status:
        return True
    node1, node2, weight, diff, edge_number = extra
    del weight
    rdiff = int(np.round(diff))

    node1_size = region_tracker.get_node_size(node1)
    node2_size = region_tracker.get_node_size(node2)

    if node1_size > node2_size:
        base_node, merge_node = node1, node2
    else:
        base_node, merge_node = node2, node1
        rdiff = -rdiff

    # 优先把小区域合并到大区域，可减少后续图更新开销。
    if rdiff != 0:
        region_tracker.unwrap_node(merge_node, rdiff)
        edge_tracker.unwrap_node(merge_node, rdiff)

    region_tracker.merge_nodes(base_node, merge_node)
    edge_tracker.merge_nodes(base_node, merge_node, edge_number)

    return False


def _cost_function(
    nyq_vector,
    vels_slice_means,
    svels_slice_means,
    v_nyq_vel,
    nfeatures,
):
    """计算目标函数值。"""
    cost = 0
    i = 0

    for reg in range(nfeatures):
        add_value = (
            vels_slice_means[reg]
            + np.round(nyq_vector[i]) * v_nyq_vel
            - svels_slice_means[reg]
        ) ** 2

        if np.isfinite(add_value):
            cost += add_value
        i += 1

    return cost


def _gradient(nyq_vector, vels_slice_means, svels_slice_means, v_nyq_vel, nfeatures):
    """计算优化目标的梯度。"""
    gradient_vector = np.zeros(len(nyq_vector))
    i = 0
    for reg in range(nfeatures):
        add_value = (
            vels_slice_means[reg]
            + np.round(nyq_vector[i]) * v_nyq_vel
            - svels_slice_means[reg]
        )
        if np.isfinite(add_value):
            gradient_vector[i] = 2 * add_value * v_nyq_vel

        vels_without_cur = np.delete(vels_slice_means, reg)
        diffs = np.square(vels_slice_means[reg] - vels_without_cur)
        if len(diffs) > 0:
            the_min = np.argmin(diffs)
        else:
            the_min = 0

        if the_min < v_nyq_vel:
            gradient_vector[i] = 0

        i += 1

    return gradient_vector


class _RegionTracker:
    """追踪区域合并和展开圈数的状态。"""

    def __init__(self, region_sizes):
        nregions = len(region_sizes) + 1
        self.node_size = np.zeros(nregions, dtype="int32")
        self.node_size[1:] = region_sizes[:]

        self.regions_in_node = np.zeros(nregions, dtype="object")
        for i in range(nregions):
            self.regions_in_node[i] = [i]

        self.unwrap_number = np.zeros(nregions, dtype="int32")

    def merge_nodes(self, node_a, node_b):
        """将节点 ``node_b`` 合并到 ``node_a``。"""
        regions_to_merge = self.regions_in_node[node_b]
        self.regions_in_node[node_a].extend(regions_to_merge)
        self.regions_in_node[node_b] = []

        self.node_size[node_a] += self.node_size[node_b]
        self.node_size[node_b] = 0

    def unwrap_node(self, node, nwrap):
        """为节点内所有区域增加展开圈数。"""
        if nwrap == 0:
            return
        regions_to_unwrap = self.regions_in_node[node]
        self.unwrap_number[regions_to_unwrap] += nwrap

    def get_node_size(self, node):
        """返回节点包含的格点数。"""
        return self.node_size[node]


class _EdgeTracker:
    """追踪边的关系、权重和优先级。"""

    def __init__(self, indices, edge_count, velocities, nyquist_interval, nnodes):
        nedges = int(len(indices[0]) / 2)

        self.node_alpha = np.zeros(nedges, dtype=np.int32)
        self.node_beta = np.zeros(nedges, dtype=np.int32)
        self.sum_diff = np.zeros(nedges, dtype=np.float32)
        self.weight = np.zeros(nedges, dtype=np.int32)

        self._common_finder = np.zeros(nnodes, dtype=np.bool_)
        self._common_index = np.zeros(nnodes, dtype=np.int32)
        self._last_base_node = -1

        self.edges_in_node = np.zeros(nnodes, dtype="object")
        for i in range(nnodes):
            self.edges_in_node[i] = []

        edge = 0
        idx1, idx2 = indices
        vel1, vel2 = velocities
        for i, j, count, vel, nvel in zip(idx1, idx2, edge_count, vel1, vel2):
            if i < j:
                continue
            self.node_alpha[edge] = i
            self.node_beta[edge] = j
            self.sum_diff[edge] = (vel - nvel) / nyquist_interval
            self.weight[edge] = count
            self.edges_in_node[i].append(edge)
            self.edges_in_node[j].append(edge)
            edge += 1

        self.priority_queue = []

    def merge_nodes(self, base_node, merge_node, foo_edge):
        """合并两个节点对应的边信息。"""
        self.weight[foo_edge] = -999
        self.edges_in_node[merge_node].remove(foo_edge)
        self.edges_in_node[base_node].remove(foo_edge)
        self._common_finder[merge_node] = False

        edges_in_merge = list(self.edges_in_node[merge_node])

        if self._last_base_node != base_node:
            self._common_finder[:] = False
            edges_in_base = list(self.edges_in_node[base_node])
            for edge_num in edges_in_base:
                if self.node_beta[edge_num] == base_node:
                    self._reverse_edge_direction(edge_num)
                assert self.node_alpha[edge_num] == base_node

                neighbor = self.node_beta[edge_num]
                self._common_finder[neighbor] = True
                self._common_index[neighbor] = edge_num

        for edge_num in edges_in_merge:
            if self.node_beta[edge_num] == merge_node:
                self._reverse_edge_direction(edge_num)
            assert self.node_alpha[edge_num] == merge_node

            self.node_alpha[edge_num] = base_node

            neighbor = self.node_beta[edge_num]
            if self._common_finder[neighbor]:
                base_edge_num = self._common_index[neighbor]
                self._combine_edges(base_edge_num, edge_num, merge_node, neighbor)
            else:
                self._common_finder[neighbor] = True
                self._common_index[neighbor] = edge_num

        edges = self.edges_in_node[merge_node]
        self.edges_in_node[base_node].extend(edges)
        self.edges_in_node[merge_node] = []
        self._last_base_node = int(base_node)

    def _combine_edges(self, base_edge, merge_edge, merge_node, neighbor_node):
        """合并重复边。"""
        self.weight[base_edge] += self.weight[merge_edge]
        self.weight[merge_edge] = -999.0
        self.sum_diff[base_edge] += self.sum_diff[merge_edge]

        self.edges_in_node[merge_node].remove(merge_edge)
        self.edges_in_node[neighbor_node].remove(merge_edge)

    def _reverse_edge_direction(self, edge):
        """反转边的方向。"""
        old_alpha = int(self.node_alpha[edge])
        old_beta = int(self.node_beta[edge])
        self.node_alpha[edge] = old_beta
        self.node_beta[edge] = old_alpha
        self.sum_diff[edge] = -1.0 * self.sum_diff[edge]

    def unwrap_node(self, node, nwrap):
        """节点展开后，更新相关边的差值。"""
        if nwrap == 0:
            return

        for edge in self.edges_in_node[node]:
            weight = self.weight[edge]
            if node == self.node_alpha[edge]:
                self.sum_diff[edge] += weight * nwrap
            else:
                assert self.node_beta[edge] == node
                self.sum_diff[edge] += -weight * nwrap

    def pop_edge(self):
        """取出当前权重最高的边。"""
        edge_num = np.argmax(self.weight)
        node1 = self.node_alpha[edge_num]
        node2 = self.node_beta[edge_num]
        weight = self.weight[edge_num]
        diff = self.sum_diff[edge_num] / float(weight)

        if weight < 0:
            return True, None
        return False, (node1, node2, weight, diff, edge_num)


__all__ = ["dealias_region_based", "RegionDealiasPlugin", "GridGateFilter"]
