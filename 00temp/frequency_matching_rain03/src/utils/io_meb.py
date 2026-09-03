# -*- coding: utf-8 -*-
"""路径展开与 Micaps I/O：直接用 ``meteva_base``。"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable, Optional, Sequence, Tuple

try:
    import meteva_base as meb
except ImportError as exc:
    raise ImportError("未安装 meteva_base，请先执行: pip install meteva_base") from exc


GRID_SUFFIXES = (".m4", ".nc")
STA_SUFFIXES = (".m3",)


def expand_data_path(template: str, dt_input: datetime, i_valid: int = 0) -> str:
    """``VVV`` 换成 ``TTT`` 后 ``meb.get_path``。"""
    tpl = str(template).replace("VVV", "TTT").replace("VV", "TT")
    return meb.get_path(tpl, dt_input, i_valid)


def resolve_existing_path(
    path: str,
    suffixes: Sequence[str] = GRID_SUFFIXES + STA_SUFFIXES,
) -> Optional[str]:
    """已存在则返回：原路径 → 追加后缀 → 去掉已有后缀。"""
    if not path:
        return None
    if os.path.isfile(path):
        return path
    for suffix in suffixes:
        candidate = path + suffix
        if os.path.isfile(candidate):
            return candidate
    root, ext = os.path.splitext(path)
    if ext and os.path.isfile(root):
        return root
    return None


def find_grid_file(template: str, dt_input: datetime, i_valid: int = 0) -> Tuple[str, Optional[str]]:
    raw = expand_data_path(template, dt_input, i_valid)
    return raw, resolve_existing_path(raw, GRID_SUFFIXES)


def find_sta_file(template: str, dt_input: datetime, i_valid: int = 0) -> Tuple[str, Optional[str]]:
    raw = expand_data_path(template, dt_input, i_valid)
    return raw, resolve_existing_path(raw, STA_SUFFIXES)


def norm_sta_id(value) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        try:
            return str(int(float(text)))
        except Exception:
            pass
    return text


def read_stadata_rows(path: str) -> list:
    sta = meb.read_stadata_from_micaps3(path)
    if sta is None:
        raise RuntimeError(f"meb.read_stadata_from_micaps3 失败: {path}")
    data_col = sta.columns[-1]
    rows = []
    for _, row in sta.iterrows():
        rows.append((
            norm_sta_id(row["id"]),
            float(row["lon"]),
            float(row["lat"]),
            float(row[data_col]),
        ))
    return rows


def write_stadata_m3(ids: Iterable, lons: Iterable, lats: Iterable, vals: Iterable, path: str) -> None:
    import pandas as pd
    id_list = []
    for item in ids:
        try:
            id_list.append(int(item))
        except Exception:
            id_list.append(item)
    sta = meb.sta_data(pd.DataFrame({
        "id": id_list,
        "lon": list(lons),
        "lat": list(lats),
        "data0": list(vals),
    }))
    meb.write_stadata_to_micaps3(sta, save_path=path, effectiveNum=2, creat_dir=True)
