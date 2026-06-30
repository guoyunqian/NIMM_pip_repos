"""Plugin wrapper for fast refined interpolation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FastRefineInterpPlugin:
    """快速精细化插值插件。

    插件只负责接收显式参数并调用算法入口；具体的模式数据、地形数据、
    站点文件和业务配置仍按原算法的配置文件规则读取。
    """

    debug: int = 0
    update: int = 0
    operation: str = "i"
    begin_date: str | None = None
    resolution: str = "site"
    para_file: str = "Fast_refine_interp_site.ini"
    work_dir: str | Path | None = None
    model_region: str = "EC_12P5KM"
    root_path: str | Path | None = None
    s3_method: str = "g_interp"
    site_name: str = "Station1"

    def process(self):
        """Run fast refined interpolation with the configured parameters."""
        from .fast_refine_interp import run_fast_refine

        return run_fast_refine(
            debug=self.debug,
            update=self.update,
            operation=self.operation,
            begin_date=self.begin_date,
            resolution=self.resolution,
            para_file=self.para_file,
            work_dir=str(self.work_dir) if self.work_dir is not None else None,
            model_region=self.model_region,
            root_path=str(self.root_path) if self.root_path is not None else None,
            s3_method=self.s3_method,
            site_name=self.site_name,
        )
