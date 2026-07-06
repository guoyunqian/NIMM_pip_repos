"""本模块定义了插件基类与后处理插件基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

import numpy as np
import xarray as xr


class BasePlugin(ABC):
    """基础插件类。"""

    def __call__(self, *args, **kwargs):
        """使插件类实例可以直接调用。"""
        return self.process(*args, **kwargs)

    @abstractmethod
    def process(self, *args, **kwargs):
        """插件处理主函数。"""
        pass

class PostProcessingPlugin(BasePlugin):
    """适配 meteva_base 网格数据的后处理插件基类。"""

    @staticmethod
    def post_process(result):
        """
        对后处理结果做统一收口。

        当前默认不修改结果对象，仅保留统一扩展入口。
        """
        return result

    def __call__(self, *args, **kwargs):
        """执行处理主函数并调用统一后处理钩子。"""
        result = super().__call__(*args, **kwargs)
        if isinstance(result, xr.DataArray):
            return self.post_process(result)
        if isinstance(result, (np.ndarray, np.ma.MaskedArray)):
            return result
        if isinstance(result, Iterable) and not isinstance(result, (str, bytes)):
            return type(result)(
                self.post_process(item) if isinstance(item, xr.DataArray) else item
                for item in result
            )
        return result