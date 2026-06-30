# multi_wind_fft_blending 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `multi_wind_fft_blending` |
| 中文名称 | 多风场FFT融合 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\FftForNimm` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 胡海川、李振、郭云谦 |
| 算法分类 | `05blending` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于多风场 FFT 特征匹配融合。核心类 `FFTMergePlugin` 基于频域谱方法和迭代优化计算主风场与辅助风场之间的二维位移场，再对主风场进行平流，得到特征对齐后的融合风场。

核心能力包括：

- 支持 `member=2` 的 `u/v` 矢量风融合。
- 支持 `member=1` 的标量场融合。
- 支持多个辅助风场，对各辅助场分别计算位移后取平均。
- 支持通过 `feature_border`、`max_iterations` 和 `move_percent` 控制效率、迭代和移动幅度。

## 本次整理操作

已将原始目录内容整理到中间目录：

`00temp/multi_wind_fft_blending/`

整理内容包括：

- `src/fft_merge.py`：由原始根目录 `fft_merge.py` 复制而来。
- `cli/fft_merge_cli.py`：由原始根目录 `ftt_merge_cli.py` 复制并修正拼写。
- `cli/__main__.py`：已修正为调用 `cli/fft_merge_cli.py`。
- `docs/`：复制原始说明文档，并新增 `multi_wind_fft_blending.md`。
- `nbs/`：复制 notebook 示例。
- `resource/`：复制 Micaps11 和 NetCDF 样例数据及参考输出。
- `test/`：复制测试脚本，并将 `test_ftt_merge_cli.py` 改名为 `test_fft_merge_cli.py`。
- `test_data/`、`utils/`：原始目录无对应内容，已保留空目录以符合中间目录结构。

未执行操作：

- 未删除或移动任何原始文件。
- 未复制 `__pycache__` 编译产物。
- 未补充到正式 `NIMM/05blending/` 目录。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/multi_wind_fft_blending/src/` | 核心算法源码 |
| `00temp/multi_wind_fft_blending/cli/` | CLI 调度与示例脚本 |
| `00temp/multi_wind_fft_blending/resource/` | 样例数据、参考输出和依赖记录 |
| `00temp/multi_wind_fft_blending/test/` | 单元测试 |
| `00temp/multi_wind_fft_blending/test_data/` | 原始目录无独立测试数据，当前为空 |
| `00temp/multi_wind_fft_blending/nbs/` | notebook 示例 |
| `00temp/multi_wind_fft_blending/docs/` | 文档 |
| `00temp/multi_wind_fft_blending/utils/` | 原始目录无工具函数，当前为空 |

## 已发现问题与后续建议

1. 原始 CLI 文件名为 `ftt_merge_cli.py`，拼写错误。本次中间整理已改为 `fft_merge_cli.py`，并同步修正 `cli/__main__.py`、测试和说明文档中的引用。
2. 原始源码直接位于根目录。本次已放入 `src/fft_merge.py`，后续补充至正式仓库时需要统一导入路径。
3. CLI 示例会写入或覆盖 `resource/sample_*_fft_*` 和 `resource/sample_*_line_*` 文件，正式测试前应区分输入样例、参考输出和运行生成结果。
4. 当前未运行完整 pytest 测试。正式补充前应确认环境依赖，包括 `numpy`、`scipy`、`meteva`、`click`、`xarray`、`pytest`。
5. `FFTMergePlugin` 已提供类和 `process` 方法，但未继承仓库已有 `NIMM.utilities.base_plugin.BasePlugin`，后续可按仓库规范评估是否补充。

