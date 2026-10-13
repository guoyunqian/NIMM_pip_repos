# radar_echo_classification 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `radar_echo_classification` |
| 中文名称 | 雷达回波分类 |
| 原始路径 | `D:\workspace\pyart_nimm\echo_class`（原包名 `echo_class`） |
| 路径说明 | 自原 QPE 目录拆出的独立模块 |
| 整理日期 | 2026-07-16（NIMM 标准化）；2026-10-13（增量同步） |
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
| `00temp/radar_echo_classification/utils/` | 本地 `BasePlugin` |
| `00temp/radar_echo_classification/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/radar_echo_classification/resource/` | 仅说明；样例未同步 |

## 2026-10-13 更新

- 任务一再次整理 `D:\workspace\pyart_nimm\echo_class`。路径此前已归入 `00temp/radar_echo_classification/`，本次为增量同步，未新建第二套中间目录，未修改原目录。
- 同步内容：
  - `src/echo_class.py`、`src/utils/_grid_utils.py`：改用 `meb`，去掉本地 `utils/utils.py` 依赖。
  - CLI、测试、`docs/echo_class.md`、`nbs/echo_class.ipynb` 与原目录对齐；导入统一为 `radar_echo_classification`。
- 按用户要求删除包内脚手架：`00log/`、`00temp/`、`NIMM_list.md`、`.gitignore`。
- 删除中间目录多余的 `utils/utils.py`（原目录已无）。
- 未拷贝 `test_data/`；`resource/` 仅放说明；保留并更新中文概述 `docs/雷达回波分类.md`。
- 中间目录 pytest：**15 passed / 4 skipped**（CLI 缺样例 skip）。
- 贡献人未修改：郭云谦、王亭波。

## 2026-07-16 更新

- NIMM 标准化：自 `pyart_nimm/echo_class` 同步；导入统一为 `radar_echo_classification`。
- 未同步 `test_data/`；原目录测试通过；中间目录 pytest 13 passed, 4 skipped（缺样例 CLI）。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/01obs_adustment/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. 测试样例在 `NIMM_pip_testdata` / 原目录（体量较大），中间目录未同步；正式入库前筛选必要样例。
4. `resource/` 仅有说明文件，无雷达样例。
