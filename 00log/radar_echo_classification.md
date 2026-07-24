# radar_echo_classification 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `radar_echo_classification` |
| 中文名称 | 雷达回波分类 |
| 原始路径 | `D:\workspace\pyart_nimm\echo_class`（原包名 `echo_class`） |
| 路径说明 | 自原 QPE 目录拆出的独立模块 |
| 整理日期 | 2026-07-16（NIMM 标准化目录结构整理） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `01obs_adustment` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法从 Py-ART 回波分类逻辑迁移而来，面向雷达网格数据执行层状/对流分类、自适应特征识别与半监督水凝物分类。输入输出均为 `meteva_base.grid_data` 风格的 `xarray.DataArray`。

主要方法包括：

- `steiner_conv_strat`：Steiner 层状/对流分类。
- `feature_detection`：自适应特征识别。
- `hydroclass_semisupervised`：半监督水凝物分类。
- `conv_strat_raut`：Raut 小波层状/对流分类。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/radar_echo_classification/src/echo_class.py` | 四个插件类与分类算法函数 |
| `00temp/radar_echo_classification/src/utils/` | Steiner/特征、小波、水凝物、网格辅助 |
| `00temp/radar_echo_classification/cli/*_main.py` | 四个算法示例入口 |
| `00temp/radar_echo_classification/utils/` | 网格校验工具与本地 `BasePlugin` |
| `00temp/radar_echo_classification/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/radar_echo_classification/00temp/`、`00log/` | 中间数据与包内整理日志 |
| `00temp/radar_echo_classification/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-16 更新

- NIMM 标准化：自 `pyart_nimm/echo_class` 同步；导入统一为 `radar_echo_classification`。
- 未同步 `test_data/`；原目录测试通过；中间目录 pytest 13 passed, 4 skipped（缺样例 CLI）。
- 详细过程见：`00temp/radar_echo_classification/00log/echo_class_整理_20260716.log`。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/01obs_adustment/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. 测试样例在 `NIMM_pip_testdata/radar_echo_classification/`（体量较大，含 CLI 输入/输出），中间目录未同步；正式入库前筛选必要样例。
4. `resource/` 当前为空，正式补充时确认是否保留。
