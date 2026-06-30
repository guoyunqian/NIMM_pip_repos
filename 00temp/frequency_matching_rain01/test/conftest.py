# -*- coding: utf-8 -*-
import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_test_dir)
_src = os.path.join(_root, "src")
for p in (_src, _root):
    if p not in sys.path:
        sys.path.insert(0, p)
