# -*- coding: utf-8 -*-
"""SAMOS 概率订正插件。训练和订正函数在 ``samos_calibration.py``。"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
_TEMP = _SRC.parent.parent
for _path in (str(_TEMP), str(_SRC)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from utils.base_plugin import BasePlugin
from samos_calibration import apply_samos, train_samos


class SamosProbabilityCalibrationPlugin(BasePlugin):
    """SAMOS 订正插件。

    SAMOS（Standardized Anomaly Model Output Statistics，标准化异常模式输出统计）
    先用 GAM（Generalized Additive Model，广义可加模型）估计气候均值和标准差，
    把变量换成标准化异常，再做 EMOS（Ensemble Model Output Statistics，集合模式输出统计），
    最后用实况气候态还原。
    """

    def process(self, task="apply", **kwargs):
        """按任务训练系数或订正预报。

        参数
        ----
        task :
            ``train`` 调用 ``train_samos``；``apply`` 调用 ``apply_samos``。
        kwargs :
            原函数的具名参数，例如历史预报、实况、GAM 特征和分布名。
        """
        name = (task or "apply").strip().lower()
        if name == "train":
            return train_samos(**kwargs)
        if name == "apply":
            return apply_samos(**kwargs)
        raise ValueError("task 只能是 train 或 apply")


__all__ = ["SamosProbabilityCalibrationPlugin", "apply_samos", "train_samos"]
