# orographic_precipitation_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_precipitation_downscaling` |
| 中文名称 | 降水降尺度(地形) |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\算法_王\improve\orographic_enhancement` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `00space_downscale` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于降水地形降尺度和地形增强订正，核心思想是利用温湿压、风场和地形高度计算地形抬升导致的降水增强项，并支持将增强项叠加或扣除到降水场。

核心源码包括：

- `src/orographic_enhancement.py`
  - `ResolveWindComponents`：将风速和风向解析为目标网格坐标系下的 `u/v` 风分量。
  - `MetaOrographicEnhancement`：从多层气象场提取边界层代表高度，组织地形增强计算流程。
  - `OrographicEnhancement`：计算迎风抬升项、地形增强格点贡献和上游贡献，输出地形增强结果。
- `src/apply_orographic_enhancement.py`
  - `ApplyOrographicEnhancement`：将地形增强项以 `add` 或 `subtract` 模式应用到降水场，并处理时间匹配和最小降水率保护。

CLI 入口 `cli/dsc_orographic_enhancement.py` 读取温度、相对湿度、气压、风速、风向和地形 `nc` 文件，调用 `MetaOrographicEnhancement` 输出地形增强项。

## 本次整理操作

已将原始目录内容复制到中间目录：

`00temp/orographic_precipitation_downscaling/`

复制内容包括：

- `src/`：核心算法源码。
- `cli/`：示例调度脚本。
- `docs/`：原始算法说明文档，并新增 `orographic_precipitation_downscaling.md`。
- `nbs/`：notebook 示例。
- `test/`：pytest 测试脚本。
- `test_data/`：样例 `nc` 测试数据。
- `utils/`：原始工具函数。
- `resource/`：原始资源目录。

未执行操作：

- 未删除或移动任何原始文件。
- 未补充到正式 `NIMM/00space_downscale/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/orographic_precipitation_downscaling/src/` | 核心算法源码 |
| `00temp/orographic_precipitation_downscaling/cli/` | CLI 调度与示例脚本 |
| `00temp/orographic_precipitation_downscaling/resource/` | 资源目录 |
| `00temp/orographic_precipitation_downscaling/test/` | 单元测试 |
| `00temp/orographic_precipitation_downscaling/test_data/` | 测试数据 |
| `00temp/orographic_precipitation_downscaling/nbs/` | notebook 示例 |
| `00temp/orographic_precipitation_downscaling/docs/` | 文档 |
| `00temp/orographic_precipitation_downscaling/utils/` | 算法内部工具函数 |

## 已发现问题与后续建议

1. 原始代码导入路径仍使用 `orographic_enhancement.src...` 和 `orographic_enhancement.utils...`。当前中间目录保持原样，后续补充至正式仓库时需要统一调整为 `NIMM` 下的实际包路径。
2. 当前未运行完整 pytest 测试。正式补充前应确认环境依赖，包括 `numpy`、`xarray`、`cf_units`、`scipy`、`pyproj`、`meteva_base`、`pytest`、`netcdf4`。
3. `src/orographic_enhancement.py` 中 `MetaOrographicEnhancement` 和 `OrographicEnhancement` 已提供类和 `process` 方法，`src/apply_orographic_enhancement.py` 中 `ApplyOrographicEnhancement` 也提供插件式接口；但均未继承仓库已有 `NIMM.utilities.base_plugin.BasePlugin`，后续可按仓库规范评估是否补充。
4. 测试数据中包含 `cli_test_result.nc`、`_test_orog.nc` 等结果或临时文件，正式入库前建议筛选必要样例并清理临时输出。
5. `resource/` 目录当前为空或无算法必要资源，正式补充时可确认是否保留空目录。

