# NIMM 算法仓库整理清单

> 一次原始算法整理过程对应 `00log/` 下的一份日志；中间数据放 `00temp/region_dealias/`。

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | CLI 入口 |
| --- | --- | --- | --- | --- | --- |
| 观测相关处理 | **region_dealias** | 基于区域连通关系的多普勒雷达径向速度退模糊 | 2026-07-21 | 郭云谦、王亭波 | `python radar_wind_dealiasing/cli/region_dealias.py` |

## region_dealias 目录明细

| 类别 | 路径 | 作用 |
| --- | --- | --- |
| 核心算法 | `src/region_dealias.py` | `dealias_region_based` 与 `RegionDealiasPlugin` |
| 门限过滤 | `src/grid_gate_filter.py` | `GridGateFilter` |
| 内部工具 | `src/utils/` | 区域求解、地理重映射、极坐标体扫辅助 |
| 模块工具 | `utils/utils.py` | meteva_base 网格数据校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI | `cli/region_dealias.py`、`cli/polar_volume_main.py` | 文件式调用与体扫准备 |
| 文档 | `docs/region_dealias.md`、`docs/radar_wind_dealiasing.md` | 算法说明 |
| notebook | `nbs/region_dealias.ipynb` | 示例与验证 |
| 测试 | `test/` | 单元测试与 CLI 测试 |
| 整理日志 | `00log/region_dealias_整理_20260721.log` | 本次整理过程记录 |

## region_dealias 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
| --- | --- | --- |
| 1 | 入库路径 | 补充至 NIMM/01obs_adustment/ 时需调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | resource/ | 当前为空，正式补充时确认是否保留 |

## region_dealias 验证记录

| 环境 | 结果 | 日期 |
| --- | --- | --- |
| 中间目录 `00temp/radar_wind_dealiasing/` | 32 passed | 2026-07-21 |
| 原代码目录 `D:\workspace\pyart_nimm\region_dealias` | 全部测试通过 | 2026-07-21 |
