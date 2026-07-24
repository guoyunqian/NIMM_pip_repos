# neighbourhood_probability_processing 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `neighbourhood_probability_processing` |
| 中文名称 | 邻域(nbhood)处理及概率生成 |
| 原始路径 | `D:\workspace\improver\nbhood`（原包名 `nbhood`） |
| 整理日期 | 2026-06-29（初整）；2026-07-09（NIMM 标准化目录结构整理） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `07probability` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法用于集合/概率预报后处理中的邻域统计和概率生成，主要围绕空间邻域平均、邻域求和、圆形核百分位、外部掩码、陆海分区和地形带分层处理展开。

核心源码包括：

- `src/nbhood.py`
  - `NeighbourhoodProcessing`：执行方形或圆形邻域处理，支持邻域平均、邻域和、外部掩码和可变半径。
  - `GeneratePercentilesFromANeighbourhood`：在圆形邻域内生成百分位结果。
  - `BaseNeighbourhoodProcessing`：公共半径、时效和输入校验逻辑。
  - `circular_kernel`、`check_radius_against_distance` 等邻域工具函数。
- `src/use_nbhood.py`
  - `ApplyNeighbourhoodProcessingWithAMask`：按掩码分层逐层执行邻域处理，并支持按权重折叠。
- `src/utils/`
  - 提供 `radius_by_lead_time`、角度复数转换和 halo 裁剪等辅助工具（原 `meta_nbhood_utils` 已拆入此目录）。

CLI 入口包括：

- `cli/ens_nbhood.py`：普通邻域概率和邻域百分位。
- `cli/ens_nbhood_iterate_with_mask.py`：按分层掩码迭代处理。
- `cli/ens_nbhood_land_and_sea.py`：陆海/地形带分区邻域处理并合并输出。
- `cli/io.py`：掩码/权重 NetCDF 读取辅助。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/neighbourhood_probability_processing/src/nbhood.py` | 邻域概率与百分位 |
| `00temp/neighbourhood_probability_processing/src/use_nbhood.py` | 掩码邻域处理 |
| `00temp/neighbourhood_probability_processing/src/utils/` | 网格、核与重网格辅助 |
| `00temp/neighbourhood_probability_processing/cli/` | 三类 CLI 与 `io.py` |
| `00temp/neighbourhood_probability_processing/utils/` | 网格校验工具与本地 `BasePlugin` |
| `00temp/neighbourhood_probability_processing/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/neighbourhood_probability_processing/00temp/`、`00log/` | 中间数据与包内整理日志 |
| `00temp/neighbourhood_probability_processing/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-09 更新

- NIMM 标准化：自 `improver/nbhood` 同步；导入统一为 `neighbourhood_probability_processing`。
- 未同步 `test_data/`（样例独立管理）；原代码目录 pytest 全部通过（2026-07-09）。
- 详细过程见：`00temp/neighbourhood_probability_processing/00log/nbhood_整理_20260709.log`。

## 2026-06-29 更新

- 初整至中间目录；当时导入仍为原始 `nbhood` 包名。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/07probability/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. 测试样例在 `NIMM_pip_testdata/neighbourhood_probability_processing/`（含多组 CLI 输出），中间目录未同步；正式入库前筛选必要样例。
4. `resource/` 当前为空，正式补充时确认是否保留。
