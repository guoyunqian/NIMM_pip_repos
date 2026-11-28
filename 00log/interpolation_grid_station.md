# interpolation_grid_station 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `interpolation_grid_station` |
| 中文名称 | 格点→站点插值 |
| 原始路径 | `D:\workspace\test\00temp\interpolation_grid_station`（新包） |
| 整理日期 | 2026-11-28（统一入口 `InterpGs` 与 CLI/文档/notebook）；2026-11-18 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `ancillaries`（与 gg/sg 插值包统一） |
| 当前状态 | 已同步至中间目录 `00temp/interpolation_grid_station`（2026-11-28 刷新，对外统一入口 `InterpGs`）；待正式补充至算法仓库 |

## 算法理解

将源格点场插值到站点位置，面向 `meteva_base` 六维场。对外统一入口 `InterpGs(method=linear|nearest|cubic)`，接口 `process(grd, sta)`；子插件 `InterpGsLinear` / `InterpGsNearest` / `InterpGsCubic` 仍可单独使用。`used_coords`（`xy` / `xyz` / `xydt`）仅 `linear` 生效。水平 `xy` 与 `meteva_base.interp_gs_*` 对齐。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/interpolation_grid_station/src/` | 统一入口 `interp_gs_plugin.py`（`InterpGs`）、三个算法插件与 `gs_helpers` |
| `00temp/interpolation_grid_station/cli/` | `interpolation_grid_station_cli.py`（模块级 `process`，`method=`）；`python -m interpolation_grid_station` / `python -m cli` |
| `00temp/interpolation_grid_station/resource/` | `conf.ini`（`method` 等与 `process` 形参对应）与小样例 nc/csv |
| `00temp/interpolation_grid_station/test/` | 统一入口、配置与插件测试 |
| `00temp/interpolation_grid_station/nbs/` | `interpolation_grid_station_说明.ipynb` |
| `00temp/interpolation_grid_station/docs/` | `interpolation_grid_station.md` |
| `00temp/interpolation_grid_station/utils/` | `util_env.py` |

## 2026-11-28 统一入口

- 自 `D:\workspace\test\00temp\interpolation_grid_station` 覆盖同步至 `00temp/interpolation_grid_station/`；未修改、未删除源目录。仅覆盖仓库工作区，未执行 git 提交。
- 同步范围：`src/`、`cli/`、`docs/`、`test/`、`nbs/`、`utils/`、`resource/conf.ini`。跳过 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`。
- **未同步** ShowDoc 产物 `resource/showdoc_demo/`。未覆盖仓库里原有的 `resource/2026100900.024.nc`、`2026100900.024_sta.csv`、`cli_linear_out.csv`。
- 文本/代码哈希校验：新增 3 + 覆盖 7，与源目录一致的文本/代码共 20 个（含未改的 10 个），无不一致。
- **新增统一入口**：`src/interp_gs_plugin.py` 的 `InterpGs(method=...)`，`src/__init__.py` 导出；`method` 为 `linear` / `nearest` / `cubic`。`used_coords` 仅 `linear` 使用。
- **CLI**：`process` 经统一入口调用；键名与形参同名；`resource/conf.ini` 改为 `method=`，不再使用旧的 `--module`。
- **文档与笔记本**：`docs/interpolation_grid_station.md`、`cli/README.md` 改为 `InterpGs` 为主线；`nbs/interpolation_grid_station_说明.ipynb` 随源目录覆盖。未在算法仓库内重跑 notebook。
- **删除**：`nbs/interpolation_grid_station.ipynb`（旧文件名，由说明 notebook 取代）。
- **测试**：在算法仓库内 `pytest test` 为 18 passed。

## 2026-11-18 首次同步

- 自 `D:\workspace\test\00temp\interpolation_grid_station` 同步至 `00temp/interpolation_grid_station/`；未修改、未删除源目录。
- 未同步 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`；无 >5MB 数据需跳过。
- 文本/代码哈希校验：17 个 `.py`/`.md`/`.ini`/`.ipynb` 一致；另复制小样例数据；合计 20 文件。
- 注：`frequency_matching_rain24` 的格点→站点仍走 `meteva.base.interp_gs_linear`，未强制改接本包。

## 仍存在问题（需人工补充）

1. 正式入库时改为 `NIMM/ancillaries/` 包路径。
2. 是否让频率匹配等业务改接本包 `InterpGsLinear` 需另定。
