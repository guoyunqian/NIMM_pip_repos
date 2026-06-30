# orographic_temperature_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_temperature_downscaling` |
| 中文名称 | 气温降尺度(地形) |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\算法_王\improve\temperature` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、王亭波 |
| 建议算法分类 | `00space_downscale` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法以气温、地形高度、陆海掩膜和层结递减率为核心输入，完成两类主要任务：

- 使用邻域梯度法估计每个网格点的局地层结递减率。
- 基于源地形与目标地形的高度差，将层结递减率应用到温度场，实现地形订正和空间降尺度。

核心源码 `src/lapse_rate.py` 中提供：

- `compute_lapse_rate_adjustment`：根据层结递减率和地形高度差计算温度订正量。
- `LapseRate`：根据温度、地形和陆海掩膜估计层结递减率。
- `ApplyGriddedLapseRate`：将层结递减率应用到温度场进行地形订正。

原始目录中还包含 `src/feels_like_temperature.py` 及相关 CLI、文档和测试，该部分属于体感温度诊断能力，与本次算法名“气温降尺度(地形)”不完全一致，暂随原目录一并整理，后续建议单独拆分或明确归档策略。

## 本次整理操作

已将原始目录内容复制到中间目录：

`00temp/orographic_temperature_downscaling/`

复制内容包括：

- `src/`：核心算法源码。
- `cli/`：示例调度脚本。
- `docs/`：原始算法说明文档，并新增 `orographic_temperature_downscaling.md`。
- `nbs/`：notebook 示例。
- `test/`：pytest 测试脚本。
- `test_data/`：样例 `nc` 测试数据。
- `utils/`：原始工具函数。
- `resource/`：原始资源目录。

未执行操作：

- 未删除或移动任何原始文件。
- 未补充到正式 `NIMM/00space_downscale/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/orographic_temperature_downscaling/src/` | 核心算法源码 |
| `00temp/orographic_temperature_downscaling/cli/` | CLI 调度与示例脚本 |
| `00temp/orographic_temperature_downscaling/resource/` | 资源目录 |
| `00temp/orographic_temperature_downscaling/test/` | 单元测试 |
| `00temp/orographic_temperature_downscaling/test_data/` | 测试数据 |
| `00temp/orographic_temperature_downscaling/nbs/` | notebook 示例 |
| `00temp/orographic_temperature_downscaling/docs/` | 文档 |
| `00temp/orographic_temperature_downscaling/utils/` | 算法内部工具函数 |

## 已发现问题与后续建议

1. 原始代码导入路径仍使用 `temperature.src...` 和 `temperature.utils...`。当前中间目录保持原样，后续补充至正式仓库时需要统一调整为 `NIMM` 下的实际包路径。
2. `feels_like_temperature` 体感温度算法与本次气温地形降尺度主题不同，建议后续拆分成独立算法条目，分类可考虑 `02diagnostic` 或 `10weather_pheno`。
3. 当前未运行完整 pytest 测试。正式补充前应确认环境依赖，包括 `numpy`、`xarray`、`cf_units`、`meteva_base`、`pytest`。
4. `src/lapse_rate.py` 中 `LapseRate` 和 `ApplyGriddedLapseRate` 已提供类和 `process` 方法，符合插件式整理方向；但未继承仓库已有 `NIMM.utilities.base_plugin.BasePlugin`，后续可按仓库规范评估是否补充。
5. 测试数据体积和数量较多，正式入库时需确认哪些属于必要小样例，哪些应放入外部数据管理位置。

