# multi_rain_mait01_blending 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `multi_rain_mait01_blending` |
| 中文名称 | 逐小时多源自适应降水集成MAIT01 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\mait_1h` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、曹勇、陈荣 |
| 算法分类 | `05blending` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于 1 小时降水多源自适应集成。主流程读取多套模式 Micaps3 站点降水、实况站点降水和背景格点场，通过近 10 日同时效样本与当前前 1 小时样本计算局地 TS 权重，完成多模式站点融合和频率匹配订正，再通过 Cressman 插值、平滑、掩膜约束和格点频率匹配生成格点产品。

核心源码包括：

- `src/mait_1h_cli.py`
  - `process()`：算法主入口。
  - `RunProcess`：解析配置，逐起报、逐时效执行读数、质检、融合、插值和写出。
- `src/mait_1_plugin.py`
  - `AnalysisTsWeightProcess`：按空间子区计算 TS 动态权重，完成站点融合和频率匹配。
  - `StationDataInterp2GridDataProcess`：将融合站点结果插值到格点并做频率匹配。
  - `DataFlgProcess`：统计历史和当前模式数据可用性。
- `src/mait_1_plugin_util.py`
  - 历史样本读取、当前模式读取、背景格点读取、起报和实况时间换算。
- `utils/`
  - 配置解析、Micaps/NetCDF 写出、空间分析、多进程辅助等工具。

## 本次整理操作

已将原始目录内容复制到中间目录：

`00temp/multi_rain_mait01_blending/`

复制内容包括：

- `src/`：核心算法源码。
- `cli/`：命令行入口和验证脚本。
- `docs/`：原始算法说明文档，并新增 `multi_rain_mait01_blending.md`。
- `nbs/`：notebook 示例和图件。
- `resource/`：配置、站点、掩膜、HDF5 资源和示例图件。
- `test/`：测试脚本。
- `utils/`：原始工具函数。
- `test_data/`：原始目录未提供独立测试数据目录，本次新建空目录以匹配仓库整理结构。

未复制内容：

- `__pycache__/`
- `.ipynb_checkpoints/`
- `*.pyc`

未执行操作：

- 未删除或移动任何原始文件。
- 未补充到正式 `NIMM/05blending/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/multi_rain_mait01_blending/src/` | 核心算法源码 |
| `00temp/multi_rain_mait01_blending/cli/` | CLI 调度与验证脚本 |
| `00temp/multi_rain_mait01_blending/resource/` | 配置、站点、掩膜和业务资源 |
| `00temp/multi_rain_mait01_blending/test/` | 测试脚本 |
| `00temp/multi_rain_mait01_blending/test_data/` | 预留测试数据目录，原始目录未提供独立内容 |
| `00temp/multi_rain_mait01_blending/nbs/` | notebook 示例 |
| `00temp/multi_rain_mait01_blending/docs/` | 文档 |
| `00temp/multi_rain_mait01_blending/utils/` | 算法内部工具函数 |

## 已发现问题与后续建议

1. 原始代码导入路径仍使用本地 `src` 和 `utils` 包路径。当前中间目录保持原样，后续补充至正式仓库时需要统一调整为 `NIMM` 下的实际包路径。
2. 原始 `utils/` 中缺少 `mai_1_plugin_context.py` 源码，但多个源码文件依赖 `utils.mai_1_plugin_context`。同名源码位于 `cli/verify/mai_1_plugin_context.py`，后续需要人工确认是否复制或迁移到 `utils/`。
3. `resource/mait_1.ini` 指向 `resource/para_1_background.ini`，但原始 `resource/` 中未提供该文件；运行前需要补充背景场配置。
4. `resource/mait_1_sta_all.h5` 约 72 MB，正式入库前建议确认是否必须保留在算法资源目录。
5. 当前未运行完整 pytest 测试。正式补充前应确认环境依赖，包括 `numpy`、`pandas`、`meteva`、`meteva_base`、`clize`、`h5py` 或 PyTables 相关库。
6. 原始资源和测试脚本依赖外部业务路径、Micaps 文件和背景场文件，后续需要补充可复现的小样例数据或将不可复现实例标为人工验证项。

