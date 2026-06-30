import meteva
import pandas as pd
import numpy as np
import meteva_base as meb
import meteva.product as mpd

import meteva.method as mem
import meteva.product as mpd

import datetime

ob_dir = r"/data/mnt/107_Observation/R01_national/sfc/YYYYMMDD/h01_YYYYMMDDHH00.m3"
cma3km_dir = r"/data/mnt/model_RT/mesoCMA_3KM/APCP/YYYY/YYYYMMDD/YYYYMMDDHH.TTT.nc"
mait_dir = r"/data100/st_qpf/rain01/mait_st/sfc/YYYY/YYYYMMDD/YYYYMMDDHH.TTT.nc"

sta_info = r"../resource/sta_20260601.info"


time = datetime.datetime(2025, 4, 1, 8, 0, 0)
dtime = 3

ob_path = meb.get_path(ob_dir, time+datetime.timedelta(hours=dtime))
cma3km_path = meb.get_path(cma3km_dir, time-datetime.timedelta(hours=8), dtime)
mait_path = meb.get_path(mait_dir, time-datetime.timedelta(hours=8), dtime)


station = meteva.base.io.read_stadata_from_micaps3(sta_info)

print("=----------------->>>> : ", ob_path)
ob_sta = meteva.base.io.read_stadata_from_micaps3(ob_path)
ob_dat = meb.put_stadata_on_station(ob_sta, station)
print(ob_dat)

print("=----------------->>>> : ", cma3km_path)
cma3km_grd = meteva.base.io.read_griddata_from_nc(cma3km_path)
cma3km_dat = meteva.base.interp_gs_nearest(cma3km_grd, station)
print(cma3km_dat)

print("=----------------->>>> : ", mait_path)
mait_grd = meteva.base.io.read_griddata_from_nc(mait_path)
mait_dat = meteva.base.interp_gs_nearest(mait_grd, station)
print(mait_dat)
