# grid_grid_fusion 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `grid_grid_fusion` |
| 中文名称 | 格点→格点融合 |
| 原始路径 | `D:\workspace\test\00temp\grid_grid_fusion` |
| 整理日期 | 2026-11-16 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `08consistense` |
| 当前状态 | 已同步至中间目录 `00temp/grid_grid_fusion`；待正式补充至算法仓库 |

## 算法理解

将源格点场重采样到目标水平网格，面向 `meteva_base` 六维场。包内两类能力：

- **等距经纬插值（InterpGg\*）**：`InterpGgLinear` / `InterpGgNearest` / `InterpGgCubic`；统一 `process(grd, grid)`；越界用 `outer_value` 填充。
- **海陆感知重网格（LandSea）**：`InterpGgLandSea`（统一入口，按 `regrid_mode` 分派 scipy 或 `*-2` 路径，可选掩码）、`InterpGgLandSea2`（`*-2` 实现）、`AdjustLandSeaPoints`（`nearest-with-mask` 事后海陆订正，通常由 LandSea 调用）。

自 `regrid` 合并/更名：`RegridLandSea` → `InterpGgLandSea`，`RegridWithLandSeaMask` → `InterpGgLandSea2`，`AdjustLandSeaPoints` 保留。`InterpGgLinear/Nearest/Cubic` 亦收入本包，布局上取代独立的 `interp_gg_linear`。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/grid_grid_fusion/src/` | 五插件 + LandSea 内核 `src/utils/` |
| `00temp/grid_grid_fusion/cli/` | `python -m cli`（Gg）与 `tran_regrid.py`（LandSea） |
| `00temp/grid_grid_fusion/resource/` | `conf.ini`；小样例 `data/2026100900.024.nc` |
| `00temp/grid_grid_fusion/test/` | 线性/最近邻/三次与 LandSea 单元测试 |
| `00temp/grid_grid_fusion/docs/` | `grid_grid_fusion.md` |
| `00temp/grid_grid_fusion/nbs/` | `grid_grid_fusion_说明.ipynb`（不同步 `cmp_gg_vs_regrid.ipynb`） |
| `00temp/grid_grid_fusion/utils/` | `util_env.py`、包内 `base_plugin` |

## 2026-11-16 增量同步（二次）

- 自 `D:\workspace\test\00temp\grid_grid_fusion` 覆盖更新差异文件：`cli/grid_grid_fusion_cli.py`、`docs/grid_grid_fusion.md`、`resource/conf.ini`、`test/test_cli_config.py`、`utils/util_env.py`。
- **不同步** `nbs/cmp_gg_vs_regrid.ipynb`；若中间目录已有该文件则删除。
- 仍跳过 `HGT_M_1KM_CHINA.nc`（约 50MB）；保留已同步小 nc。
- **删除**中间目录旧包：`00temp/regrid`、`00temp/interp_gg_linear`（能力已并入本包）。历史说明见 `00log/regrid.md`。

## 2026-11-16 首次同步

- 自 `D:\workspace\test\00temp\grid_grid_fusion` 同步至 `00temp/grid_grid_fusion/`；未修改、未删除源目录；未同步 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`。
- `regrid` 方法已更名/合并入本包；`InterpGg*` 一并纳入。
- 已同步小样例 `resource/data/2026100900.024.nc`（约 0.37MB）；**跳过** `HGT_M_1KM_CHINA.nc`（约 50MB）。
- 同步校验：34 个 `.py`/`.md`/`.ini`/`.ipynb` 哈希与源一致；另复制 1 个小 nc；合计 35 文件。

## 仍存在问题（需人工补充）

1. 迁入正式 `NIMM/08consistense/` 时调整为仓库正式包路径。
2. `HGT_M_1KM_CHINA.nc`（约 50MB）未同步；是否放入 `NIMM_pip_testdata` / 正式仓库需再定。
3. `BasePlugin` 正式入库时评估是否改为仓库统一基类。

## 2026-11-16 依赖改接

- 已将 `frequency_matching_rain24`、`interp_sg_cressman` 中对旧包 `interp_gg_linear` 的路径改接为本包 `InterpGgLinear`（`process(grd, grid)`）。
- `interp_sg_cressman` 与 `station_grid_fusion.InterpSgCressman` 算法不同，二者并存；频率匹配仍用前者。
- `meb.interp_gg_linear`（meteva_base 库 API）未改。
