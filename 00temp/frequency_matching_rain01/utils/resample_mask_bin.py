"""Resample mask010.dat (0.1 deg float32 bin) to finer resolution bins.

Output layout matches GridData.read_float_val_from_bin / write_float_val_to_bin:
  shape [yn, xn], row-major float32, same domain as source.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def _grid_dims(
    lon_start: float,
    lon_end: float,
    lat_start: float,
    lat_end: float,
    dlon: float,
    dlat: float,
) -> tuple[int, int, np.ndarray, np.ndarray]:
    xn = int(round((float(lon_end) + 1e-5 - lon_start) / dlon)) + 1
    yn = int(round((float(lat_end) + 1e-5 - lat_start) / dlat)) + 1
    lon = lon_start + np.arange(xn, dtype=float) * dlon
    lat = lat_start + np.arange(yn, dtype=float) * dlat
    return xn, yn, lon, lat


def resample_mask(
    src_path: Path,
    dst_path: Path,
    dlon_new: float,
    dlat_new: float,
    lon_start: float,
    lon_end: float,
    lat_start: float,
    lat_end: float,
    src_dlon: float,
    src_dlat: float,
    method: str = "nearest",
) -> None:
    xn_s, yn_s, lon_s, lat_s = _grid_dims(
        lon_start, lon_end, lat_start, lat_end, src_dlon, src_dlat
    )
    xn_d, yn_d, lon_d, lat_d = _grid_dims(
        lon_start, lon_end, lat_start, lat_end, dlon_new, dlat_new
    )
    arr = np.fromfile(src_path, dtype=np.float32, count=xn_s * yn_s)
    if arr.size != xn_s * yn_s:
        raise SystemExit(
            f"bad source size: got {arr.size} floats, expect {xn_s * yn_s} "
            f"({yn_s}x{xn_s}) from {src_path}"
        )
    val_s = arr.reshape(yn_s, xn_s).astype(float)

    try:
        from scipy.interpolate import RegularGridInterpolator  # type: ignore

        rgi = RegularGridInterpolator(
            (lat_s, lon_s),
            val_s,
            method=method,
            bounds_error=False,
            fill_value=float(val_s.mean()),
        )
        lon_m, lat_m = np.meshgrid(lon_d, lat_d, indexing="xy")
        pts = np.stack([lat_m.ravel(), lon_m.ravel()], axis=-1)
        val_d = rgi(pts).reshape(yn_d, xn_d).astype(np.float32)
    except Exception:
        # Fallback: nearest index mapping (same as nearest RGI for aligned grids)
        iy = np.clip(
            np.round((lat_d[:, None] - lat_s[0]) / src_dlat).astype(int),
            0,
            yn_s - 1,
        )
        ix = np.clip(
            np.round((lon_d[None, :] - lon_s[0]) / src_dlon).astype(int),
            0,
            xn_s - 1,
        )
        val_d = val_s[iy, ix].astype(np.float32)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    val_d.tofile(dst_path)
    print(
        f"wrote {dst_path} shape=({yn_d}, {xn_d}) dlon={dlon_new} dlat={dlat_new} "
        f"bytes={dst_path.stat().st_size}"
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, default=Path("info/mask010.dat"))
    p.add_argument("--lon0", type=float, default=70.0)
    p.add_argument("--lon1", type=float, default=140.0)
    p.add_argument("--lat0", type=float, default=0.0)
    p.add_argument("--lat1", type=float, default=60.0)
    p.add_argument("--src-dlon", type=float, default=0.1)
    p.add_argument("--src-dlat", type=float, default=0.1)
    p.add_argument("--out-005", type=Path, default=Path("info/mask005.dat"))
    p.add_argument("--out-001", type=Path, default=Path("info/mask001.dat"))
    p.add_argument(
        "--method",
        choices=("nearest", "linear"),
        default="nearest",
        help="interpolation for mask (nearest preserves class-like boundaries)",
    )
    args = p.parse_args()

    base = Path(__file__).resolve().parents[1]
    src = args.src if args.src.is_absolute() else base / args.src
    out005 = args.out_005 if args.out_005.is_absolute() else base / args.out_005
    out001 = args.out_001 if args.out_001.is_absolute() else base / args.out_001

    resample_mask(
        src,
        out005,
        0.05,
        0.05,
        args.lon0,
        args.lon1,
        args.lat0,
        args.lat1,
        args.src_dlon,
        args.src_dlat,
        method=args.method,
    )
    resample_mask(
        src,
        out001,
        0.01,
        0.01,
        args.lon0,
        args.lon1,
        args.lat0,
        args.lat1,
        args.src_dlon,
        args.src_dlat,
        method=args.method,
    )


if __name__ == "__main__":
    main()
