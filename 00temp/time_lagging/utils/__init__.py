# -*- coding: utf-8 -*-
"""时间滞后集合可复用包。

路径合并后，``from utils.merge_params`` 仍指向 ``00temp/utils``，
本目录的 ``meteva_data`` 再导出 ``util/meteva_data.py``。
"""
import os

_here = os.path.dirname(os.path.abspath(__file__))
_shared_utils = os.path.normpath(os.path.join(_here, "..", "..", "utils"))

__path__ = [_here]
if os.path.isdir(_shared_utils) and _shared_utils not in __path__:
    __path__.append(_shared_utils)
