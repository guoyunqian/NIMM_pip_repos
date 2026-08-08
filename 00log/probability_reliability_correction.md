# probability_reliability_correction 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `probability_reliability_correction` |
| 中文名称 | 概率可靠性订正 |
| 原始路径 | `D:\workspace\improver\reliability_calibration`（原包名 `reliability_calibration`） |
| 整理日期 | 2026-08-08 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `07probability` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法用历史概率预报与阈值化实况构建可靠性表，经可选聚合与整理后，按表插值订正待发布概率场。面向 meb 六维网格与站点表；算法思想来自 Flowerdew (2014)。

核心能力包括：

- `ConstructReliabilityCalibrationTables`：历史概率预报 + 阈值化实况 → 可靠性表。
- `AggregateReliabilityCalibrationTables`：多表和/或指定坐标求和。
- `ManipulateReliabilityTable`：合并欠采样箱、强制观测频率单调。
- `ApplyReliabilityCalibration`：用可靠性表插值订正概率预报。
- CLI `cli/prb_*.py`、`cli/preprocess_test_data.py`：文件式示例与官方样例预处理。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/probability_reliability_correction/src/reliability_calibration.py` | 四插件编排 |
| `00temp/probability_reliability_correction/src/utils/` | 建表/整理/应用数值内核 |
| `00temp/probability_reliability_correction/cli/` | 四阶段 CLI 与预处理 |
| `00temp/probability_reliability_correction/utils/` | 本地 BasePlugin 与 meb 工具 |
| `00temp/probability_reliability_correction/test/`、`docs/`、`nbs/` | 测试、文档、notebook |
| `00temp/probability_reliability_correction/00temp/`、`00log/` | 中间数据约定与整理日志 |
| `00temp/probability_reliability_correction/NIMM_list.md` | 算法级整理清单 |

## 2026-08-08 整理

- 按 NIMM 标准从 improver/reliability_calibration 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 中间目录与导入包名定为 `probability_reliability_correction`。
- 未改算法计算骨架；未同步 `test_data/`（约 1.32MB、54 文件）；单元测试不依赖样例；CLI 直跑缺样例时提示而不崩溃。
- 原算法目录与中间目录 pytest：均为 18 passed（improver venv，2026-08-08）。
- 详细过程见：`00temp/probability_reliability_correction/00log/probability_reliability_correction_整理_20260808.log`。

## 仍存在问题（需人工补充）

1. 迁入正式 `NIMM/07probability/` 时调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `test_data` 约 1.32MB，中间目录未同步；是否放入 `NIMM_pip_testdata` / 正式仓库需再定。
4. `resource/` 当前为空；正式入库时确认是否需要。
