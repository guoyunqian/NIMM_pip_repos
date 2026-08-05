# regrid 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `regrid` |
| 中文名称 | 海陆感知重网格 |
| 原始路径 | `D:\workspace\improver\regrid`（原包名 `regrid`） |
| 整理日期 | 2026-07-30 初整；2026-08-05 增量同步 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `ancillaries` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

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

## 2026-07-30 整理

- 按 NIMM 标准从 improver/regrid 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 导入路径保持 `regrid`（包内绝对导入）；未改算法计算骨架。
- 未同步 `test_data/`（约 1.7MB、27 文件）；缺数据时相关用例会跳过；CLI 直跑缺样例时提示而不崩溃。
- improver 仅使用相对 `parents[2]/improver-1.18.7`；缺 improver 时与原版对比会跳过。
- 原算法目录 pytest：38 passed（improver venv）；中间目录 pytest：25 passed, 13 skipped（2026-07-30）。
- 详细过程见：`00temp/regrid/00log/regrid_整理_20260730.log`。

## 仍存在问题（需人工补充）

1. 迁入正式 `NIMM/ancillaries/` 时调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `test_data` 约 1.7MB，中间目录未同步；是否放入 `NIMM_pip_testdata` / 正式仓库需再定。
4. `resource/` 当前为空；正式入库时确认是否需要。

## 2026-08-05 增量同步

- 自 `D:\workspace\improver\regrid` 覆盖同步有差异文件；新增 `cli/preprocess_test_data.py`。
- 保留中间目录脚手架与 `docs/regrid_overview.md`；仍未同步 `test_data/`（约 1.78MB、27 文件）。
- CLI / 预处理脚本在缺样例时提示而不崩溃。
- 原目录 pytest：38 passed；中间目录：25 passed, 13 skipped（2026-08-05）。
