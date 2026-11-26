# -*- coding: utf-8 -*-
"""sklearn 子模块可复用包。合并 ``00temp/utils``，命令行仍可 ``from utils.merge_params``。"""
import os

_here = os.path.dirname(os.path.abspath(__file__))
_shared_utils = os.path.normpath(os.path.join(_here, "..", "..", "utils"))

__path__ = [_here]
if os.path.isdir(_shared_utils) and _shared_utils not in __path__:
    __path__.append(_shared_utils)
