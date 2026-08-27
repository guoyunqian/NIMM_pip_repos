# simple_bias_correction 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `simple_bias_correction` |
| 中文名称 | 简单加性偏差订正 |
| 原始路径 | `D:\workspace\improver\simple_bias_correction` |
| 整理日期 | 2026-08-27（初整） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `04single_calibration` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法迁移自 Met Office IMPROVER `improver/calibration/simple_bias_correction.py`，用于单数值模式偏差订正：由历史预报与实况估计空间偏差场，再对当前预报做加性订正。输入适配 `meteva_base` 六维网格（`member, level, time, dtime, lat, lon`），主入口为 `xarray.DataArray`，底层误差/订正函数亦支持 `numpy.ndarray`，缺测统一用 `NaN` 表示。

核心计算：

```text
error     = forecast - truth
bias      = mean_over_time(error)     # CalculateForecastBias
corrected = forecast - bias           # ApplyBiasCorrection
```

核心源码包括：

- `src/simple_bias_correction.py`
  - `evaluate_additive_error`：计算平均加性误差（预报减实况），两侧缺测取并集。
  - `apply_additive_correction`：订正量 = 预报减偏差，偏差单位对齐预报。
  - `CalculateForecastBias`：历史样本按有效时刻配对、检查起报钟点与时效一致后沿 `time` 求平均，输出偏差场 `forecast_error_of_<原预报名>`。
  - `ApplyBiasCorrection`：拆分预报/偏差、支持多偏差沿起报时间平均、可选物理上下界裁剪与偏差 NaN 填 0。
- `src/utils/_calibration_utilities.py`
  - 时间配对、单位换算、`time_bounds` 占位清理、概率场拒绝等辅助函数。

CLI 调度：

- `cli/cal_calculate_forecast_bias.py`：读历史预报/实况 nc，写出偏差场。
- `cli/prb_bias_correction.py`：读当前预报与偏差 nc，写出订正场。
- `cli/preprocess_test_data.py`：官方投影样例预处理为 meb / 经纬对照输入。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/simple_bias_correction/src/simple_bias_correction.py` | 核心偏差计算与订正算法 |
| `00temp/simple_bias_correction/src/utils/` | 时间配对、单位换算等内部辅助 |
| `00temp/simple_bias_correction/cli/` | CLI 调度与测试数据预处理 |
| `00temp/simple_bias_correction/utils/` | 本地 `BasePlugin` |
| `00temp/simple_bias_correction/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/simple_bias_correction/resource/` | 资源文件（当前为空） |

## 2026-08-27 更新

- 首次整理至中间目录：从 `D:\workspace\improver\simple_bias_correction` 完整同步源码、CLI、文档、notebook 与测试。
- 包名保留原名 `simple_bias_correction`（已直观标明算法功能），源码导入已使用包名，无需调整导入路径。
- `test_data/` 未同步（由独立仓库存放，正式入库前筛选）。
- 新增整理说明文档 `docs/simple_bias_correction_overview.md`。
- 原目录与中间目录 pytest 均 195 passed。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/04single_calibration/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. 测试样例在 `test_data/`（约 6.10MB，含官方投影与经纬对照、CLI 输出对照），中间目录未同步；正式入库前筛选必要样例至 `NIMM_pip_testdata`。
4. `resource/` 当前为空，正式补充时确认是否保留。
