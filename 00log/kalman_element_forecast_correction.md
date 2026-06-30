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
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

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

1. 原始代码导入路径仍使用 `nimm_kalman...` 包名。当前中间目录保持原样，后续补充至正式仓库时需要统一调整为 `NIMM` 下的实际包路径。
2. 默认生产路径包含 `/data234/GUO_data/Kalman_data`、`/data234/DataPool/01CLDAS/00HRCLDAS/Hourly`、`/data/mnt/model_RT/globalECMWF_D1D/...`，正式测试需替换为仓库内可复现样例。
3. 原始目录没有独立 `test_data/`，需要补充最小 NetCDF 测试样例。
4. 完整业务流程依赖 `meteva_base`、`xarray`、`numpy` 和真实网格数据环境。
5. 现有单元测试主要覆盖 `grid_utils`，后续建议补充 `KalmanME`、`KalmanFix` 插件级测试和 CLI 路径模板测试。

