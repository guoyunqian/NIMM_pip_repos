# -*- coding: utf-8 -*-
"""MAIT 24h 工具与共享模块包。

根目录 ``utils/`` 与 ``src/utils/`` 合并为同一 ``utils`` 包（``extend_path``）；
``src/utils/`` 下仅放模块文件，不要添加 ``__init__.py``。
"""
import os
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_src_utils = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src", "utils"))
if _src_utils not in __path__:
    __path__.append(_src_utils)
