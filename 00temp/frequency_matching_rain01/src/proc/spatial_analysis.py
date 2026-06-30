from __future__ import annotations

import math
import numpy as np

from data import GridData, ScatterData


class SpatialAnalysis:
    @staticmethod
    def grid_data_fix_by_scatter(sd_input_data: ScatterData, gd_output_data: GridData) -> None:
        gd_flag = np.zeros_like(gd_output_data.val)
        for station in sd_input_data.sta_data:
            ix = int(round((station.lon - gd_output_data.lon_start) / gd_output_data.dlon))
            iy = int(round((station.lat - gd_output_data.lat_start) / gd_output_data.dlat))
            if 0 <= ix < gd_output_data.xn and 0 <= iy < gd_output_data.yn:
                if gd_flag[iy, ix] == 0.0 or station.val >= gd_output_data.val[iy, ix]:
                    gd_output_data.val[iy, ix] = station.val
                    gd_flag[iy, ix] = 1.0

    @staticmethod
    def _cressman_one_step_for_rain(
        sd_input_data: ScatterData,
        gd_background_data: GridData,
        distance_limit: float,
        number_limit: float = 1.0,
        smooth: float = 0.001,
        power_param: float = 2.0,
        rain_limit: float = 0.01,
    ) -> GridData:
        length = sd_input_data.length
        sd_from_background = sd_input_data.copy_scatter_data()
        scatter_data = sd_input_data.copy_scatter_data()
        influence_grid = int(distance_limit / gd_background_data.dlon)
        sd_from_background.clear_to_num(0.0)

        for n in range(length):
            station = sd_input_data.sta_data[n]
            ix = int((station.lon + 1e-5 - gd_background_data.lon_start) / gd_background_data.dlon)
            iy = int((station.lat + 1e-5 - gd_background_data.lat_start) / gd_background_data.dlat)
            xmin = max(ix - influence_grid, 0)
            xmax = min(ix + influence_grid, gd_background_data.xn - 1)
            ymin = max(iy - influence_grid, 0)
            ymax = min(iy + influence_grid, gd_background_data.yn - 1)
            lon_window = gd_background_data.lon[xmin : xmax + 1]
            lat_window = gd_background_data.lat[ymin : ymax + 1]
            dx = lon_window[:, None] - station.lon
            dy = lat_window[None, :] - station.lat
            dist = np.sqrt(dx * dx + dy * dy)
            mask = dist <= distance_limit
            if np.any(mask):
                weights = np.where(mask, 1.0 / np.power(dist + smooth, power_param), 0.0)
                # val[y, x]；dist/weights 的形状是 [wx, wy]（x 在前，y 在后）
                values = gd_background_data.val[ymin : ymax + 1, xmin : xmax + 1]  # [wy, wx]
                weight_sum = weights.sum()
                sd_from_background.sta_data[n].val = (
                    float((weights.T * values).sum() / weight_sum)
                    if weight_sum >= 1e-5
                    else station.val
                )
            else:
                sd_from_background.sta_data[n].val = station.val

        for idx in range(length):
            scatter_data.sta_data[idx].val -= sd_from_background.sta_data[idx].val

        grid1 = np.zeros_like(gd_background_data.val)
        grid2 = np.zeros_like(gd_background_data.val)
        grid3 = np.zeros_like(gd_background_data.val)
        for station in scatter_data.sta_data:
            ix = int((station.lon - gd_background_data.lon_start) / gd_background_data.dlon)
            iy = int((station.lat - gd_background_data.lat_start) / gd_background_data.dlat)
            xmin = max(ix - influence_grid, 0)
            xmax = min(ix + influence_grid, gd_background_data.xn - 1)
            ymin = max(iy - influence_grid, 0)
            ymax = min(iy + influence_grid, gd_background_data.yn - 1)
            lon_window = gd_background_data.lon[xmin : xmax + 1]
            lat_window = gd_background_data.lat[ymin : ymax + 1]
            dx = lon_window[:, None] - station.lon
            dy = lat_window[None, :] - station.lat
            dist = np.sqrt(dx * dx + dy * dy)
            mask = dist <= distance_limit
            if not np.any(mask):
                continue
            weights = np.where(mask, 1.0 / np.power(dist + smooth, power_param), 0.0)
            # grid1/2/3 是 val[y, x] => [wy, wx]，因此把 weights/mask 转置后再累加
            grid1[ymin : ymax + 1, xmin : xmax + 1] += weights.T * station.val
            grid2[ymin : ymax + 1, xmin : xmax + 1] += weights.T
            grid3[ymin : ymax + 1, xmin : xmax + 1] += mask.T.astype(float)

        output = gd_background_data.copy_grid_data()
        valid = (grid2 >= 1e-5) & (grid3 >= number_limit)
        output.val = gd_background_data.val.copy()
        output.val[valid] = grid1[valid] / grid2[valid] + gd_background_data.val[valid]
        low_mask = valid & (output.val <= rain_limit)
        output.val[low_mask] = gd_background_data.val[low_mask]
        return output

    @staticmethod
    def gressman_interpolation_for_rain(
        sd_input_data: ScatterData,
        gd_background_data: GridData,
        distance_limits: list[float] | np.ndarray,
        num_limit: float = 1.0,
        smooth: float = 0.001,
        power_param: float = 2.0,
        rain_limit: float = 0.01,
    ) -> GridData:
        output = gd_background_data.copy_grid_data()
        for distance in distance_limits:
            output = SpatialAnalysis._cressman_one_step_for_rain(
                sd_input_data,
                output,
                float(distance),
                num_limit,
                smooth,
                power_param,
                rain_limit,
            )
        return output

    @staticmethod
    def gressman_interpolation(
        sd_input_data: ScatterData,
        gd_background_data: GridData,
        distance_limits: list[float] | np.ndarray,
        num_limit: float = 1.0,
        smooth: float = 0.001,
        power_param: float = 2.0,
    ) -> GridData:
        return SpatialAnalysis.gressman_interpolation_for_rain(sd_input_data, gd_background_data, distance_limits, num_limit, smooth, power_param, -1e99)
