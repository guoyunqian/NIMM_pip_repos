# orographic_wind_downscaling

## 算法概述

`orographic_wind_downscaling` 用于基于地形粗糙度和地形高度差进行风速空间降尺度。原始算法迁移自 Met Office IMPROVER 风速降尺度相关实现，并适配 `meteva_base` 的 `grid_data` 六维数据结构，同时支持 `numpy.ndarray` 输入。

本次整理的核心能力包括：

- 根据地形轮廓粗糙度、网格内地形高度标准差、目标地形、模式地形和植被粗糙度长度构建订正参数。
- 对输入风速执行粗糙度订正和高度订正。
- 支持一维公共高度层或三维空间变化高度层。
- 提供 CLI 示例、notebook 示例和单元测试。

## 算法分类

- 分类：`00space_downscale`
- 分类依据：算法以地形和粗糙度辅助场为约束，对风速场进行空间降尺度和地形影响订正。

## 主要文件


| 类型   | 文件                                       | 说明                          |
| ---- | ---------------------------------------- | --------------------------- |
| 核心源码 | `src/wind_downscaling.py`                | 风速粗糙度订正和高度订正核心算法            |
| 辅助源码 | `utils/base_plugin.py`                   | 插件基类与后处理插件基类                |
| 辅助源码 | `utils/utils.py`                         | `meteva_base` 网格数据校验与输出封装工具 |
| CLI  | `cli/dsc_wind_downscaling.py`            | 风速降尺度示例调度脚本                 |
| 文档   | `docs/wind_downscaling.md`               | 原始算法分析文档                    |
| 测试   | `test/test_RoughnessCorrection.py`       | 粗糙度订正主流程测试                  |
| 测试   | `test/test_official_wind_downscaling.py` | 官方样例数据对照测试                  |




## 输入输出

输入：

- `wind_speed`：待订正风速场，支持 `xarray.DataArray` 或 `numpy.ndarray`。
- `a_over_s`：地形轮廓粗糙度，无量纲。
- `sigma`：网格内地形高度标准差，单位通常为 `m`。
- `pporo`：目标网格地形高度，单位通常为 `m`。
- `modoro`：插值至目标网格的模式地形高度，单位通常为 `m`。
- `z0`：植被粗糙度长度，可选，单位通常为 `m`。
- `modres`：模式原始分辨率。
- `ppres`：后处理目标网格分辨率，`pporo` 为 `DataArray` 时可由坐标推断。
- `height_grid`：风速对应高度层，一维或三维。

输出：

- 经地形粗糙度和高度订正后的风速场，输出结构与输入风速保持一致；`DataArray` 输入返回 `meteva_base` 六维结构。



## 当前整理状态

当前阶段为原始算法整理至中间目录，尚未补充到正式算法仓库目录。

已完成：

- 原始源码、CLI、文档、notebook、测试脚本、测试数据复制到 `00temp/orographic_wind_downscaling/`。
- 2026-07-02 从 `D:\workspace\improver\wind_calculations` 增量同步，导入路径已统一为中间目录模块名 `orographic_wind_downscaling`。

待处理：

- 补充至正式仓库时，需将导入路径调整为 `NIMM` 下实际包路径。
- 正式入库时需评估 `utils/base_plugin.py` 是否替换为仓库统一基类。
- 需要在正式补充阶段运行完整测试，并确认 `meteva_base`、`cf_units`、`xarray`、`numpy`、`pytest`、`netcdf4` 等依赖。

