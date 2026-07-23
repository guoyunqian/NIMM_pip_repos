# -*- coding: utf-8 -*-
"""NIMM 共享插件工具包。

提供 ``base_plugin``、``multipro_plugin``、``data_prepare_plugin``、
``data_distribute_pulgin`` 等跨算法通用模块。

各算法项目通过本地 ``utils/__init__.py`` 将本目录并入 ``utils`` 包后，
统一使用 ``from utils.xxx import ...``。
"""
