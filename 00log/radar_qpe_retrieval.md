# radar_qpe_retrieval 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `radar_qpe_retrieval` |
| 中文名称 | 雷达降水定量反演QPE |
| 原始路径 | `D:\workspace\pyart_nimm\qpe`（原包名 `qpe`） |
| 路径说明 | 原目录曾含回波分类，已拆分为独立模块 `radar_echo_classification` |
| 整理日期 | 2026-06-29（初整）；2026-07-13（NIMM 标准化）；2026-07-17（文档路径再同步） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `01obs_adustment` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法基于雷达反射率、KDP、比衰减和水凝物分类等网格数据，使用 Z-R、KDP-R、A-R、融合和水凝物分类等方法估算降水率。面向 `meteva_base.grid_data` 风格输入输出。

核心能力包括：

- `QPEPlugin` 与多类 `EstimateRainRate*` / `est_rain_rate_*` 入口。
- CLI `cli/qpe.py` 统一调度；`cinrad_*` 辅助读数与预处理。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/radar_qpe_retrieval/src/qpe.py` | QPE 核心算法与插件 |
| `00temp/radar_qpe_retrieval/src/utils/` | 频率关系等辅助 |
| `00temp/radar_qpe_retrieval/cli/` | QPE CLI 与 CINRAD 辅助 |
| `00temp/radar_qpe_retrieval/utils/` | 网格校验与本地插件基类 |
| `00temp/radar_qpe_retrieval/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/radar_qpe_retrieval/00temp/`、`00log/` | 中间数据与包内整理日志 |
| `00temp/radar_qpe_retrieval/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-17 更新

- 自原目录再同步 `docs/qpe.md`，并统一中间目录模块路径表述。

## 2026-07-13 更新

- NIMM 标准化：自 `pyart_nimm/qpe` 同步；导入统一为 `radar_qpe_retrieval`；移除已拆出的 echo_class。
- 未同步 `test_data/`；原目录测试通过；中间目录 pytest 32 passed, 6 skipped（缺样例 CLI）。
- 详细过程见：`00temp/radar_qpe_retrieval/00log/qpe_整理_20260713.log`。

## 2026-06-29 更新

- 初整至中间目录；当时仍混有回波分类等内容。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/01obs_adustment/` 时需调整为仓库正式包路径。
2. `PostProcessingPlugin` / 基类正式入库时评估是否改为仓库统一基类。
3. 测试样例在 `NIMM_pip_testdata/radar_qpe_retrieval/`（体量较大，含 CLI 输出），中间目录未同步；正式入库前筛选必要样例。
4. `resource/` 当前为空，正式补充时确认是否保留。
