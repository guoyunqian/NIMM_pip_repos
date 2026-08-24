# threshold_probability_conversion 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `threshold_probability_conversion` |
| 中文名称 | 阈值概率转换 |
| 原始路径 | `D:\workspace\improver\threshold`（原包名 `threshold`） |
| 整理日期 | 2026-08-24 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `07probability` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法把诊断场转为相对阈值的 0～1 真值/概率场。硬阈值得到 0/1；fuzzy 在阈值附近线性过渡。面向 `meteva_base` 六维网格（阈值写入 `level`）与 `numpy.ndarray`。

核心源码包括：

- `src/threshold.py`
  - `Threshold`：硬阈值 / fuzzy、多阈值、单位换算、`fill_masked`、`collapse_coord`、`vicinity`。
- `src/utils/`
  - 比较符、线性重标定、等面积格距推断、方形邻域最大值。
- 邻域格距依赖中间目录 `neighbourhood_probability_processing`（原目录依赖 `nbhood`）。

CLI 入口包括：

- `cli/prb_threshold.py`：文件式阈值概率转换。
- `cli/preprocess_test_data.py`：官方 Iris/投影样例预处理为 meb。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/threshold_probability_conversion/src/threshold.py` | 阈值概率转换主插件 |
| `00temp/threshold_probability_conversion/src/utils/` | 比较符、重标定、格距与 vicinity |
| `00temp/threshold_probability_conversion/cli/` | 业务 CLI 与官方样例预处理 |
| `00temp/threshold_probability_conversion/utils/` | 本地 `BasePlugin` |
| `00temp/threshold_probability_conversion/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |

## 2026-08-24 更新

- 从 `D:\workspace\improver\threshold` 首次整理至中间目录：
  - 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
  - 导入统一为 `threshold_probability_conversion`；`nbhood` 依赖改为 `neighbourhood_probability_processing`。
- 未同步 `test_data/`（约 5.88MB、32 文件）；CLI / 预处理缺样例时提示而不崩溃。
- 官方对照缺 `test_data` 时 skip（原测试已有 skipif）。
- 原目录没有 `utils/utils.py`，中间目录不另建。
- 原目录 pytest：41 passed；中间目录 pytest：27 passed, 14 skipped（2026-08-24；缺 test_data 时官方对照 skip）。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/07probability/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `test_data` 样例约 5.88MB（32 文件），中间目录未同步；是否纳入 `NIMM_pip_testdata` / 正式仓库后续决定。
4. `resource/` 当前为空，正式补充时确认是否保留。
5. vicinity 格距依赖同级中间目录 `neighbourhood_probability_processing`；正式入库时需改为仓库正式包路径。
