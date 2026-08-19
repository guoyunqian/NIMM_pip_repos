# orographic_precipitation_downscaling

## 算法概述

`orographic_precipitation_downscaling` 用于基于地形抬升效应计算降水地形增强项，并支持将该增强项叠加或扣除到降水场。原始算法迁移自 Met Office IMPROVER 的地形增强相关实现，并适配 `meteva_base` 的 `grid_data` 六维数据结构，同时保留二维场和 `numpy.ndarray` 输入能力。

核心能力包括：

- 从温度、相对湿度、气压、风速、风向和目标地形计算地形增强项。
- 将风速风向解析为目标网格坐标系下的 `u/v` 风分量。
- 基于迎风抬升项 `v·gradZ`、湿度阈值、地形阈值和上游贡献计算地形增强。
- 支持将地形增强项以 `add` 或 `subtract` 模式应用到降水场。
- 提供 CLI 示例、notebook 示例和单元测试。

## 算法分类

- 分类：`00space_downscale`
- 分类依据：算法以地形抬升和风场为主要物理约束，对降水场进行空间降尺度和地形影响订正。

## 正式目录

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| 核心源码 | `NIMM/00space_downscale/orographic_precipitation_downscaling/orographic_enhancement.py` | 地形增强项计算、风分量解析和元插件流程 |
| 应用源码 | `NIMM/00space_downscale/orographic_precipitation_downscaling/apply_orographic_enhancement.py` | 将地形增强项叠加或扣除到降水场 |
| 算法内工具 | `NIMM/00space_downscale/orographic_precipitation_downscaling/utils/` | 插件基类、网格封装，以及网格/数值/饱和水汽压等内部函数 |
| CLI | `cli/00space_downscale/orographic_precipitation_downscaling/dsc_orographic_enhancement_main.py` | 地形增强项计算业务调度 |
| 文档 | `docs/00space_downscale/orographic_precipitation_downscaling/` | 算法说明 |
| notebook | `nbs/00space_downscale/orographic_precipitation_downscaling/` | 验证与官方样例 |
| 测试 | `test/00space_downscale/orographic_precipitation_downscaling/` | 单元测试与官方样例对照 |
| 资源 | `resource/00space_downscale/orographic_precipitation_downscaling/` | 当前仅说明文件 |

官方样例预处理脚本仍保留在中间目录 `00temp/orographic_precipitation_downscaling/cli/preprocess_test_data.py`，不进入正式 `cli/`。

因分类目录以数字开头，CLI 与测试使用 `importlib.import_module()` 动态导入。

## 当前整理状态

已补充至正式算法仓库目录。中间目录文件未删除。
