import meteva
import pandas as pd
import meteva_base as meb

import meteva.method as mem
import meteva.product as mpd


from datetime import datetime

para_example= {
    "num_process": 4,
    "base_on": "foTime",  # 程序运行时段范围是基于起报时间还是预报时间(foTime 表示基于起报时间，obTime 表示基于实况时间)
    "begin_time":datetime(2025,8,26,0,0,0),
    #"end_time":datetime(2025,7,30,12,0,0),
    "end_time":datetime(2025,8,26,0,0,0),
    "time_type": "UT", # 程序运行时段是基于北京时还是世界时，BT表示北京时，UT表示世界时
    "how_fo":"outer", #不同模式数据的合并逻辑，outer 表示取不同模式的时间、时效并集， inner 表示取不同模式的时间时效交集
    # "station_file":r"/data/python_code/mait_24h/info/station_info.txt",
    "station_file":r"../resource/sta_20260601.info",
    # "station_file":"",
    "defalut_value":0,
    "hdf_file_name":"verify_data_20250401-20251001.h5",
    "interp": meteva.base.interp_gs_nearest,
    "ob_data":{
        "dir_ob": r"/mnt/Observation/r24/sfc/YYMMDDHH.000",
        "hour": [8, 20, 12],
        "read_method": meteva.base.io.read_stadata_from_micaps3,
        "read_para": {},
        "reasonable_value": [0, 1000],
        "operation":None,
        "operation_para": {},
        "time_type": "BT",   #数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
    },
    "fo_data":{
        "ec": {
            "dir_fo": r"/mnt/nimm_data/model_RT/globalECMWF_C1D/APCP24/YYYY/YYYYMMDD/NC/YYYYMMDDHH.TTT.nc",
            "hour": [0, 12, 12],
            "dtime": [36, 252, 24],
            "read_method": meteva.base.io.read_griddata_from_nc,
            "read_para": {},
            "reasonable_value": [0, 1000],
            "operation": None,
            "operation_para": {},
            "time_type": "UT",  # 数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
            "move_fo_time": 0,
            "file_time_type": "UT"
        },
        "mait": {
            "dir_fo": r"/mnt/sm_qpf/v2021/rain24/mait/sfc/YYYYMMDD/YYYYMMDDHH.TTT.m3",
            "hour": [0, 12, 12],
            "dtime": [36, 252, 24],
            "read_method": meteva.base.io.read_stadata_from_micaps3,
            "read_para": {},
            "reasonable_value": [0, 1000],
            "operation": None,
            "operation_para": {},
            "time_type": "UT",  # 数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
            "move_fo_time": 0,
            "file_time_type": "UT"
        },
    },
    "output_dir":r"/data/python_code/mait_24h/resource/verify_data_20260601"
}


def get_ts(sta_all, grade_list, product_list, h5_file, plot="bar"):
    result = mpd.score(sta_all, mem.ts, grade_list=grade_list, g="dtime", plot=plot, save_path=f"mait24h_ts_{plot}_20250401-20251001.png", show=True)
    print(result)
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
    # # # 组织获取检验数据
    # sta_all = prepare_dataset(para_example)
    # # pd.set_option('display.max_rows', None)
    # print(sta_all)
    # h5_file = "verify_data_20250401-20251001.h5"
    # sta_all.to_hdf(h5_file, key="sta_all")


    # 处理检验，生成图片，保存检验结果
    h5_file = r"D:\data1\zhongzhuan\20260601\verify_data_20250401-20251001.h5"
    sta_all = pd.read_hdf(h5_file, key="sta_all")

    # pd.set_option('display.max_columns', None)  # 显示所有列
    # pd.set_option('display.max_rows', None)  # 显示所有行
    # pd.set_option('display.max_colwidth', None)  # 显示完整列内容
    # pd.set_option('display.width', None)  # 自动检测显示宽度
    # print(sta_all)

    df_filtered = sta_all[(sta_all['ob'] > 50) & (sta_all['ob'] < 100)]
    print(df_filtered)
    df_filtered = sta_all[(sta_all['ec'] > 50) & (sta_all['ec'] < 100)]
    print(df_filtered)
    df_filtered = sta_all[(sta_all['mait'] > 50) & (sta_all['mait'] < 100)]
    print(df_filtered)

    product_list = ["ec", 'mait']
    grade_list = [0.1, 10, 25, 50, 100]
    get_ts(sta_all, grade_list, product_list, h5_file)  # 保存ts评分结果




