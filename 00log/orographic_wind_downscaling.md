# orographic_wind_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_wind_downscaling` |
| 中文名称 | 风降尺度(地形) |
| 原始路径 | `D:\workspace\improver\wind_calculations`（原包名 `wind_calculations`） |
| 路径说明 | 2026-06-29 初整曾基于汇总副本；2026-07-06 以本地 improver 目录为准完成 NIMM 标准化 |
| 整理日期 | 2026-06-29（初整）；2026-07-06（NIMM 标准化目录结构整理） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `00space_downscale` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法用于风速空间降尺度。利用地形轮廓粗糙度、网格内地形高度标准差、目标地形与模式地形高度差，以及植被粗糙度长度，对风速进行粗糙度订正和高度订正。面向 `meteva_base.grid_data` 风格输入输出。

核心源码 `src/wind_downscaling.py` 提供：

- `FrictionVelocity`：基于对数风速廓线计算摩擦速度。
- `RoughnessCorrectionUtilities`：计算半峰谷高度、地形波数、参考高度，并执行粗糙度订正和高度订正。
- `RoughnessCorrection`：风速降尺度主插件，负责输入结构统一、空间维度校验、批量切片处理和输出重组。

CLI 入口 `cli/dsc_wind_downscaling.py` 读取风速、地形高度标准差、目标地形、标准地形、地形轮廓粗糙度和植被粗糙度等 NetCDF，调用 `RoughnessCorrection` 输出订正后的风速场。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/orographic_wind_downscaling/src/wind_downscaling.py` | 核心算法与插件类 |
| `00temp/orographic_wind_downscaling/cli/dsc_wind_downscaling.py` | 文件式 CLI 调度 |
| `00temp/orographic_wind_downscaling/utils/` | 网格校验工具与本地 `BasePlugin` |
| `00temp/orographic_wind_downscaling/test/` | 单元测试与官方样例对照 |
| `00temp/orographic_wind_downscaling/docs/`、`nbs/` | 文档与 notebook |
| `00temp/orographic_wind_downscaling/00temp/` | 整理过程中间数据（`wind_downscaling/`） |
| `00temp/orographic_wind_downscaling/00log/` | 整理过程日志（一次整理一份） |
| `00temp/orographic_wind_downscaling/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-06 更新

- NIMM 标准化目录结构整理：自 `improver/wind_calculations` 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 导入路径由 `wind_calculations` 统一为中间目录模块名 `orographic_wind_downscaling`。
- `RoughnessCorrection` 已继承本地 `BasePlugin`；建立算法内 `00log/`、`00temp/`、`NIMM_list.md`、`.gitignore`。
- 原代码目录 pytest 全部通过（2026-07-06）。
- 详细过程见：`00temp/orographic_wind_downscaling/00log/wind_downscaling_整理_20260706.log`。

## 2026-06-29 更新

- 初整：将算法复制到中间目录 `00temp/orographic_wind_downscaling/`。
- 当时导入路径仍保留原始 `wind_calculations` 包名，后续由 2026-07-06 标准化更新。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/00space_downscale/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `resource/` 当前为空，正式补充时确认是否保留。
