# radar_wind_dealiasing 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `radar_wind_dealiasing` |
| 中文名称 | 雷达风场退模糊算法 |
| 原始路径 | `D:\workspace\pyart_nimm\region_dealias`（原包名 `region_dealias`） |
| 路径说明 | 2026-06-29 初整曾基于旧 `pyart.correct` 路径副本；2026-07-21 以本地 `region_dealias` 为准完成标准化 |
| 整理日期 | 2026-06-29（初整）；2026-07-21（NIMM 标准化及单层样例同步）；2026-10-13（增量同步） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `01obs_adustment` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法用于多普勒雷达径向速度退模糊。迁移自 Py-ART 区域连通关系退模糊流程：按 Nyquist 区间分段，在扫描层二维平面识别连通区域并依据边界关系合并展开；支持参考速度锚定、门点过滤与可选经纬度重映射。面向 `meteva_base.grid_data` 风格输入输出。

主要入口包括：

- `dealias_region_based`、`RegionDealiasPlugin`、`GridGateFilter`。
- CLI `cli/region_dealias.py` 与极坐标体扫准备 `cli/polar_volume_main.py`（含单层截取）。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/radar_wind_dealiasing/src/region_dealias.py` | 核心退模糊与插件 |
| `00temp/radar_wind_dealiasing/src/grid_gate_filter.py` | 门点过滤器 |
| `00temp/radar_wind_dealiasing/src/utils/` | 区域求解、地理重映射、体扫辅助 |
| `00temp/radar_wind_dealiasing/cli/` | 文件式 CLI 与体扫准备 |
| `00temp/radar_wind_dealiasing/utils/` | 本地 `BasePlugin` |
| `00temp/radar_wind_dealiasing/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/radar_wind_dealiasing/resource/` | 仅说明；样例未同步 |

## 2026-10-13 更新

- 任务一再次整理 `D:\workspace\pyart_nimm\region_dealias`。路径此前已归入 `00temp/radar_wind_dealiasing/`，本次为增量同步，未新建第二套中间目录，未修改原目录。
- 同步内容：源码、CLI、测试、`docs/region_dealias.md`、`nbs/region_dealias.ipynb` 与原目录对齐；导入统一为 `radar_wind_dealiasing`（含裸包名 `from region_dealias import ...`）。
- 按用户要求删除包内脚手架：`00log/`、`00temp/`、`NIMM_list.md`、`.gitignore`。
- 删除中间目录多余的 `utils/utils.py`（原目录已无，改用 `meb`）。
- 未拷贝 `test_data/`；`resource/` 仅放说明；保留并更新中文概述 `docs/radar_wind_dealiasing.md`。
- 中间目录 pytest：**33 passed**。
- 贡献人未修改：郭云谦、王亭波。

## 2026-07-21 更新

- NIMM 标准化：自 `pyart_nimm/region_dealias` 同步；导入统一为 `radar_wind_dealiasing`（包内绝对导入）。
- notebook / CLI 改为单层仰角样例；新增 `extract_polar_volume_sweep`。
- 未同步 `test_data/`；原目录与中间目录 pytest 均为 33 passed。

## 2026-06-29 更新

- 初整至中间目录；当时仍保留 `pyart.correct` 风格导入路径。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/01obs_adustment/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `resource/` 仅有说明文件，无雷达样例；正式入库前筛选必要小样例。
4. 单层小样例是否纳入中间目录 / 正式仓库，后续决定（样例见 `NIMM_pip_testdata/radar_wind_dealiasing/`）。
