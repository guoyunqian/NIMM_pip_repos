# -*- coding: utf-8 -*-
"""1 小时降水频率匹配插件。

分位映射和分段线性订正在 ``FrequencyMatch``。本类只按插件入口把两步接起来。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
_TEMP = _ROOT.parent
# 包根在前，``utils`` 才会合并 src/utils 与 00temp/utils。
for _path in (str(_SRC), str(_ROOT)):
    if _path in sys.path:
        sys.path.remove(_path)
sys.path.insert(0, str(_SRC))
sys.path.insert(0, str(_ROOT))

_base_path = _TEMP / "utils" / "base_plugin.py"
_spec = importlib.util.spec_from_file_location("nimm_shared_base_plugin", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
BasePlugin = _base.BasePlugin

try:
    from proc.frequency_match import FrequencyMatch
except ImportError:
    from frequency_matching_rain01.src.proc.frequency_match import FrequencyMatch


class FrequencyMatchingRain01Plugin(BasePlugin):
    """用历史样本的分位映射订正当前降水格点。"""

    def process(
        self,
        current_grid,
        model_data,
        fact_data,
        fact_level,
        fact_level_limit=None,
        extend=True,
    ):
        """建立模式—实况分位表，并对当前格点做分段线性订正。

        参数
        ----
        current_grid :
            要订正的当前格点。
        model_data :
            用来建映射的模式样本（格点或站点列表）。
        fact_data :
            与样本配对的实况。
        fact_level :
            实况等级阈值，单位毫米。
        fact_level_limit :
            建表时两端剔除的样本数，用来减弱极值。
        extend :
            为真时对超出样本最大等级的一端做外延。
        """
        if extend:
            model_level, used_fact = FrequencyMatch.get_used_model_level_and_extend(
                model_data, fact_data, fact_level, fact_level_limit
            )
        else:
            model_level, used_fact = FrequencyMatch.get_used_model_level(
                model_data, fact_data, fact_level, fact_level_limit
            )
        # 分段线性：模式分位拉到对应实况分位
        return FrequencyMatch.correct_model_data(current_grid, used_fact, model_level)
