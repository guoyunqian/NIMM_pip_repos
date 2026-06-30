from __future__ import annotations

import numpy as np

from data import GridData, PointData, ScatterData
from .spatial_analysis import SpatialAnalysis


class OpticalFlow:
    @staticmethod
    def _central_gradient_x(grid: GridData) -> GridData:
        out = grid.copy_grid_data()
        out.clear_to_num(0.0)
        # val[y, x] => x 方向是 axis=1
        out.val[:, 1:-1] = (grid.val[:, 2:] - grid.val[:, :-2]) / (2.0 * grid.dlon)
        return out

    @staticmethod
    def _central_gradient_y(grid: GridData) -> GridData:
        out = grid.copy_grid_data()
        out.clear_to_num(0.0)
        # val[y, x] => y 方向是 axis=0
        out.val[1:-1, :] = (grid.val[2:, :] - grid.val[:-2, :]) / (2.0 * grid.dlat)
        return out

    @staticmethod
    def get_wind_from_optical_flow(
        gd_qpf_before: list[GridData],
        gd_qpf_next: list[GridData],
        min_window: list[list[float]],
        gd_output: list[GridData],
        rain_limit: float = 0.1,
        delta_rain_limit: float = 0.1,
        num_limit: int = 100,
    ) -> None:
        window = min_window[0]
        dx_count = max(int(window[0] / gd_qpf_before[0].dlon), 1)
        dy_count = max(int(window[1] / gd_qpf_before[0].dlat), 1)
        pdx = max(int(0.5 * dx_count), 1)
        pdy = max(int(0.5 * dy_count), 1)
        x_index = list(range(int(0.5 * dx_count) + 1, gd_qpf_before[0].xn - 1, pdx))
        y_index = list(range(int(0.5 * dy_count) + 1, gd_qpf_before[0].yn - 1, pdy))

        grad_x, grad_y, delta = [], [], []
        for before, after in zip(gd_qpf_before, gd_qpf_next):
            gx = OpticalFlow._central_gradient_x(before)
            gx.add_val(OpticalFlow._central_gradient_x(after))
            gx.multi_val(0.5)
            gy = OpticalFlow._central_gradient_y(before)
            gy.add_val(OpticalFlow._central_gradient_y(after))
            gy.multi_val(0.5)
            d = after.copy_grid_data()
            d.sub_val(before)
            grad_x.append(gx.val)
            grad_y.append(gy.val)
            delta.append(d.val)

        before_vals = [g.val for g in gd_qpf_before]
        next_vals = [g.val for g in gd_qpf_next]
        u_points: list[PointData] = []
        v_points: list[PointData] = []
        for j_idx in y_index:
            j0, j1 = j_idx - pdy, j_idx + pdy + 1
            for i_idx in x_index:
                i0, i1 = i_idx - pdx, i_idx + pdx + 1
                rows = []
                rhs = []
                for level in range(len(gd_qpf_before)):
                    # val[y, x] => [y_slice, x_slice]
                    gx = grad_x[level][j0:j1, i0:i1]
                    gy = grad_y[level][j0:j1, i0:i1]
                    dv = delta[level][j0:j1, i0:i1]
                    mask = (
                        (np.abs(dv) >= delta_rain_limit)
                        & (before_vals[level][j0:j1, i0:i1] >= rain_limit)
                        & (next_vals[level][j0:j1, i0:i1] >= rain_limit)
                    )
                    if np.any(mask):
                        rows.append(np.column_stack((gx[mask], gy[mask])))
                        rhs.append(-dv[mask])
                if not rhs:
                    continue
                a = np.vstack(rows)
                b = np.concatenate(rhs)
                if b.size < num_limit:
                    continue
                x, *_ = np.linalg.lstsq(a, b, rcond=None)
                lon = gd_qpf_before[0].lon_start + i_idx * gd_qpf_before[0].dlon
                lat = gd_qpf_before[0].lat_start + j_idx * gd_qpf_before[0].dlat
                u_points.append(PointData(f"u_{i_idx}_{j_idx}", float(lon), float(lat), float(x[0])))
                v_points.append(PointData(f"v_{i_idx}_{j_idx}", float(lon), float(lat), float(x[1])))

        if not u_points:
            gd_output[0].clear_to_num(0.0)
            gd_output[1].clear_to_num(0.0)
            return

        coarse_u = gd_output[0].mesh_val(gd_output[0].lon_start, gd_output[0].lon_end, gd_output[0].lat_start, gd_output[0].lat_end, window[0], window[1])
        coarse_v = gd_output[1].mesh_val(gd_output[1].lon_start, gd_output[1].lon_end, gd_output[1].lat_start, gd_output[1].lat_end, window[0], window[1])
        distance_limits = [4.0 * window[0], 2.0 * window[0], 1.0 * window[0]]
        grid_u = SpatialAnalysis.gressman_interpolation(ScatterData(u_points), coarse_u, distance_limits)
        grid_v = SpatialAnalysis.gressman_interpolation(ScatterData(v_points), coarse_v, distance_limits)
        gd_output[0] = grid_u.mesh_val(gd_output[0].lon_start, gd_output[0].lon_end, gd_output[0].lat_start, gd_output[0].lat_end, gd_output[0].dlon, gd_output[0].dlat)
        gd_output[1] = grid_v.mesh_val(gd_output[1].lon_start, gd_output[1].lon_end, gd_output[1].lat_start, gd_output[1].lat_end, gd_output[1].dlon, gd_output[1].dlat)
