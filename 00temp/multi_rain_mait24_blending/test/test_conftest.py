# -*- coding: utf-8 -*-
"""pytest 公共配置：路径与轻量依赖桩。"""
import os
import sys
from types import ModuleType

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 单元测试不跑完整 Micaps 栈；缺 meteva 时提供空模块以便 import 链通过
if "meteva" not in sys.modules:
    _meteva = ModuleType("meteva")
    _meteva_method = ModuleType("meteva.method")
    _meteva.method = _meteva_method
    sys.modules["meteva"] = _meteva
    sys.modules["meteva.method"] = _meteva_method
