#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2019 NMC Developers.
# Distributed under the terms of the GPL V3 License.
"""带掩码分层的邻域处理算法。"""

from typing import Any, List, Optional, Tuple, Union

import numpy as np
import xarray as xr
from numpy import ndarray

from neighbourhood_probability_processing.src.nbhood import NeighbourhoodProcessing
from neighbourhood_probability_processing.src.utils._helpers import (
    _extract_data_array,
    _slice_lead_times_for_reshaped_data,
)
from neighbourhood_probability_processing.utils.base_plugin import BasePlugin
from neighbourhood_probability_processing.utils.utils import check_for_meb_griddata


class ApplyNeighbourhoodProcessingWithAMask(BasePlugin):
    """对每个掩码分层分别执行邻域处理，并按需折叠掩码维度。

    该类迁移自 Improver 的 ``ApplyNeighbourhoodProcessingWithAMask``。原算法
    用 Iris Cube 的坐标系统管理 ``coord_for_masking`` 维；迁移版改为同时支持
    ``xarray.DataArray`` 和 ``numpy.ndarray``，维度顺序约定如下：

    - ``data`` 最后两维为 ``y, x`` 空间维；
    - ``mask`` 最后一维两维为 ``y, x``，掩码分层维位于空间维之前；
    - 未提供 ``collapse_weights`` 时，输出形状为
      ``(*data前导维, n_mask, y, x)``；
    - 提供 ``collapse_weights`` 时，沿 ``n_mask`` 维加权平均，输出形状与
      ``data`` 一致。
    - ``xarray.DataArray`` 输入会返回 ``xarray.DataArray``，纯数组输入会返回
      ``numpy.ndarray`` 或 ``numpy.ma.MaskedArray``。
    """

    def __init__(
        self,
        coord_for_masking: str,
        neighbourhood_method: str,
        radii: Union[float, List[float]],
        lead_times: Optional[List[float]] = None,
        collapse_weights: Optional[Union[xr.DataArray, ndarray]] = None,
        weighted_mode: bool = False,
        sum_only: bool = False,
    ) -> None:
        """初始化带掩码的邻域处理插件。

        参数
        ----------
        coord_for_masking : str
            掩码分层维名称，例如 ``topographic_zone``。
        neighbourhood_method : str
            邻域方法，支持 ``"square"`` 和 ``"circular"``。
        radii : float 或 list[float]
            邻域半径，单位为米。
        lead_times : list[float], optional
            与 ``radii`` 对应的时效，单位为小时。若提供，则会按输入时效
            对半径做线性插值。
        collapse_weights : xr.DataArray 或 ndarray, optional
            掩码分层折叠权重。若提供，则邻域处理完成后会沿掩码分层维做
            加权平均，输出形状恢复为原输入形状。
        weighted_mode : bool, optional
            是否启用圆形邻域加权核。仅在底层邻域方法为 ``"circular"``
            时有效。
        sum_only : bool, optional
            是否只输出邻域和而不是邻域平均。
        """
        self.coord_for_masking = coord_for_masking
        self.neighbourhood_method = neighbourhood_method
        self.radii = radii
        self.lead_times = lead_times
        self.collapse_weights = collapse_weights
        self.weighted_mode = weighted_mode
        self.sum_only = sum_only
        self.re_mask = False

    def _mask_axis(self, mask: Union[xr.DataArray, ndarray]) -> int:
        """确定掩码分层维度位置。"""
        if isinstance(mask, xr.DataArray):
            if self.coord_for_masking not in mask.dims:
                raise ValueError(f"mask 中缺少维度 {self.coord_for_masking}")
            return mask.get_axis_num(self.coord_for_masking)
        return np.ndim(mask) - 3

    def _normalise_mask_array(self, mask: Union[xr.DataArray, ndarray]) -> ndarray:
        """将掩码数组调整为 ``(n_mask, y, x)`` 形式。"""
        mask_array = _extract_data_array(mask)
        if mask_array.ndim < 3:
            raise ValueError("mask 至少需要包含掩码分层维和二维空间维")
        mask_axis = self._mask_axis(mask)
        if mask_axis < 0:
            mask_axis += mask_array.ndim
        if mask_axis >= mask_array.ndim - 2:
            raise ValueError("掩码分层维必须位于最后两个空间维之前")
        mask_array = np.moveaxis(mask_array, mask_axis, 0)
        if mask_array.ndim != 3:
            raise ValueError("迁移版当前仅支持形状为 (n_mask, y, x) 的掩码")
        return mask_array

    def _normalise_weights_array(
        self,
        weights: Union[xr.DataArray, ndarray],
        n_mask: int,
        spatial_shape: Optional[Tuple[int, int]] = None,
    ) -> ndarray:
        """将折叠权重调整为 ``(n_mask, y, x)`` 形式。"""
        weights_array = _extract_data_array(weights)
        if isinstance(weights, xr.DataArray) and self.coord_for_masking in weights.dims:
            weights_axis = weights.get_axis_num(self.coord_for_masking)
            weights_array = np.moveaxis(weights_array, weights_axis, 0)
        if weights_array.ndim != 3:
            raise ValueError("collapse_weights 当前仅支持形状为 (n_mask, y, x) 的数组")
        if weights_array.shape[0] != n_mask:
            raise ValueError(
                f"collapse_weights 的掩码层数 {weights_array.shape[0]} 与 mask 层数 {n_mask} 不一致"
            )
        # 显式校验权重空间维与结果一致：折叠时用 np.broadcast_to 广播权重，
        # 若某空间维为 1 会被静默广播（等价于原版 iris.collapsed 会拦下的错配），
        # 这里提前给出友好报错，避免算错或抛出隐晦的广播异常。
        if spatial_shape is not None and weights_array.shape[-2:] != tuple(spatial_shape):
            raise ValueError(
                f"collapse_weights 的空间形状 {weights_array.shape[-2:]} 与数据 {tuple(spatial_shape)} 不一致"
            )
        return weights_array

    def _mask_coord_values(
        self, mask: Union[xr.DataArray, ndarray], n_mask: int
    ) -> ndarray:
        """获取掩码分层维的坐标值。"""
        if isinstance(mask, xr.DataArray) and self.coord_for_masking in mask.coords:
            return np.asarray(mask.coords[self.coord_for_masking].values)
        return np.arange(n_mask, dtype=np.int32)

    def _make_xarray_result(
        self,
        result: ndarray,
        data: xr.DataArray,
        mask: Union[xr.DataArray, ndarray],
        collapsed: bool,
    ) -> xr.DataArray:
        """将结果包装为 DataArray，保留输入维度名和空间坐标。"""
        values = np.ma.getdata(result) if np.ma.isMaskedArray(result) else result
        output_name = data.name if data.name else "neighbourhood_result"
        if collapsed:
            dims = data.dims
            coords = {
                name: coord
                for name, coord in data.coords.items()
                if set(coord.dims).issubset(dims)
            }
        else:
            dims = (*data.dims[:-2], self.coord_for_masking, *data.dims[-2:])
            coords = {
                name: coord
                for name, coord in data.coords.items()
                if set(coord.dims).issubset(dims)
            }
            coords[self.coord_for_masking] = self._mask_coord_values(
                mask, result.shape[-3]
            )
        return xr.DataArray(
            values,
            dims=dims,
            coords=coords,
            attrs=data.attrs.copy(),
            name=output_name,
        )

    def _stack_mask_coord_into_member(self, data: xr.DataArray) -> xr.DataArray:
        """将掩码分层维并入 member 维，保持六维输出结构。"""
        if self.coord_for_masking not in data.dims or "member" not in data.dims:
            return data

        stacked = data.stack(stacked_member=("member", self.coord_for_masking))
        member_index = stacked.indexes["stacked_member"]
        input_member = np.asarray(member_index.get_level_values("member"))
        mask_layer = np.asarray(
            member_index.get_level_values(self.coord_for_masking)
        )

        drop_names = [
            name for name in ("member", self.coord_for_masking) if name in stacked.coords
        ]
        if drop_names:
            stacked = stacked.drop_vars(drop_names)

        remaining_dims = [d for d in data.dims if d not in ("member", self.coord_for_masking)]
        stacked = stacked.transpose("stacked_member", *remaining_dims).rename(
            {"stacked_member": "member"}
        )
        stacked = stacked.assign_coords(
            member=np.arange(stacked.sizes["member"], dtype=np.int32),
            member_input_member=("member", input_member),
            member_mask_layer=("member", mask_layer),
        )

        attrs = dict(data.attrs)
        attrs["member_is_stacked"] = "True"
        attrs["member_stack_dims"] = f"member,{self.coord_for_masking}"
        stacked.attrs.update(attrs)

        target_dims = ("member", "level", "time", "dtime", "lat", "lon")
        if set(stacked.dims) == set(target_dims):
            stacked = stacked.transpose(*target_dims)
        if stacked.name is None:
            stacked = stacked.copy()
            stacked.name = "neighbourhood_result"
        return stacked

    @staticmethod
    def _normalise_grid_spacing(
        grid_spacing: Optional[Union[float, Tuple[float, float]]],
    ) -> Optional[Union[float, Tuple[float, float]]]:
        """返回传给底层邻域处理的网格分辨率。"""
        if grid_spacing is None:
            return None
        if isinstance(grid_spacing, tuple):
            return grid_spacing
        return float(grid_spacing)

    def collapse_mask_coord(
        self,
        data: Union[xr.DataArray, ndarray],
        collapse_weights: Optional[Union[xr.DataArray, ndarray]] = None,
        mask_axis: Optional[int] = None,
    ) -> ndarray:
        """沿掩码分层维做加权平均，自动忽略 NaN 和 masked 数据。

        参数
        ----------
        data : xr.DataArray 或 ndarray
            已按掩码分层完成邻域处理的结果。
        collapse_weights : xr.DataArray 或 ndarray, optional
            分层权重；未传入时使用初始化时的 ``collapse_weights``。
        mask_axis : int, optional
            ``numpy`` 输入的掩码分层轴。默认使用空间维之前的一维。
        返回值
        -------
        ndarray
            折叠后的加权平均结果。
        """
        weights = self.collapse_weights if collapse_weights is None else collapse_weights
        if weights is None:
            raise ValueError("collapse_mask_coord 需要提供 collapse_weights")

        values = _extract_data_array(data)
        if isinstance(data, xr.DataArray) and self.coord_for_masking in data.dims:
            axis = data.get_axis_num(self.coord_for_masking)
        elif mask_axis is not None:
            axis = mask_axis
        else:
            axis = values.ndim - 3
        if axis < 0:
            axis += values.ndim
        if axis >= values.ndim - 2:
            raise ValueError("掩码分层维必须位于最后两个空间维之前")

        values = np.moveaxis(values, axis, -3)
        n_mask = values.shape[-3]
        weights_array = self._normalise_weights_array(
            weights, n_mask, spatial_shape=values.shape[-2:]
        )
        if np.ma.isMaskedArray(weights_array):
            weights_broadcast = np.ma.masked_array(
                np.broadcast_to(np.ma.getdata(weights_array), values.shape),
                mask=np.broadcast_to(np.ma.getmaskarray(weights_array), values.shape),
                copy=False,
            )
        else:
            weights_broadcast = np.broadcast_to(weights_array, values.shape)

        values_data = np.ma.getdata(values)
        values_mask = np.ma.getmaskarray(values) | ~np.isfinite(values_data)
        masked_values = np.ma.masked_array(values_data, mask=values_mask, copy=False)

        weights_data = np.ma.getdata(weights_broadcast)
        weights_mask = np.ma.getmaskarray(weights_broadcast) | ~np.isfinite(
            weights_data
        )
        masked_weights = np.ma.masked_array(
            weights_data, mask=weights_mask, copy=False
        )
        # 结果和权重任一侧无效时，都不应参与最终折叠。
        combined_mask = np.ma.getmaskarray(masked_values) | np.ma.getmaskarray(
            masked_weights
        )
        masked_values = np.ma.array(np.ma.getdata(masked_values), mask=combined_mask)
        masked_weights = np.ma.array(np.ma.getdata(masked_weights), mask=combined_mask)

        numerator = np.ma.sum(masked_values * masked_weights, axis=-3)
        denominator = np.ma.sum(masked_weights, axis=-3)
        with np.errstate(divide="ignore", invalid="ignore"):
            result = numerator / denominator
        result = np.ma.masked_where(np.ma.getdata(denominator) == 0, result)
        if np.ma.isMaskedArray(result):
            result.data[result.mask] = np.nan
        return result.astype(np.float32)

    def process(
        self,
        data: Union[xr.DataArray, ndarray],
        mask: Union[xr.DataArray, ndarray],
        input_lead_times: Optional[Union[float, ndarray]] = None,
        grid_spacing: Optional[Union[float, Tuple[float, float]]] = None,
    ) -> Union[xr.DataArray, ndarray]:
        """对输入数据应用每个掩码分层的邻域处理。

        参数
        ----------
        data : xr.DataArray 或 ndarray
            输入数据，最后两个维度视为空间维。
        mask : xr.DataArray 或 ndarray
            掩码分层数组；零值表示无效点。
        input_lead_times : float 或 ndarray, optional
            numpy 输入使用可变半径时需要显式传入的时效，单位为小时。
        grid_spacing : float 或 tuple[float, float], optional
            numpy 输入对应的网格分辨率，单位为米。
        返回值
        -------
        ndarray
            未折叠时形状为 ``(*data前导维, n_mask, y, x)``；折叠时形状
            与 ``data`` 一致。
        """
        if isinstance(data, xr.DataArray):
            data = check_for_meb_griddata(data, valid_val=(-np.inf, np.inf, np.nan))

        values = _extract_data_array(data)
        if values.ndim < 2:
            raise ValueError("输入数据至少需要二维空间网格")

        mask_array = self._normalise_mask_array(mask)
        if mask_array.shape[-2:] != values.shape[-2:]:
            raise ValueError("mask 的空间形状必须与输入数据最后两个维度一致")

        plugin = NeighbourhoodProcessing(
            self.neighbourhood_method,
            self.radii,
            lead_times=self.lead_times,
            weighted_mode=self.weighted_mode,
            sum_only=self.sum_only,
            re_mask=self.re_mask,
        )

        leading_shape = values.shape[:-2]
        y_size, x_size = values.shape[-2:]
        if isinstance(data, xr.DataArray):
            mask_outputs = [
                plugin.process(
                    data,
                    mask=mask_slice,
                    input_lead_times=input_lead_times,
                    grid_spacing=grid_spacing,
                )
                for mask_slice in mask_array
            ]
            result = np.ma.stack(mask_outputs, axis=len(leading_shape))
            if self.collapse_weights is not None:
                result = self.collapse_mask_coord(
                    result,
                    collapse_weights=self.collapse_weights,
                    mask_axis=-3,
                )
                return self._make_xarray_result(result, data, mask, collapsed=True)
            expanded = self._make_xarray_result(result, data, mask, collapsed=False)
            return self._stack_mask_coord_into_member(expanded)

        grid_spacing = self._normalise_grid_spacing(grid_spacing)
        flat_values = values.reshape((-1, y_size, x_size))
        lead_values = _slice_lead_times_for_reshaped_data(
            input_lead_times, leading_shape, y_size, x_size
        )
        output_slices = []
        for index, data_slice in enumerate(flat_values):
            lead_time = None if lead_values is None else np.asarray([lead_values[index]])
            mask_outputs = []
            for mask_slice in mask_array:
                # 每个二维切片都要对所有掩码层分别做一次邻域处理。
                mask_outputs.append(
                    plugin.process(
                        data_slice,
                        mask=mask_slice,
                        input_lead_times=lead_time,
                        grid_spacing=grid_spacing,
                    )
                )
            output_slices.append(np.ma.stack(mask_outputs, axis=0))

        result = np.ma.stack(output_slices, axis=0).reshape(
            (*leading_shape, mask_array.shape[0], y_size, x_size)
        )
        if self.collapse_weights is not None:
            result = self.collapse_mask_coord(
                result,
                collapse_weights=self.collapse_weights,
                mask_axis=-3,
            )
        return result
