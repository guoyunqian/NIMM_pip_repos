# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 14:14:50 2023

@author: cheny
"""
from .base_plugin import PostProcessingPlugin
from typing import Optional
from .utils import *
from optical_flow_nowcast.src.extrapolation import forecast
import meteva_base as meb
import xarray as xr


class Extrapolation(PostProcessingPlugin):

    def __init__(self,
                 model_id_attr: Optional[str] = None,
                 extrap_method: Optional[str] = "semilagrangian",
                 extrap_kwargs: Optional[dict] = None,
                 measure_time: Optional[bool] = False,
                 ) -> None:
        """
        Initialise the class

        Args:
        model_id_attr:
            Name of the attribute used to identify the source model for
            blending.
            feature_method: {'blob', 'domain' 'shitomasi'}
        extrap_method: str, optional
            Name of the extrapolation method to use. See the documentation of
            pysteps.extrapolation.interface.
        extrap_kwargs: dict, optional
            Optional dictionary that is expanded into keyword arguments for the
            extrapolation method.
        measure_time: bool, optional
            If True, measure, print, and return the computation time.

        """
        self.model_id_attr = model_id_attr
        self.extrap_method = extrap_method
        self.extrap_kwargs = extrap_kwargs
        self.measure_time = measure_time

    def process(self,
                precip_griddata_list: list,
                velocity_griddata: xr.DataArray,
                timesteps: int,
                delta_t=timedelta(minutes=10)
                ) -> xr.DataArray:
        """
        Args:
            precip_griddata_list: 实况降水列表，meb网格数据，依次从前到后
            velocity_griddata：平流速度
            timesteps： 外推多少个时次
            delta_t： 实况间隔，暨每个时次间隔时间
        """
        # 时间排序
        precip_griddata_list = sort_meb_griddata_list_along_time(precip_griddata_list)
        # 数据维度一致性检查
        for precip_griddata in precip_griddata_list:
            if precip_griddata.values.squeeze().ndim != 2:
                raise ValueError("uncorrect dimension, expect 2 dimensions data like [m,n]")
            else:
                continue

        if velocity_griddata.values.squeeze().ndim != 3 and velocity_griddata.values.squeeze().shape[0] != 2:
            raise ValueError("uncorrect dimension, expect 3 dimensions data like [2,m,n]")

        # 时间间隔一致性检查
        if check_meb_griddata_time_interval(precip_griddata_list):
            pass
        else:
            raise ValueError('unequal time intervals in meb_griddata_list detected!')

        # 数据提取
        precip_np_array = []
        for precip_griddata in precip_griddata_list:
            precip_np_array.append(precip_griddata.values.squeeze())

        velocity_np_array = velocity_griddata.values.squeeze()

        # 构建三维输入
        precip_np_array = np.array(precip_np_array)[-1]
        velocity_np_array = np.array(velocity_np_array)

        # 维度提取
        grid_info = meb.get_grid_of_data(precip_griddata)
        gtime = grid_info.gtime
        glon = [grid_info.slon, grid_info.elon, grid_info.dlon]
        glat = [grid_info.slat, grid_info.elat, grid_info.dlat]

        if delta_t.seconds % 3600 == 0:
            delta_t = delta_t.seconds / 3600
            delta_t_units = 'hours'
        elif delta_t.seconds % 60 == 0:
            delta_t = delta_t.seconds / 60
            delta_t_units = 'minutes'
        elif delta_t.seconds % 1 == 0:
            delta_t = delta_t.seconds
            delta_t_units = 'seconds'

        dtime_list = np.arange(delta_t, timesteps * delta_t + 1, delta_t)
        grid = meb.grid(glon, glat, gtime, dtime_list=dtime_list, dtime_units_attr=delta_t_units)

        result_np = forecast(precip_np_array,
                             velocity_np_array,
                             timesteps,
                             extrap_method=self.extrap_method,
                             extrap_kwargs=self.extrap_kwargs,
                             measure_time=self.measure_time,
                             )

        # 重构meb.griddata
        nlat = result_np.shape[1]
        nlon = result_np.shape[2]
        result_np = result_np.reshape(1, 1, 1, timesteps, nlat, nlon)
        result_griddata = meb.grid_data(grid, result_np)
        return result_griddata
