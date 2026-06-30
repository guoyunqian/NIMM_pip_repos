# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of 'IMPROVER' and is released under the BSD 3-Clause license.
# See LICENSE in the root of the repository for full licensing details.
"""Module containing plugin base class."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

import xarray as xr

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("improver")
    except PackageNotFoundError:
        pass
except ImportError:
    pass


class BasePlugin(ABC):
    """An abstract class for IMPROVER plugins."""

    def __call__(self, *args, **kwargs) -> Any:
        return self.process(*args, **kwargs)

    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        pass


class PostProcessingPlugin(BasePlugin):
    """Post-processing plugin updating title attributes on xarray outputs."""

    def __call__(self, *args, **kwargs) -> Any:
        MANDATORY_ATTRIBUTE_DEFAULTS = {
            "title": "unknown",
            "source": "IMPROVER",
            "institution": "unknown",
        }

        result = super().__call__(*args, **kwargs)
        default_title = MANDATORY_ATTRIBUTE_DEFAULTS["title"]

        def _update_title(obj):
            if "title" not in obj.attrs:
                return
            title = obj.attrs["title"]
            if title != default_title and "Post-Processed" not in title:
                obj.attrs["title"] = f"Post-Processed {title}"

        if isinstance(result, xr.Dataset):
            _update_title(result)
            for var in result.data_vars:
                _update_title(result[var])
        elif isinstance(result, xr.DataArray):
            _update_title(result)
        elif isinstance(result, Iterable) and not isinstance(result, str):
            for item in result:
                if isinstance(item, (xr.Dataset, xr.DataArray)):
                    if isinstance(item, xr.Dataset):
                        _update_title(item)
                    else:
                        _update_title(item)
        return result
