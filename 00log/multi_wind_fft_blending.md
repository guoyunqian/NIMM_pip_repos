# multi_wind_fft_blending 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `multi_wind_fft_blending` |
| 中文名称 | 多风场FFT融合 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\FftForNimm` |
| 整理日期 | 2026-06-29（初整）；2026-07-22（入口 + is_multi）；2026-07-23（CLI / main 职责分离） |
| 算法贡献人 | 胡海川、李振、郭云谦 |
| 算法分类 | `05blending` |
| 当前状态 | 已整理至中间目录；`process` 可模块调度；CLI 在 `cli/`；待补样例与正式入库 |

## 算法理解

该算法用于多风场 FFT 特征匹配融合。核心类 `FFTMergePlugin` 基于频域谱方法和迭代优化计算主风场与辅助风场之间的二维位移场，再对主风场进行平流，得到特征对齐后的融合风场。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/multi_wind_fft_blending/src/fft_merge.py` | 核心算法 |
| `00temp/multi_wind_fft_blending/src/main.py` | `process` 供模块引用；`__main__` 直接传参运行 |
| `00temp/multi_wind_fft_blending/cli/__main__.py` | `python -m cli` 解析参数 → `main.process` |
| `00temp/utils/multipro_plugin.py` | 共享多进程工具（`SimpleParallelTool`） |
| `00temp/multi_wind_fft_blending/test/` | `test_fft_merge.py`、`test_main.py` |
| `NIMM_pip_testdata/multi_wind_fft_blending/test_data/` | 与仓库同级的样例数据目录（需人工补齐） |
| `00temp/multi_wind_fft_blending/docs/`、`nbs/` | 文档与 notebook |
| `00temp/multi_wind_fft_blending/00temp/` | 整理过程中间数据 |
| `00temp/multi_wind_fft_blending/00log/` | 整理过程日志（一次整理一份） |
| `00temp/multi_wind_fft_blending/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-23 更新

- argparse 从 `src/main.py` 迁至 `cli/__main__.py`。
- `src/main.py` 仅保留可调度 `process`；`__main__` 中直接给 `process` 传参（对齐 `multi_weather_phenom_grid_12h`）。
- 详细过程见：`00temp/multi_wind_fft_blending/00log/fft_merge_整理_20260723.log`。

## 2026-07-22 更新

- 新增 `src/main.py`：`process` 显式传参、`is_multi` / `pro_count`。
- 废弃 `cli/fft_merge_cli.py`；样例改为同级 `NIMM_pip_testdata`。
- 详见：`00temp/multi_wind_fft_blending/00log/fft_merge_整理_20260722.log`。

## 仍存在问题（需人工补充）

1. `NIMM_pip_testdata/multi_wind_fft_blending/test_data/` 样例缺失，需补齐 `sample_a1/a2_uv.m11`、`sample_b1/b2_uv.m11`。
2. `nbs/` 中旧 `resource/` / `fft_merge_cli.py` 文案需人工核对。
3. `FFTMergePlugin` 未继承仓库统一 `BasePlugin`。
4. 尚未补充到正式 `NIMM/05blending/` 目录。
5. 未做完整业务数据试跑与结果对比。
