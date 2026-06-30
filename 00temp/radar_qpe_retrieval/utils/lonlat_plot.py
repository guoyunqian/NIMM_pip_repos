"""cinrad 色标 + matplotlib 经纬度填色（与 retrieve/nbs/qpe.ipynb 内联方案一致）。"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import BoundaryNorm, ListedColormap
from mpl_toolkits.axes_grid1 import make_axes_locatable
from cinrad.visualize.utils import (
    cmap_cbar,
    cmap_plot,
    cbar_text,
    norm_cbar,
    norm_plot,
    prodname,
    unit,
)

_CHINESE_FONT_PROP = None

# 表1 降雨量分级及其色标规定（离散分级，单位 mm/h）
QPE_PRECIP_CLASS_BOUNDS = (
    0.0,
    0.1,
    10.0,
    25.0,
    50.0,
    100.0,
    250.0,
)
QPE_PRECIP_CLASS_RGB = (
    (255, 255, 255),
    (161, 241, 141),
    (61, 186, 61),
    (96, 184, 255),
    (0, 0, 255),
    (250, 0, 250),
)
QPE_PRECIP_CLASS_LABELS = (
    "0~<0.1",
    "0.1~<10",
    "10~<25",
    "25~<50",
    "50~<100",
    "100~<250",
)

CINRAD_DTYPE_ALIASES = {
    "reflectivity": "REF",
    "corrected_reflectivity": "REF",
    "specific_differential_phase": "KDP",
    "specific_differential_phase_hv": "KDP",
    "radar_echo_classification": "HCL",
    "velocity": "VEL",
    "radial_velocity": "VEL",
}


def setup_matplotlib_chinese():
    """配置 matplotlib 中文字体（Windows 优先微软雅黑/黑体）。"""
    global _CHINESE_FONT_PROP
    from matplotlib import font_manager

    font_path = None
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc"):
        candidate = windir / "Fonts" / name
        if candidate.is_file():
            font_path = candidate
            break

    if font_path is None:
        for name in ("Microsoft YaHei", "SimHei", "SimSun", "Microsoft JhengHei"):
            try:
                candidate = Path(font_manager.findfont(name, fallback_to_default=False))
            except Exception:
                continue
            if candidate.is_file():
                font_path = candidate
                break

    if font_path is None:
        print("警告: 未找到可用中文字体，图中的中文可能显示为方框。")
        return None

    font_manager.fontManager.addfont(str(font_path))
    font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
    _CHINESE_FONT_PROP = font_manager.FontProperties(fname=str(font_path))
    plt.rcParams.update(
        {
            "font.family": font_name,
            "font.sans-serif": [font_name, "DejaVu Sans"],
            "axes.unicode_minus": False,
        }
    )
    return font_name


def chinese_font():
    """返回中文字体 FontProperties。"""
    if _CHINESE_FONT_PROP is None:
        setup_matplotlib_chinese()
    return _CHINESE_FONT_PROP


def apply_chinese_to_figure(fig):
    """为图中标题、坐标轴和色标标签应用中文字体。"""
    fp = chinese_font()
    if fp is None:
        return
    if fig._suptitle is not None:
        fig._suptitle.set_fontproperties(fp)
    for ax in fig.get_axes():
        title = ax.get_title()
        if title:
            ax.set_title(title, fontproperties=fp)
        xlabel = ax.get_xlabel()
        if xlabel:
            ax.set_xlabel(xlabel, fontproperties=fp)
        ylabel = ax.get_ylabel()
        if ylabel:
            ax.set_ylabel(ylabel, fontproperties=fp)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(fp)


def create_qpe_discrete_cmap():
    """返回 QPE 降水产品离散色标（表1 降雨量分级）。

    Returns
    -------
    cmap : ListedColormap
    norm : BoundaryNorm
    cbar_ticks : list[float]
        色标刻度位置（分级边界）。
    cbar_tick_labels : list[str]
        色标刻度文字。
    """
    bounds = list(QPE_PRECIP_CLASS_BOUNDS)
    colors = [(r / 255.0, g / 255.0, b / 255.0) for r, g, b in QPE_PRECIP_CLASS_RGB]
    cmap = ListedColormap(colors, name="qpe_precip_class")
    cmap.set_bad((1.0, 1.0, 1.0, 1.0))
    cmap.set_under((1.0, 1.0, 1.0, 1.0))
    norm = BoundaryNorm(bounds, ncolors=cmap.N, clip=True)
    cbar_ticks = [
        (bounds[i] + bounds[i + 1]) / 2.0 for i in range(len(QPE_PRECIP_CLASS_LABELS))
    ]
    return cmap, norm, cbar_ticks, list(QPE_PRECIP_CLASS_LABELS)


def style_qpe_discrete_colorbar(cbar, *, label: str = "降水量 (mm/h)"):
    """为 QPE 离散色标设置刻度与标签。"""
    _, _, tick_pos, tick_labels = create_qpe_discrete_cmap()
    cbar.set_ticks(tick_pos)
    cbar.set_ticklabels(tick_labels)
    cbar.set_label(label)
    cbar.ax.tick_params(length=0, labelsize=9)
    fp = chinese_font()
    if fp is not None:
        cbar.set_label(label, fontproperties=fp)
        for tick_label in cbar.ax.get_yticklabels():
            tick_label.set_fontproperties(fp)


def resolve_cinrad_dtype(field_name: str) -> str:
    key = str(field_name).strip()
    upper = key.upper()
    if upper in norm_plot:
        return upper
    alias = CINRAD_DTYPE_ALIASES.get(key.lower())
    if alias is not None:
        return alias
    raise ValueError(f"Unknown cinrad field: {field_name}")


def _colorbar_tick_positions(cbar_norm, labels, *, plot_norm=None):
    """计算色标刻度位置；分类场用 BoundaryNorm 类别中心。"""
    labels = list(labels)
    n = len(labels)
    if n == 0:
        return None, None

    boundary_norm = plot_norm if isinstance(plot_norm, BoundaryNorm) else None
    if boundary_norm is None and isinstance(cbar_norm, BoundaryNorm):
        boundary_norm = cbar_norm
    if boundary_norm is not None:
        bounds = np.asarray(boundary_norm.boundaries, dtype=float)
        if bounds.size >= n + 1:
            tick_pos = (bounds[:n] + bounds[1 : n + 1]) / 2.0
            return tick_pos, labels
        return np.arange(n, dtype=float), labels

    vmin = float(getattr(cbar_norm, "vmin", 0.0))
    vmax = float(getattr(cbar_norm, "vmax", 1.0))
    return np.linspace(vmin, vmax, n), labels


def plot_lonlat_field(
    data,
    lon,
    lat,
    field_name,
    title,
    *,
    extent=None,
    cmap=None,
    norm=None,
    cbar_label=None,
    cbar_tick_labels=None,
    figsize=(8.0, 6.5),
):
    """用 cinrad 内置 cmap/norm 在经纬度网格上填色绘图。

    默认产品与 cinrad PPI 一致：填色用 norm_plot/cmap_plot，色标用 norm_cbar/cmap_cbar。
    """
    use_cinrad_cbar = cmap is None and norm is None and cbar_tick_labels is None
    if use_cinrad_cbar:
        dtype = resolve_cinrad_dtype(field_name)
        plot_cmap = cmap_plot[dtype]
        plot_norm = norm_plot[dtype]
        cbar_cmap = cmap_cbar[dtype]
        cbar_norm = norm_cbar[dtype]
        tick_labels = cbar_text.get(dtype)
    else:
        dtype = str(field_name).strip().upper()
        plot_cmap = cmap
        plot_norm = norm
        cbar_cmap = cmap
        cbar_norm = norm
        tick_labels = cbar_tick_labels

    values = np.asarray(data, dtype=np.float32)
    lon = np.asarray(lon, dtype=np.float64)
    lat = np.asarray(lat, dtype=np.float64)
    if lon.ndim == 1 and lat.ndim == 1:
        lon_plot, lat_plot = np.meshgrid(lon, lat)
    else:
        lon_plot, lat_plot = lon, lat

    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    ax.pcolormesh(lon_plot, lat_plot, values, cmap=plot_cmap, norm=plot_norm, shading="auto")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal", adjustable="box")
    if extent is not None:
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
    ax.grid(True, linestyle="--", linewidth=0.6, color="0.45", alpha=0.55)

    cax = make_axes_locatable(ax).append_axes("right", size="3.5%", pad=0.12)
    cbar = ColorbarBase(
        cax,
        cmap=cbar_cmap,
        norm=cbar_norm,
        orientation="vertical",
    )
    cbar.ax.tick_params(axis="both", which="both", length=0, labelsize=9)

    if cbar_label is not None:
        cbar.set_label(cbar_label)
    elif use_cinrad_cbar:
        unit_label = unit.get(dtype, "")
        name = prodname.get(dtype, dtype)
        cbar.set_label(f"{name} ({unit_label})" if unit_label else name)

    if tick_labels is not None:
        tick_pos, tick_lbl = _colorbar_tick_positions(
            cbar_norm,
            tick_labels,
            plot_norm=plot_norm if not use_cinrad_cbar else None,
        )
        if tick_pos is not None:
            cbar.set_ticks(tick_pos)
            cbar.set_ticklabels([str(t) for t in tick_lbl])

    fp = chinese_font()
    if fp is not None:
        fig.suptitle(title, fontproperties=fp)
        label_text = cbar_label if cbar_label is not None else cbar.ax.get_ylabel()
        if label_text:
            cbar.set_label(label_text, fontproperties=fp)
        for label in cbar.ax.get_yticklabels():
            label.set_fontproperties(fp)
    else:
        fig.suptitle(title)
    return type("LonLatPlot", (), {"fig": fig, "ax": ax, "cbar": cbar})()


def show_lonlat_field(data, lon, lat, field_name, title, **kwargs):
    """在 Jupyter 中显示一张 lon/lat 填色图并关闭 figure。"""
    from IPython.display import display

    with plt.ioff():
        plot = plot_lonlat_field(data, lon, lat, field_name, title, **kwargs)
        apply_chinese_to_figure(plot.fig)
    display(plot.fig)
    plt.close(plot.fig)
    return plot
