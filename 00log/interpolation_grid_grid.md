# interpolation_grid_grid 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `interpolation_grid_grid` |
| 中文名称 | 格点→格点插值 |
| 原始路径 | `D:\workspace\test\00temp\interpolation_grid_grid`（由 `grid_grid_fusion` 更名） |
| 整理日期 | 2026-11-18（更名同步）；此前见 `00log/grid_grid_fusion.md` |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `ancillaries`（原记 `08consistense`，2026-11-18 更正） |
| 当前状态 | 已同步至中间目录 `00temp/interpolation_grid_grid`；旧目录 `00temp/grid_grid_fusion` 已删除；待正式补充至算法仓库 |

## 算法理解

将源格点场重采样到目标水平网格，面向 `meteva_base` 六维场。包内两类能力：

- **等距经纬插值（InterpGg\*）**：`InterpGgLinear` / `InterpGgNearest` / `InterpGgCubic`；统一 `process(grd, grid)`；越界用 `outer_value` 填充。
- **海陆感知重网格（LandSea）**：`InterpGgLandSea` / `InterpGgLandSea2` / `AdjustLandSeaPoints`。

自 `regrid` 合并后曾名 `grid_grid_fusion`，2026-11-18 更名为 `interpolation_grid_grid`。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/interpolation_grid_grid/src/` | 五插件 + LandSea 内核 `src/utils/` |
| `00temp/interpolation_grid_grid/cli/` | `python -m cli`（Gg）与 `tran_regrid.py`（LandSea） |
| `00temp/interpolation_grid_grid/resource/` | `conf.ini`；小样例 `data/*.nc` |
| `00temp/interpolation_grid_grid/test/` | 线性/最近邻/三次与 LandSea 单元测试 |
| `00temp/interpolation_grid_grid/docs/` | `interpolation_grid_grid.md` |
| `00temp/interpolation_grid_grid/nbs/` | `interpolation_grid_grid_说明.ipynb`（源侧无 `cmp_gg_vs_regrid.ipynb`） |
| `00temp/interpolation_grid_grid/utils/` | `util_env.py`、包内 `base_plugin` |

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
