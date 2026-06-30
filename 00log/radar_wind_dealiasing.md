# radar_wind_dealiasing 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `radar_wind_dealiasing` |
| 中文名称 | 雷达风场退模糊算法 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\算法_王\pyart\correct` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `01obs_adustment` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于多普勒雷达径向速度退模糊。核心方法迁移自 Py-ART 的 region-based dealias 算法：先按 Nyquist 区间对速度场分段，在单个 sweep 二维平面上识别连通区域，再依据相邻区域边界速度差合并区域并展开速度；若提供参考速度场，则进一步进行整体或分区锚定。整理版面向 `meteva_base.grid_data` 风格输入输出，并提供门限过滤和可选地理重映射。

核心源码包括：

- `src/region_dealias.py`：`dealias_region_based` 核心函数和 `RegionDealiasPlugin` 插件封装。
- `src/grid_gate_filter.py`：`GridGateFilter` 门点过滤器。
- `src/_common_dealias.py`：Nyquist 速度解析、过滤器解析和输出属性处理。
- `src/_fast_edge_finder.py`：区域边界快速查找。
- `utils/utils.py`：`meteva_base` 网格校验、门点经纬度附加和规则经纬网格重映射工具。
- `cli/region_dealias.py`：文件式调用入口。

## 本次整理操作

已将原始目录内容整理到中间目录：

`00temp/radar_wind_dealiasing/`

整理内容包括：

- `src/`：核心算法源码、过滤器和内部辅助模块。
- `cli/`：区域退模糊文件式调用入口。
- `docs/`：原始 `region_dealias.md`，并新增 `radar_wind_dealiasing.md`。
- `test_data/`：原始 NetCDF、MDV、CDF、`.npy` 输入样例和 CLI 参考输出。
- `test/`：退模糊和地理工具单元测试。
- `nbs/`：notebook 示例。
- `utils/`：网格、地理坐标和重映射工具。
- `resource/`：保留原始资源目录，当前无文件。

未执行操作：

- 未删除或移动任何原始文件。
- 未补充到正式 `NIMM/01obs_adustment/` 目录。
- 未修改原始算法逻辑。
- 未清理 `test_data/region_dealias/cli_output/`，其中内容按原始参考输出保留。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/radar_wind_dealiasing/src/` | 核心退模糊算法源码 |
| `00temp/radar_wind_dealiasing/cli/` | CLI 调度入口 |
| `00temp/radar_wind_dealiasing/resource/` | 资源目录，当前为空 |
| `00temp/radar_wind_dealiasing/test/` | 单元测试 |
| `00temp/radar_wind_dealiasing/test_data/` | 测试输入数据和参考输出 |
| `00temp/radar_wind_dealiasing/nbs/` | notebook 示例 |
| `00temp/radar_wind_dealiasing/docs/` | 文档 |
| `00temp/radar_wind_dealiasing/utils/` | 网格和地理工具函数 |

## 已发现问题与后续建议

1. 原始代码保留 `pyart.correct` 包路径和相对导入，例如依赖上层 `plugin_base.BasePlugin`，正式补充至算法仓库时需要统一包路径。
2. 算法虽然使用 `meteva_base.grid_data` 容器，但核心退模糊仍依赖雷达极坐标门拓扑；普通规则经纬度网格输入不能直接视为物理正确。
3. `test_data/region_dealias/cli_output/` 中包含原始 CLI 输出文件，正式测试时应避免覆盖参考输出或改用临时输出目录。
4. 依赖包括 `numpy`、`scipy`、`xarray`、`meteva_base`；完整测试前需要确认环境依赖。
5. `resource/` 目录当前为空，正式入库时可确认是否保留空目录或补充资源说明。

## 校验记录

- 已完成中间目录复制。
- 已确认中间目录无 `.venv`、`.idea`、`__pycache__`、`.pyc`、`.ipynb_checkpoints` 或运行日志残留。
- 已补充算法说明文档。
- 已使用 Codex 捆绑 Python 完成 14 个 Python 文件的语法解析校验。
- 尝试最小导入 `radar_wind_dealiasing` 时，当前 Codex 捆绑 Python 环境缺少 `xarray`，未继续执行到核心算法依赖与包路径校验；正式测试前需补齐依赖并确认 `pyart.correct` 包路径。
