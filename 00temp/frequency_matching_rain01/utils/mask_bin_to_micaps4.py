"""Write mask *.dat (float32 [yn,xn] bin) to Micaps4 *.m4 (ASCII, same layout as GridData fallback).

Does not import meteva; only numpy. Header matches `GridData.write_val_to_micaps4` manual branch
so `_read_micaps4_legacy` can read the file back.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np


def _grid_dims(
    lon_start: float,
    lon_end: float,
    lat_start: float,
    lat_end: float,
    dlon: float,
    dlat: float,
) -> tuple[int, int]:
    xn = int(round((float(lon_end) + 1e-5 - lon_start) / dlon)) + 1
    yn = int(round((float(lat_end) + 1e-5 - lat_start) / dlat)) + 1
    return xn, yn


def write_micaps4_mask(
    bin_path: Path,
    m4_path: Path,
    lon_start: float,
    lon_end: float,
    lat_start: float,
    lat_end: float,
    dlon: float,
    dlat: float,
    dt_input: datetime,
    i_valid: int,
) -> None:
    xn, yn = _grid_dims(lon_start, lon_end, lat_start, lat_end, dlon, dlat)
    arr = np.fromfile(bin_path, dtype=np.float32, count=xn * yn)
    if arr.size != xn * yn:
        raise SystemExit(
            f"{bin_path}: expected {xn * yn} floats, got {arr.size} "
            f"(grid {yn}x{xn}, dlon={dlon}, dlat={dlat})"
        )
    val = arr.reshape(yn, xn)

    # Must match `GridData.write_val_to_micaps4` fallback header tokenization (parts[22:] = data).
    header = (
        " diamond 4 "
        f"{dt_input:%Y%m%d%H}_{i_valid:03d}时效001小时降水预报场 "
        f"{dt_input:%Y %m %d %H} {i_valid:03d} 0 {dlon:.2f}  {dlat:.2f}  "
        f"{lon_start:.0f} {lon_end:.0f} {lat_start:.0f} {lat_end:.0f} "
        f"{xn} {yn}  5  0 200 0  0"
    )
    m4_path.parent.mkdir(parents=True, exist_ok=True)
    with m4_path.open("w", encoding="gb2312", errors="ignore") as f:
        f.write(header + "\n")
        for j in range(yn):
            f.write(
                "  ".join(f"{float(val[j, i]):8.2f}" for i in range(xn)) + "\n"
            )
    print(f"wrote {m4_path} ({m4_path.stat().st_size} bytes)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lon0", type=float, default=70.0)
    p.add_argument("--lon1", type=float, default=140.0)
    p.add_argument("--lat0", type=float, default=0.0)
    p.add_argument("--lat1", type=float, default=60.0)
    p.add_argument("--dt", type=str, default="2025100100", help="YYYYMMDDHH in header")
    p.add_argument("--i-valid", type=int, default=0)
    args = p.parse_args()
    dt_input = datetime.strptime(args.dt, "%Y%m%d%H")

    root = Path(__file__).resolve().parents[1]
    jobs = [
        (root / "info" / "mask005.dat", root / "info" / "mask005.m4", 0.05, 0.05),
        (root / "info" / "mask001.dat", root / "info" / "mask001.m4", 0.01, 0.01),
    ]
    for bin_path, m4_path, dlon, dlat in jobs:
        if not bin_path.is_file():
            print(f"skip (missing): {bin_path}", file=sys.stderr)
            continue
        write_micaps4_mask(
            bin_path,
            m4_path,
            args.lon0,
            args.lon1,
            args.lat0,
            args.lat1,
            dlon,
            dlat,
            dt_input,
            args.i_valid,
        )


if __name__ == "__main__":
    main()
