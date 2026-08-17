# kalman_element_forecast_correction 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `kalman_element_forecast_correction` |
| 中文名称 | kalman滤波要素预报订正 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\nimm_kalman` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、曹勇、陈荣 |
| 算法分类 | `04single_calibration` |
| 当前状态 | 已补充至正式算法仓库目录 |

## 算法理解

该算法用于要素预报的 Kalman 滤波偏差订正。核心流程包括：

- 根据最新预报和实况更新 Kalman 平均误差场或平均绝对误差场。
- 使用最新误差场对当前预报进行订正。
- 按变量 `SWVL`、`STL` 和层级 `5/10/40` 循环处理业务路径模板。
- 支持源数据复制、误差场写出和订正结果写出。

核心源码包括：

- `src/kalman_me_plugin.py`：`KalmanME` 误差场更新插件。
- `src/kalman_fix_plugin.py`：`KalmanFix` 预报订正插件。
- `src/kalman_cli.py`：业务流程调度，包括回溯历史误差场、读取预报/实况和写出结果。
- `src/data_transfer.py`：原始数据复制流程。
- `utils/grid_utils.py`：网格校验、坐标匹配、误差更新和订正数值计算。

## 分类说明

用户初始给定分类为 `05blending`。根据仓库分类定义和代码内容，该算法不做多模式融合，而是针对单要素预报进行 Kalman 偏差订正，因此经用户确认后分类调整为 `04single_calibration`。

## 本次整理操作

已将原始目录内容复制到中间目录：

`00temp/kalman_element_forecast_correction/`

复制内容包括：

- `src/`：核心算法源码。
- `cli/`：命令行入口。
- `docs/`：原始说明文档，并新增 `kalman_element_forecast_correction.md`。
- `nbs/`：notebook 示例。
- `resource/`：资源说明目录。
- `test/`：单元测试。
- `utils/`：算法内部工具函数。
- 根目录配置和包装脚本：`__init__.py`、`pyproject.toml`、`setup.py`、`setup.cfg`、`pytest.ini`、`kalman_data.sh`、`trans_data.sh`。

新增内容包括：

- `test_data/README.md`：说明原始目录无独立测试数据，正式入库前需补充最小样例。

未执行操作：

- 未删除或移动任何原始文件。
- 未复制 `__pycache__` 和 `.pyc` 编译缓存。
- 未补充到正式 `NIMM/04single_calibration/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/kalman_element_forecast_correction/src/` | 核心算法源码 |
| `00temp/kalman_element_forecast_correction/cli/` | CLI 调度入口 |
| `00temp/kalman_element_forecast_correction/resource/` | 资源说明目录 |
| `00temp/kalman_element_forecast_correction/test/` | 测试脚本 |
| `00temp/kalman_element_forecast_correction/test_data/` | 测试数据说明，待补充最小样例 |
| `00temp/kalman_element_forecast_correction/nbs/` | notebook 示例 |
| `00temp/kalman_element_forecast_correction/docs/` | 文档 |
| `00temp/kalman_element_forecast_correction/utils/` | 算法内部工具函数 |

## 已发现问题与后续建议

1. `00temp/` 中间目录仍保持原始 `nimm_kalman...` 包名；正式归档目录已调整为仓库内相对导入或动态导入。
2. 默认生产路径包含 `/data234/GUO_data/Kalman_data`、`/data234/DataPool/01CLDAS/00HRCLDAS/Hourly`、`/data/mnt/model_RT/globalECMWF_D1D/...`，正式测试需替换为仓库内可复现样例。
3. 原始目录没有独立 `test_data/`，需要补充最小 NetCDF 测试样例。
4. 完整业务流程依赖 `meteva_base`、`xarray`、`numpy` 和真实网格数据环境。
5. 现有单元测试主要覆盖 `grid_utils`，后续建议补充 `KalmanME`、`KalmanFix` 插件级测试和 CLI 路径模板测试。

## 2026-07-13 正式归档操作

已按仓库规范将该算法补充至正式算法仓库目录，未修改 Kalman 误差更新和订正计算逻辑。

归档目录包括：

| 正式目录 | 内容说明 |
| --- | --- |
| `NIMM/04single_calibration/kalman_element_forecast_correction/` | 核心算法源码、插件类、业务流程和算法内部工具 |
| `cli/04single_calibration/kalman_element_forecast_correction/` | CLI 调度入口 |
| `docs/04single_calibration/kalman_element_forecast_correction/` | 算法文档 |
| `nbs/04single_calibration/kalman_element_forecast_correction/` | notebook 示例 |
| `resource/04single_calibration/kalman_element_forecast_correction/` | 资源说明 |
| `test/04single_calibration/kalman_element_forecast_correction/` | 单元测试 |

本次调整包括：

- 将 `src/kalman_cli.py` 归档为 `kalman_workflow.py`，明确其为业务流程而非 CLI 参数入口。
- 将 `cli/kalman_data.py` 和 `cli/trans_data.py` 分别归档为 `kalman_data_main.py`、`trans_data_main.py`。
- 将 Kalman 专用的 `base_plugin.py`、`grid_utils.py` 放入算法内部 `utils/`，未提升为全局公共工具。
- 正式目录源码已移除原始 `nimm_kalman` 导入路径，改为相对导入或 `importlib.import_module()` 动态导入，以兼容 `04single_calibration` 数字开头目录名。
- 在正式 `src`/`cli` 对应代码中补充算法贡献人和软件产权说明。
- 已运行 `test/04single_calibration/kalman_element_forecast_correction/test_grid_utils.py` 的纯数值单元测试。

仍需后续补充或审核：

- 默认生产路径仍依赖 `/data234/GUO_data/Kalman_data`、`/data234/DataPool/01CLDAS/00HRCLDAS/Hourly` 和 `/data/mnt/model_RT/globalECMWF_D1D/...`。
- 完整业务流程仍依赖 `meteva_base`、`xarray`、`numpy` 和真实 NetCDF 网格数据环境。
- 测试数据仓库当前缺少 `fcst_new.nc`、`obs_new.nc`、`me_before.nc`、`expected_result.nc` 等最小端到端样例。
- 因上述外部数据和环境未提供，尚未运行完整业务端到端测试。

## 2026-08-17 代码更新

本次以 `D:\nimm-file\cli_code\nimm_kalman` 为更新源，同步用户改进后的 Kalman 算法代码。

更新内容包括：

- 将新版代码同步到 `00temp/kalman_element_forecast_correction/`，复制时排除 `__pycache__` 和 `.pyc` 缓存文件。
- 将新版核心源码同步到 `NIMM/04single_calibration/kalman_element_forecast_correction/`。
- 将新版 CLI、测试、文档和 notebook 同步到正式分类目录。
- 正式目录继续保持相对导入或动态导入，未恢复原始 `nimm_kalman` 包路径。
- CLI 新增/保留 `--obs-end-time` 参数，用于限制最新可用观测时间。
- 已运行正式目录下的最小数值单元测试。

仍需后续补充或审核：

- 完整业务流程仍依赖生产路径、`meteva_base` 和真实 NetCDF 网格资料。
- 独立最小端到端测试数据仍未补充。

