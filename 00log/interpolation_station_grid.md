# interpolation_station_grid 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `interpolation_station_grid` |
| 中文名称 | 站点→格点插值融合 |
| 原始路径 | `D:\workspace\test\00temp\interpolation_station_grid`（由 `station_grid_fusion` 更名） |
| 整理日期 | 2026-11-18（更名同步）；此前见 `00log/station_grid_fusion.md` |
| 算法贡献人 | 郭云谦、陈荣 |
| 算法分类 | `ancillaries`（原记 `08consistense`，2026-11-18 更正） |
| 当前状态 | 已同步至中间目录 `00temp/interpolation_station_grid`；旧目录 `00temp/station_grid_fusion` 已删除；依赖同级 `interpolation_grid_grid` |

## 算法理解

将站点观测融合到规则格点场。四个插件统一 `process(sta, grid, background=None)`：

- `InterpSgIdw` / `InterpSgGaussian` / `InterpSgKriging`：可选背景偏差订正
- `InterpSgCressman`：经典逐步订正；可选背景作初估场（与独立包 `interp_sg_cressman` 算法不同，二者并存）

背景对齐依赖同级包 `interpolation_grid_grid.InterpGgLinear`（各插件内 `_ensure_interpolation_grid_grid_on_path`，路径为 `interpolation_grid_grid` 而非旧名）。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/interpolation_station_grid/src/` | 四插件 |
| `00temp/interpolation_station_grid/cli/` | `python -m cli` 与 `interpolation_station_grid_cli.py` |
| `00temp/interpolation_station_grid/resource/` | `conf.ini` 与小样例 nc/csv |
| `00temp/interpolation_station_grid/test/` | 配置与算法测试 |
| `00temp/interpolation_station_grid/nbs/` | `interpolation_station_grid_说明.ipynb` |
| `00temp/interpolation_station_grid/docs/` | `interpolation_station_grid.md` |
| `00temp/interpolation_station_grid/utils/` | `util_env.py` 等 |

## 2026-11-18 更名同步

- 自 `D:\workspace\test\00temp\interpolation_station_grid` 覆盖同步至 `00temp/interpolation_station_grid/`；未修改、未删除源目录。
- 未同步 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`；无 >5MB 数据需跳过。
- 文本/代码哈希校验：25 个 `.py`/`.md`/`.ini`/`.ipynb` 一致；另复制小样例数据；合计 29 文件。
- **删除**旧中间目录 `00temp/station_grid_fusion`。
- 已核对：源内 `InterpGgLinear` 引导目录名为 `interpolation_grid_grid`。

## 仍存在问题（需人工补充）

1. 正式入库时改为 `NIMM/ancillaries/` 包路径。
2. 与 `interp_sg_cressman` 的并存关系需在正式文档中保持区分说明。
