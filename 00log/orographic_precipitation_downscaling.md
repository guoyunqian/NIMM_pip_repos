# orographic_precipitation_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_precipitation_downscaling` |
| 中文名称 | 降水降尺度(地形) |
| 原始路径 | `D:\workspace\improver\orographic_enhancement`（原包名 `orographic_enhancement`） |
| 整理日期 | 2026-06-29（初整）；2026-07-06（NIMM 标准化）；2026-08-18（增量同步）；2026-08-19（正式归档） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `00space_downscale` |
| 当前状态 | 已补充至正式算法仓库目录 |

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

## 2026-06-29 更新

- 初整至中间目录；当时导入仍为原始 `orographic_enhancement` 包名。

## 2026-07-06 更新

- NIMM 标准化：自 improver 重新同步源码与文档；导入统一为 `orographic_precipitation_downscaling`。
- 原代码目录 pytest 全部通过（2026-07-06）。
- 详细过程见：`00temp/orographic_precipitation_downscaling/00log/orographic_enhancement_整理_20260706.log`。

## 2026-08-18 更新

- 从 `D:\workspace\improver\orographic_enhancement` 完整同步最新修改：
  - `src/orographic_enhancement.py`：改用 `meb.checkout_griddata()` 直接调用，移除本地封装函数 `check_for_meb_griddata()` / `check_for_xy_coordinates()`。
  - `src/apply_orographic_enhancement.py`：同步改用 `meb.checkout_griddata()` 进行网格数据校验。
  - `cli/dsc_orographic_enhancement.py`：同步改用 `meb.checkout_griddata()` 直接调用。
  - 补齐 `cli/preprocess_test_data.py`（官方投影样例预处理脚本）。
  - `test/test_orographic_enhancement.py`：同步最新测试用例。
  - `docs/orographic_enhancement.md`：同步最新文档说明。
  - `nbs/orographic_enhancement_validation.ipynb`：同步最新验证 notebook。
  - `utils/base_plugin.py`、`utils/utils.py`：同步最新工具函数。

## 2026-08-19 正式归档

已将中间目录 `00temp/orographic_precipitation_downscaling/` 复制补充到正式算法仓库，未删除中间目录文件。

本次操作包括：

- 核心源码归档到 `NIMM/00space_downscale/orographic_precipitation_downscaling/`，包内改为相对导入。
- CLI 归档到 `cli/00space_downscale/orographic_precipitation_downscaling/`，命名为 `dsc_orographic_enhancement_main.py`。官方样例预处理脚本不进入正式 `cli/`，仍保留在中间目录。
- 测试、文档、notebook、资源说明归档到对应分类目录。
- 因分类目录以数字开头，CLI 与测试使用 `importlib.import_module()` 动态导入。
- 在 src 与 cli 中补充算法贡献人（郭云谦、王亭波）和软件产权说明。
- 正式目录 pytest：8 passed, 1 skipped（缺官方样例时对照测试 skip）；CLI 缺样例时提示而不崩溃。
- 纠正正式包结构：去掉误保留的 `src/`，将 `_grid.py`、`_numerics.py`、`_svp.py`、`_apply.py` 并入包级 `utils/`，与风、气温降尺度正式目录一致。

正式归档目录如下：

| 正式目录 | 内容说明 |
| --- | --- |
| `NIMM/00space_downscale/orographic_precipitation_downscaling/` | 核心插件与算法内 utils |
| `cli/00space_downscale/orographic_precipitation_downscaling/` | 业务调度 `dsc_orographic_enhancement_main.py` |
| `test/00space_downscale/orographic_precipitation_downscaling/` | 单元测试与官方对照 |
| `docs/00space_downscale/orographic_precipitation_downscaling/` | 算法文档 |
| `nbs/00space_downscale/orographic_precipitation_downscaling/` | 验证 notebook |
| `resource/00space_downscale/orographic_precipitation_downscaling/` | 资源说明（无样例数据） |

## 仍存在问题（需人工补充）

1. `BasePlugin` 仍为算法内本地类，待评估是否改为仓库统一基类。
2. `resource/` 当前仅有说明文件，未附带地形或官方样例。
3. `test_data/` 未同步到正式目录；官方对照测试缺数据时会 skip。

