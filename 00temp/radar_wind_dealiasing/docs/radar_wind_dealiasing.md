# 雷达风场退模糊

## 基本信息

- 算法名称：`radar_wind_dealiasing`
- 原始路径：`D:\workspace\pyart_nimm\region_dealias`
- 算法类型：`01obs_adustment`
- 贡献人：郭云谦、王亭波

## 算法功能

该算法从 Py-ART 的区域连通关系退模糊逻辑迁移而来，面向多普勒雷达径向速度做 Nyquist 速度折叠订正。输入输出均为 `meteva_base.grid_data` 风格的 `xarray.DataArray`，并支持门点过滤、参考速度锚定与可选经纬度重映射。

## 主要方法

| 方法 | 功能 |
| --- | --- |
| `dealias_region_based` | 基于区域连通关系的核心退模糊 |
| `RegionDealiasPlugin` | 插件封装，含地理后处理 |
| `GridGateFilter` | 门点过滤掩码构造 |
| `cli/region_dealias.process` | 文件式 CLI 调用 |
| `cli/polar_volume_main` | 极坐标体扫准备与校验 |

## 目录说明

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| 核心源码 | `src/region_dealias.py` | 插件类与核心算法函数 |
| 内部工具 | `src/utils/` | 区域求解、地理重映射、体扫辅助 |
| CLI | `cli/region_dealias.py`、`cli/polar_volume_main.py` | 示例入口 |
| 测试 | `test/` | 单元测试与 CLI 测试 |
| 文档 | `docs/region_dealias.md` | 详细算法说明 |
| notebook | `nbs/region_dealias.ipynb` | 示例 |

## 当前整理状态

- 已从 `D:\workspace\pyart_nimm\region_dealias` 同步源码、CLI、测试、文档与 notebook。
- 导入路径已统一为中间目录模块名 `radar_wind_dealiasing`。
- 未同步 `test_data/`（仅 notebook / CLI 演示用；单元测试不依赖）。
- 补充至 `NIMM/01obs_adustment/` 时需调整为仓库正式包路径。
