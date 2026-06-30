import meteva_base as meb
import numpy as np
import datetime
import shutil
import copy
import os


para_example= {
    "base_on":"foTime",
    "begin_time": None,
    "end_time": None,
    "station_file":r"",
    "defalut_value":0,
    "hdf_file_name":"output",
    "interp": meb.interp_gs_nearest,
    "how_fo":"outer",
    "time_type":"UT",
    "ob_data":{},
    "fo_data":{},
    "output_dir":r"H:\test_data\output\mpd\application"
}

ob_data_dict = {
    "dir_ob": r"",
    "hour":None,
    "read_method": meb.read_stadata_from_micaps3,
    "read_para": {},
    "reasonable_value": [0, 1000],
    # "operation":meb.fun.sum_of_sta,
    "operation": None,
    "operation_para": {"used_coords": ["time"], "span": None},
    "time_type": "BT",
}

fo_data_dict = {
    "dir_fo": r"",
    "hour":[0, 12, 12],
    "dtime":[36, 252, 24],
    "read_method": meb.read_stadata_from_micaps3,
    "read_para": {},
    "reasonable_value": [0, 1000],
    # "operation": meb.fun.sum_of_sta,
    "operation": None,
    "operation_para": {"used_coords": ["time"], "span": 24},
    "time_type": "UT",
    "move_fo_time": 0
}

para_list_example = [
    {
        "input":r"O:\data\grid\GRAPES_GFS\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output":r"L:\luoqi\GRAPES_GFS\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start":datetime.datetime(2020,3,1,8,0),
        "end":datetime.datetime(2020,6,1,8,0),
        "hour_range":[8,21,12],
        "dh_range":[3,241,3],
        "recover":False
    },

    {
        "input": r"O:\data\grid\ECMWF_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\ECMWF_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [8, 21, 12],
        "dh_range": [3, 241, 3],
        "recover": False
    },

    {
        "input": r"O:\data\grid\NCEP_GFS_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\NCEP_GFS_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [8, 21, 12],
        "dh_range": [3, 241, 3],
        "recover": False
    },

    {
        "input": r"O:\data\grid\SHANGHAI_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\SHANGHAI_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [0, 24, 1],
        "dh_range": [0, 25, 1],
        "recover": False
    },

    {
        "input": r"O:\data\grid\GRAPES_MESO_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\GRAPES_MESO_HR\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [2, 24, 3],
        "dh_range": [0, 85, 1],
        "recover": False
    },

    {
        "input": r"O:\data\grid\GRAPES_3KM\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "output": r"L:\luoqi\GRAPES_3KM\APCP\YYYYMMDD\YYMMDDHH.TTT.nc",
        "start": datetime.datetime(2020, 3, 1, 8, 0),
        "end": datetime.datetime(2020, 6, 1, 8, 0),
        "hour_range": [2, 24, 3],
        "dh_range": [0, 37, 1],
        "recover": False
    },

]


def copy_data_file(para_list):
    for para in para_list:
        time0 = para["start"]
        time1 = datetime.datetime(time0.year,time0.month,time0.day,0,0)
        hour_list =  np.arange(para["hour_range"][0],para["hour_range"][1],para["hour_range"][2]).tolist()
        dh_list = np.arange(para["dh_range"][0], para["dh_range"][1], para["dh_range"][2]).tolist()
        recover = para["recover"]
        while time1 <= para["end"]:
            for hour in hour_list:
                time2 = time1 +datetime.timedelta(hours=hour)
                for dh in dh_list:
                    path_out = meb.get_path(para["output"],time2,dh)
                    if recover or not os.path.exists(path_out):
                        path_in = meb.get_path(para["input"],time2,dh)
                        if os.path.exists(path_in):
                            meb.creat_path(path_out)
                            shutil.copyfile(path_in,path_out)
            time1 = time1 + datetime.timedelta(hours=24)


def copy_during_data_file(root_in,root_out,start = None,end = None,recover = False):
    path_list = meb.path_tools.get_during_path_list_in_dir(root_in,None,start,end)
    for path in path_list:
        path_copy = path.replace(root_in,root_out)
        if not os.path.exists(path_copy) or recover:
            meb.path_tools.creat_path(path_copy)
            shutil.copy(path,path_copy)


class BaseDataDict:
    def __init__(self,
        begin_time: datetime,
        end_time: datetime,
        station_file: str,
        hdf_file_name: str,
        output_dir: str,
        **kwargs):

        self.para_dict = copy.deepcopy(para_example)
        self.para_dict["begin_time"] = begin_time
        self.para_dict["end_time"] = end_time
        self.para_dict["station_file"] = station_file
        self.para_dict["hdf_file_name"] = hdf_file_name
        self.para_dict["output_dir"] = output_dir

        for key, value in kwargs.items():
            self.para_dict[key] = value

    def get_ob_data(self, **kwargs):
        ob_dict = copy.deepcopy(ob_data_dict)
        self.para_dict["ob_data"] = ob_dict
        for key, value in kwargs.items():
            self.para_dict["ob_data"][key] = value

    def get_fo_data(self, pro_name, **kwargs):
        fo_dict = copy.deepcopy(fo_data_dict)
        self.para_dict["fo_data"][pro_name] = fo_dict
        for key, value in kwargs.items():
            self.para_dict["fo_data"][pro_name][key] = value

    def get_data_dcit(self, model_names, model_paths, fact_paths):
        ob_kwargs = {
            'dir_ob': fact_paths
        }
        self.get_ob_data(**ob_kwargs)

        for idx, model_name in enumerate(model_names):
            fo_kwargs = {
                'dir_fo': model_paths[idx],
            }
            self.get_fo_data(model_name, **fo_kwargs)

    @property
    def data_dict(self):
        return self.para_dict



if __name__ == '__main__':
    copy_data_file(para_list_example)
    # pass
