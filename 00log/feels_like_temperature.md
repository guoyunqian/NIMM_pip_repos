# feels_like_temperature 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `feels_like_temperature` |
| 中文名称 | 体感温度 |
| 原始路径 | `D:\workspace\improver\feels_like_temperature`（原包名 `feels_like_temperature`） |
| 路径说明 | 2026-07-06 以本地 improver 目录为准完成 NIMM 标准化；2026-08-17 再从该原目录增量同步 |
| 整理日期 | 2026-07-06（NIMM 标准化）；2026-08-17（原目录增量同步） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `02diagnostic` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法根据气温、10 米风速、相对湿度和气压，综合风寒与显温计算体感温度诊断场。面向 `meteva_base.grid_data` 风格输入输出。

核心能力包括：

- `CalculateWindChill` / 风寒计算。
- `calculate_feels_like_temperature`：融合风寒与显温得到体感温度。
- CLI `cli/der_feel_like_temp.py`：文件式示例调度。`cli/preprocess_test_data.py` 将官方投影样例预处理为方案一（投影维重命名）和方案二（经纬重网格）。网格校验使用 `meb.checkout_griddata`。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/feels_like_temperature/src/feels_like_temperature.py` | 核心算法与插件 |
| `00temp/feels_like_temperature/src/utils/` | 饱和水汽压、风寒、显温及融合逻辑 |
| `00temp/feels_like_temperature/cli/der_feel_like_temp.py` | CLI 调度 |
| `00temp/feels_like_temperature/cli/preprocess_test_data.py` | 官方样例预处理（仅中间目录） |
| `00temp/feels_like_temperature/utils/` | 网格校验工具与本地 `BasePlugin` |
| `00temp/feels_like_temperature/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/feels_like_temperature/00temp/`、`00log/` | 中间数据与包内整理日志 |
| `00temp/feels_like_temperature/NIMM_list.md` | 算法包内整理清单 |

## 2026-08-17 更新

- 自 `improver/feels_like_temperature` 增量同步原目录后续修改：`meb.checkout_griddata`、预处理 CLI、`PostProcessingPlugin` 对齐。
- 导入路径仍统一为中间目录模块名 `feels_like_temperature`。
- 未同步 `test_data/`；CLI 缺样例时提示而不崩溃。
- 原目录 pytest：14 passed；中间目录 pytest：12 passed, 2 skipped（缺官方样例时对照测试 skip）。
- 详细过程见：`00temp/feels_like_temperature/00log/feels_like_temperature_整理_20260817.log`。

## 2026-07-06 更新

- NIMM 标准化：自 improver 独立模块同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 导入路径统一为 `feels_like_temperature`；建立算法内脚手架。
- 原代码目录 pytest 全部通过（2026-07-06）。
- 详细过程见：`00temp/feels_like_temperature/00log/feels_like_temperature_整理_20260706.log`。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/02diagnostic/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `resource/` 当前为空，正式补充时确认是否保留。
4. `test_data/` 未同步；中间目录的官方对照测试缺数据时会 skip。
