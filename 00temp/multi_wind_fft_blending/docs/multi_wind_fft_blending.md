# multi_wind_fft_blending

## 算法概述

`multi_wind_fft_blending` 用于多风场特征匹配融合。算法基于 FFT 谱方法与迭代优化理论，估计主风场与一个或多个辅助风场之间的二维位移场，再按位移场对主风场进行平流调整，实现空间特征对齐后的融合。

该算法适用于：

- 多源风场空间特征对齐。
- UV 矢量风融合。
- 集合预报中多个辅助风场的特征匹配融合。
- 台风、锋面等强空间特征的位移调整。

## 算法分类

- 分类：`05blending`
- 分类依据：算法面向多个风场或多个预报成员的融合处理，通过频域特征匹配和位移平流生成融合结果。

## 主要文件

| 类型 | 文件 | 说明 |
| --- | --- | --- |
| 核心源码 | `src/fft_merge.py` | `FFTMergePlugin` 核心算法 |
| CLI | `cli/fft_merge_cli.py` | 示例命令行脚本，原始文件名 `ftt_merge_cli.py` 已修正 |
| CLI入口 | `cli/__main__.py` | `python -m cli` 入口 |
| 文档 | `docs/FFT_MERGE_程序说明.md` | 原始程序说明 |
| 测试 | `test/test_fft_merge.py` | 核心算法测试 |
| 测试 | `test/test_fft_merge_cli.py` | CLI 示例流程测试，原始测试文件名已修正 |
| 资源 | `resource/sample_*` | Micaps11 和 NetCDF 样例数据及参考输出 |

## 输入输出

输入：

- `main_da`：主风场，`xarray.DataArray`，标准六维结构为 `member, level, time, dtime, lat, lon`。
- `ass_da_list`：辅助风场列表，每个元素与主风场结构和空间分辨率一致。
- `feature_border`：内部特征匹配重采样网格边长。
- `max_iterations`：最大迭代次数。
- `move_percent`：主场向辅助场特征位置移动的比例，取值范围 `(0, 1]`。

输出：

- 融合后的 `xarray.DataArray`。当 `member` 长度为 2 时按 `u/v` 矢量风处理；当 `member` 长度为 1 时按标量场处理。

## 当前整理状态

当前阶段为原始算法整理至中间目录，尚未补充到正式算法仓库目录。

已完成：

- 将原始根目录源码 `fft_merge.py` 整理到 `src/`。
- 将原始 CLI `ftt_merge_cli.py` 改名为 `cli/fft_merge_cli.py`，并修正入口与测试引用。
- 复制原始文档、notebook、测试和样例资源。
- 未复制 `__pycache__` 编译产物。

待处理：

- 正式补充到仓库时需要统一导入路径和 CLI 调度命名。
- CLI 示例会写入或覆盖 `resource/sample_*_fft_*` 与 `sample_*_line_*` 输出文件，正式测试前应区分输入样例和生成结果。
- 当前核心类 `FFTMergePlugin` 已提供 `process` 方法，但未继承仓库已有 `NIMM.utilities.base_plugin.BasePlugin`，后续可按仓库规范评估是否补充。

