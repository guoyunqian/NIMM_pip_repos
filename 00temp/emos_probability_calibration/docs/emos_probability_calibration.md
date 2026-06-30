# emos_probability_calibration

## 算法概述

`emos_probability_calibration` 用于集合预报的 EMOS 概率订正。原始实现基于 Met Office IMPROVER 的 EMOS calibration 思路，移除了 `iris` 强依赖的主流程，转为以 `xarray` 数据结构实现站点类集合预报订正。

本次整理的核心能力包括：

- 基于历史集合预报和实况训练 EMOS 系数。
- 支持正态分布 `norm` 和截断正态分布 `truncnorm` 的 CRPS 最小化。
- 根据训练系数生成订正分布的位置参数和尺度参数。
- 将 EMOS 结果输出为集合成员、概率或分位数结果。
- 支持附加静态预测因子，例如高度差 `delta_z`。

## 算法分类

- 分类：`07probability`
- 分类依据：算法面向集合预报概率订正和概率/分位数输出，属于集合及概率预报相关算法。

## 主要文件

| 类型 | 文件 | 说明 |
| --- | --- | --- |
| 核心源码 | `src/emos_calibration.py` | EMOS 系数训练、分布参数生成和 ApplyEMOS 主流程 |
| 核心源码 | `src/calibration_utilities.py` | 训练数据对齐、检查、展平和坐标匹配工具 |
| 核心源码 | `src/base_init.py` | 插件基类 |
| 工具源码 | `utils/xarray_core.py` | xarray 数据结构、坐标、属性和输出封装工具 |
| 工具源码 | `utils/xarray_ecc.py` | 概率、分位数、ECC 和集合重排序工具 |
| 工具源码 | `utils/xarray_probabilistic.py` | 概率和阈值坐标识别工具 |
| CLI | `cli/emos_probability_calibration_main.py` | 中间整理阶段新增的最小训练和应用调度脚本 |
| 示例 | `nbs/emos_probability_calibration_example.py` | 使用样例数据训练和应用 EMOS 的脚本示例 |
| 测试 | `test/run_demo.py` | 原始对照 demo，依赖 `iris` 和 `improver` |
| 数据 | `test_data/` | 样例预报、实况、分位数和高度差数据 |

## 输入输出

### 系数训练

输入：

- `historic_forecasts`：历史集合预报。
- `truths`：对应实况。
- `additional_fields`：可选附加预测因子，如高度差。

输出：

- `emos_coefficient_alpha`
- `emos_coefficient_beta`
- `emos_coefficient_gamma`
- `emos_coefficient_delta`

### 应用订正

输入：

- `forecast`：当前待订正集合、概率或分位数预报。
- `coefficients`：训练得到的 EMOS 系数。
- `additional_fields`：训练阶段使用的附加预测因子。
- `prob_template`：可选概率模板，用于输出阈值概率。

输出：

- 订正后的集合预报、概率预报或分位数预报。

## 当前整理状态

当前阶段为原始算法整理至中间目录，尚未补充到正式算法仓库目录。

已完成：

- 原始 `src/`、`utils/`、`test/`、`test_data/` 已复制到 `00temp/emos_probability_calibration/`。
- 已排除 `__pycache__` 和 `.pyc` 编译缓存。
- 已补齐 `cli/`、`docs/`、`nbs/`、`resource/` 目录。
- 已新增最小 CLI、示例脚本和整理说明文档。

待处理：

- 原始代码导入路径仍使用 `src...` 和 `utils...`，补充到正式仓库时需要统一改为仓库包路径。
- `test/run_demo.py` 依赖 `iris`、`improver` 与原始 IMPROVER 结果对照，正式测试策略需要确认。
- 当前实现说明为 spot-only，不支持 gridded x/y domains，需要在正式文档中明确适用范围。

