# linear_scd_multi_time_fusion 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `linear_scd_multi_time_fusion` |
| 中文名称 | 线性SCD多时效融合 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\nimm_scd` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、丰硕 |
| 算法分类 | `05mulit_integrate` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法面向短临降水与模式降水产品的多时效无缝融合。核心流程先将 `unet_qpf` 与 `mait_st` 产品拆分到统一的 0.01 度、10 分钟网格，再按时效配置对两个来源进行线性融合或显著性融合，并支持用实况和 `mait_st` 产品对融合结果前后时段进行补齐。

核心源码包括：

- `src/qpf_split_plugin.py`：提供 `QpfSplitPlugin`，封装短临与模式降水 10 分钟拆分流程。
- `src/scd_fusion_plugin.py`：提供 `ScdFusionPlugin`，封装 SCD 双源融合流程。
- `src/linear_blending.py`：提供 `linear_blending_forecast` 和显著性图计算，是融合的核心数值算法。
- `src/split_workflow.py`：读取 `unet_qpf`、`mait_st`，完成重叠区域插值和时间拆分。
- `src/pair_fusion_workflow.py`：按配置配对拆分后的两个来源文件，并按关键时效权重输出融合产品。
- `src/padding_workflow.py`：对融合输出进行起报前和融合尾段补齐。

## 本次整理操作

已将原始目录内容整理到中间目录：

`00temp/linear_scd_multi_time_fusion/`

整理内容包括：

- `src/`：核心算法、拆分流程、融合流程和补齐流程源码。
- `cli/`：时间拆分、SCD 融合和结果补齐命令行入口。
- `docs/`：原始 `scd_algorithm.md`，并新增 `linear_scd_multi_time_fusion.md`。
- `resource/`：拆分和融合默认配置模板。
- `test/`：线性融合最小单元测试。
- `nbs/`：SCD demo notebook。
- `utils/`：原始工具目录，目前仅包含初始化文件。
- `test_data/README.md`：说明原始目录未提供独立小样例测试数据。

未执行操作：

- 未删除或移动任何原始文件。
- 未复制 `.venv`、`.idea`、`__pycache__`、`.pyc` 和 `.ipynb_checkpoints` 缓存或环境目录。
- 未补充到正式 `NIMM/05mulit_integrate/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/linear_scd_multi_time_fusion/src/` | 核心算法源码 |
| `00temp/linear_scd_multi_time_fusion/cli/` | CLI 调度入口 |
| `00temp/linear_scd_multi_time_fusion/resource/` | 默认配置模板 |
| `00temp/linear_scd_multi_time_fusion/test/` | 最小单元测试 |
| `00temp/linear_scd_multi_time_fusion/test_data/` | 测试数据说明，待补充业务小样例 |
| `00temp/linear_scd_multi_time_fusion/nbs/` | notebook 示例 |
| `00temp/linear_scd_multi_time_fusion/docs/` | 文档 |
| `00temp/linear_scd_multi_time_fusion/utils/` | 工具目录 |

## 已发现问题与后续建议

1. 中间目录名称为 `linear_scd_multi_time_fusion`，但原始代码导入路径仍使用 `nimm_scd.src` 和 `nimm_scd.cli`，正式补充至算法仓库时需要统一包名或调整导入路径。
2. 默认配置文件保留生产路径，例如 `/data/data_215/unet_qpf`、`/data/data_84/rain01/mait_st/sfc` 和 `/data/mnt/GUO_data/scd_data/...`，离线测试前需要替换为本地样例路径。
3. `resource/scd_pair_fusion_config.ini` 当前 `dry_run = false`，直接运行会写出融合结果，建议测试时先启用 dry run 或使用临时输出目录。
4. 原始目录未提供独立小体量 NetCDF、MICAPS4 和实况样例数据，当前无法验证完整拆分、融合和补齐业务流程。
5. 依赖包括 `numpy`、`scipy`、`h5py`、`xarray` 和 `pytest`；正式入库前需要确认运行环境依赖。

## 校验记录

- 已完成中间目录复制和缓存文件清理。
- 已补充算法说明文档和测试数据说明。
- 已使用 Codex 捆绑 Python 完成 16 个 Python 文件的语法解析校验。
- 尝试执行 `linear_blending_forecast` 最小断言时，当前 Codex 捆绑 Python 环境缺少 `scipy`，未能运行到数值断言；正式测试前需补齐 `scipy` 等依赖。
