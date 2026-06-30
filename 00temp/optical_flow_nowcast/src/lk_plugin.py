# -*- coding: utf-8 -*-
"""
Created on Tue Sep 26 15:44:26 2023

@author: cheny
"""

from .base_plugin import PostProcessingPlugin
from typing import Optional, Tuple
from .utils import *
from scipy.interpolate import Rbf
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
import meteva_base as meb
from optical_flow_nowcast.src.lk import forecast 
import datetime
import pandas as pd
import xarray as xr
from optical_flow_nowcast.src import dB_trans

class  LK(PostProcessingPlugin):

    def __init__(self, 
                transform_method:Optional[str]=None,
                transform_para:Optional[dict]=None,
                model_id_attr: Optional[str] = None,
                lk_kwargs: Optional[dict]=None,
                fd_method: Optional[str]="shitomasi",
                fd_kwargs: Optional[dict]=None,
                interp_method: Optional[str]="idwinterp2d",
                interp_kwargs: Optional[dict]=None,
                dense: Optional[bool]=True,
                nr_std_outlier: Optional[int]=3,
                k_outlier: Optional[int]=30,
                size_opening: Optional[int]=3,
                decl_scale: Optional[int]=20,
                verbose: Optional[bool]=False,
                ) -> None:
        """
        Initialise the class

        Args:
            model_id_attr:
                Name of the attribute used to identify the source model for
                blending.
            lk_kwargs: dict, optional
                Optional dictionary containing keyword arguments for the `Lucas-Kanade`_
                features tracking algorithm. See the documentation of
                :py:func:`pysteps.tracking.lucaskanade.track_features`.

            fd_method: {"shitomasi", "blob", "tstorm"}, optional
            Name of the feature detection routine. See feature detection methods in
            :py:mod:`pysteps.feature`.

            fd_kwargs: dict, optional
                Optional dictionary containing keyword arguments for the features
                detection algorithm.
                See the documentation of :py:mod:`pysteps.feature`.

            interp_method: {"idwinterp2d", "rbfinterp2d"}, optional
            Name of the interpolation method to use. See interpolation methods in
            :py:mod:`pysteps.utils.interpolate`.

            interp_kwargs: dict, optional
                Optional dictionary containing keyword arguments for the interpolation
                algorithm. See the documentation of :py:mod:`pysteps.utils.interpolate`.

            dense: bool, optional
                If True, return the three-dimensional array (2, m, n) containing
                the dense x- and y-components of the motion field.

                If False, return the sparse motion vectors as 2-D **xy** and **uv**
                arrays, where **xy** defines the vector positions, **uv** defines the
                x and y direction components of the vectors.

            nr_std_outlier: int, optional
                Maximum acceptable deviation from the mean in terms of number of
                standard deviations. Any sparse vector with a deviation larger than
                this threshold is flagged as outlier and excluded from the
                interpolation.
                See the documentation of
                :py:func:`pysteps.utils.cleansing.detect_outliers`.

            k_outlier: int or None, optional
                The number of nearest neighbors used to localize the outlier detection.
                If set to None, it employs all the data points (global detection).
                See the documentation of
                :py:func:`pysteps.utils.cleansing.detect_outliers`.

            size_opening: int, optional
                The size of the structuring element kernel in pixels. This is used to
                perform a binary morphological opening on the input fields in order to
                filter isolated echoes due to clutter. If set to zero, the filtering
                is not performed.
                See the documentation of
                :py:func:`pysteps.utils.images.morph_opening`.

            decl_scale: int, optional
                The scale declustering parameter in pixels used to reduce the number of
                redundant sparse vectors before the interpolation.
                Sparse vectors within this declustering scale are averaged together.
                If set to less than 2 pixels, the declustering is not performed.
                See the documentation of
                :py:func:`pysteps.utils.cleansing.decluster`.

            verbose: bool, optional
                If set to True, print some information about the program.

                    
        """
        self.model_id_attr=model_id_attr
        self.lk_kwargs=lk_kwargs
        self.fd_method=fd_method
        self.fd_kwargs=fd_kwargs
        self.interp_method=interp_method
        self.interp_kwargs=interp_kwargs
        self.dense=dense
        self.nr_std_outlier=nr_std_outlier
        self.k_outlier=k_outlier
        self.size_opening=size_opening
        self.decl_scale=decl_scale
        self.verbose=verbose
        self.transform_method=transform_method
        self.transform_para=transform_para

 
    def process(
        self,
        meb_griddata_list)->Tuple[xr.DataArray, datetime.timedelta]:
        """
        LK插件计算平流
        Args:
            meb_griddata_list: meb网格数据的列表，从前到后为之前到最近的实况场
        Returns:
            uv： 平流速度场
            delta： 外推间隔时间
        """

        #时间排序
        meb_griddata_list=sort_meb_griddata_list_along_time(meb_griddata_list)

        # 数据维度一致性检查
        for griddata in meb_griddata_list:
            if griddata.values.squeeze().ndim!=2:
                raise ValueError("uncorrect dimension, expect 2 dimensions data like [m,n]")
            else:
                continue

        # 时间间隔一致性检查
        if check_meb_griddata_time_interval(meb_griddata_list):
            pass
        else:
            raise ValueError('unequal time intervals in meb_griddata_list detected!')

        ## 数据提取
        np_array=[]
        for griddata in meb_griddata_list:
            np_array.append(griddata.values.squeeze())
        
        #构建三维输入

        np_array=np.array(np_array)
        

        #transform
        transform_mapping={'db':'dB_transform',
                           'box':'boxcox_transform',
                           'NQ':'NQ_transform',
                           'sqrt':'sqrt_transform'
                           }
        

        if self.transform_method is None:
            transform=None
        else:
            method=transform_mapping[self.transform_method]
            
            transform=getattr(dB_trans,method)

            np_array, metadata = transform(np_array,**self.transform_para)

            

        ## 维度提取
        grid_info=meb.get_grid_of_data(griddata)
        glon=[grid_info.slon,grid_info.elon,grid_info.dlon]
        glat=[grid_info.slat,grid_info.elat,grid_info.dlat]
        gtime=grid_info.gtime
        delta_t=pd.to_datetime(meb_griddata_list[-1].time).to_pydatetime()-pd.to_datetime(meb_griddata_list[-2].time).to_pydatetime()
        delta_t=delta_t[0]

        grid=meb.grid(glon,glat,gtime)
        grid.members=['u','v']

        result_np=forecast(np_array,
                            lk_kwargs=self.lk_kwargs,
                            fd_method=self.fd_method,
                            fd_kwargs=self.fd_kwargs,
                            interp_method=self.interp_method,
                            interp_kwargs=self.interp_kwargs,
                            dense=self.dense,
                            nr_std_outlier=self.nr_std_outlier,
                            k_outlier=self.k_outlier,
                            size_opening=self.size_opening,
                            decl_scale=self.decl_scale,
                            verbose=self.verbose)
        
        #重构meb.griddata
        nlat=result_np.shape[1]
        nlon=result_np.shape[2]
        result_np=result_np.reshape(2,1,1,1,nlat,nlon)
        result_griddata=meb.grid_data(grid,result_np)

        return result_griddata, delta_t
    



        

        

        

        
        
        
    