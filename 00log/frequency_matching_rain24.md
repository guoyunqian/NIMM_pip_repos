# 逐日降水频率匹配订正整理日志

## 原始算法信息

- 算法名称：`frequency_matching_rain24`
- 中文名称：逐日降水频率匹配订正
- 原始工程名：`qpf_fm_rain24`
- 原始路径：`D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\qpf_fm_rain24`
- 算法类型：`04single_calibration`
- 贡献人：郭云谦、陈荣、李东勇
- 整理日期：2026-06-29

## 算法理解

原始算法 `optimize_tp_24h` 针对 24 小时累积降水预报进行频率匹配订正。算法先基于历史模式场与当前模式场进行相似个例检索，再对切片区域执行光流位移订正和频率匹配，最后融合站点订正结果与模式背景场，生成订正后的站点和格点降水产品。

## 本次整理操作

- 在 `00temp/frequency_matching_rain24/` 下创建统一中间目录。
- 将原始 `src/`、`cli/`、`resource/`、`test/`、`nbs/`、`docs/`、`utils/` 复制到中间目录。
- 复制根目录 `README.md` 和 `requirements-cli.txt`，保留原工程说明和依赖信息。
- 将原始 `log/` 复制到 `resource/original_log/`，保留运行日志用于追溯。
- 过滤 `__pycache__`、`.pyc` 和 `.ipynb_checkpoints` 生成缓存，未删除或修改原始目录文件。
- 新增 `docs/逐日降水频率匹配订正.md`，补充算法功能、目录结构、入口、CLI 示例和当前限制。
- 更新 `NIMM_list.md`，追加该算法整理记录。

## 验证记录

- 使用 Codex 捆绑 Python 对中间目录全部 Python 文件执行 `compileall` 语法编译，结果通过。
- 使用 Python 导入 `utils.util_env.get_resolved_paths` 并读取路径配置，结果通过。
- 尝试导入 `src/correct_tp_24h.py` 主流程，因当前环境未安装 `meteva`，报 `ModuleNotFoundError: No module named 'meteva'`，未执行完整业务流程。
- 本次验证生成的 `__pycache__` 已清理。

## 中间目录结构

- 源码位置：`00temp/frequency_matching_rain24/src/`
- CLI位置：`00temp/frequency_matching_rain24/cli/`
- 资源位置：`00temp/frequency_matching_rain24/resource/`
- 测试位置：`00temp/frequency_matching_rain24/test/`
- Notebook位置：`00temp/frequency_matching_rain24/nbs/`
- 文档位置：`00temp/frequency_matching_rain24/docs/`
- 工具位置：`00temp/frequency_matching_rain24/utils/`

## 2026-11-27 Cressman 改走 InterpSg，插值适配层改用正式插值包

- 自 `D:\workspace\test\00temp\frequency_matching_rain24` 与算法仓库现有内容做**三方合并**后同步至 `00temp/frequency_matching_rain24/`（基线为算法仓库 `c20b191`，仓库 `ef092bd` 之后的改动与本地改动分别核对，不整目录覆盖）；未修改、未删除源目录。仅覆盖仓库工作区，未执行 git 提交。
- 同步范围：`src/`、`cli/`、`docs/`、`test/`、`nbs/`、`NIMM_list.md`；跳过 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`；`resource/` 下的数据不同步（`resource/r24/` 示例数据、`resource/output/`、`resource/showdoc_demo/` 均不入仓库），`ecmwf_v2/`、`log/` 为运行产物亦不同步；无 >5MB 需跳过项。
- **Cressman 统一经 `InterpSg`**：`GressManInterpolation`（`interpolation_station_grid.src.gressman_plugin`，该模块在仓库中已不存在）全部替换为 `InterpSg(method="cressman", reprocess=True, degree_blend=...)`；涉及 `src/frequency_matching_rain24_plugin.py`、`cal_optical_flow.py`、`cal_slice_tp.py`、`correct_tp_24h.py`、`frequency_matching_rain24_plugin_util.py`、`cli/frequency_matching_rain24_cli.py`。`match_mode=original` 的 Cressman 为 `InterpSg(..., degree_blend=1.0)`（与原 `GressManInterpolation` 度制形态一致），插件内 `cressman_fn=None` 时直接使用；`aligned`（默认）由 CLI 注入 `cressman_project_innov`（`degree_blend=0.85`）+ `LagrangianAligned`。**保持 `ef092bd` 的 `cressman_fn` 注入结构**：`_cressman_and_lagrangian` 仍返回 `(切片函数, 格点函数, 外推类)`（`original` 为 `(None, None, Lagrangian)`），插件类 `correct_by_opticalFlow` / `OpticalFlowSliceCorrectPlugin` / `CressmanFreqMatchGridPlugin` 仍接收 `cressman_fn`；`cal_slice_tp` / `correct_tp_24h` 的 `cressman_fn` 注入同样保留。
- **`src/interpolation.py` 改为适配层**：`mesh_val` → `interpolation_grid_grid.InterpGgLinear(outer_value=0.0)`，`bilinear_interp` → `interpolation_grid_station.InterpGsLinear(used_coords="xy")`；不再导出 `GressManInterpolation`。`interpolation_gg_linear.py` 的格点→站点同样转发 `InterpGsLinear`；`interpolation_sg_cressman.py` 的度→距离换算由 111000 m 改为千米（`ER·π/180`），与 `InterpSgCressman` 的千米单位一致。
- **光流与外推来源（本包独立）**：`frequency_matching_rain24_plugin.py` 沿用仓库 `ef092bd` 的设计，使用本包 `cal_optical_flow` 的 `Lagrangian` / `OpticalFlow`，不依赖 `optical_flow_nowcast`；`cal_optical_flow.py` 内部 Cressman 已改用 `InterpSg`。对照验证：与 `optical_flow_nowcast` 的 `Lagrangian`、`OpticalFlow`（单场、多场）在同一份合成降水场上结果逐位相同（最大差 0.0）。
- **`src/utils/cressman_extrap_reprocess.py`**：保留 `cressman_project_innov(sta, grd, distance_limits, ...)`，改为 `InterpSg(method="cressman", reprocess=True, degree_blend=0.85)` 的旧签名薄封装（站点为空返回背景场副本；与直接调用 `InterpSg(degree_blend=0.85)` 在同一份合成数据上结果逐位相同），供 `aligned` 注入（原 `ef092bd` 版直接构造 `InterpSgCressman`）；删除 `cressman_innov_gressman_like`（依赖不存在的 `gressman_plugin`）、`cressman_innov_wrap`、`project_innov_wrap` 别名（仓库内无调用方）；保留 `LagrangianAligned`、`extrapolate_like_lagrangian`、`OpticalFlowProject`；对 `optical_flow_nowcast`（`Extrapolation.forecast`、`LsqrOpticalFlow`）改为**按需延迟加载**（采用 `ef092bd` 的延迟思路，加载前后保存并恢复 `src`、`utils` 的模块缓存与 `sys.path`），只在 `aligned` 或项目版路径首次用到时才导入，`original` 模式导入插件不再加载 nowcast。**删除** `src/utils/project_align.py`。
- **文档/笔记本**：仓库已于 11-26 把 `docs/`、`nbs/` 改为以包名命名，本次内容并入现有文件名（`docs/frequency_matching_rain24.md`、`docs/frequency_matching_rain24_overview.md`、`nbs/frequency_matching_rain24.ipynb`），`NIMM_list.md` 更新；`overview` 文档与 `NIMM_list.md` 为两边无冲突合并。
- **测试与 demo**：`test/test_correct_tp_24h_entry.py`、`test/test_apply_interp_optical_flow.py` 与 9 个 `test/demo_*.py` 同步改用 `InterpSg`（路径指向 `interpolation_station_grid`，半径改千米）。
- **合并决策（需知晓）**：仓库 `ef092bd`（11-26）在三个文件上与本地冲突，处理结果：
  - `frequency_matching_rain24_plugin.py`：**保留 `ef092bd` 的设计**（用本包 `cal_optical_flow`），并去掉其对 `gressman_plugin` 的间接依赖（`cal_optical_flow` 与 `interpolation.py` 已改用 `InterpSg`、`InterpGgLinear`）。
  - `interpolation.py`：`ef092bd` 仍 `from gressman_plugin import ...`（该模块从未提交进仓库，仅存在于弃用包本地副本），**取本地适配层**，改转发 `InterpGgLinear` / `InterpGsLinear`。
  - `cressman_extrap_reprocess.py`：**保留 `ef092bd` 的 `cressman_project_innov` 及其在 `aligned` 的调用结构**（改为转发 `InterpSg`，不再依赖旧包路径），同时**吸收 `ef092bd` 的延迟加载思路**；`cressman_innov_gressman_like`、`cressman_innov_wrap`、`project_innov_wrap` 未保留，仓库内无调用方，需要时可从 `ef092bd` 取回。
- **测试**（在算法仓库副本内逐文件运行）：`test_correct_tp_24h_entry.py` 6 passed、`test_apply_interp_optical_flow.py` 4 passed；`test_multi_optimize_tp_24h.py` 2 passed / 7 failed（沿用旧 CLI 结构，待重写）；`test_compare_version.py` 含 `D:/Work/...` 硬编码路径，未运行。整目录在同一进程内运行会因 `cli` 模块重名失败，需逐文件运行。
- 依赖：`original` 模式需同级目录 `interpolation_station_grid`、`interpolation_grid_grid`、`interpolation_grid_station` 及 `00temp/utils`；`aligned` 模式与项目版（`correct_tp_24h_nowcast`、`cal_optical_flow_nowcast`）另需 `optical_flow_nowcast`（按需加载）。

## 仍存在问题

> 以下 2026-06-29 的条目为当时记录，部分已过期（例如 11-23 起已有插件类与 `process()`），最新状态以各日期小节为准。

- 2026-11-27 新增：`test/test_multi_optimize_tp_24h.py` 需按当前 CLI 结构重写（7 项失败）；`docs/` 中引用 `../resource/output/pngs/...` 的图片未随仓库同步，链接在仓库内会失效；`gressman_plugin` 仅存在于弃用包 `interp_sg_cressman` 的本地副本（未入仓库），crong 本地若仍有基于它的代码，拉取本次改动后需要同步迁移到 `InterpSg`。
- 核心入口为 `src/correct_tp_24h.py::mainProcess`，尚未封装为仓库规范中的算法插件类和 `process()` 方法。
- 完整运行依赖 `meteva`、真实模式 24 小时降水、站点实况、站点模板和掩码文件。
- `resource/plugin/*.json` 保留生产路径模板，正式运行前需改为目标环境路径。
- `resource/optimize_tp_24.ini` 当前默认包含回算起报时间，正式业务部署前需确认实时/回算配置。
- `src/verify_data/` 暂按原始结构保留，后续可考虑迁移到 `test_data/` 并调整测试引用。
- 尚未运行完整业务测试。
