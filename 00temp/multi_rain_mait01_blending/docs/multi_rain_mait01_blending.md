# multi_rain_mait01_blending

## 算法概述

`multi_rain_mait01_blending` 对应“逐小时多源自适应降水集成 MAIT01”。算法用于 1 小时降水多源/多模式融合，核心流程是读取多套模式站点降水预报和实况样本，按空间分区动态计算 TS 权重，完成站点级线性融合与频率匹配订正，再经 Cressman 插值和掩膜约束生成格点产品。

## 算法分类

- 分类：`05blending`
- 分类依据：算法核心是多源、多模式降水融合和自适应权重集成。

## 主要能力

- 支持多个起报时间 `time_inputs` 批处理。
- 支持逐小时预报时效循环，默认 `1-48 h`。
- 基于近 10 日同时效样本和当前前 1 小时样本计算 TS 动态权重。
- 支持按 `split_lat` 和 `split_lon` 子区计算局地权重。
- 支持 Micaps3 站点产品输出。
- 支持站点融合结果到格点产品的 Cressman 插值、平滑、频率匹配和掩膜裁剪。
- 支持 Micaps4 与 NetCDF 格点产品写出。

## 主要文件

| 类型 | 文件 | 说明 |
| --- | --- | --- |
| 主入口 | `src/mait_1h_cli.py` | `process()`、`RunProcess` 和 Clize CLI 入口 |
| 核心算法 | `src/mait_1_plugin.py` | TS 权重融合、站点到格点插值、数据可用性判断 |
| 数据读取 | `src/mait_1_plugin_util.py` | 历史样本、当前模式、背景场读取和时间处理 |
| CLI | `cli/__main__.py` | `python -m cli` 转发入口 |
| 配置 | `resource/mait_1.ini` | 默认路径、时效、多进程和网格划分参数 |
| 配置/资源 | `resource/para.ini`、`resource/sta.info`、`resource/mask010.dat` | 模式路径、站点表和插值掩膜 |
| 文档 | `docs/MAIT_1H_程序说明.md` | 原始程序说明 |
| Notebook | `nbs/mait_1h_说明.ipynb` | 示例说明和检验对比 |
| 测试 | `test/` | 运行上下文、业务样例和对比测试脚本 |

## 输入输出

输入：

- 多模式 Micaps3 站点 1 小时降水预报。
- 实况 Micaps3 站点降水。
- 背景 Micaps4 或 NetCDF 格点场。
- 站点表、服务区掩膜、模式路径配置和背景路径配置。

输出：

- 融合后的 Micaps3 站点降水产品。
- 插值订正后的 Micaps4 和 NetCDF 格点降水产品。

## 当前整理状态

当前阶段为原始算法整理至中间目录，尚未补充到正式算法仓库目录。

已完成：

- 原始源码、CLI、文档、notebook、测试脚本、资源文件复制到 `00temp/multi_rain_mait01_blending/`。
- 跳过运行缓存目录和文件：`__pycache__`、`.ipynb_checkpoints`、`*.pyc`。
- 新建空 `test_data/` 目录，并记录原始目录未提供独立 `test_data`。
- 保留原始代码逻辑和原始包导入路径。

待处理：

- 原始 `utils/` 中缺少 `mai_1_plugin_context.py` 源码，但 `src/mait_1h_cli.py`、`src/mait_1_plugin.py`、`src/mait_1_plugin_util.py` 和 `utils/util_new.py` 均依赖该模块；同名源码位于 `cli/verify/mai_1_plugin_context.py`，后续需要确认是否补回 `utils/`。
- `resource/mait_1.ini` 指向 `resource/para_1_background.ini`，但原始资源目录未提供该文件。
- `resource/mait_1_sta_all.h5` 约 72 MB，正式入库前建议确认是否作为必要资源保留。
- 正式补充到算法仓库时需要统一导入路径，并确认 `meteva`、`meteva_base`、`clize`、`pandas`、`numpy` 等依赖。

