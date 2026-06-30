# -*- coding: utf-8 -*-
"""
Created on Mon Sep 18 09:30:25 2023

@author: cheny
"""

from .base_plugin import PostProcessingPlugin
from typing import Optional, Tuple
from .utils import *
from optical_flow_nowcast.src.steps import forecast
import meteva_base as meb
from datetime import timedelta 
class Steps(PostProcessingPlugin):
    
    def __init__(self, 
                 model_id_attr: Optional[str] = None,
                 n_ens_members: Optional[int]=4,
                 n_cascade_levels: Optional[int]=6,
                 precip_thr : Optional[float] = None,
                 kmperpixel : Optional[float] = None,
                 timestep : Optional[float] =None,
                 extrap_method : Optional[str] = 'semilagrangian',
                 decomp_method : Optional[str] = 'fft',
                 bandpass_filter_method : Optional[str]="gaussian",
                 noise_method : Optional[str]="nonparametric",
                 noise_stddev_adj: Optional[str]=None,
                 ar_order : Optional[int]=2,
                 vel_pert_method : Optional[str]= None,
                 conditional: Optional[bool]=False,
                 probmatching_method: Optional[str]="cdf",
                 mask_method: Optional[str]= None,
                 seed: Optional[int]=None,
                 num_workers: Optional[int]=1,
                 fft_method : Optional[str]="numpy",
                 domain : Optional[str]="spatial",
                 extrap_kwargs: Optional[dict]=None,
                 filter_kwargs: Optional[dict]=None,
                 noise_kwargs: Optional[dict]=None,
                 vel_pert_kwargs: Optional[dict]=None,
                 mask_kwargs: Optional[dict]=None,
                 measure_time: Optional[bool]=False,
                 callback=None,
                 return_output: Optional[bool]=True,
                 ) -> None:
        """
        Initialise the class

        Args:
        model_id_attr:
            Name of the attribute used to identify the source model for
            blending.
        n_ens_members: int, optional
            The number of ensemble members to generate.
        n_cascade_levels: int, optional
            The number of cascade levels to use.
        precip_thr: float, optional
            Specifies the threshold value for minimum observable precipitation
            intensity. Required if mask_method is not None or conditional is True.
        kmperpixel: float, optional
            Spatial resolution of the input data (kilometers/pixel). Required if
            vel_pert_method is not None or mask_method is 'incremental'.
        timestep: float, optional
            Time step of the motion vectors (minutes). Required if vel_pert_method is
            not None or mask_method is 'incremental'.
        extrap_method: str, optional
            Name of the extrapolation method to use. See the documentation of
            pysteps.extrapolation.interface.
        decomp_method: {'fft'}, optional
            Name of the cascade decomposition method to use. See the documentation
            of pysteps.cascade.interface.
        bandpass_filter_method: {'gaussian', 'uniform'}, optional
            Name of the bandpass filter method to use with the cascade decomposition.
            See the documentation of pysteps.cascade.interface.
        noise_method: {'parametric','nonparametric','ssft','nested',None}, optional
            Name of the noise generator to use for perturbating the precipitation
            field. See the documentation of pysteps.noise.interface. If set to None,
            no noise is generated.
        noise_stddev_adj: {'auto','fixed',None}, optional
            Optional adjustment for the standard deviations of the noise fields added
            to each cascade level. This is done to compensate incorrect std. dev.
            estimates of casace levels due to presence of no-rain areas. 'auto'=use
            the method implemented in pysteps.noise.utils.compute_noise_stddev_adjs.
            'fixed'= use the formula given in :cite:`BPS2006` (eq. 6), None=disable
            noise std. dev adjustment.
        ar_order: int, optional
            The order of the autoregressive model to use. Must be >= 1.
        vel_pert_method: {'bps',None}, optional
            Name of the noise generator to use for perturbing the advection field. See
            the documentation of pysteps.noise.interface. If set to None, the advection
            field is not perturbed.
        conditional: bool, optional
            If set to True, compute the statistics of the precipitation field
            conditionally by excluding pixels where the values are below the
            threshold precip_thr.
        mask_method: {'obs','sprog','incremental',None}, optional
            The method to use for masking no precipitation areas in the forecast
            field. The masked pixels are set to the minimum value of the observations.
            'obs' = apply precip_thr to the most recently observed precipitation
            intensity field, 'sprog' = use the smoothed forecast field from S-PROG,
            where the AR(p) model has been applied, 'incremental' = iteratively
            buffer the mask with a certain rate (currently it is 1 km/min),
            None=no masking.
        probmatching_method: {'cdf','mean',None}, optional
            Method for matching the statistics of the forecast field with those of
            the most recently observed one. 'cdf'=map the forecast CDF to the observed
            one, 'mean'=adjust only the conditional mean value of the forecast field
            in precipitation areas, None=no matching applied. Using 'mean' requires
            that precip_thr and mask_method are not None.
        seed: int, optional
            Optional seed number for the random generators.
        num_workers: int, optional
            The number of workers to use for parallel computation. Applicable if dask
            is enabled or pyFFTW is used for computing the FFT. When num_workers>1, it
            is advisable to disable OpenMP by setting the environment variable
            OMP_NUM_THREADS to 1. This avoids slowdown caused by too many simultaneous
            threads.
        fft_method: str, optional
            A string defining the FFT method to use (see utils.fft.get_method).
            Defaults to 'numpy' for compatibility reasons. If pyFFTW is installed,
            the recommended method is 'pyfftw'.
        domain: {"spatial", "spectral"}
            If "spatial", all computations are done in the spatial domain (the
            classical STEPS model). If "spectral", the AR(2) models and stochastic
            perturbations are applied directly in the spectral domain to reduce
            memory footprint and improve performance :cite:`PCH2019b`.
        extrap_kwargs: dict, optional
            Optional dictionary containing keyword arguments for the extrapolation
            method. See the documentation of pysteps.extrapolation.
        filter_kwargs: dict, optional
            Optional dictionary containing keyword arguments for the filter method.
            See the documentation of pysteps.cascade.bandpass_filters.py.
        noise_kwargs: dict, optional
            Optional dictionary containing keyword arguments for the initializer of
            the noise generator. See the documentation of pysteps.noise.fftgenerators.
        vel_pert_kwargs: dict, optional
            Optional dictionary containing keyword arguments 'p_par' and 'p_perp' for
            the initializer of the velocity perturbator. The choice of the optimal
            parameters depends on the domain and the used optical flow method.
    
            Default parameters from :cite:`BPS2006`:
            p_par  = [10.88, 0.23, -7.68]
            p_perp = [5.76, 0.31, -2.72]
    
            Parameters fitted to the data (optical flow/domain):
    
            darts/fmi:
            p_par  = [13.71259667, 0.15658963, -16.24368207]
            p_perp = [8.26550355, 0.17820458, -9.54107834]
    
            darts/mch:
            p_par  = [24.27562298, 0.11297186, -27.30087471]
            p_perp = [-7.80797846e+01, -3.38641048e-02, 7.56715304e+01]
    
            darts/fmi+mch:
            p_par  = [16.55447057, 0.14160448, -19.24613059]
            p_perp = [14.75343395, 0.11785398, -16.26151612]
    
            lucaskanade/fmi:
            p_par  = [2.20837526, 0.33887032, -2.48995355]
            p_perp = [2.21722634, 0.32359621, -2.57402761]
    
            lucaskanade/mch:
            p_par  = [2.56338484, 0.3330941, -2.99714349]
            p_perp = [1.31204508, 0.3578426, -1.02499891]
    
            lucaskanade/fmi+mch:
            p_par  = [2.31970635, 0.33734287, -2.64972861]
            p_perp = [1.90769947, 0.33446594, -2.06603662]
    
            vet/fmi:
            p_par  = [0.25337388, 0.67542291, 11.04895538]
            p_perp = [0.02432118, 0.99613295, 7.40146505]
    
            vet/mch:
            p_par  = [0.5075159, 0.53895212, 7.90331791]
            p_perp = [0.68025501, 0.41761289, 4.73793581]
    
            vet/fmi+mch:
            p_par  = [0.29495222, 0.62429207, 8.6804131 ]
            p_perp = [0.23127377, 0.59010281, 5.98180004]
    
            fmi=Finland, mch=Switzerland, fmi+mch=both pooled into the same data set
    
            The above parameters have been fitten by using run_vel_pert_analysis.py
            and fit_vel_pert_params.py located in the scripts directory.
    
            See pysteps.noise.motion for additional documentation.
        mask_kwargs: dict
            Optional dictionary containing mask keyword arguments 'mask_f' and
            'mask_rim', the factor defining the the mask increment and the rim size,
            respectively.
            The mask increment is defined as mask_f*timestep/kmperpixel.
        measure_time: bool
            If set to True, measure, print and return the computation time.
        callback: function, optional
            Optional function that is called after computation of each time step of
            the nowcast. The function takes one argument: a three-dimensional array
            of shape (n_ens_members,h,w), where h and w are the height and width
            of the input precipitation fields, respectively. This can be used, for
            instance, writing the outputs into files.
        return_output: bool, optional
            Set to False to disable returning the outputs as numpy arrays. This can
            save memory if the intermediate results are written to output files using
            the callback function.
        """
        self.model_id_attr = model_id_attr
        self.n_ens_members=n_ens_members
        self.n_cascade_levels=n_cascade_levels
        self.precip_thr=precip_thr
        self.kmperpixel=kmperpixel
        self.timestep=timestep
        self.extrap_method=extrap_method
        self.decomp_method=decomp_method
        self.bandpass_filter_method=bandpass_filter_method
        self.noise_method=noise_method
        self.noise_stddev_adj=noise_stddev_adj
        self.ar_order=ar_order
        self.vel_pert_method=vel_pert_method
        self.conditional=conditional
        self.probmatching_method=probmatching_method
        self.mask_method=mask_method
        self.seed=seed
        self.num_workers=num_workers
        self.fft_method=fft_method
        self.domain=domain
        self.extrap_kwargs=extrap_kwargs
        self.filter_kwargs=filter_kwargs
        self.noise_kwargs=noise_kwargs
        self.vel_pert_kwargs=vel_pert_kwargs
        self.mask_kwargs=mask_kwargs
        self.measure_time=measure_time
        self.callback=callback
        self.return_output=return_output

    @deprecate_args({"R": "precip", "V": "velocity", "R_thr": "precip_thr"}, "1.8.0")
    def process(
        self,
        precip_griddata_list:list,
        velocity_griddata:meb.basicdata.grid_data,
        timesteps:int,
        delta_t = timedelta(minutes=10)
    ):
        """
        Generate a nowcast ensemble by using the Short-Term Ensemble Prediction
        System (STEPS) method.
    
        Parameters
        ----------
        precip: array-like
            Array of shape (ar_order+1,m,n) containing the input precipitation fields
            ordered by timestamp from oldest to newest. The time steps between the
            inputs are assumed to be regular.
        velocity: array-like
            Array of shape (2,m,n) containing the x- and y-components of the advection
            field. The velocities are assumed to represent one time step between the
            inputs. All values are required to be finite.
        timesteps: int or list of floats
            Number of time steps to forecast or a list of time steps for which the
            forecasts are computed (relative to the input time step). The elements
            of the list are required to be in ascending order.
        
    
        Returns
        -------
        out: ndarray
            If return_output is True, a four-dimensional array of shape
            (n_ens_members,num_timesteps,m,n) containing a time series of forecast
            precipitation fields for each ensemble member. Otherwise, a None value
            is returned. The time series starts from t0+timestep, where timestep is
            taken from the input precipitation fields. If measure_time is True, the
            return value is a three-element tuple containing the nowcast array, the
            initialization time of the nowcast generator and the time used in the
            main loop (seconds).
    
        See also
        --------
        pysteps.extrapolation.interface, pysteps.cascade.interface,
        pysteps.noise.interface, pysteps.noise.utils.compute_noise_stddev_adjs
    
        References
        ----------
        :cite:`Seed2003`, :cite:`BPS2006`, :cite:`SPN2013`, :cite:`PCH2019b`
        """
    
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
            
        member_list=np.arange(0,self.n_ens_members,1)
        dtime_list=np.arange(delta_t,timesteps*delta_t+1,delta_t)
        grid=meb.grid(glon,glat,gtime,dtime_list=dtime_list,dtime_units_attr=delta_t_units,member_list=member_list)

        result_np=forecast( precip_np_array,
                            velocity_np_array,
                            timesteps,
                            n_ens_members=self.n_ens_members,
                            n_cascade_levels=self.n_cascade_levels,
                            precip_thr=self.precip_thr,
                            kmperpixel=self.kmperpixel,
                            timestep=self.timestep,
                            extrap_method=self.extrap_method,
                            decomp_method=self.decomp_method,
                            bandpass_filter_method=self.bandpass_filter_method,
                            noise_method=self.noise_method,
                            noise_stddev_adj=self.noise_stddev_adj,
                            ar_order=self.ar_order,
                            vel_pert_method=self.vel_pert_method,
                            conditional=self.conditional,
                            probmatching_method=self.probmatching_method,
                            mask_method=self.mask_method,
                            seed=self.seed,
                            num_workers=self.num_workers,
                            fft_method=self.fft_method,
                            domain=self.domain,
                            extrap_kwargs=self.extrap_kwargs,
                            filter_kwargs=self.filter_kwargs,
                            noise_kwargs=self.noise_kwargs,
                            vel_pert_kwargs=self.vel_pert_kwargs,
                            mask_kwargs=self.mask_kwargs,
                            measure_time=self.measure_time,
                            callback=self.callback,
                            return_output=self.return_output,
                            )
         #重构meb.griddata
        nlat=result_np.shape[2]
        nlon=result_np.shape[3]
        result_np=result_np.reshape(1,1,self.n_ens_members,timesteps,nlat,nlon)
        result_griddata=meb.grid_data(grid,result_np)
        return result_griddata
        




        
