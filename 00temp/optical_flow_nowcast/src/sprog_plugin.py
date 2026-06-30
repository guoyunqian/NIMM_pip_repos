# -*- coding: utf-8 -*-
"""
Created on Thu Aug 17 14:55:04 2023

@author: cheny
"""
from .base_plugin import PostProcessingPlugin
from typing import Optional, Tuple
from .utils import *
from optical_flow_nowcast.src.sprog import forecast
import meteva_base as meb
import xarray as xr


class Sprog(PostProcessingPlugin):

    def __init__(self,
                 model_id_attr: Optional[str] = None,
                 precip_thr: Optional[float] = -5,
                 n_cascade_levels: Optional[int] = 6,
                 extrap_method: Optional[str] = "semilagrangian",
                 decomp_method: Optional[str] = "fft",
                 bandpass_filter_method: Optional[str] = "gaussian",
                 ar_order: Optional[int] = 2,
                 conditional: Optional[bool] = False,
                 probmatching_method: Optional[str] = "cdf",
                 num_workers: Optional[int] = 1,
                 fft_method: Optional[str] = "numpy",
                 domain: Optional[str] = "spatial",
                 extrap_kwargs: Optional[dict] = None,
                 filter_kwargs: Optional[dict] = None,
                 measure_time: Optional[bool] = False,) -> None:
        """
        Initialise the class

        Args:
        model_id_attr:
            Name of the attribute used to identify the source model for
            blending.
        precip_thr: float, required
            The threshold value for minimum observable precipitation intensity.
        n_cascade_levels: int, optional
            The number of cascade levels to use.
        extrap_method: str, optional
            Name of the extrapolation method to use. See the documentation of
            pysteps.extrapolation.interface.
        decomp_method: {'fft'}, optional
            Name of the cascade decomposition method to use. See the documentation
            of pysteps.cascade.interface.
        bandpass_filter_method: {'gaussian', 'uniform'}, optional
            Name of the bandpass filter method to use with the cascade decomposition.
            See the documentation of pysteps.cascade.interface.
        ar_order: int, optional
            The order of the autoregressive model to use. Must be >= 1.
        conditional: bool, optional
            If set to True, compute the statistics of the precipitation field
            conditionally by excluding pixels where the values are
            below the threshold precip_thr.
        probmatching_method: {'cdf','mean',None}, optional
            Method for matching the conditional statistics of the forecast field
            (areas with precipitation intensity above the threshold precip_thr) with
            those of the most recently observed one. 'cdf'=map the forecast CDF to the
            observed one, 'mean'=adjust only the mean value,
            None=no matching applied.
        num_workers: int, optional
            The number of workers to use for parallel computation. Applicable if dask
            is enabled or pyFFTW is used for computing the FFT.
            When num_workers>1, it is advisable to disable OpenMP by setting
            the environment variable OMP_NUM_THREADS to 1.
            This avoids slowdown caused by too many simultaneous threads.
        fft_method: str, optional
            A string defining the FFT method to use (see utils.fft.get_method).
            Defaults to 'numpy' for compatibility reasons. If pyFFTW is installed,
            the recommended method is 'pyfftw'.
        domain: {"spatial", "spectral"}
            If "spatial", all computations are done in the spatial domain (the
            classical S-PROG model). If "spectral", the AR(2) models are applied
            directly in the spectral domain to reduce memory footprint and improve
            performance :cite:`PCH2019a`.
        extrap_kwargs: dict, optional
            Optional dictionary containing keyword arguments for the extrapolation
            method. See the documentation of pysteps.extrapolation.
        filter_kwargs: dict, optional
            Optional dictionary containing keyword arguments for the filter method.
            See the documentation of pysteps.cascade.bandpass_filters.py.
        measure_time: bool
            If set to True, measure, print and return the computation time.
        """
        self.model_id_attr = model_id_attr
        self.precip_thr = precip_thr
        self.n_cascade_levels = n_cascade_levels
        self.extrap_method = extrap_method
        self.decomp_method = decomp_method
        self.bandpass_filter_method = bandpass_filter_method
        self.ar_order = ar_order
        self.conditional = conditional
        self.probmatching_method = probmatching_method
        self.num_workers = num_workers
        self.fft_method = fft_method
        self.domain = domain
        self.extrap_kwargs = extrap_kwargs
        self.filter_kwargs = filter_kwargs
        self.measure_time = measure_time

    from datetime import timedelta

    @deprecate_args({"R": "precip", "V": "velocity", "R_thr": "precip_thr"}, "1.8.0")
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

        if velocity_griddata.values.squeeze(
        ).ndim != 3 and velocity_griddata.values.squeeze().shape[0] != 2:
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
        precip_np_array = np.array(precip_np_array)
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
                             precip_thr=self.precip_thr,
                             n_cascade_levels=self.n_cascade_levels,
                             extrap_method=self.extrap_method,
                             decomp_method=self.decomp_method,
                             bandpass_filter_method=self.bandpass_filter_method,
                             ar_order=self.ar_order,
                             conditional=self.conditional,
                             probmatching_method=self.probmatching_method,
                             num_workers=self.num_workers,
                             fft_method=self.fft_method,
                             domain=self.domain,
                             extrap_kwargs=self.extrap_kwargs,
                             filter_kwargs=self.filter_kwargs,
                             measure_time=self.measure_time,
                             )

        # 重构meb.griddata
        nlat = result_np.shape[1]
        nlon = result_np.shape[2]
        result_np = result_np.reshape(1, 1, 1, timesteps, nlat, nlon)
        result_griddata = meb.grid_data(grid, result_np)
        return result_griddata
