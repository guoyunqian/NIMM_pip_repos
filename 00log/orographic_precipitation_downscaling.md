# orographic_precipitation_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_precipitation_downscaling` |
| 中文名称 | 降水降尺度(地形) |
| 原始路径 | `D:\workspace\improver\orographic_enhancement`（原包名 `orographic_enhancement`） |
| 整理日期 | 2026-06-29（初整）；2026-07-06（NIMM 标准化目录结构整理） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `00space_downscale` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法用于降水地形降尺度和地形增强订正，核心思想是利用温湿压、风场和地形高度计算地形抬升导致的降水增强项，并支持将增强项叠加或扣除到降水场。

核心源码包括：

- `src/orographic_enhancement.py`
  - `ResolveWindComponents`：将风速和风向解析为目标网格坐标系下的 `u/v` 风分量。
  - `MetaOrographicEnhancement`：从多层气象场提取边界层代表高度，组织地形增强计算流程。
  - `OrographicEnhancement`：计算迎风抬升项、地形增强格点贡献和上游贡献，输出地形增强结果。
- `src/apply_orographic_enhancement.py`
  - `ApplyOrographicEnhancement`：将地形增强项以 `add` 或 `subtract` 模式应用到降水场，并处理时间匹配和最小降水率保护。
- `src/utils/`
  - 网格处理、数值计算、饱和水汽压等内部辅助函数。

CLI 入口 `cli/dsc_orographic_enhancement.py` 读取温度、相对湿度、气压、风速、风向和地形 `nc` 文件，调用 `MetaOrographicEnhancement` 输出地形增强项。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/orographic_precipitation_downscaling/src/orographic_enhancement.py` | 核心增强算法 |
| `00temp/orographic_precipitation_downscaling/src/apply_orographic_enhancement.py` | 增强项应用 |
| `00temp/orographic_precipitation_downscaling/src/utils/` | 网格、数值与水汽辅助 |
| `00temp/orographic_precipitation_downscaling/cli/` | CLI 调度 |
| `00temp/orographic_precipitation_downscaling/utils/` | 网格校验工具与本地 `BasePlugin` |
| `00temp/orographic_precipitation_downscaling/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/orographic_precipitation_downscaling/00temp/`、`00log/` | 中间数据与包内整理日志 |
| `00temp/orographic_precipitation_downscaling/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-06 更新

- NIMM 标准化：自 improver 重新同步源码与文档；导入统一为 `orographic_precipitation_downscaling`。
- 原代码目录 pytest 全部通过（2026-07-06）。
- 详细过程见：`00temp/orographic_precipitation_downscaling/00log/orographic_enhancement_整理_20260706.log`。

## 2026-06-29 更新

- 初整至中间目录；当时导入仍为原始 `orographic_enhancement` 包名。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/00space_downscale/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. 测试样例在 `NIMM_pip_testdata/orographic_precipitation_downscaling/`（含 CLI 输出对照），中间目录未同步；正式入库前筛选必要样例。
4. `resource/` 当前为空，正式补充时确认是否保留。
