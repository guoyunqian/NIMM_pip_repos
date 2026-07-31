# dz_rescaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `dz_rescaling` |
| 中文名称 | 站点高差订正 |
| 原始路径 | `D:\workspace\improver\dz_rescaling`（原包名 `dz_rescaling`） |
| 整理日期 | 2026-07-31 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `04single_calibration` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法在模式格点高度与站点高度不一致时，用历史站点预报、实况与邻点高差拟合斜率，估计订正因子并乘到新站点预报上，减弱高度差引起的系统性偏差。I/O 为 meteva_base 站点表（`pandas.DataFrame`）。

核心能力包括：

- `EstimateDzRescaling`：由历史预报、实况与邻点高差估计 `scaled_vertical_displacement`。
- `ApplyDzRescaling`：将订正因子乘到待订正站点预报。
- CLI `cli/dsc_estimate_dz_rescaling.py`、`cli/dsc_apply_dz_rescaling.py`：文件式示例调度。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/dz_rescaling/src/dz_rescaling.py` | 核心算法插件 |
| `00temp/dz_rescaling/cli/` | 估计与应用 CLI 示例 |
| `00temp/dz_rescaling/utils/` | 本地 `BasePlugin` / `PostProcessingPlugin` |
| `00temp/dz_rescaling/test/`、`docs/`、`nbs/` | 测试、文档、notebook |
| `00temp/dz_rescaling/00temp/`、`00log/` | 中间数据约定与整理日志 |
| `00temp/dz_rescaling/NIMM_list.md` | 算法级整理清单 |

## 2026-07-31 整理

- 按 NIMM 标准从 improver/dz_rescaling 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 导入路径保持 `dz_rescaling`（包内绝对导入）；未改算法计算骨架。
- 未同步 `test_data/`（约 3.07MB、21 文件）；缺官方样例时 CLI 冒烟会跳过；CLI 直跑缺样例时提示而不崩溃。
- 原算法目录 pytest：27 passed（improver venv）；中间目录 pytest：26 passed, 1 skipped（2026-07-31）。
- 详细过程见：`00temp/dz_rescaling/00log/dz_rescaling_整理_20260731.log`。

## 仍存在问题（需人工补充）

1. 迁入正式 `NIMM/04single_calibration/` 时调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `test_data` 约 3.07MB，中间目录未同步；是否放入 `NIMM_pip_testdata` / 正式仓库需再定。
4. `resource/` 当前为空；正式入库时确认是否需要。
