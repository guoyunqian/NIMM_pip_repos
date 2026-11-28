# interpolation_grid_grid 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `interpolation_grid_grid` |
| 中文名称 | 格点→格点插值 |
| 原始路径 | `D:\workspace\test\00temp\interpolation_grid_grid`（由 `grid_grid_fusion` 更名） |
| 整理日期 | 2026-11-28（统一入口 `InterpGg`、面积加权与 CLI/文档/notebook）；2026-11-18（更名同步）；此前见 `00log/grid_grid_fusion.md` |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `ancillaries`（原记 `08consistense`，2026-11-18 更正） |
| 当前状态 | 已同步至中间目录 `00temp/interpolation_grid_grid`（2026-11-28 刷新，对外统一入口 `InterpGg`）；旧目录 `00temp/grid_grid_fusion` 已删除；待正式补充至算法仓库 |

## 算法理解

将源格点场重采样到目标水平网格，面向 `meteva_base` 六维场。包内两类能力：

- **等距经纬插值**：对外统一入口 `InterpGg(method=linear|nearest|cubic|conservative)`，接口 `process(grd, grid)`；子插件 `InterpGgLinear` / `InterpGgNearest` / `InterpGgCubic` / `InterpGgConservative` 仍可单独使用。越界用 `outer_value` 填充。`conservative` 为一阶面积加权（`mdtol`、`spherical`），核在 `src/utils/area_weighted.py`。
- **海陆感知重网格（LandSea）**：`InterpGgLandSea` / `InterpGgLandSea2` / `AdjustLandSeaPoints`。

自 `regrid` 合并后曾名 `grid_grid_fusion`，2026-11-18 更名为 `interpolation_grid_grid`。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/interpolation_grid_grid/src/` | 统一入口 `interp_gg_plugin.py`（`InterpGg`）、四个等距经纬插件、LandSea 插件；面积加权核 `src/utils/area_weighted.py` |
| `00temp/interpolation_grid_grid/cli/` | `interpolation_grid_grid_cli.py`（模块级 `process`，`method=`）、`tran_regrid_cli.py`；`python -m interpolation_grid_grid` / `python -m cli` |
| `00temp/interpolation_grid_grid/resource/` | `conf.ini`（`method` 等与 `process` 形参对应）；小样例 `data/*.nc` |
| `00temp/interpolation_grid_grid/test/` | 统一入口、面积加权、线性/最近邻/三次与 LandSea 单元测试 |
| `00temp/interpolation_grid_grid/docs/` | `interpolation_grid_grid.md` |
| `00temp/interpolation_grid_grid/nbs/` | `interpolation_grid_grid_说明.ipynb` |
| `00temp/interpolation_grid_grid/utils/` | 包内 `base_plugin`（`util_env.py` 已删除） |

## 2026-11-28 统一入口与面积加权

- 自 `D:\workspace\test\00temp\interpolation_grid_grid` 覆盖同步至 `00temp/interpolation_grid_grid/`；未修改、未删除源目录。仅覆盖仓库工作区，未执行 git 提交。
- 同步范围：`src/`、`cli/`、`docs/`、`test/`、`nbs/`、`utils/`、`resource/conf.ini`。跳过 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`。
- **未同步** ShowDoc 与 CLI 跑出来的数据：`resource/showdoc_demo/`、`resource/data/cli_linear_out.m4`、`cli_conservative_out.m4`、`cli_target_grid.nc`。未覆盖仓库里原有的 `resource/data/2026100900.024.nc`、`target_grid.nc`、`cli_landsea_bilinear_out.nc`。
- 文本/代码哈希校验：新增 6 + 覆盖 8，与源目录一致的文本/代码共 38 个（含未改的 24 个），无不一致。
- **新增统一入口**：`src/interp_gg_plugin.py` 的 `InterpGg(method=...)`，`src/__init__.py` 导出；`method` 为 `linear` / `nearest` / `cubic` / `conservative`。未用于当前方法的构造参数忽略。
- **面积加权**：`InterpGgConservative` 与 `src/utils/area_weighted.py`；CLI 暴露 `mdtol`、`spherical`。
- **CLI**：`process` 经统一入口调用；键名与形参同名；`resource/conf.ini` 增加 `method`，并保留 `outer_value` / `mdtol` / `spherical`。
- **文档与笔记本**：`docs/interpolation_grid_grid.md` 改为 `InterpGg` 为主线；`nbs/interpolation_grid_grid_说明.ipynb` 随源目录覆盖（示例目标网格 0.05°）。未在算法仓库内重跑 notebook。
- **删除**：`nbs/interpolation_grid_grid.ipynb`（旧文件名，由说明 notebook 取代）、`utils/util_env.py`（CLI 已不再引用）。
- **测试**：在算法仓库内 `pytest test` 为 51 passed、1 skipped。

## 2026-11-18 更名同步

- 自 `D:\workspace\test\00temp\interpolation_grid_grid` 覆盖同步至 `00temp/interpolation_grid_grid/`；未修改、未删除源目录。
- 未同步 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`。
- **跳过** `resource/data/cli_linear_out.m4`（约 29.91MB）；保留小 nc（含约 0.37MB 样例与约 2.5MB landsea 输出样例）。
- 文本/代码哈希校验：33 个 `.py`/`.md`/`.ini`/`.ipynb` 一致；另复制 3 个小数据文件；合计 36 文件。
- **删除**旧中间目录 `00temp/grid_grid_fusion`。
- 下游路径改接：当时 `interp_sg_cressman`、`frequency_matching_rain24` 的 sys.path 引导改为本包名；`meb.interp_gg_linear` API 未改。（注：2026-11-20 起原 `interp_sg_cressman` 包已删，Cressman 改由 `interpolation_station_grid.InterpSgCressman` 提供。）
- **分类**：由 `08consistense` 调整为 `ancillaries`（插值辅助工具族）。

## 仍存在问题（需人工补充）

1. 迁入正式 `NIMM/ancillaries/` 时调整为仓库正式包路径。
2. 大体量 `cli_linear_out.m4` 未同步；是否放入 testdata 需再定。
3. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
