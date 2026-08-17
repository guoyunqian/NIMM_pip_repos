# orographic_wind_downscaling

## 算法概述

`orographic_wind_downscaling` 用于基于地形粗糙度和地形高度差进行风速空间降尺度。原始算法迁移自 Met Office IMPROVER 风速降尺度相关实现，并适配 `meteva_base` 的 `grid_data` 六维数据结构，同时支持 `numpy.ndarray` 输入。

核心能力包括：

- 根据地形轮廓粗糙度、网格内地形高度标准差、目标地形、模式地形和植被粗糙度长度构建订正参数。
- 对输入风速执行粗糙度订正和高度订正。
- 支持一维公共高度层或三维空间变化高度层。
- 支持投影米制与真经纬分辨率推断。

## 算法分类

- 分类：`00space_downscale`
- 分类依据：算法以地形和粗糙度辅助场为约束，对风速场进行空间降尺度和地形影响订正。

## 正式目录

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| 核心源码 | `NIMM/00space_downscale/orographic_wind_downscaling/wind_downscaling.py` | 风速粗糙度订正和高度订正核心算法 |
| 辅助源码 | `NIMM/00space_downscale/orographic_wind_downscaling/utils/` | 插件基类与网格封装工具 |
| CLI | `cli/00space_downscale/orographic_wind_downscaling/dsc_wind_downscaling_main.py` | 风速降尺度业务调度 |
| 文档 | `docs/00space_downscale/orographic_wind_downscaling/` | 算法说明 |
| notebook | `nbs/00space_downscale/orographic_wind_downscaling/` | 验证与官方样例 |
| 测试 | `test/00space_downscale/orographic_wind_downscaling/` | 单元测试与官方样例对照 |
| 资源 | `resource/00space_downscale/orographic_wind_downscaling/` | 当前仅说明文件 |

官方样例预处理脚本仍保留在中间目录 `00temp/orographic_wind_downscaling/cli/preprocess_test_data.py`，不进入正式 `cli/`。

因分类目录以数字开头，CLI 与测试使用 `importlib.import_module()` 动态导入。

## 当前整理状态

已补充至正式算法仓库目录。中间目录文件未删除。
