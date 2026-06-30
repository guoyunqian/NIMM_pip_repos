"""
2. 短时预报检验评分，0-24h逐1h预报 （优先提取）
实况： 10.28.16.234/data1/DataPool/01CLDAS/02CMPAS/Hourly/NRT_1km/APCP， 1km逐1h网格实况
预报1： 10.20.90.100/GridDataShare100/jianyan/NMC/st_qpf/rain01/mait_st/sfc/2025，mait01h。 用户名密码: nmc/nmc
预报2： 10.28.16.186/2021YFC_data/subject5/xuj/云南， CGAN。 用户名密码：user/123456Test(只读)
预报3： 10.28.16.234/model_RT/mesoCMA_3KM/APCP01， CMA3km。
预报5： 10.28.16.234/model_RT/mesoCMA_SH9KM/APCP01, SH9KM。
"""

import meteva
import pandas as pd
import meteva_base as meb
import meteva.method as mem
import meteva.product as mpd

from datetime import datetime

from utils.data_prepare_plugin import prepare_dataset

para_example= {
    "num_process": 8,
    "base_on": "foTime",  # 程序运行时段范围是基于起报时间还是预报时间(foTime 表示基于起报时间，obTime 表示基于实况时间)
    # "begin_time":datetime(2025,6,1,0,0,0),
    "begin_time":datetime(2025,10,1,0,0,0),
    "end_time":datetime(2025,10,1,12,0,0),
    # "end_time":datetime(2025,6,30,12,0,0),
    "time_type": "UT", # 程序运行时段是基于北京时还是世界时，BT表示北京时，UT表示世界时
    "how_fo":"outer", #不同模式数据的合并逻辑，outer 表示取不同模式的时间、时效并集， inner 表示取不同模式的时间时效交集
    # "station_file":r"/data/python_code/mait_24h/info/station_info.txt",
    "station_file":r"D:/Work/qpf_fm_rain01/resource/data/R01_national/sfc/20251001/h01_202510010000.m3",
    # "station_file":"",
    "defalut_value":0,
    "hdf_file_name":"verify_data.h5",
    "interp": meteva.base.interp_gs_nearest,
    "ob_data":{
        "dir_ob": r"D:/Work/qpf_fm_rain01/resource/data/R01_national/sfc/YYYYMMDD/h01_YYYYMMDDHH00.m3",
        "hour": [0, 23, 1],
        "read_method": meteva.base.io.read_stadata_from_micaps3,
        "read_para": {},
        "reasonable_value": [0, 1000],
        "operation":None,
        "operation_para": {},
        "time_type": "BT",   #数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
    },
    "fo_data":{
        "QpfFrequencyMatch_Rain01": {
            "dir_fo": r"D:/Work/QpfFrequencyMatch_Rain01/output/rain01/ecmwf_V2/YYYYMMDD/YYYYMMDDHH.TTT.m3",
            "hour": [0, 12, 12],
            "dtime": [1, 48, 1],
            "read_method": meteva.base.io.read_stadata_from_micaps3,
            "read_para": {},
            "reasonable_value": [0, 1000],
            "operation": None,
            "operation_para": {},
            "time_type": "UT",  #数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
            "move_fo_time": 0,
            "file_time_type": "UT"
        },
        "qpf_fm_rain01": {
            "dir_fo": r"D:/Work/qpf_fm_rain01/resource/data/output/rain01/ecmwf_nimm/YYYYMMDD/YYYYMMDDHH.TTT.m3",
            "hour": [0, 12, 12],
            "dtime": [1, 48, 1],
            "read_method": meteva.base.io.read_stadata_from_micaps3,
            "read_para": {},
            "reasonable_value": [0, 1000],
            "operation": None,
            "operation_para": {},
            "time_type": "UT",   #数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
            "move_fo_time": 0,
            "file_time_type": "UT"
        },
    },
    "output_dir":r"./verify_data"
}

if __name__ == "__main__":
    h5_file = "D:/Work/qpf_fm_rain01/resource/data/output/verify_data.h5"
    # sta_all = prepare_dataset(para_example)
    # print(sta_all)
    # sta_all.to_hdf(h5_file, key="sta_all")

    sta_all = pd.read_hdf(h5_file, key="sta_all")
    print(sta_all)
    product_list = ["QpfFrequencyMatch_Rain01", "qpf_fm_rain01"]
    grade_list = [0.1, 5, 10]
    # get_ts(sta_all, grade_list, product_list, h5_file)  # 保存ts评分结果
    result = mpd.score(sta_all, mem.ts, grade_list=grade_list, g="dtime", plot="bar", ncol=1, save_path=f"ts_bar.png", show=True)