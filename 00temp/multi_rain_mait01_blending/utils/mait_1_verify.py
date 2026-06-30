import meteva
import pandas as pd
import meteva_base as meb

import meteva.method as mem
import meteva.product as mpd


from datetime import datetime

para_example= {
    "num_process": 6,
    "base_on": "foTime",  # 程序运行时段范围是基于起报时间还是预报时间(foTime 表示基于起报时间，obTime 表示基于实况时间)
    "begin_time":datetime(2026,4,15,8,0,0),
    "end_time":datetime(2026,4,20,20,0,0),
    "time_type": "BT", # 程序运行时段是基于北京时还是世界时，BT表示北京时，UT表示世界时
    "how_fo":"outer", #不同模式数据的合并逻辑，outer 表示取不同模式的时间、时效并集， inner 表示取不同模式的时间时效交集
    # "station_file":r"/data/python_code/mait_24h/info/station_info.txt",
    "station_file":r"/data/mnt/107_Observation/R01_national/sfc/20260401/h01_202604010000.m3",
    # "station_file":"",
    "defalut_value":0,
    "hdf_file_name":"mait_1_verify_data.h5",
    "interp": meteva.base.interp_gs_nearest,
    "ob_data":{
        "dir_ob": r"/data/mnt/107_Observation/R01_national/sfc/YYYYMMDD/h01_YYYYMMDDHH00.m3",
        "hour": [0, 23, 1],
        "read_method": meteva.base.io.read_stadata_from_micaps3,
        "read_para": {},
        "reasonable_value": [0, 1000],
        "operation":None,
        "operation_para": {},
        "time_type": "BT",   #数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
    },
    "fo_data":{
        "mait_st": {
            "dir_fo": r"/data100/st_qpf/rain01/mait_st/sfc/YYYY/YYYYMMDD/YYYYMMDDHH.TTT.m3",
            "hour":[8,20,12],
            "dtime":[0,24,1],
            "read_method": meteva.base.io.read_stadata_from_micaps3,
            "read_para": {},
            "reasonable_value": [0, 1000],
            "operation": None,
            "operation_para": {},
            "time_type": "UT",  # 数据文件是以北京时还是世界时命名，BT表示北京时，UT表示世界时
            "move_fo_time": 0,
            "file_time_type": "UT"
        },
        "mait_chen": {
            "dir_fo": r"/data234/GUO_data/250825_smqpf/rain01/mait_chen/YYYYMMDD/YYYYMMDDHH.TTT.m3",
            "hour": [0,12,12],
            "dtime": [0,24,1],
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
    "output_dir":r"/data/code/mait_1_test/verify_mait_1"
}


def get_verify_result(sta_all):
    """
    计算并保存验证结果。

    参数
    ----------
    sta_all : pandas.DataFrame
        包含观测和预报数据的DataFrame

    返回值
    -------
    None
    """
    # 添加小时列用于筛选
    sta_all['hour'] = pd.to_datetime(sta_all['time']).dt.hour

    # 筛选8时和20时的数据
    sta_all_08 = sta_all[sta_all['hour'] == 8].copy()
    sta_all_20 = sta_all[sta_all['hour'] == 20].copy()

    # 重置索引
    sta_all_08 = sta_all_08.reset_index(drop=True)
    sta_all_20 = sta_all_20.reset_index(drop=True)

    # 删除临时小时列
    sta_all.drop(columns=['hour'], inplace=True)
    sta_all_08.drop(columns=['hour'], inplace=True)
    sta_all_20.drop(columns=['hour'], inplace=True)

    # 打印数据信息
    print(sta_all_08)
    print("=------------------------------------------------------------------------------->>>")
    print(sta_all_20)

    # 定义阈值列表
    grade_list = [0.1, 10, 25, 50, 100]

    # 定义预报时效列表
    dtimes = [36, 60, 84, 108, 132, 156, 180, 204, 228, 252]

    # 创建验证结果DataFrame
    verify_df_08 = pd.DataFrame({'dtime': dtimes})
    verify_df_20 = pd.DataFrame({'dtime': dtimes})

    # 定义预报产品名称列表
    pro_names = ["mait_st", "mait_chen"]  # 后续添加新的产品名称只需修改这里

    # 遍历每个预报时效
    for idx, dtime in enumerate(dtimes):
        # 获取观测数据
        ob_sta_08 = sta_all_08[sta_all_08['dtime'] == dtime]['ob'].values
        ob_sta_20 = sta_all_20[sta_all_20['dtime'] == dtime]['ob'].values

        # 遍历每个预报产品
        for pro_name in pro_names:
            # 获取预报数据
            pro_sta_08 = sta_all_08[sta_all_08['dtime'] == dtime][pro_name].values
            pro_sta_20 = sta_all_20[sta_all_20['dtime'] == dtime][pro_name].values

            # 计算验证指标
            pro_hfmc_08 = mem.hfmc(ob_sta_08, pro_sta_08, grade_list=grade_list)
            pro_hfmc_20 = mem.hfmc(ob_sta_20, pro_sta_20, grade_list=grade_list)

            pro_ts_08 = mem.ts(ob_sta_08, pro_sta_08, grade_list=grade_list)
            pro_ts_20 = mem.ts(ob_sta_20, pro_sta_20, grade_list=grade_list)

            # 打印验证结果
            print("=--------------------------------------------------->>> ", dtime, pro_name)
            print(pro_hfmc_08)
            print(pro_hfmc_20)
            print(pro_ts_08)
            print(pro_ts_20)

            # 填充验证结果到DataFrame
            for grade_idx, grade in enumerate(grade_list):
                # 填充8时验证结果
                verify_df_08.loc[idx, f'{pro_name}_hit_{grade}'] = pro_hfmc_08[grade_idx][0]
                verify_df_08.loc[idx, f'{pro_name}_miss_{grade}'] = pro_hfmc_08[grade_idx][1]
                verify_df_08.loc[idx, f'{pro_name}_over_{grade}'] = pro_hfmc_08[grade_idx][2]
                verify_df_08.loc[idx, f'{pro_name}_ts_{grade}'] = pro_ts_08[grade_idx]

                # 填充20时验证结果
                verify_df_20.loc[idx, f'{pro_name}_hit_{grade}'] = pro_hfmc_20[grade_idx][0]
                verify_df_20.loc[idx, f'{pro_name}_miss_{grade}'] = pro_hfmc_20[grade_idx][1]
                verify_df_20.loc[idx, f'{pro_name}_over_{grade}'] = pro_hfmc_20[grade_idx][2]
                verify_df_20.loc[idx, f'{pro_name}_ts_{grade}'] = pro_ts_20[grade_idx]

                # 打印最终验证结果
    print(verify_df_08)
    print(verify_df_20)

    # 保存验证结果到CSV文件
    verify_df_08.to_csv('verify_results_08.csv')
    verify_df_20.to_csv('verify_results_20.csv')

    # 保存验证结果到HDF文件
    verify_df_08.to_hdf('verify_results.h5', key='res_08')
    verify_df_20.to_hdf('verify_results.h5', key='res_20')
    sta_all.to_hdf('verify_results.h5', key='sta_all')

    return


def get_ts(sta_all, grade_list, product_list, h5_file, plot="bar"):
    result = mpd.score(sta_all, mem.ts, grade_list=grade_list, g="dtime", plot=plot, save_path=f"ts_{plot}.png", show=True)
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
    # h5_file = "mait_1_sta_all.h5"
    # sta_all.to_hdf(h5_file, key="sta_all")

    # # 处理检验，生成表格
    # # sta_all = pd.read_hdf("sta_all.h5", key="sta_all")
    # # get_verify_result(sta_all)
    #
    # 处理检验，生成图片，保存检验结果
    # sta_all = pd.read_hdf(r"D:\data1\zhongzhuan\20260325\verify_results.h5", key="sta_all")
    h5_file = r"D:\data1\zhongzhuan\20260525\mait_1_sta_all.h5"
    sta_all = pd.read_hdf(h5_file, key="sta_all")
    sta_all.rename(columns={'mait_chen': 'mait_1h'}, inplace=True)
    print(sta_all)
    # result = mpd.score(sta_all,mem.ts, s = {"dtime":36, "grade_list":[50]})
    # result = mpd.score(sta_all,mem.ts, grade_list=[0.1, 10, 25, 50, 100], s = {"dtime":36}, plot="bar", save_path="ts_36_50.png", show=True)
    #
    product_list = ["mait_st", "mait_1h"]
    grade_list = [0.1, 1, 10, 20]
    get_ts(sta_all, grade_list, product_list, h5_file)  # 保存ts评分结果
    # # ts_res = pd.read_hdf(h5_file, key="ts")
    # # print(ts_res)
    # # get_dt_ts(ts_res, 36)  # 提取36时效TS评分，保存图片




