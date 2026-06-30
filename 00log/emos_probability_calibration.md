# emos_probability_calibration 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `emos_probability_calibration` |
| 中文名称 | emos概率订正 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\emos` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `07probability` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于集合预报的 EMOS 概率订正，主要面向站点维度 `spot_index` 的 xarray 数据。核心流程包括：

- 使用历史集合预报、实况和可选附加预测因子训练 EMOS 系数。
- 通过 CRPS 最小化优化正态或截断正态分布参数。
- 使用训练系数对当前预报生成订正后的分布参数。
- 根据输入和模板输出集合、概率或分位数结果。

核心源码 `src/emos_calibration.py` 中提供：

- `ContinuousRankedProbabilityScoreMinimisers`：CRPS 最小化器。
- `EstimateCoefficientsForEnsembleCalibration`：EMOS 系数训练插件。
- `CalibratedForecastDistributionParameters`：根据系数和预报生成订正分布参数。
- `ApplyEMOS`：应用 EMOS 订正并生成目标输出类型。

## 本次整理操作

已将原始目录内容复制到中间目录：

`00temp/emos_probability_calibration/`

复制内容包括：

- `src/`：核心算法源码。
- `utils/`：概率、分位数、ECC 和 xarray 工具函数。
- `test/`：原始 demo 脚本。
- `test_data/`：样例 `nc` 测试数据。

新增内容包括：

- `cli/emos_probability_calibration_main.py`：最小训练和应用调度脚本。
- `nbs/emos_probability_calibration_example.py`：样例数据训练和应用示例。
- `docs/emos_probability_calibration.md`：算法整理说明文档。
- `resource/`：按仓库结构补齐的资源目录。

未执行操作：

- 未删除或移动任何原始文件。
- 未复制 `__pycache__` 和 `.pyc` 编译缓存。
- 未补充到正式 `NIMM/07probability/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/emos_probability_calibration/src/` | 核心算法源码 |
| `00temp/emos_probability_calibration/cli/` | CLI 调度与示例脚本 |
| `00temp/emos_probability_calibration/resource/` | 资源目录 |
| `00temp/emos_probability_calibration/test/` | 测试或 demo 脚本 |
| `00temp/emos_probability_calibration/test_data/` | 测试数据 |
| `00temp/emos_probability_calibration/nbs/` | 示例脚本 |
| `00temp/emos_probability_calibration/docs/` | 文档 |
| `00temp/emos_probability_calibration/utils/` | 算法内部工具函数 |

## 已发现问题与后续建议

1. 原始代码导入路径仍使用 `src...` 和 `utils...`。当前中间目录保持原样，后续补充至正式仓库时需要统一调整为 `NIMM` 下的实际包路径。
2. 原始 `test/run_demo.py` 依赖 `iris`、`improver` 进行对照验证，当前环境未确认这些依赖是否可用。
3. 算法说明中标注为 spot-only，不支持 gridded x/y domains，正式文档需要明确适用范围。
4. 当前未运行完整测试。正式补充前应确认环境依赖，包括 `numpy`、`xarray`、`scipy`、`statsmodels`，以及对照测试所需的 `iris`、`improver`。
5. 新增 CLI 是中间整理阶段的薄包装，后续入库时应根据仓库统一 CLI 规范继续调整参数和导入路径。

