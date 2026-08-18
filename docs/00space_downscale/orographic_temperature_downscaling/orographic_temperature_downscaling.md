# orographic_temperature_downscaling

## 算法概述

`orographic_temperature_downscaling` 用于基于地形高度差进行气温降尺度和地形订正。原始算法主要迁移自 Met Office IMPROVER 的层结递减率相关方法，并适配 `meteva_base` 的 `grid_data` 数据结构，同时保留 `numpy.ndarray` 输入能力。

核心能力包括：

- 根据温度、地形高度和陆海掩膜估计网格化层结递减率。
- 将已有层结递减率应用到温度场，实现源地形到目标地形的温度订正。
- 提供 CLI 示例、notebook 示例和单元测试。

## 算法分类

- 分类：`00space_downscale`
- 分类依据：算法以地形高度差为主要物理约束，对气温场进行空间降尺度和地形订正。

## 正式目录

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| 核心源码 | `NIMM/00space_downscale/orographic_temperature_downscaling/lapse_rate.py` | 层结递减率估计与气温地形订正核心算法 |
| 辅助源码 | `NIMM/00space_downscale/orographic_temperature_downscaling/utils/` | 插件基类与网格封装工具 |
| CLI | `cli/00space_downscale/orographic_temperature_downscaling/dsc_temp_lapse_rate_main.py` | 计算层结递减率 |
| CLI | `cli/00space_downscale/orographic_temperature_downscaling/anc_lapse_rate_main.py` | 应用层结递减率做温度地形订正 |
| 文档 | `docs/00space_downscale/orographic_temperature_downscaling/` | 算法说明 |
| notebook | `nbs/00space_downscale/orographic_temperature_downscaling/` | 验证与官方样例 |
| 测试 | `test/00space_downscale/orographic_temperature_downscaling/` | 单元测试与官方样例对照 |
| 资源 | `resource/00space_downscale/orographic_temperature_downscaling/` | 当前仅说明文件 |

官方样例预处理脚本仍保留在中间目录 `00temp/orographic_temperature_downscaling/cli/preprocess_test_data.py`，不进入正式 `cli/`。

因分类目录以数字开头，CLI 与测试使用 `importlib.import_module()` 动态导入。

## 输入输出

### 层结递减率估计

输入：

- `temperature`：气温场，支持 `xarray.DataArray` 或 `numpy.ndarray`。
- `orography`：地形高度场。
- `land_sea_mask`：陆海掩膜，陆地点参与局地梯度拟合，海洋点回退为干绝热递减率。

输出：

- `air_temperature_lapse_rate`：层结递减率场，单位 `K m-1`。

### 气温地形订正

输入：

- `temperature`：待订正温度场。
- `lapse_rate`：层结递减率场。
- `source_orog`：源地形高度场。
- `dest_orog`：目标地形高度场。

输出：

- 地形订正后的温度场，输出单位为 `K`。

## 当前整理状态

已补充至正式算法仓库目录。中间目录文件未删除。
