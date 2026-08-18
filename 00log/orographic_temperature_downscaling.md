# orographic_temperature_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_temperature_downscaling` |
| 中文名称 | 气温降尺度(地形) |
| 原始路径 | `D:\workspace\improver\temperature`（原包名 `temperature`） |
| 路径说明 | 体感温度相关内容已拆分至独立模块 `feels_like_temperature` |
| 整理日期 | 2026-06-29（初整）；2026-07-06（NIMM 标准化）；2026-08-17（增量同步）；2026-08-18（正式归档） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `00space_downscale` |
| 当前状态 | 已补充至正式算法仓库目录 |

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
| `00temp/orographic_temperature_downscaling/utils/` | 单位换算、结果封装工具与本地 `BasePlugin` |
| `00temp/orographic_temperature_downscaling/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/orographic_temperature_downscaling/00temp/`、`00log/` | 中间数据与包内整理日志 |
| `00temp/orographic_temperature_downscaling/NIMM_list.md` | 算法包内整理清单 |

## 2026-08-17 更新

- 从 `D:\workspace\improver\temperature` 增量同步，发现多处实质性差异并更新：
  - `src/lapse_rate.py`：改用 `meb.checkout_griddata()` / `meb.checkout_griddata_same_coords()` 直接调用，移除本地封装函数 `check_for_meb_griddata()` / `check_for_xy_coordinates()`。
  - `utils/utils.py`：从 228 行简化为 103 行，仅保留 `rebuild_to_meb_griddata()` 和 `convert_units()`；`rebuild_to_meb_griddata()` 改用 `meb.set_griddata_attrs()` 组装属性。
  - `utils/base_plugin.py`：恢复完整 `PostProcessingPlugin`（含 `post_processed_title()` 方法）。
  - `cli/anc_lapse_rate.py`、`cli/dsc_temp_lapse_rate.py`：同步改用 `meb` 直接调用。
  - 补齐 `cli/preprocess_test_data.py`（官方投影样例预处理脚本）。
  - 同步 `nbs/lapse_rate.ipynb`（更完善的演示与验证 notebook，含 CLI 示例和原方法对照）。
  - `docs/lapse_rate.md`：补齐"测试数据预处理"章节，修正坐标验证引用。
  - `docs/orographic_temperature_downscaling.md`：更新文件列表与整理记录。

## 2026-07-06 更新

- NIMM 标准化：自 `improver/temperature` 同步；体感温度内容已拆出。
- 导入路径由 `temperature` 统一为 `orographic_temperature_downscaling`。
- 原代码目录 pytest 全部通过（2026-07-06）。
- 详细过程见：`00temp/orographic_temperature_downscaling/00log/lapse_rate_整理_20260706.log`。

## 2026-06-29 更新

- 初整至中间目录；当时导入仍为原始 `temperature` 包名，后续由 2026-07-06 标准化更新。

## 2026-08-18 正式归档

已将中间目录 `00temp/orographic_temperature_downscaling/` 重新补充到正式算法仓库，未删除中间目录文件。

本次操作包括：

- 核心源码归档到 `NIMM/00space_downscale/orographic_temperature_downscaling/`，包内改为相对导入。
- CLI 归档到 `cli/00space_downscale/orographic_temperature_downscaling/`，命名为 `dsc_temp_lapse_rate_main.py`、`anc_lapse_rate_main.py`。官方样例预处理脚本不进入正式 `cli/`，仍保留在中间目录。
- 测试、文档、notebook、资源说明归档到对应分类目录。
- 因分类目录以数字开头，CLI 与测试使用 `importlib.import_module()` 动态导入。
- 在 src 与 cli 中补充算法贡献人（郭云谦、王亭波）和软件产权说明。
- 正式 CLI 仓库根使用 `parents[3]`，样例路径指向中间目录 `test_data/`；缺样例时提示而不崩溃。
- 正式对照测试从 `00temp/orographic_temperature_downscaling/test_data/` 读取样例。
- 正式目录 pytest：15 passed, 2 skipped（缺官方样例时对照测试 skip）；CLI 缺样例时提示而不崩溃。

正式归档目录如下：

| 正式目录 | 内容说明 |
| --- | --- |
| `NIMM/00space_downscale/orographic_temperature_downscaling/` | 核心插件与算法内 utils |
| `cli/00space_downscale/orographic_temperature_downscaling/` | 业务调度 `dsc_temp_lapse_rate_main.py`、`anc_lapse_rate_main.py` |
| `test/00space_downscale/orographic_temperature_downscaling/` | 单元测试与官方对照 |
| `docs/00space_downscale/orographic_temperature_downscaling/` | 算法文档 |
| `nbs/00space_downscale/orographic_temperature_downscaling/` | 验证 notebook |
| `resource/00space_downscale/orographic_temperature_downscaling/` | 资源说明（无样例数据） |

## 仍存在问题（需人工补充）

1. `BasePlugin` 仍为算法内本地类，待评估是否改为仓库统一基类。
2. `resource/` 当前仅有说明文件，未附带地形或官方样例。
3. `test_data/` 未同步到正式目录；官方对照测试缺数据时会 skip。
