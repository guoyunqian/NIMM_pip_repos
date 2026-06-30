# orographic_wind_downscaling 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `orographic_wind_downscaling` |
| 中文名称 | 风降尺度(地形) |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\算法_王\improve\wind_calculations` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `00space_downscale` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于风速空间降尺度，核心思想是利用地形轮廓粗糙度、网格内地形高度标准差、目标地形与模式地形高度差，以及植被粗糙度长度，对风速进行粗糙度订正和高度订正。

核心源码 `src/wind_downscaling.py` 中提供：

- `FrictionVelocity`：基于对数风速廓线计算摩擦速度。
- `RoughnessCorrectionUtilities`：计算半峰谷高度、地形波数、参考高度，并执行粗糙度订正和高度订正。
- `RoughnessCorrection`：风速降尺度主插件，负责输入结构统一、空间维度校验、批量切片处理和输出重组。

CLI 入口 `cli/dsc_wind_downscaling.py` 读取风速、地形高度标准差、目标地形、标准地形、地形轮廓粗糙度和植被粗糙度等 `nc` 文件，调用 `RoughnessCorrection` 输出订正后的风速场。

## 本次整理操作

已将原始目录内容复制到中间目录：

`00temp/orographic_wind_downscaling/`

复制内容包括：

- `src/`：核心算法源码。
- `cli/`：示例调度脚本。
- `docs/`：原始算法说明文档，并新增 `orographic_wind_downscaling.md`。
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
| `00temp/orographic_wind_downscaling/src/` | 核心算法源码 |
| `00temp/orographic_wind_downscaling/cli/` | CLI 调度与示例脚本 |
| `00temp/orographic_wind_downscaling/resource/` | 资源目录 |
| `00temp/orographic_wind_downscaling/test/` | 单元测试 |
| `00temp/orographic_wind_downscaling/test_data/` | 测试数据 |
| `00temp/orographic_wind_downscaling/nbs/` | notebook 示例 |
| `00temp/orographic_wind_downscaling/docs/` | 文档 |
| `00temp/orographic_wind_downscaling/utils/` | 算法内部工具函数 |

## 已发现问题与后续建议

1. 原始代码导入路径仍使用 `wind_calculations.src...` 和 `wind_calculations.utils...`。当前中间目录保持原样，后续补充至正式仓库时需要统一调整为 `NIMM` 下的实际包路径。
2. 当前未运行完整 pytest 测试。正式补充前应确认环境依赖，包括 `numpy`、`xarray`、`cf_units`、`meteva_base`、`pytest`、`netcdf4`。
3. `src/wind_downscaling.py` 中 `RoughnessCorrection` 已提供类和 `process` 方法，符合插件式整理方向；但未继承仓库已有 `NIMM.utilities.base_plugin.BasePlugin`，后续可按仓库规范评估是否补充。
4. 测试数据中包含 `input_6d_rename_tmp.nc`、`input_6d_convert_tmp.nc`、`cli_test_tmp.nc` 等临时命名文件，正式入库前建议筛选必要样例并清理临时输出。
5. `resource/` 目录当前为空或无算法必要资源，正式补充时可确认是否保留空目录。

