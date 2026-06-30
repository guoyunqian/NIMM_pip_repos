# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 14:14:50 2023

@author: cheny
"""

from .base_plugin import PostProcessingPlugin
from typing import Optional, Tuple
from .utils import *
from optical_flow_nowcast.src.linda import forecast
import meteva_base as meb
import datetime
from datetime import timedelta

class Linda(PostProcessingPlugin):


    def __init__(self, 
                 model_id_attr: Optional[str] = None,
                 add_perturbations: Optional[bool] = False,
                 feature_method: Optional[str] = 'blob',
                 max_num_features: Optional[int] = 25,
                 feature_kwargs : Optional[dict]=None,
                 ari_order: Optional[int] = 1,
                 kernel_type : Optional[str] = "anisotropic",
                 localization_window_radius:Optional[float]=None,
                 errdist_window_radius:Optional[float]=None,
                 acf_window_radius:Optional[float]=None,
                 extrap_method : Optional[str] = "semilagrangian",
                 extrap_kwargs : Optional[dict]=None,
                 pert_thrs : Optional[tuple] = (0.5, 1.0),
                 n_ens_members : Optional[int] = 10,
                 vel_pert_method : Optional[str] = "bps",
                 vel_pert_kwargs : Optional[dict]=None,
                 kmperpixel : Optional[float]=None,
                 timestep : Optional[float]=None,
                 num_workers : Optional[int] = 1,
                 seed : Optional[int]=None,
                 use_multiprocessing : Optional[bool] = False,
                 measure_time : Optional[bool] = False,
                 callback = None,
                 return_output : Optional[bool] = True,
                 ) -> None:
        """
        Initialise the class

        Args:
        model_id_attr:
            Name of the attribute used to identify the source model for
            blending.
            feature_method: {'blob', 'domain' 'shitomasi'}
        Feature detection method:

            +-------------------+-----------------------------------------------------+
            |    Method name    |                  Description                        |
            +===================+=====================================================+
            |  blob             | Laplacian of Gaussian (LoG) blob detector           |
            |                   | implemented in scikit-image                         |
            +-------------------+-----------------------------------------------------+
            |  domain           | no feature detection, the model is applied over the |
            |                   | whole domain without localization                   |
            +-------------------+-----------------------------------------------------+
            |  shitomasi        | Shi-Tomasi corner detector implemented in OpenCV    |
            +-------------------+-----------------------------------------------------+

            Default: 'blob'
        max_num_features: int, optional
            Maximum number of features to use. It is recommended to set this between
            20 and 50, which gives a good tradeoff between localization and
            computation time. Default: 25
        feature_kwargs: dict, optional
            Keyword arguments that are passed as ``**kwargs`` for the feature detector.
            See :py:mod:`pysteps.feature.blob` and :py:mod:`pysteps.feature.shitomasi`.
        ari_order: {1, 2}, optional
            The order of the ARI(p, 1) model. Default: 1
        kernel_type: {"anisotropic", "isotropic"}, optional
            The type of the kernel. Default: 'anisotropic'
        localization_window_radius: float, optional
            The standard deviation of the Gaussian localization window.
            Default: 0.2 * min(m, n)
        errdist_window_radius: float, optional
            The standard deviation of the Gaussian window for estimating the
            forecast error distribution. Default: 0.15 * min(m, n)
        acf_window_radius: float, optional
            The standard deviation of the Gaussian window for estimating the
            forecast error ACF. Default: 0.25 * min(m, n)
        extrap_method: str, optional
            The extrapolation method to use. See the documentation of
            :py:mod:`pysteps.extrapolation.interface`. Default: 'semilagrangian'
        extrap_kwargs: dict, optional
            Optional dictionary containing keyword arguments for the extrapolation
            method. See :py:mod:`pysteps.extrapolation.interface`.
        add_perturbations: bool
            Set to False to disable perturbations and generate a single
            deterministic nowcast. Default: True
        pert_thrs: float
            Two-element tuple containing the threshold values for estimating the
            perturbation parameters (mm/h). Default: (0.5, 1.0)
        n_ens_members: int, optional
            The number of ensemble members to generate. Default: 10
        vel_pert_method: {'bps', None}, optional
            Name of the generator to use for perturbing the advection field. See
            :py:mod:`pysteps.noise.interface`. Default: 'bps'
        vel_pert_kwargs: dict, optional
            Optional dictionary containing keyword arguments 'p_par' and 'p_perp'
            for the initializer of the velocity perturbator. The choice of the
            optimal parameters depends on the domain and the used optical flow
            method. For the default values and parameters optimized for different
            domains, see :py:func:`pysteps.nowcasts.steps.forecast`.
        kmperpixel: float, optional
            Spatial resolution of the input data (kilometers/pixel). Required if
            vel_pert_method is not None.
        timestep: float, optional
            Time step of the motion vectors (minutes). Required if vel_pert_method
            is not None.
        seed: int, optional
            Optional seed for the random generators.
        num_workers: int, optional
            The number of workers to use for parallel computations. Applicable if
            dask is installed. Default: 1
        use_multiprocessing: bool, optional
            Set to True to improve the performance of certain parallelized parts of
            the code. If set to True, the main script calling linda.forecast must
            be enclosed within the 'if __name__ == "__main__":' block.
            Default: False
        measure_time: bool, optional
            If set to True, measure, print and return the computation time.
            Default: False
        callback: function, optional
            Optional function that is called after computation of each time step of
            the nowcast. The function takes one argument: a three-dimensional array
            of shape (n_ens_members,h,w), where h and w are the height and width
            of the input precipitation fields, respectively. This can be used, for
            instance, writing the outputs into files. Default: None
        return_output: bool, optional
            Set to False to disable returning the outputs as numpy arrays. This can
            save memory if the intermediate results are written to output files
            using the callback function. Default: True
        """
        self.model_id_attr = model_id_attr
        self.add_perturbations = add_perturbations
        self.feature_method = feature_method
        self.max_num_features = max_num_features
        self.feature_kwargs = feature_kwargs
        self.ari_order = ari_order
        self.kernel_type = kernel_type
        self.localization_window_radius = localization_window_radius
        self.errdist_window_radius=errdist_window_radius
        self.acf_window_radius=acf_window_radius
        self.extrap_method = extrap_method
        self.extrap_kwargs = extrap_kwargs
        self.pert_thrs = pert_thrs
        self.n_ens_members = n_ens_members
        self.vel_pert_method = vel_pert_method
        self.vel_pert_kwargs = vel_pert_kwargs
        self.kmperpixel = kmperpixel
        self.timestep = timestep
        self.num_workers = num_workers
        self.seed = seed
        self.use_multiprocessing = use_multiprocessing
        self.measure_time = measure_time
        self.callback=callback
        self.return_output = return_output


        
    
    @deprecate_args(
        {
            "precip_fields": "precip",
            "advection_field": "velocity",
            "num_ens_members": "n_ens_members",
        },
        "1.8.0",
        )
    def process(
        self,
        precip_griddata_list:list,
        velocity_griddata:meb.basicdata.grid_data,
        timesteps:int,
        delta_t = timedelta(minutes=10)
        ):
        """
        Generate a deterministic or ensemble nowcast by using the Lagrangian
        INtegro-Difference equation model with Autoregression (LINDA) model.

        Parameters
        ----------
        precip: array_like
            Array of shape (ari_order + 2, m, n) containing the input rain rate
            or reflectivity fields (in linear scale) ordered by timestamp from
            oldest to newest. The time steps between the inputs are assumed to be
            regular.
        velocity: array_like
            Array of shape (2, m, n) containing the x- and y-components of the
            advection field. The velocities are assumed to represent one time step
            between the inputs.
        timesteps: int
            Number of time steps to forecast.
        

        Returns
        -------
        out: numpy.ndarray
            A four-dimensional array of shape (n_ens_members, timesteps, m, n)
            containing a time series of forecast precipitation fields for each
            ensemble member. If add_perturbations is False, the first dimension is
            dropped. The time series starts from t0 + timestep, where timestep is
            taken from the input fields. If measure_time is True, the return value
            is a three-element tuple containing the nowcast array, the initialization
            time of the nowcast generator and the time used in the main loop
            (seconds). If return_output is set to False, a single None value is
            returned instead.

        Notes
        -----
        It is recommended to choose the feature detector parameters so that the
        number of features is around 20-40. This gives a good tradeoff between
        localization and computation time.

        It is highly recommented to set num_workers>1 to reduce computation time.
        In this case, it is advisable to disable OpenMP by setting the environment
        variable OMP_NUM_THREADS to 1. This avoids slowdown caused by too many
        simultaneous threads.
        """
        add_perturbations = self.add_perturbations
        feature_method = self.feature_method
        max_num_features = self.max_num_features
        feature_kwargs = self.feature_kwargs
        ari_order = self.ari_order
        kernel_type = self.kernel_type
        localization_window_radius = self.localization_window_radius
        errdist_window_radius=self.errdist_window_radius
        acf_window_radius=self.acf_window_radius
        extrap_method = self.extrap_method
        extrap_kwargs = self.extrap_kwargs
        pert_thrs = self.pert_thrs
        n_ens_members = self.n_ens_members
        vel_pert_method = self.vel_pert_method
        vel_pert_kwargs = self.vel_pert_kwargs
        kmperpixel = self.kmperpixel
        timestep = self.timestep
        num_workers = self.num_workers
        seed = self.seed
        use_multiprocessing = self.use_multiprocessing
        measure_time = self.measure_time
        callback=self.callback
        return_output = self.return_output

        # #时间排序
        precip_griddata_list=sort_meb_griddata_list_along_time(precip_griddata_list)

        # 数据维度一致性检查
        for precip_griddata in precip_griddata_list:
            if precip_griddata.values.squeeze().ndim!=2:
                raise ValueError("uncorrect dimension, expect 2 dimensions data like [m,n]")
            else:
                continue
        
        if velocity_griddata.values.squeeze().ndim!=3 and velocity_griddata.values.squeeze().shape[0]!=2:
            raise ValueError("uncorrect dimension, expect 3 dimensions data like [2,m,n]")
        
        # 时间间隔一致性检查
        if check_meb_griddata_time_interval(precip_griddata_list):
            pass
        else:
            raise ValueError('unequal time intervals in meb_griddata_list detected!')


        ## 数据提取
        precip_np_array=[]
        for precip_griddata in precip_griddata_list:
            precip_np_array.append(precip_griddata.values.squeeze())

        velocity_np_array=velocity_griddata.values.squeeze()
 
        
        #构建三维输入
        precip_np_array=np.array(precip_np_array)
        velocity_np_array=np.array(velocity_np_array)


        ## 维度提取
        grid_info=meb.get_grid_of_data(precip_griddata)
        gtime=grid_info.gtime
        glon=[grid_info.slon,grid_info.elon,grid_info.dlon]
        glat=[grid_info.slat,grid_info.elat,grid_info.dlat]

        if delta_t.seconds%3600==0:
            delta_t=delta_t.seconds/3600
            delta_t_units='hours'
        elif delta_t.seconds%60==0:
            delta_t=delta_t.seconds/60
            delta_t_units='minutes'
        elif delta_t.seconds%1==0:
            delta_t=delta_t.seconds
            delta_t_units='seconds'

        dtime_list=np.arange(delta_t,timesteps*delta_t+1,delta_t)
        grid=meb.grid(glon,glat,gtime,dtime_list=dtime_list,dtime_units_attr=delta_t_units)

        result_np=forecast( precip_np_array,
                            velocity_np_array,
                            timesteps,
                            add_perturbations = self.add_perturbations,
                            feature_method = self.feature_method,
                            max_num_features = self.max_num_features,
                            feature_kwargs = self.feature_kwargs,
                            ari_order = self.ari_order,
                            kernel_type = self.kernel_type,
                            localization_window_radius = self.localization_window_radius,
                            errdist_window_radius=self.errdist_window_radius,
                            acf_window_radius=self.acf_window_radius,
                            extrap_method = self.extrap_method,
                            extrap_kwargs = self.extrap_kwargs,
                            pert_thrs = self.pert_thrs,
                            n_ens_members = self.n_ens_members,
                            vel_pert_method = self.vel_pert_method,
                            vel_pert_kwargs = self.vel_pert_kwargs,
                            kmperpixel = self.kmperpixel,
                            timestep = self.timestep,
                            num_workers = self.num_workers,
                            seed = self.seed,
                            use_multiprocessing = self.use_multiprocessing,
                            measure_time = self.measure_time,
                            callback=self.callback,
                            return_output = self.return_output,
                            )
        
         #重构meb.griddata
        nlat=result_np.shape[1]
        nlon=result_np.shape[2]
        result_np=result_np.reshape(1,1,1,timesteps,nlat,nlon)
        result_griddata=meb.grid_data(grid,result_np)
        return result_griddata

        
