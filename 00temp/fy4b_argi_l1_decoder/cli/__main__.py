# -*- coding: utf-8 -*-
"""``python -m cli``：把 key=value 交给已装饰的 ``process``。"""
import sys

from .fy4b_argi_l1_decoder_cli import process
from utils.merge_params import parse_kv_argv

argv = list(sys.argv[1:])
extra = parse_kv_argv(argv) if argv else {}
result = process(**extra) if extra else process()
if isinstance(result, int) and result:
    raise SystemExit(result)
