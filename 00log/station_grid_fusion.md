# station_grid_fusion 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `station_grid_fusion` |
| 中文名称 | 网格站点融合算法 |
| 原始路径 | `D:\workspace\test\00temp\station_grid_fusion`（本次同步）；初整路径见历史节 |
| 整理日期 | 2026-06-29（初整）；2026-11-16（重构同步） |
| 算法贡献人 | 郭云谦、陈荣 |
| 算法分类 | `08consistense` |
| 当前状态 | 已同步至中间目录；依赖同级包 `grid_grid_fusion` 已于 2026-11-16 同步入库；待正式补充至算法仓库 |

## 算法理解

将站点观测融合到规则格点场，面向 `meteva_base` 站点表与六维格点场。四个插件接口统一为 `process(sta, grid, background=None)`：无背景时直接插值站点值到目标格点；有背景时先对齐背景场再参与融合（IDW / Gaussian / Kriging 为偏差订正，Cressman 为初估场）。

核心源码包括：

- `src/interp_sg_idw_plugin.py`：`InterpSgIdw`，反距离权重；可选高斯衰减与背景偏差订正。CLI 别名 `idw_delta` 对应 Idw + `gaussian`。
- `src/interp_sg_gaussian_plugin.py`：`InterpSgGaussian`，最近邻 × 高斯半径扩散；可选背景偏差订正。
- `src/interp_sg_kriging.py`：`InterpSgKriging`，局部普通克里金（OK）；可选背景偏差订正。
- `src/interp_sg_cressman_plugin.py`：`InterpSgCressman`，Cressman 逐步订正；可选背景作初估场。

背景对齐依赖同级包 `grid_grid_fusion.InterpGgLinear`（`outer_value` 控制越界填充）。该包已同步至 `00temp/grid_grid_fusion`；旧包 `interp_gg_linear` 已删除。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/station_grid_fusion/src/` | 四插件：`InterpSgIdw` / `InterpSgGaussian` / `InterpSgKriging` / `InterpSgCressman` |
| `00temp/station_grid_fusion/cli/` | `python -m cli` 与 `station_grid_fusion_cli.py` |
| `00temp/station_grid_fusion/resource/` | `conf.ini` CLI 缺省参数与说明 |
| `00temp/station_grid_fusion/test/` | 配置与算法测试（含 Cressman / Kriging 等） |
| `00temp/station_grid_fusion/nbs/` | 示例 notebook（含说明 notebook） |
| `00temp/station_grid_fusion/docs/` | `station_grid_fusion.md` |
| `00temp/station_grid_fusion/utils/` | `util_env.py` 等运行配置辅助 |

## 2026-11-16 更新

- 自 `D:\workspace\test\00temp\station_grid_fusion` 增量同步至 `00temp/station_grid_fusion/`；未修改、未删除源目录；未同步 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints` 及大体量 `resource/data`。
- 重构为 4 插件：`InterpSgIdw` / `InterpSgGaussian` / `InterpSgKriging` / `InterpSgCressman`；统一 `process(sta, grid, background=None)`。
- `idw_delta` 为 CLI 别名，对应 Idw + gaussian。
- 已删除中间目录中源侧已不存在的旧模块：`interp_sg_total_plugin.py`、`interp_sg_idw_delta_plugin.py`、`interp_sg_delta_gaussian_plugin.py`、`interp_station_to_grid_renew.py`，以及 `resource/fusion.ini`。
- 同步校验：27 个 `.py`/`.md`/`.ini`/`.ipynb` 文件哈希与源一致。
- **依赖**：背景对齐对接同级 `grid_grid_fusion.InterpGgLinear`（已入库）；旧 `interp_gg_linear` 目录已删除。

同步文件概要：

- NEW：`src/interp_sg_cressman_plugin.py`、`src/interp_sg_gaussian_plugin.py`、`src/interp_sg_kriging.py`、`nbs/station_grid_fusion_说明.ipynb`、`test/conftest.py`、`test/test_cressman.py`、`test/test_kriging_math.py`
- DIFF：`cli/README.md`、`cli/station_grid_fusion_cli.py`、`docs/station_grid_fusion.md`、`resource/conf.ini`、`src/interp_sg_idw_plugin.py`、`src/__init__.py`、`test/README.md`、`test/test_cli_config.py`、`test/test_idw_delta.py`、`test/test_idw_gaussian.py`、`test/test_interp.py`、`utils/util_env.py`
- SAME：`cli/fusion_main.py`、`cli/__init__.py`、`cli/__main__.py`、既有 notebook、`resource/README.md`、`utils/README.md`、`utils/__init__.py`

## 2026-06-29 更新

- 初整至中间目录 `00temp/station_grid_fusion/`；原始路径为 `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\00_sta_grid_interp`。
- 当时核心为 `InterpSgIdw` / `InterpSgIdwDelta` / `InterpSgDeltaGaussian` / `InterpSgTotal` 及 `interp_station_to_grid_renew.py`（已在 2026-11-16 重构移除）。
- 未删除或移动任何原始文件；未补充到正式 `NIMM/08consistense/`。

## 2026-11-16 与 `interp_sg_cressman` 的关系

- 本包 `InterpSgCressman` 为**经典逐步订正**（创新量累加）；独立包 `interp_sg_cressman` 为**观测加权覆盖**，算法不同，**并存**。
- 曾误删独立包并改接频率匹配；已恢复 `00temp/interp_sg_cressman`，`frequency_matching_rain24` 仍引用旧包行为。

## 仍存在问题（需人工补充）

1. 依赖同级包 `grid_grid_fusion.InterpGgLinear` 已于 2026-11-16 同步入库；正式联调/导入路径仍需确认。
2. 补充至正式 `NIMM/08consistense/` 时需调整为仓库正式包路径。
3. 依赖 `meteva_base`、`numpy`、`scipy`、`utils.base_plugin` 等，正式测试前需确认环境。
4. 未同步大体量测试/资源数据；`resource/` 以 `conf.ini` 与说明为主。
