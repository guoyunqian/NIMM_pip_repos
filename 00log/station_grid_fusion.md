# station_grid_fusion 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `station_grid_fusion` |
| 中文名称 | 网格站点融合算法 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\00_sta_grid_interp` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、陈荣 |
| 算法分类 | `08consistense` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于站点观测与格点背景场的一致协调和融合。无背景场时，使用反距离权重将站点值插值到目标格点；有背景场时，先计算站点观测与背景场插值值的偏差，再将偏差按 IDW 或 Gaussian 权重扩散到格点并叠加背景场，得到融合后的格点产品。

核心源码包括：

- `src/interp_sg_idw_plugin.py`：`InterpSgIdw`，站点到格点 IDW 插值插件。
- `src/interp_sg_idw_delta_plugin.py`：`InterpSgIdwDelta`，基于背景场偏差的 IDW/Gaussian 融合插件。
- `src/interp_sg_delta_gaussian_plugin.py`：`InterpSgDeltaGaussian`，最近邻偏差高斯扩散融合插件。
- `src/interp_sg_total_plugin.py`：`InterpSgTotal`，综合站点到格点插值和背景场偏差订正调度。
- `src/interp_station_to_grid_renew.py`：函数式实现、业务流程示例、日期处理和并行辅助函数。

## 本次整理操作

已将原始目录内容整理到中间目录：

`00temp/station_grid_fusion/`

整理内容包括：

- `src/`：原始根目录下的核心 Python 源码，并新增 `__init__.py` 统一导出插件类。
- `nbs/`：原始示例脚本和 notebook。
- `docs/`：新增 `station_grid_fusion.md`。
- `cli/`、`resource/`、`test/`、`test_data/`、`utils/`：原始目录未提供对应内容，已新增说明文件补齐仓库结构。

未执行操作：

- 未删除或移动任何原始文件。
- 未补充到正式 `NIMM/08consistense/` 目录。
- 未修改原始算法逻辑。
- 未补充真实测试数据。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/station_grid_fusion/src/` | 核心插件和函数式流程源码 |
| `00temp/station_grid_fusion/cli/` | CLI 说明 |
| `00temp/station_grid_fusion/resource/` | 资源说明 |
| `00temp/station_grid_fusion/test/` | 测试说明 |
| `00temp/station_grid_fusion/test_data/` | 测试数据说明 |
| `00temp/station_grid_fusion/nbs/` | 示例脚本和 notebook |
| `00temp/station_grid_fusion/docs/` | 文档 |
| `00temp/station_grid_fusion/utils/` | 工具说明 |

## 已发现问题与后续建议

1. 原始代码依赖 `nimm.PostProcessingPlugin` 和 `meteva_base`/`meteva`，当前环境未确认依赖完整性。
2. `src/interp_sg_total_plugin.py` 中包含硬编码 `sys.path.append('/data/code/nimm/nimm/sta_grid_interp')`，正式入库前需要移除并改为仓库包路径。
3. `src/interp_sg_total_plugin.py` 的有背景场分支调用 `interp_sg_idw_delta`，但文件中仅导入了 `interp_sg_idw`，后续需要补齐导入或改用 `InterpSgIdwDelta`。
4. 示例脚本和 `__main__` 块中保留 `/data/code/nimm/...`、`D:\Desktop\...`、`/home/...`、共享盘等原始路径。
5. 原始目录未提供独立 `cli/`、`docs/`、`test/`、`test_data/`、`resource/` 和 `utils/` 内容，当前仅补充说明文件。
6. `interp_station_to_grid_renew.py` 同时包含核心函数、业务流程、时间工具和并行工具，正式入库时可评估拆分。

## 校验记录

- 已完成中间目录复制和目录补齐。
- 已确认中间目录无 `.venv`、`.idea`、`__pycache__`、`.pyc`、`.ipynb_checkpoints` 或运行日志残留。
- 已补充算法说明文档和各空目录说明。
- 已使用 Codex 捆绑 Python 完成 9 个 Python 文件的语法解析校验。
- 尝试导入 `station_grid_fusion.src` 时，当前 Codex 捆绑 Python 环境缺少 `nimm.PostProcessingPlugin`，未继续执行到 `meteva_base`、`meteva` 和 `scipy` 依赖校验；正式测试前需补齐依赖并统一包路径。
