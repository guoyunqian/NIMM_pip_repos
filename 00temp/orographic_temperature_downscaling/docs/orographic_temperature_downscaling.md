# orographic_temperature_downscaling

## 算法概述

`orographic_temperature_downscaling` 用于基于地形高度差进行气温降尺度和地形订正。原始算法主要迁移自 Met Office IMPROVER 的层结递减率相关方法，并适配 `meteva_base` 的 `grid_data` 数据结构，同时保留 `numpy.ndarray` 输入能力。

本次整理的核心能力包括：

- 根据温度、地形高度和陆海掩膜估计网格化层结递减率。
- 将已有层结递减率应用到温度场，实现源地形到目标地形的温度订正。
- 提供 CLI 示例、notebook 示例、单元测试和样例 `nc` 测试数据。

## 建议算法分类

- 建议分类：`00space_downscale`
- 分类依据：算法以地形高度差为主要物理约束，对气温场进行空间降尺度和地形订正。

## 主要文件

| 类型 | 文件 | 说明 |
| --- | --- | --- |
| 核心源码 | `src/lapse_rate.py` | 层结递减率估计与气温地形订正核心算法 |
| 辅助源码 | `utils/utils.py` | `meteva_base` 网格数据校验、单位换算与结果封装工具 |
| CLI | `cli/dsc_temp_lapse_rate.py` | 从温度、地形和陆海掩膜计算层结递减率 |
| CLI | `cli/anc_lapse_rate.py` | 应用层结递减率进行温度地形订正 |
| 测试 | `test/test_lapse_rate.py` | 核心函数与插件单元测试 |
| 测试 | `test/test_official_lapse_rate_actual_orog.py` | 官方样例数据对照测试 |
| 数据 | `test_data/temp_lapse_rate_data/` | 层结递减率计算测试数据 |
| 数据 | `test_data/apply_lapse_rate_data/` | 地形订正测试数据 |

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

当前阶段为原始算法整理至中间目录，尚未补充到正式算法仓库目录。

已完成：

- 原始源码、CLI、文档、notebook、测试脚本、测试数据复制到 `00temp/orographic_temperature_downscaling/`。
- 保留原始代码逻辑。
- 记录建议分类、贡献人、已知问题和后续补充建议。

待处理：

- 当前代码导入路径仍保留原始包名 `temperature`，补充到正式仓库时需要统一改为仓库包路径。
- 原始目录同时包含 `feels_like_temperature` 体感温度相关能力，建议后续独立评估是否拆分为 `02diagnostic` 或 `10weather_pheno` 类算法。
- 需要在正式补充阶段运行完整测试，并根据仓库环境确认 `meteva_base`、`cf_units`、`xarray`、`numpy`、`pytest` 等依赖。

