# orographic_wind_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_wind_downscaling` |
| 中文名称 | 风降尺度(地形) |
| 原始路径 | `D:\workspace\improver\wind_calculations`（原包名 `wind_calculations`） |
| 路径说明 | 2026-06-29 初整曾基于汇总副本；2026-07-06 以本地 improver 目录为准完成 NIMM 标准化；2026-08-14 再从该原目录增量同步 |
| 整理日期 | 2026-06-29（初整）；2026-07-06（NIMM 标准化）；2026-08-14（原目录增量同步）；2026-08-21（中间目录说明清理） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `00space_downscale` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法用于风速空间降尺度。利用地形轮廓粗糙度、网格内地形高度标准差、目标地形与模式地形高度差，以及植被粗糙度长度，对风速进行粗糙度订正和高度订正。面向 `meteva_base.grid_data` 风格输入输出。

核心源码 `src/wind_downscaling.py` 提供：

- `FrictionVelocity`：基于对数风速廓线计算摩擦速度。
- `RoughnessCorrectionUtilities`：计算半峰谷高度、地形波数、参考高度，并执行粗糙度订正和高度订正。
- `RoughnessCorrection`：风速降尺度主插件，继承 `PostProcessingPlugin`；负责输入结构统一、空间维度校验、批量切片处理和输出重组。网格校验使用 `meb.checkout_griddata`。支持投影米制与真经纬分辨率推断（`EARTH_RADIUS_M`）。

CLI 入口 `cli/dsc_wind_downscaling.py` 读取风速、地形高度标准差、目标地形、标准地形、地形轮廓粗糙度和植被粗糙度等 NetCDF，调用 `RoughnessCorrection` 输出订正后的风速场。`cli/preprocess_test_data.py` 将官方投影样例预处理为方案一（投影维重命名）和方案二（经纬重网格）。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/orographic_wind_downscaling/src/wind_downscaling.py` | 核心算法与插件类 |
| `00temp/orographic_wind_downscaling/cli/dsc_wind_downscaling.py` | 文件式 CLI 调度 |
| `00temp/orographic_wind_downscaling/cli/preprocess_test_data.py` | 官方样例预处理（仅中间目录） |
| `00temp/orographic_wind_downscaling/utils/` | 网格校验工具与本地 `BasePlugin` / `PostProcessingPlugin` |
| `00temp/orographic_wind_downscaling/test/` | 单元测试与官方样例对照 |
| `00temp/orographic_wind_downscaling/docs/`、`nbs/` | 文档与 notebook |

## 2026-08-21 更新

- 正式入库提交已撤回，当前仍为中间目录整理状态。
- 保留 `docs/orographic_wind_downscaling.md`。
- 中间目录说明与 CLI 提示对齐原目录 `D:\workspace\improver\wind_calculations`：验证 notebook 统一为 `nbs/wind_calculations.ipynb`。
- 删除包内 `00log/`、`00temp/`、`NIMM_list.md`。

## 2026-08-14 更新

- 自 `improver/wind_calculations` 增量同步原目录后续修改：真经纬分辨率推断、`PostProcessingPlugin`、`meb.checkout_griddata`、预处理 CLI、新增测试与 notebook。
- 导入路径仍统一为中间目录模块名 `orographic_wind_downscaling`。
- 未同步 `test_data/`；CLI 缺样例时提示而不崩溃。
- 原目录 pytest：32 passed；中间目录 pytest：30 passed, 2 skipped（缺官方样例时对照测试 skip）。

## 2026-07-06 更新

- NIMM 标准化目录结构整理：自 `improver/wind_calculations` 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 导入路径由 `wind_calculations` 统一为中间目录模块名 `orographic_wind_downscaling`。
- `RoughnessCorrection` 已继承本地 `BasePlugin`。
- 原代码目录 pytest 全部通过（2026-07-06）。

## 2026-06-29 更新

- 初整：将算法复制到中间目录 `00temp/orographic_wind_downscaling/`。
- 当时导入路径仍保留原始 `wind_calculations` 包名，后续由 2026-07-06 标准化更新。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/00space_downscale/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `resource/` 当前为空，正式补充时确认是否保留。
4. `test_data/` 未同步；中间目录的官方对照测试缺数据时会 skip。
