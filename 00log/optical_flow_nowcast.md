# optical_flow_nowcast 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `optical_flow_nowcast` |
| 中文名称 | 临近光流法外推预报 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\nowcast` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、陈荣、丰硕 |
| 算法分类 | `03nowcast` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于临近降水外推预报。核心流程是使用 Lucas-Kanade 光流法从连续实况降水场中估计二维平流速度场，再使用半拉格朗日方法将最近一次降水场向未来多个时效外推。

原始目录中还包含 LINDA、S-PROG、STEPS 等相关临近预报算法实现。由于它们与光流和外推共用工具函数、示例和数据，本次作为同一原始目录内容一并保留。

核心能力包括：

- `LK`：基于 Lucas-Kanade 特征追踪计算平流速度场。
- `Extrapolation`：基于平流速度场执行临近外推。
- `Linda`、`Sprog`、`Steps`：同目录内相关临近预报插件。

## 本次整理操作

已将原始目录内容整理到中间目录：

`00temp/optical_flow_nowcast/`

整理内容包括：

- `src/`：复制原始核心源码，并新增 `__init__.py` 与 `base_plugin.py`。
- `nbs/`：复制原始 notebook 示例。
- `test_data/`：复制原始 NetCDF 输出样例。
- `cli/`：新增归档占位入口，原始目录未提供独立 CLI。
- `docs/`：新增 `optical_flow_nowcast.md` 归档说明。
- `resource/`、`utils/`：新增说明文件，补齐仓库规范目录。
- `test/`：新增最小输入校验测试脚本。

已执行的规范化调整：

- 未删除或移动任何原始文件。
- 未复制 `__pycache__` 和 `.pyc` 缓存文件。
- 原始插件继承 `nimm.PostProcessingPlugin`；归档副本提供轻量 `PostProcessingPlugin` 兼容基类。
- 原始内部导入 `nimm.nowcast.*`；归档副本已调整为 `optical_flow_nowcast.src.*`。
- `src/__init__.py` 使用懒加载，避免包根导入时立即要求完整业务依赖。
- 新增 `pyproject.toml`、`setup.py`、`setup.cfg` 和 `pytest.ini`。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/optical_flow_nowcast/src/` | 核心算法源码与插件类 |
| `00temp/optical_flow_nowcast/cli/` | CLI 占位入口 |
| `00temp/optical_flow_nowcast/resource/` | 资源说明 |
| `00temp/optical_flow_nowcast/test/` | 最小测试脚本 |
| `00temp/optical_flow_nowcast/test_data/` | 原始输出样例数据 |
| `00temp/optical_flow_nowcast/nbs/` | notebook 示例 |
| `00temp/optical_flow_nowcast/docs/` | 算法说明文档 |
| `00temp/optical_flow_nowcast/utils/` | 工具说明目录 |

## 2026-11-27 LsqrOpticalFlow 改走 InterpSg / InterpGgLinear

- 自 `D:\workspace\test\00temp\optical_flow_nowcast` 与算法仓库现有内容做**三方合并**后同步至 `00temp/optical_flow_nowcast/`（基线为算法仓库 `c20b191`）；未修改、未删除源目录。仅覆盖仓库工作区，未执行 git 提交。
- 同步范围：`src/lsqr_optical_flow_plugin.py`、`docs/optical_flow_nowcast.md`。其余本地文件与仓库一致；不同步 `test_data/output/`（运行产物）与 `resource/showdoc_demo/`（ShowDoc 制作产物）；跳过 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`；无 >5MB 需跳过项。
- **`src/lsqr_optical_flow_plugin.py`**：稀疏 UV 铺密由 `gressman_plugin.GressManInterpolation`（该模块在仓库中已不存在）改为同级 `interpolation_station_grid.InterpSg(method="cressman", reprocess=True, degree_blend=1.0)`，网格重采样 `mesh_val` 改为 `interpolation_grid_grid.InterpGgLinear(outer_value=0.0)`（越界填 0，保留 `member` 坐标）；路径辅助函数改名为 `_ensure_interp_packages_on_path`，加入 `00temp` 根、`interpolation_station_grid/src`、`interpolation_grid_grid/src`。
- **`docs/optical_flow_nowcast.md`**：仅措辞调整：两个小节标题改为"窗域最小二乘（`LsqrOpticalFlow`）""半拉格朗日平流（`Lagrangian`）"，CLI 说明段中的 `LsqrOpticalFlow` 改称"窗域最小二乘"。
- **保留仓库已有改动**：11-26 的 `cli/*_cli.py` 输出（`save_grid_result`）、`resource/conf.ini` 的 `output` 键、`utils/cli_grid_io.py`、`utils/util_env.py`、`src/lk_plugin.py` 的掩码类型修正，以及 `nbs/optical_flow_nowcast_{extrapolation,linda,sprog,steps}.ipynb` 的命名，均不受本次同步影响。`nbs/optical_flow_nowcast.ipynb` 本地与仓库内容一致、仅 kernel 名不同，保留仓库版本（`python3`）。
- **测试**：在算法仓库内运行 `pytest test` 为 10 passed。
- 依赖：`LsqrOpticalFlow` 现需同级目录 `interpolation_station_grid`、`interpolation_grid_grid` 与 `00temp/utils` 共存。
- 联动：`frequency_matching_rain24` 的 `aligned` 模式与项目版仍按需引用本包的 `Extrapolation.forecast` / `LsqrOpticalFlow` / `LK`；其 `original` 模式使用 `rain24` 自带的 `cal_optical_flow`，不依赖本包。本包 `Lagrangian`、`OpticalFlow` 与 `rain24` 的同名实现在同一份合成数据上结果逐位相同。

## 已发现问题与后续建议

> 以下 2026-06-29 的条目为当时记录，部分已过期（例如已补充 CLI 与 docs），最新状态以各日期小节为准。


1. 完整运行依赖 `scipy`、`scikit-image`、`opencv-python`、`pandas`、`xarray`、`meteva-base` 等环境；当前运行时未安装这些依赖。
2. `temp_demo.py` 和 notebook 中仍保留原始 `/home/nimm` 与 `nimm.cli.nimm.*` 示例路径，正式入库前建议改写为仓库内 CLI 或删除生产路径示例。
3. 原始目录没有独立 CLI、docs、test、resource、utils 结构，本次已补齐基础归档骨架，但业务 CLI 仍需后续按仓库规范补充。
4. 当前归档目录尚未补充到正式 `NIMM/03nowcast/` 目录。

## 校验记录

- 使用 Codex bundled Python 执行 `python -m compileall -q .`，语法编译通过。
- 包根和 `optical_flow_nowcast.src` 懒加载入口导入通过。
- 直接导入核心 `extrapolation` 模块时，当前运行时缺少 `scipy`，未能继续执行核心 smoke test。
