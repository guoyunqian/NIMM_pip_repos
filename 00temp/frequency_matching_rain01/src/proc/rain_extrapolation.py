from __future__ import annotations

import numpy as np

from data import GridData


class RainExtrapolation:
    @staticmethod
    def simple_semi_lagrangian_in_angle(
        gd_uwnd: GridData,
        gd_vwnd: GridData,
        gd_rain: GridData,
        deta_time: float,
    ) -> GridData:
        gd_output = gd_rain.copy_grid_data()
        # val[y, x] => lon/lat 网格也用 [y, x] 的布局
        lon_grid, lat_grid = np.meshgrid(
            gd_output.lon, gd_output.lat, indexing="xy"
        )  # [yn, xn]
        from_lon = lon_grid - gd_uwnd.val * deta_time
        from_lat = lat_grid - gd_vwnd.val * deta_time
        fallback = gd_rain.val
        sampled = gd_rain.interpolate_points(from_lon, from_lat, np.nan)
        gd_output.val = np.where(np.isnan(sampled), fallback, sampled)
        return gd_output
