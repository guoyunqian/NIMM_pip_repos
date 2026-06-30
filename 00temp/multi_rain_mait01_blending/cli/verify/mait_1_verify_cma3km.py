import meteva
import pandas as pd
import meteva_base as meb

import meteva.method as mem
import meteva.product as mpd


from datetime import datetime

para_example= {
    "num_process": 6,
    "base_on": "foTime",  # 程序运行时段范围是基于起报时间还是预报时间(foTime 表示基于起报时间，obTime 表示基于实况时间)
    "begin_time":datetime(2025,4,1,0,0,0),
    # "end_time":datetime(2025,4,1,21,0,0),
    "end_time":datetime(2025,10,1,23,0,0),
    "time_type": "BT", # 程序运行时段是基于北京时还是世界时，BT表示北京时，UT表示世界时
    "how_fo":"outer", #不同模式数据的合并逻辑，outer 表示取不同模式的时间、时效并集， inner 表示取不同模式的时间时效交集
    # "station_file":r"/data/python_code/mait_24h/info/station_info.txt",
    "station_file":r"../resource/sta_20260601.info",
    # "station_file":"",
    "defalut_value":0,
    "hdf_file_name":"mait_1_verify_cma3km.h5",
    "interp": meteva.base.interp_gs_nearest,
    "ob_data":{
        "dir_ob": r"/data/mnt/107_Observation/R01_national/sfc/YYYYMMDD/h01_YYYYMMDDHH00.m3",
        "hour": [0, 23, 1],
        # "hour": [11,14,3],
        "read_method": meteva.base.io.read_stadata_from_micaps3,
        "read_para": {},
        "reasonable_value": [0, 1000],
        "operation":None,
        "operation_para": {},
        "time_type": "BT",   #数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
    },
    "fo_data":{
        "mait_1h": {
            "dir_fo": r"/data100/st_qpf/rain01/mait_st/sfc/YYYY/YYYYMMDD/YYYYMMDDHH.TTT.nc",
            "hour":[0,21,3],
            "dtime":[0,24,1],
            # "dtime":[0,3,3],
            "read_method": meteva.base.io.read_griddata_from_nc,
            "read_para": {},
            "reasonable_value": [0, 1000],
            "operation": None,
            "operation_para": {},
            "time_type": "UT",  # 数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
            "move_fo_time": 0,
            "file_time_type": "UT"
        },
        "cma_3km": {
            "dir_fo": r"/data/mnt/model_RT/mesoCMA_3KM/APCP/YYYY/YYYYMMDD/YYYYMMDDHH.TTT.nc",
            "hour": [0,21,3],
            "dtime": [0,24,1],
            # "dtime": [0,3,3],
            "read_method": meteva.base.io.read_griddata_from_nc,
            "read_para": {},
            "reasonable_value": [0, 1000],
            "operation": None,
            "operation_para": {},
            "time_type": "UT",  # 数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
            "move_fo_time": 0,
            "file_time_type": "UT"
        },
    },
    "output_dir":r"/data/code/mait_1_test/verify_mait_1_20260601"
}


def get_ts(sta_all, grade_list, product_list, h5_file, plot="bar"):
    result = mpd.score(sta_all, mem.ts, grade_list=grade_list, g="dtime", plot=plot, save_path=f"ts_{plot}_20250401-20251001.png", show=True)
    res_array = result[0]
    dtimes = result[1]
    df_list = []

    for i, shixiao in enumerate(dtimes):
        for j, product in enumerate(product_list):
            row = [product] + res_array[i, j].tolist()
            df_list.append([shixiao] + row)

    columns = ["时效", "产品名称"] + grade_list

    df = pd.DataFrame(df_list, columns=columns)
    df.to_hdf(h5_file, key="ts", mode='a')
    print(df)

    return df


def get_dt_ts(ts, dt):
    df_36 = ts[ts["时效"] == dt]
    ts_values = df_36[grade_list].values
    product_names = df_36["产品名称"].tolist()
    print(ts_values)
    print(product_names)

    # 使用meteva的绘图函数
    name_list_dict2 = {"预报成员": product_names,
                       "分级(单位：mm)": grade_list}
    meb.bar(
        ts_values,
        name_list_dict=name_list_dict2,
        ylabel="TS评分",
        title=f"{dt}时效TS评分",
        save_path=f"ts_{dt}.png",
        grid=True,
        show=True
    )

    return


if __name__ == "__main__":
    # # 组织获取检验数据
    # sta_all = prepare_dataset(para_example)
    # print(sta_all)
    # # print(sta_all[sta_all['dtime'] == 3])
    # h5_file = "mait_1_verify_cma3km.h5"
    # sta_all.to_hdf(h5_file, key="sta_all")

    h5_file = r"D:\data1\zhongzhuan\20260603\mait_1_verify_cma3km.h5"
    # h5_file = r"D:\data1\zhongzhuan\20260601\mait_1_verify.h5"
    sta_all = pd.read_hdf(h5_file, key="sta_all")
    print(sta_all)
    unique_values = sta_all['id'].unique()
    print(len(unique_values), unique_values)

    product_list = ["mait_1h", "cma_3km"]
    grade_list = [0.1, 1, 5, 10]
    get_ts(sta_all, grade_list, product_list, h5_file)  # 保存ts评分结果



