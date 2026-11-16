# regrid 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `regrid` |
| 中文名称 | 海陆感知重网格 |
| 原始路径 | `D:\workspace\improver\regrid`（原包名 `regrid`） |
| 整理日期 | 2026-07-30 初整；2026-08-05 / 2026-08-17 增量同步 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `ancillaries` |
| 当前状态 | **已被 `grid_grid_fusion` 更名/合并取代**；`00temp/regrid` 已于 2026-11-16 删除；请用 `00temp/grid_grid_fusion`；本日志仅作历史记录 |

## 算法理解

该算法将源场重网格到目标空间网格，可选按海陆掩膜感知，避免陆点取海值、海点取陆值。面向 `xarray.DataArray` / meteva_base 六维网格。

核心能力包括：

- `RegridLandSea`：统一入口，按 `regrid_mode` 分派 scipy 路径或新版 `*-2` 路径。
- `AdjustLandSeaPoints`：最近邻后的海陆点匹配订正（`nearest-with-mask`）。
- `RegridWithLandSeaMask`：新版经纬度源网格上的最近邻 / 双线性（可选掩膜）。
- CLI `cli/tran_regrid.py`：文件式示例调度。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/regrid/src/landsea.py`、`landsea2.py` | 核心算法插件 |
| `00temp/regrid/cli/` | 重网格 CLI 示例 |
| `00temp/regrid/utils/` | 场校验工具与本地 `BasePlugin` |
| `00temp/regrid/test/`、`docs/`、`nbs/` | 测试、文档、notebook |
| `00temp/regrid/00temp/`、`00log/` | 中间数据约定与整理日志 |
| `00temp/regrid/NIMM_list.md` | 算法级整理清单 |

## 2026-11-16 更名/合并至 grid_grid_fusion，并删除中间目录

- 源侧能力已并入 `grid_grid_fusion`（`00temp/grid_grid_fusion`）。
- 类更名对照：

| 原 `regrid` | 新 `grid_grid_fusion` |
| --- | --- |
| `RegridLandSea` | `InterpGgLandSea` |
| `RegridWithLandSeaMask` | `InterpGgLandSea2` |
| `AdjustLandSeaPoints` | `AdjustLandSeaPoints`（保留，位于 landsea 插件） |

- **已删除** `00temp/regrid` 目录；同期删除被本包布局取代的 `00temp/interp_gg_linear`。
- 新工作应使用 `grid_grid_fusion`；详见 `00log/grid_grid_fusion.md`。

## 2026-08-17 增量同步

- 自 `D:\workspace\improver\regrid` 覆盖同步有差异文件：网格校验改用 `meb.checkout_griddata`，`rebuild_to_meb_griddata` 改用 `meb.set_griddata_attrs`。
- 保留中间目录脚手架与 `docs/regrid_overview.md`；仍未同步 `test_data/`（约 1.70MB、27 文件）。
- CLI / 预处理脚本在缺样例时提示而不崩溃。
- 原目录 pytest：38 passed；中间目录：25 passed, 13 skipped（2026-08-17）。
- 详细过程见：`00temp/regrid/00log/regrid_整理_20260817.log`。

## 2026-08-05 增量同步

- 自 `D:\workspace\improver\regrid` 覆盖同步有差异文件；新增 `cli/preprocess_test_data.py`。
- 保留中间目录脚手架与 `docs/regrid_overview.md`；仍未同步 `test_data/`（约 1.78MB、27 文件）。
- CLI / 预处理脚本在缺样例时提示而不崩溃。
- 原目录 pytest：38 passed；中间目录：25 passed, 13 skipped（2026-08-05）。

## 2026-09-28 更新

- 容器冒烟约定：`tran_regrid.main()` 默认使用 `resource/cli_input`；包根 `python -m cli regrid`。
- 写入最小样例（`global_cutout.nc`、`ukvx_grid.nc`）；仿真容器冒烟通过（依赖 `pyproj`/`cartopy`）。
- 包内文档补充子命令说明（示例路径未改）。

## 2026-07-30 整理

- 按 NIMM 标准从 improver/regrid 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 导入路径保持 `regrid`（包内绝对导入）；未改算法计算骨架。
- 未同步 `test_data/`（约 1.7MB、27 文件）；缺数据时相关用例会跳过；CLI 直跑缺样例时提示而不崩溃。
- improver 仅使用相对 `parents[2]/improver-1.18.7`；缺 improver 时与原版对比会跳过。
- 原算法目录 pytest：38 passed（improver venv）；中间目录 pytest：25 passed, 13 skipped（2026-07-30）。
- 详细过程见：`00temp/regrid/00log/regrid_整理_20260730.log`。

## 仍存在问题（需人工补充）

1. **中间目录已删除**；能力由 `grid_grid_fusion` 承接，正式路径应落在 `NIMM/08consistense/grid_grid_fusion`。
2. `frequency_matching_rain24` / `interp_sg_cressman` 背景对齐已改接 `grid_grid_fusion.InterpGgLinear`；Cressman 算法仍用独立包 `interp_sg_cressman`（与 `station_grid_fusion` 逐步订正版并存）。
