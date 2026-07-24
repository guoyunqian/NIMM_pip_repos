# orographic_temperature_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_temperature_downscaling` |
| 中文名称 | 气温降尺度(地形) |
| 原始路径 | `D:\workspace\improver\temperature`（原包名 `temperature`） |
| 路径说明 | 体感温度相关内容已拆分至独立模块 `feels_like_temperature` |
| 整理日期 | 2026-06-29（初整）；2026-07-06（NIMM 标准化目录结构整理） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `00space_downscale` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法基于层结递减率和地形高度差进行气温空间降尺度与地形订正。面向 `meteva_base.grid_data` 风格输入输出。

核心源码 `src/lapse_rate.py` 提供：

- `LapseRate`：层结递减率计算。
- `ApplyGriddedLapseRate`：将递减率应用于格点温度场做地形订正。
- `compute_lapse_rate_adjustment`：递减率订正量计算。

CLI 包括 `cli/dsc_temp_lapse_rate.py`（递减率）与 `cli/anc_lapse_rate.py`（温度地形订正）。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/orographic_temperature_downscaling/src/lapse_rate.py` | 核心算法与插件 |
| `00temp/orographic_temperature_downscaling/cli/` | 递减率与地形订正 CLI |
| `00temp/orographic_temperature_downscaling/utils/` | 网格校验工具与本地 `BasePlugin` |
| `00temp/orographic_temperature_downscaling/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/orographic_temperature_downscaling/00temp/`、`00log/` | 中间数据与包内整理日志 |
| `00temp/orographic_temperature_downscaling/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-06 更新

- NIMM 标准化：自 `improver/temperature` 同步；体感温度内容已拆出。
- 导入路径由 `temperature` 统一为 `orographic_temperature_downscaling`。
- 原代码目录 pytest 全部通过（2026-07-06）。
- 详细过程见：`00temp/orographic_temperature_downscaling/00log/lapse_rate_整理_20260706.log`。

## 2026-06-29 更新

- 初整至中间目录；当时导入仍为原始 `temperature` 包名，后续由 2026-07-06 标准化更新。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/00space_downscale/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. 测试样例在 `NIMM_pip_testdata/orographic_temperature_downscaling/`，中间目录未同步；正式入库前确认必要样例范围。
4. `resource/` 当前为空，正式补充时确认是否保留。
