# interpolation_station_grid 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `interpolation_station_grid` |
| 中文名称 | 站点→格点插值融合 |
| 原始路径 | `D:\workspace\test\00temp\interpolation_station_grid`（由 `station_grid_fusion` 更名） |
| 整理日期 | 2026-11-27（统一入口 `InterpSg`、半径单位更正、CLI 与测试补全）；2026-11-20（并入原 `interp_sg_cressman`）；2026-11-18（更名同步）；此前见 `00log/station_grid_fusion.md` |
| 算法贡献人 | 郭云谦、陈荣 |
| 算法分类 | `ancillaries`（原记 `08consistense`，2026-11-18 更正） |
| 当前状态 | 已同步至中间目录 `00temp/interpolation_station_grid`（2026-11-27 刷新，对外统一入口 `InterpSg`）；旧目录 `00temp/station_grid_fusion`、`00temp/interp_sg_cressman` 已删除；依赖同级 `interpolation_grid_grid` |

## 算法理解

将站点观测融合到规则格点场。对外统一入口 `InterpSg(method=idw|gaussian|kriging|cressman)`，接口 `process(sta, grid=None, background=None)`，按 `method` 分派到四个算法插件（各插件仍可单独使用）：

- `InterpSgIdw` / `InterpSgGaussian` / `InterpSgKriging`：可选背景偏差订正
- `InterpSgCressman`：`reprocess=False` 为原 `interp_sg_cressman` 覆盖式（千米半径）；`reprocess=True` 为经典逐步订正（度制创新量，可用 `degree_blend`、`rain_limit` 等高级参数）；可选背景作初估场
- `reprocess` 只决定绝对值 / 偏差路径，与 IDW 的 `gaussian`（是否乘高斯核）相互独立
- 所有距离、半径（`effectR`、`halfR`、`range_`，以及 `reprocess=False` 时 Cressman 的 `r_list`）单位均为**千米**，可写小数；`reprocess=True` 的 Cressman `r_list` 为度

背景对齐依赖同级包 `interpolation_grid_grid.InterpGgLinear`（各插件内 `_ensure_interpolation_grid_grid_on_path`，路径为 `interpolation_grid_grid` 而非旧名）。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/interpolation_station_grid/src/` | 统一入口 `interp_sg_plugin.py`（`InterpSg`）与四个算法插件 |
| `00temp/interpolation_station_grid/cli/` | `interpolation_station_grid_cli.py`（模块级 `process`，键名即形参，`key=value`） |
| `00temp/interpolation_station_grid/resource/` | `conf.ini`（默认配置）与小样例 nc/csv |
| `00temp/interpolation_station_grid/test/` | 配置、统一入口与算法测试（共 52 项） |
| `00temp/interpolation_station_grid/nbs/` | `interpolation_station_grid_说明.ipynb` |
| `00temp/interpolation_station_grid/docs/` | `interpolation_station_grid.md` |
| `00temp/interpolation_station_grid/utils/` | 仅 `README.md`、`__init__.py`（共享 `utils` 并入）；`util_env.py` 已删除 |

## 2026-11-27 统一入口、单位更正与 CLI/测试补全

- 自 `D:\workspace\test\00temp\interpolation_station_grid` 覆盖同步至 `00temp/interpolation_station_grid/`；未修改、未删除源目录。仅覆盖仓库工作区，未执行 git 提交。
- 同步范围：`src/`、`cli/`、`docs/`、`test/`、`nbs/`、`utils/`、`resource/`（不含 `resource/showdoc_demo/`，该目录为 ShowDoc 页面的制作产物，不入算法仓库）；跳过 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`；最大文件为 `nbs/interpolation_station_grid_说明.ipynb`（约 4.2 MB），无 >5MB 需跳过项。
- 文本/代码哈希校验：新增 4 + 覆盖 18，共 30 个文件，与源目录逐一一致，仓库内无多余文件。同步 `00temp/utils/__init__.py`（删除"格点双线性、站点 Cressman 已独立为子模块"的过时说明）。
- **新增统一入口**：`src/interp_sg_plugin.py` 的 `InterpSg(method=...)`，`src/__init__.py` 导出；构造参数全部显式列出，未用于当前 `method` 的项忽略。
- **CLI 重构**：`process` 经统一入口调用，参数四级优先级（显式 > `config` 指定 ini > `resource/conf.ini` > 签名默认值）；键名与形参同名，`conf.ini` 与形参一一对应；`method` 仅支持 `idw` / `gaussian` / `kriging` / `cressman`。
- **CLI 暴露 Cressman 度制路径高级参数**：`cressman_rain_limit`、`cressman_num_limit`、`cressman_smooth`、`cressman_power_param`、`cressman_r_km_scale`、`cressman_innov_gain`、`cressman_residual_passes`、`cressman_residual_degree_polish`、`cressman_residual_polish_rounds`、`cressman_degree_blend`、`cressman_station_anchor_radius`、`cressman_station_anchor_strength`；预设值与 `InterpSgCressman` 一致，只在 `method=cressman` 且 `reprocess=true` 时生效，含数值范围校验。
- **半径单位更正**：`InterpSgIdw.effectR`、`InterpSgGaussian.halfR`、`InterpSgKriging.range_` 的距离单位为千米（原注释/文档写"米"，数值与算法未变）；`InterpSgCressman` 的 `reprocess=False` 以千米为单位，默认 `r_list=(60, 40, 20)`。
- **半径支持小数**：`InterpSgGaussian` 不再对 `halfR` 做 `int()` 截断；`effectR`、`halfR` 及 CLI 的 `idw_effect_r`、`gaussian_half_r` 类型改为 `float`。
- **`reprocess` 与 `gaussian` 独立**：IDW 偏差路径默认纯 IDW 权重，需要高斯权重时显式 `gaussian=True`；新增 `test_idw_reprocess_gaussian.py`。
- **测试**：包内由 18 项增至 52 项（统一入口与四个子插件的形参/默认值/结果一致性、小数半径、CLI 键与 `conf.ini` 对应、参数转发与数值校验）；在算法仓库内运行 `pytest test` 为 52 passed。
- **文档与笔记本**：`docs/interpolation_station_grid.md`、`cli/README.md`、`resource/README.md` 补充统一入口、千米单位与 Cressman 高级参数；`nbs/interpolation_station_grid_说明.ipynb` 改为 `InterpSg` 为主线，半径按千米改写（`effectR=150`、`halfR=80` 等）并整本重跑。
- **删除**（本地已删除，仓库同步镜像）：`cli/fusion_main.py`、`nbs/interpolation_station_grid.ipynb`（旧文件名，由 `interpolation_station_grid_说明.ipynb` 取代）、`test/test_idw_delta.py`、`utils/util_env.py`。
- **ShowDoc**：线上插件页已改为只展示统一入口 `InterpSg`（含签名下划线转义修正）；仓库内 `resource/showdoc_demo/` 下原有文件（`plugin_page.md`、`cli_page.md`、`_upload_pngs_mcp.py`）在仓库工作区已为删除状态，本次未恢复。

## 2026-11-20 并入原 interp_sg_cressman

- 自 `D:\workspace\test\00temp\interpolation_station_grid` 覆盖同步至 `00temp/interpolation_station_grid/`；未修改、未删除源目录。
- 同步范围：`src/`、`cli/`、`docs/`、`test/`、`nbs/`、`utils/`、`resource/`（含 `resource/showdoc_demo/*.md`、`.py`）；跳过 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`；无 >5MB 需跳过项。
- 文本/代码哈希校验：NEW 3 + DIFF 12 覆盖后全部一致。
- **合并**：原独立包 `interp_sg_cressman` 逻辑并入本包 `InterpSgCressman`（`reprocess=False` 旧覆盖式；`reprocess=True` 经典逐步订正）；CLI/docs/nbs 已更新。
- **删除**中间目录 `00temp/interp_sg_cressman`。
- `frequency_matching_rain24` 改接：`src/interpolation_sg_cressman.py` → `InterpSgCressman(reprocess=False)`；相关注释与 docs/`NIMM_list` 同步。
- 分类仍为 `ancillaries`。

## 2026-11-18 更名同步

- 自 `D:\workspace\test\00temp\interpolation_station_grid` 覆盖同步至 `00temp/interpolation_station_grid/`；未修改、未删除源目录。
- 未同步 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`；无 >5MB 数据需跳过。
- 文本/代码哈希校验：25 个 `.py`/`.md`/`.ini`/`.ipynb` 一致；另复制小样例数据；合计 29 文件。
- **删除**旧中间目录 `00temp/station_grid_fusion`。
- 已核对：源内 `InterpGgLinear` 引导目录名为 `interpolation_grid_grid`。

## 仍存在问题（需人工补充）

1. 正式入库时改为 `NIMM/ancillaries/` 包路径。
