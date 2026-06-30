# -- coding: utf-8 --
# @Time : 2025/1/17 16:53
# @Author : 马劲松
# @Email : mjs1263153117@163.com
# @File : correctTP_24H.py
# @Software: PyCharm

import os, sys, json
from config import *
from datetime import timedelta, datetime
from multiprocessing import Pool
from utils.logger import logger
from utils.util_env import get_resolved_paths, get_runtime_config
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor

from data_save import *
from interpolation import *
from cal_similarity import similarity
from cal_slice_tp import correct_by_opticalFlow
from cal_frequency_match import FrequencyMatch

_CFG = get_runtime_config()
rpt_list = _CFG["rpt_list"]
ipt_model = _CFG["ipt_model"]
ipt_obs = _CFG["ipt_obs"]
ipt_type = _CFG["ipt_type"]
opt_type = _CFG["opt_type"]
over_w = _CFG["over_w"]
start_dtime = _CFG["start_dtime"]
end_dtime = _CFG["end_dtime"]
inter_dtime1 = _CFG["inter_dtime1"]
inter_dtime2 = _CFG["inter_dtime2"]
report_inter = _CFG["report_inter"]
res = _CFG["res"]
slon, elon, slat, elat = _CFG["slon"], _CFG["elon"], _CFG["slat"], _CFG["elat"]
slon_l, elon_l, slat_l, elat_l = _CFG["slon_l"], _CFG["elon_l"], _CFG["slat_l"], _CFG["elat_l"]
pool_num = _CFG["pool_num"]

class gain_dataset:
    """
    加载模式和实况资料
    :param
    report_time：起报时间
    dtime：预报时效
    """
    def __init__(self, parafile, report_time, dtime):
        self.parafile = parafile
        self.rpt = report_time
        self.dtime = dtime
        self.inter_extend = [slon_l, elon_l, slat_l, elat_l, res]
        self.inter = [slon, elon, slat, elat, res]
        self.read_cfg_json()
        self.bool = self.preLogical()
        if not self.bool:
            return

        env_paths = get_resolved_paths()
        self.sta_info = meb.read_stadata_from_micaps3(env_paths['station_info'])
        # self.mask_grd = meb.read_griddata_from_nc(env_paths['mask_nc'])
        self.grd_hislist_model, self.grd_hislist_model_smooth, self.sta_hislist_obs = self.read_his_ds()
        self.grd_current_model, self.grd_current_model_smooth = self.read_current_ds()
        self.mask_array = mesh_val(meb.read_griddata_from_nc(env_paths['mask_nc']), self.inter_extend).data.squeeze()
        # grd0 = meb.get_grid_of_data(self.grd_current_model)
        # self.mask_array = mesh_val(meb.read_griddata_from_nc('srcfile/mask010.nc'),
        #                            [grd0.slon, grd0.elon, grd0.slat, grd0.elat, grd0.dlon]).data.squeeze()

    def read_cfg_json(self):
        if not os.path.exists(self.parafile):
            logger.error(f'缺失配置文件：{self.parafile}')
            sys.exit(1)
        with open(self.parafile, "r", encoding='utf-8') as f:
            path_config = json.load(f)
            self.tp_model = path_config.get('tp_model')
            self.tp_obs = path_config.get('tp_obs')
            self.correct_tp_outpath = path_config.get('correct_tp_outpath')

    def preLogical(self):
        self.current_modelpath = self.tp_model.format(rpt=self.rpt, dtime=self.dtime)
        self.opt_m3 = self.correct_tp_outpath.format(rpt=self.rpt, dtime=self.dtime) + '.m3'
        self.opt_grd = self.correct_tp_outpath.format(rpt=self.rpt, dtime=self.dtime) + '.' + opt_type

        if os.path.exists(self.current_modelpath):
            if os.path.exists(self.opt_m3) & os.path.exists(self.opt_grd):
                if over_w == 1:
                    return True
                else:
                    logger.info('本地已存在降水订正产品')
                    return False
            else:
                return True
        else:
            logger.error('当前数据缺失')
            return False

    def read_his_ds(self):
        logger.info('加载历史数据集')
        model_hislist, model_hislist_smooth, obs_hislist = [], [], []

        for del_year in range(0, his_year + 1):
            start_year = self.rpt + relativedelta(years=(-1 * del_year))
            start_time = start_year - timedelta(days=his_day)
            if del_year == 0:
                end_time = start_year + timedelta(days=-1)
            else:
                end_time = start_year + timedelta(days=his_day)

            while start_time <= end_time:
                try:
                    if ipt_model == ipt_obs:
                        obs_time = start_time + timedelta(hours=self.dtime)
                    else:
                        if ipt_model >= 1 and ipt_obs == 0:
                            obs_time = start_time + timedelta(hours=self.dtime) - timedelta(hours=8)
                        elif ipt_model == 0 and ipt_obs >= 1:
                            obs_time = start_time + timedelta(hours=self.dtime) + timedelta(hours=8)
                        else:
                            raise TypeError('输入降水数据时间判断有误')
                    model_temppath = self.tp_model.format(rpt=start_time, dtime=self.dtime)
                    obs_temppath = self.tp_obs.format(rpt=obs_time)
                    if os.path.exists(model_temppath) and os.path.exists(obs_temppath):
                        if ipt_type == 'm4':
                            grd = meb.read_griddata_from_micaps4(model_temppath)
                        elif ipt_type == 'nc':
                            grd = meb.read_griddata_from_nc(model_temppath)
                        else:
                            logger.error('历史数据格式有误：{0}.{1:03d}'.format(start_time.strftime('%Y%m%d%H'), self.dtime))
                            continue
                        # grd_mesh = grd.copy()
                        grd_mesh = mesh_val(grd, self.inter_extend)
                        grd_smooth = smooth9(grd_mesh, smooth_num)
                        sta = meb.read_stadata_from_micaps3(obs_temppath)
                        sta_merge = pd.merge(self.sta_info, sta, on=['id'], how='left')
                        data_merge = sta_merge.data0_y
                        data_merge[np.isnan(data_merge)] = 0
                        sta = self.sta_info.copy()
                        sta.data0 = data_merge

                        sta = clear_to_num_greater_than(sta, 0.0, 500.0)
                        sta = clear_to_num_less_than(sta, 0.0, 0.0)
                        model_hislist.append(grd_mesh)
                        obs_hislist.append(sta)
                        model_hislist_smooth.append(grd_smooth)
                    else:
                        logger.error('历史数据缺失：{0}.{1:03d}'.format(start_time.strftime('%Y%m%d%H'), self.dtime))
                except Exception as e:
                    logger.error(e)
                    continue
                finally:
                    start_time += timedelta(days=1)

        logger.info('历史数据读取成功')
        return model_hislist, model_hislist_smooth, obs_hislist

    # 读取当前模式
    def read_current_ds(self):
        try:
            logger.info('加载当前模式数据')
            if ipt_type == 'm4':
                grd_current_model = meb.read_griddata_from_micaps4(self.current_modelpath)
            elif ipt_type == 'nc':
                grd_current_model = meb.read_griddata_from_nc(self.current_modelpath)
            else:
                logger.error('当前模式数据格式有误')
                return None, None

            grd_current_model_mesh = mesh_val(grd_current_model, self.inter_extend)
            # grd_current_model_mesh = grd_current_model.copy()
            grd_current_model_smooth = grd_current_model_mesh.copy()
        except:
            grd_current_model_mesh, grd_current_model_smooth = None, None
        return grd_current_model_mesh, grd_current_model_smooth

class correct_24H_TP(gain_dataset):
    """
    模式1H降水频率匹配订正

    :param
    report_time：起报时间
    dtime：预报时效
    """
    def __init__(self, parafile, report_time, dtime):
        logger.info(f'开始降水订正：起报时间-{report_time:%Y%m%d%H}, 预报时效-{dtime:03d}')
        super().__init__(parafile, report_time, dtime)
        self.gain_slice()

    def gain_slice(self):
        if (self.dtime <= 60) and (elon - slon > 10) and (elat - slat > 10):
            self.center_lon_left = GetNumUp(slon, elon)
            self.center_lon_right = GetNumDown(slon, elon)
            self.center_lat_bottom = GetNumUp(slat, elat)
            self.center_lat_top = GetNumDown(slat, elat)
        else:
            self.center_lon_left = [slon]
            self.center_lon_right = [elon]
            self.center_lat_bottom = [slat]
            self.center_lat_top = [elat]
        self.large_lon_left = [i - expansion for i in self.center_lon_left]
        self.large_lon_right = [i + expansion for i in self.center_lon_right]
        self.large_lat_bottom = [i - expansion for i in self.center_lat_bottom]
        self.large_lat_top = [i + expansion for i in self.center_lat_top]

    def _correct_Slice_TP(self, org_extend, ext_extend):
        grd_05res = ext_extend + [res * 5]
        sta = select_by_extend(self.sta_info, org_extend)
        sta_ext = select_by_extend(self.sta_info, ext_extend)
        if len(sta) <= 0:
            return None

        mask_array = self.mask_array.copy()
        mask_array[mask_array <= 0] = 0
        # 数据集切片
        current_model_slice = mesh_val(self.grd_current_model_smooth * mask_array, grd_05res)
        history_model_slice = [mesh_val(i * mask_array, grd_05res) for i in self.grd_hislist_model_smooth]
        #  计算当前模式和历史模式的相似度
        similarity_Obj = similarity(history_model_slice, current_model_slice, similar_level)
        similarity_index = similarity_Obj.get_similarity_index()
        del current_model_slice
        del history_model_slice
        #  获取切片网格的光流场，基于光流场订正当前模式降水
        correct_tp_obj = correct_by_opticalFlow(similarity_index, ext_extend, self.grd_hislist_model,
                                                self.grd_hislist_model_smooth, self.sta_hislist_obs)
        correct_current_model = correct_tp_obj.correct_sliceTP(self.dtime, sta_ext, self.grd_current_model,
                                                               self.grd_current_model_smooth)

        correct_current_model_sta_slice = bilinear_interp(correct_current_model, sta)
        correct_current_model_sta_slice = clear_to_num_less_than(correct_current_model_sta_slice, 0.0, 0.01)
        return correct_current_model_sta_slice

    def cycle_correct_Slice(self):
        logger.info('订正切片网格内站点降水信息')
        correct_slice_sta = []
        for jy in range(len(self.center_lat_bottom)):
            for ix in range(len(self.center_lon_left)):
                try:
                    org_extend = [self.center_lon_left[ix], self.center_lon_right[ix],
                                  self.center_lat_bottom[jy], self.center_lat_top[jy]]
                    ext_extend = [self.large_lon_left[ix], self.large_lon_right[ix],
                                  self.large_lat_bottom[jy], self.large_lat_top[jy]]
                    correct_current_model_sta_slice = self._correct_Slice_TP(org_extend, ext_extend)
                    if correct_current_model_sta_slice is not None:
                        correct_slice_sta.append(correct_current_model_sta_slice)
                except Exception as e:
                    logger.error(e)
                    continue
        return correct_slice_sta

    def cycle_correct_Slice_pool(self):
        logger.info('估算切片网格内站点降水信息')

        correct_slice_sta = []
        def process_slice(ix, jy):
            try:
                org_extend = [self.center_lon_left[ix], self.center_lon_right[ix],
                              self.center_lat_bottom[jy], self.center_lat_top[jy]]
                ext_extend = [self.large_lon_left[ix], self.large_lon_right[ix],
                              self.large_lat_bottom[jy], self.large_lat_top[jy]]
                correct_current_model_sta_slice = self._correct_Slice_TP(org_extend, ext_extend)
                if correct_current_model_sta_slice is not None:
                    return correct_current_model_sta_slice
            except Exception as e:
                logger.error(e)
            return None

        with ThreadPoolExecutor() as executor:
            futures = []
            for jy in range(len(self.center_lat_bottom)):
                for ix in range(len(self.center_lon_left)):
                    futures.append(executor.submit(process_slice, ix, jy))
            for future in futures:
                result = future.result()
                if result is not None:
                    correct_slice_sta.append(result)
        return correct_slice_sta

    def _correct_current_TP_sta(self, sd_model_sta_array):
        try:
            logger.info('制作降水订正站点产品')
            _extend = [self.center_lon_left[0], self.center_lon_right[-1],
                       self.center_lat_bottom[0], self.center_lat_top[-1]]
            correct_current_model_sta = pd.concat(sd_model_sta_array, ignore_index=True)
            correct_current_model_sta = select_by_extend(correct_current_model_sta, _extend)
            correct_current_model_sta = clear_to_num_less_than(correct_current_model_sta, 0.0, 0.01)
            correct_current_model_sta.time = self.rpt
            correct_current_model_sta.dtime = self.dtime
            return correct_current_model_sta
        except Exception as e:
            logger.error(e)
            return None

    def _correct_current_TP_grd(self, correct_current_model_sta):
        try:
            logger.info('制作降水订正格点产品')
            grd_current_model = mesh_val(self.grd_current_model, self.inter)
            lon, lat, data = subtilize_grd(self.grd_current_model, self.mask_array, inter_dis)
            current_model_sta = creat_M3_grd(lon, lat, data, self.rpt, dtime=self.dtime)
            current_model_sta = select_by_extend(current_model_sta, [slon, elon, slat, elat])
            current_model_sta_add = pd.concat([correct_current_model_sta, current_model_sta], ignore_index=True)

            current_model_grd_add = GressManInterpolation(current_model_sta_add, grd_current_model, [0.8, 0.6, 0.4, 0.2], rain_limit=0.01)
            current_model_grd_add = smooth9(current_model_grd_add, 10)
            sta_roi = clear_to_num_greater_than(correct_current_model_sta, 0, 0)
            current_model_sta_inter = bilinear_interp(current_model_grd_add, sta_roi)

            FrequencyMatchObj = FrequencyMatch([current_model_sta_inter], [correct_current_model_sta], fact_level1)
            used_model_level = FrequencyMatchObj.get_used_model_level_and_extend('grd')
            print(used_model_level)

            correct_current_model_grd = FrequencyMatch.correct_model_grid(current_model_grd_add, used_model_level)
            correct_current_model_grd = clear_to_num_less_than_grd(correct_current_model_grd, 0.0, 0.01)
            return correct_current_model_grd
        except Exception as e:
            logger.error(e)
            return None

    def mainProc(self):
        """
        模式1H降水频率匹配订正主函数
        :return:
        """
        if not self.bool:
            return
        correct_slice_sta = self.cycle_correct_Slice()
        correct_current_model_sta = self._correct_current_TP_sta(correct_slice_sta)
        if correct_current_model_sta is None:
            return
        write_stadata_to_micaps3(correct_current_model_sta, save_path=self.opt_m3, effectiveNum=2, creat_dir=True, show=True)

        correct_current_model_sta = select_by_extend(correct_current_model_sta, [slon, elon, slat, elat])
        correct_current_model_grd = self._correct_current_TP_grd(correct_current_model_sta)
        if correct_current_model_grd is None:
            return
        write_griddata(correct_current_model_grd, self.opt_grd, opt_type)

def correctTP_24(parafile, report_time, dtime):
    correct_tp_obj = correct_24H_TP(parafile, report_time, dtime)
    correct_tp_obj.mainProc()

def mainProcess(parafile):
    if len(rpt_list) == 0:
        etime = datetime.now() - timedelta(hours=datetime.now().hour % report_inter)
        stime = etime - timedelta(days=1)
    elif len(rpt_list) == 1:
        stime = datetime.strptime(str(rpt_list[0]), '%Y%m%d%H')
        etime = stime
    elif len(rpt_list) == 2:
        stime = datetime.strptime(str(rpt_list[0]), '%Y%m%d%H')
        etime = datetime.strptime(str(rpt_list[1]), '%Y%m%d%H')
    else:
        raise ('输入参数有误, 请输入%Y%m%d%H')

    res_list = []
    multiPool = Pool(pool_num)

    while etime >= stime:
        begin_dtime = start_dtime
        while begin_dtime <= end_dtime:
            inter_dtime = inter_dtime1 if begin_dtime < 60 else inter_dtime2
            res_list.append(multiPool.starmap_async(correctTP_24, [[parafile, etime, begin_dtime]]))
            begin_dtime += inter_dtime
        etime -= timedelta(hours=report_inter)

    for res in res_list:
        try:
            res.get()
        except:
            continue
    multiPool.close()
    multiPool.join()