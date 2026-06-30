# -*- coding: utf-8 -*-
"""
1 小时气象预报集成主程序（``src/mait_1h_cli.py``）。

**结果相关约定（重构后保持不变）**：

- 模式/站点检索基准：``ctx.dt_search_base()``（``is_obs_bjt`` 时 ``dt_now-8h``）
- 写出 Micaps 时间：``grid_base.gtime = [dt_search_base]``（非 ``dt_now`` 原值）
- TS 融合、频率匹配、``data0×1.2``、掩码插值与 ``clip_coords`` 裁剪写出等算法未改
- ``RunContext`` / ``mait_1.ini`` 仅改变配置加载方式，不改变计算公式

详见 ``docs/MAIT_1H_程序说明.md``。

命令行
------
- 独立运行：``python src/mait_1h_cli.py --time-inputs=...``
- 模块入口：``python -m cli --time-inputs=...``（项目根目录）
"""
import sys
from pathlib import Path


def _bootstrap_paths():
    """将 ``src`` 与项目根加入 ``sys.path``，保证 ``utils`` 与同目录模块可导入。"""
    _src = Path(__file__).resolve().parent
    _root = _src.parent
    for p in (str(_src), str(_root)):
        if p not in sys.path:
            sys.path.insert(0, p)


_bootstrap_paths()

import datetime
import os
import numpy as np
import pandas as pd

from utils.multipro_plugin import SimpleParallelTool
from utils.mai_1_plugin_context import build_run_context
from mait_1_plugin import AnalysisTsWeightProcess, StationDataInterp2GridDataProcess, DataFlgProcess

from mait_1_plugin_util import (
    _read_history_source_micaps3,
    _read_mait_st_like_score_samples,
    _read_now_source_micaps3_nc,
    _analysis_background_ini,
)
from utils.util_env import (
    get_resolved_paths,
    get_default_clip_coords,
    get_default_predict_valid_list,
    get_default_is_obs_bjt,
    get_default_is_multi,
    get_default_pro_count,
    get_default_split_lat,
    get_default_split_lon,
)
from utils.util_new import read_grid_mask, _prepare, _analysis_para_ini, _data_write_to_micaps3, write_grid_to_micaps4


class RunProcess():
    """1小时预报集成处理类。"""

    def __init__(self, time_input, para_path, beta_path, is_obs_bjt, clip_coords, split_lat=1, split_lon=1, predict_valid_list=None):
        self.time_input = time_input
        self.para_path = para_path
        self.beta_path = beta_path
        self.is_obs_bjt = is_obs_bjt
        self.clip_coords = clip_coords
        self.split_lat = split_lat
        self.split_lon = split_lon
        self.predict_valid_list = predict_valid_list
        if predict_valid_list is None:
            self.predict_valid_list = [i for i in range(1, 48 + 1, 1)]

    def _setup_context(self):
        """解析配置、读站点表、组装 ``RunContext``；失败时返回 ``ctx=None``。"""
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        env_paths = get_resolved_paths()
        para_filepath = self.para_path or env_paths["para_ini"]
        beta_filepath = self.beta_path or env_paths["beta_path_template"]
        log_file = env_paths["log_file_template"]

        simple_log, dt_now, sd_sta_info = _prepare(self.time_input, log_file, env_paths["station_info"])
        ini_tuple = _analysis_para_ini(para_filepath, simple_log)

        if not ini_tuple:
            return None, env_paths, simple_log
        model_name, model_path, fact_path, output_sample_path = ini_tuple

        background_ini = env_paths["background_ini"]
        background_templates = _analysis_background_ini(background_ini)
        if not background_templates:
            simple_log.error("背景格点配置文件不存在或为空: %s", background_ini)
            return None, env_paths, simple_log
        missing = [n for n in model_name if n not in background_templates]
        if missing:
            simple_log.error(
                "para_1_background.ini 缺少模式键（须与 para.ini 一致）: %s", ", ".join(missing))
            return None, env_paths, simple_log

        ctx = build_run_context(
            beta_path_template=beta_filepath,
            is_obs_bjt=self.is_obs_bjt,
            clip_coords=self.clip_coords,
            split_lat=self.split_lat,
            split_lon=self.split_lon,
            dt_now=dt_now,
            sd_sta_info=sd_sta_info,
            simple_log=simple_log,
            model_name=model_name,
            model_path=model_path,
            fact_path=fact_path,
            output_sample_path=output_sample_path,
            background_templates=background_templates,
            area_scale=0.5,
            predict_type=1,
        )
        return ctx, env_paths, simple_log

    def _process_single(self):
        """按时效循环：读数 → 质检 → TS 融合 → 站点/格点写出。"""
        ctx, env_paths, simple_log = self._setup_context()
        if ctx is None:
            if simple_log is not None:
                print("RunContext 初始化失败，详见日志:", env_paths.get("log_file_template", "log/YYYYMMDD.txt"))
            return

        model_name = list(ctx.models.model_name)
        mask_file = env_paths["mask_dat"]
        print("=---------------------------------------------------->>>> mask_file: ", mask_file)

        if len(self.predict_valid_list) == 0:
            return

        for predict_valid in self.predict_valid_list:
            # --- 1) 历史样本（Micaps3 站点；路径/时刻逻辑未改）---
            sta_before_flg, sta_current_flg1, sd_current_model, sd_before_model, sd_fact, md_current_datetime, dt_model_current = (
                _read_history_source_micaps3(predict_valid, ctx))
            before_model_series, before_model_flag, before_fact_series, before_fact_flag, front_model, front_model_flag, front_fact = (
                _read_mait_st_like_score_samples(predict_valid, ctx))
            if before_model_flag is not None:
                for i_model in range(len(ctx.paths.model_path)):
                    if np.any(before_model_flag[i_model, :] == 1.0):
                        sta_before_flg[i_model] = 1.0

            # --- 2) 当前时效：站点 M3 + 背景 m4（para_1_background.ini）---
            # 检索基准 dt_search_base 与写出 gtime 覆盖见下方两行（早晚时次产品关键）
            dt_search_base = ctx.dt_search_base()
            sta_current_flg2, gd_back_ground, grid_base, _ = _read_now_source_micaps3_nc(
                dt_model_current, predict_valid, sta_current_flg1, sd_current_model,
                md_current_datetime, ctx, dt_search_base=dt_search_base)
            grid_base.gtime = [dt_search_base]
            grid_base.dtimes = [predict_valid]

            # --- 3) 质检：历史全缺不中断；当前全缺跳过该时效 ---
            _, currentTotalFlg, sta_current_flg = DataFlgProcess(
                sta_before_flg, sta_current_flg2, ctx).process()
            if currentTotalFlg == 0.0:
                continue

            # --- 4) 分区 TS 权重融合（beta 历史链仍关闭，score_before 矩阵置零）---
            iflag_list = [[[0 for _ in range(ctx.grid.split_lon)] for _ in range(ctx.grid.split_lat)]]
            score_before_list = [[[[0.0 for _ in model_name] for _ in range(ctx.grid.split_lon)] for _ in range(ctx.grid.split_lat)]]

            analysis_ts = AnalysisTsWeightProcess(
                grid_base, sd_before_model, sd_current_model, sd_fact,
                sta_before_flg, sta_current_flg, iflag_list, score_before_list, ctx,
                before_model_series=before_model_series,
                before_model_flag=before_model_flag,
                before_fact_series=before_fact_series,
                before_fact_flag=before_fact_flag,
                front_model=front_model,
                front_model_flag=front_model_flag,
                front_fact=front_fact,
            )
            sd_output, _score_last = analysis_ts.process()

            sd_outputs = []
            for idx in range(len(sd_output[0])):
                for jdx in range(len(sd_output[0][idx])):
                    sd_outputs.append(sd_output[0][idx][jdx])
            __sd_output = pd.concat(sd_outputs, ignore_index=True)
            if 'id' in __sd_output.columns:
                __sd_output = __sd_output.drop_duplicates(subset=['id'], keep='last').reset_index(drop=True)
            # 业务系数 1.2：与 mait_st 站点产品幅值对齐（未改）
            if 'data0' in __sd_output.columns:
                __sd_output['data0'] = __sd_output['data0'] * 1.2

            _data_write_to_micaps3(__sd_output, grid_base, ctx)

            # --- 5) 掩码 + Cressman 插值；clip_coords 裁剪写出 Micaps4/NC ---
            gd_mask_val, gd_mask_xn, gd_mask_yn = read_grid_mask(mask_file, grid_base)
            gd_final_output = StationDataInterp2GridDataProcess(
                gd_mask_val, gd_mask_xn, gd_mask_yn, grid_base, gd_back_ground, __sd_output).process()
            write_grid_to_micaps4(gd_final_output, grid_base, ctx)


def process_single(para_path, beta_path, is_obs_bjt, clip_coords, split_lat, split_lon, predict_valid_list, **params):
    param = params['param']
    print(param)
    RunProcess(
        param['time_input'], para_path, beta_path, is_obs_bjt,
        clip_coords, split_lat, split_lon, predict_valid_list,
    )._process_single()


def process_multi(params, pro_count, para_path, beta_path, is_obs_bjt, clip_coords, split_lat, split_lon, predict_valid_list):
    sw_all = datetime.datetime.now()
    parallel_tool = SimpleParallelTool(
        target_func=process_single,
        parallel_mode="async",
        with_return=True,
        num_process=pro_count,
        fixed_params={
            "para_path": para_path,
            "beta_path": beta_path,
            "is_obs_bjt": is_obs_bjt,
            "clip_coords": clip_coords,
            "split_lat": split_lat,
            "split_lon": split_lon,
            "predict_valid_list": predict_valid_list,
        }
    )
    parallel_tool.process({"param": params})
    print(">>> Time elasped: " + str((datetime.datetime.now() - sw_all).total_seconds()))


def process(*,
            time_inputs: list = None,
            predict_valid_list: list = None,
            para_path: str = None,
            beta_path: str = None,
            is_obs_bjt = None,
            is_multi = None,
            clip_coords: list = None,
            pro_count = None,
            split_lat = None,
            split_lon = None,
            ):
    """1小时气象预报集成处理的主函数。"""
    if predict_valid_list is None:
        predict_valid_list = get_default_predict_valid_list()
    if is_obs_bjt is None:
        is_obs_bjt = get_default_is_obs_bjt()
    if is_multi is None:
        is_multi = get_default_is_multi()
    if clip_coords is None:
        clip_coords = get_default_clip_coords()
    if pro_count is None:
        pro_count = get_default_pro_count()
    if split_lat is None:
        split_lat = get_default_split_lat()
    if split_lon is None:
        split_lon = get_default_split_lon()

    params = [{"time_input": time_input} for time_input in time_inputs]

    if not is_multi:
        for param in params:
            process_single(para_path, beta_path, is_obs_bjt, clip_coords, split_lat, split_lon, predict_valid_list, **{"param": param})
    else:
        process_multi(params, pro_count, para_path, beta_path, is_obs_bjt, clip_coords, split_lat, split_lon, predict_valid_list)


# ---------------------------------------------------------------------------
# 命令行（Clize）
# ---------------------------------------------------------------------------

def _cli_converters():
    from clize.parser import value_converter

    @value_converter
    def comma_str_list(s):
        if s is None or not str(s).strip():
            return None
        return [x.strip() for x in str(s).split(",") if x.strip()]

    @value_converter
    def comma_int_list(s):
        if s is None or not str(s).strip():
            return None
        return [int(x.strip()) for x in str(s).split(",") if x.strip()]

    @value_converter
    def comma_float_list(s):
        if s is None or not str(s).strip():
            return None
        return [float(x.strip()) for x in str(s).split(",") if x.strip()]

    @value_converter
    def optional_str(s):
        if s is None or not str(s).strip():
            return None
        return str(s)

    @value_converter
    def optional_bool_cli(s):
        if s is None:
            return None
        if isinstance(s, bool):
            return s
        t = str(s).strip().lower()
        if t in ("", "none"):
            return None
        if t in ("1", "true", "yes", "y", "on"):
            return True
        if t in ("0", "false", "no", "n", "off"):
            return False
        raise ValueError("期望布尔：true/false/1/0 等")

    @value_converter
    def optional_int_cli(s):
        if s is None:
            return None
        t = str(s).strip()
        if not t:
            return None
        return int(t)

    return comma_str_list, comma_int_list, comma_float_list, optional_str, optional_bool_cli, optional_int_cli


def _make_cli_entry():
    from clize.runner import Clize

    (
        comma_str_list, comma_int_list, comma_float_list,
        optional_str, optional_bool_cli, optional_int_cli,
    ) = _cli_converters()

    def run_cli(
        *,
        time_inputs: comma_str_list,
        predict_valid_list: comma_int_list = None,
        para_path: optional_str = None,
        beta_path: optional_str = None,
        is_obs_bjt: optional_bool_cli = None,
        is_multi: optional_bool_cli = None,
        clip_coords: comma_float_list = None,
        pro_count: optional_int_cli = None,
        split_lat: optional_int_cli = None,
        split_lon: optional_int_cli = None,
    ):
        """
        1 小时气象预报集成处理（Clize 命令行）

        :param time_inputs: 起报时间列表，逗号分隔，如 202401010800,202401011200
        :param predict_valid_list: 预报时效（小时）；省略则从 ``resource/mait_1.ini`` 读取
        :param para_path: para.ini；省略则用 ini 中的 ``para_ini``
        :param beta_path: beta 模板；省略则用 ini 中的 ``beta_path_template``
        :param is_obs_bjt: ``--is-obs-bjt=true|false``；省略则用 ini 的 ``is_obs_bj``
        :param is_multi: ``--is-multi=true|false``；省略则用 ini 的 ``is_multi``
        :param clip_coords: 六浮点逗号分隔；省略则用 ini 的 ``clip_coords``
        :param pro_count / split_lat / split_lon: 省略则读 ``mait_1.ini`` 中对应项
        """
        process(
            time_inputs=time_inputs,
            predict_valid_list=predict_valid_list,
            para_path=para_path,
            beta_path=beta_path,
            is_obs_bjt=is_obs_bjt,
            is_multi=is_multi,
            clip_coords=clip_coords,
            pro_count=pro_count,
            split_lat=split_lat,
            split_lon=split_lon,
        )

    return Clize(run_cli)


def main():
    """Clize 命令行入口。"""
    from clize.runner import run
    run(_make_cli_entry())


if __name__ == "__main__":
    main()
