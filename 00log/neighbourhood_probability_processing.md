# neighbourhood_probability_processing 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `neighbourhood_probability_processing` |
| 中文名称 | 邻域(nbhood)处理及概率生成 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\算法_王\improve\nbhood` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `07probability` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

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
- `src/meta_nbhood_utils.py`
  - 提供 `radius_by_lead_time`、角度复数转换和 halo 裁剪等元处理工具。

CLI 入口包括：

- `cli/ens_nbhood.py`：普通邻域概率和邻域百分位。
- `cli/ens_nbhood_iterate_with_mask.py`：按分层掩码迭代处理。
- `cli/ens_nbhood_land_and_sea.py`：陆海/地形带分区邻域处理并合并输出。

## 本次整理操作

已将原始目录内容复制到中间目录：

`00temp/neighbourhood_probability_processing/`

复制内容包括：

- `src/`：核心算法源码。
- `cli/`：示例调度脚本。
- `docs/`：原始算法说明文档，并新增 `neighbourhood_probability_processing.md`。
- `nbs/`：notebook 示例。
- `test/`：pytest 测试脚本。
- `test_data/`：官方样例和对照 `nc` 测试数据。
- `utils/`：原始工具函数。
- `resource/`：原始资源目录。

未执行操作：

- 未删除或移动任何原始文件。
- 未补充到正式 `NIMM/07probability/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/neighbourhood_probability_processing/src/` | 核心算法源码 |
| `00temp/neighbourhood_probability_processing/cli/` | CLI 调度与示例脚本 |
| `00temp/neighbourhood_probability_processing/resource/` | 资源目录 |
| `00temp/neighbourhood_probability_processing/test/` | 单元测试 |
| `00temp/neighbourhood_probability_processing/test_data/` | 测试数据 |
| `00temp/neighbourhood_probability_processing/nbs/` | notebook 示例 |
| `00temp/neighbourhood_probability_processing/docs/` | 文档 |
| `00temp/neighbourhood_probability_processing/utils/` | 算法内部工具函数 |

## 已发现问题与后续建议

1. 原始代码导入路径仍使用 `nbhood.src...`、`nbhood.cli...` 和 `nbhood.utils...`。当前中间目录保持原样，后续补充至正式仓库时需要统一调整为 `NIMM` 下的实际包路径。
2. 当前未运行完整 pytest 测试。正式补充前应确认环境依赖，包括 `numpy`、`xarray`、`cf_units`、`meteva_base`、`pytest`。
3. `src/nbhood.py` 和 `src/use_nbhood.py` 中核心类已提供 `process` 方法，符合插件式整理方向；但未继承仓库已有 `NIMM.utilities.base_plugin.BasePlugin`，后续可按仓库规范评估是否补充。
4. `test_data/` 中包含较多官方对照结果和 CLI 输出结果文件，正式入库前建议筛选必要小样例，避免测试数据过重。
5. `resource/` 目录当前为空或无算法必要资源，正式补充时可确认是否保留空目录。

