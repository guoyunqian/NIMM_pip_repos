# 地形平滑系数生成

## 基本信息

- 算法名称：`generate_orographic_smoothing_coefficients`
- 原始路径：`D:\workspace\improver\generate_orographic_smoothing_coefficients`
- 算法类型：`ancillaries`
- 贡献人：郭云谦、王亭波

## 算法功能

基于地形邻接梯度生成递归滤波所用的 x/y 方向平滑系数；可选掩码将系数置零。面向 `xarray.DataArray` / meteva_base 六维单场网格；支持投影米制坐标与经纬球面路径。

## 主要方法

| 方法 | 功能 |
| --- | --- |
| `OrographicSmoothingCoefficients` | 由地形梯度生成 x/y 平滑系数 |
| `cli/dsc_generate_orographic_smoothing_coefficients.py` | 文件式 CLI 示例 |

## 目录说明

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| 核心源码 | `src/generate_orographic_smoothing_coefficients.py` | 插件类 |
| 模块工具 | `src/utils/` | 邻接梯度（投影 / 经纬） |
| CLI | `cli/dsc_*.py` | 示例入口 |
| 测试 | `test/` | 单元测试 |
| 文档 | `docs/generate_orographic_smoothing_coefficients.md` | 详细算法说明 |
| notebook | `nbs/generate_orographic_smoothing_coefficients.ipynb` | 示例 |

## 当前整理状态

- 已从原目录同步源码、CLI、测试、文档与 notebook；模块名保持 `generate_orographic_smoothing_coefficients`。
- 未同步 `test_data/`（约 1.7MB，样例独立管理）。
- 原目录 pytest 19 passed；中间目录 8 passed, 11 skipped（2026-07-29；缺 test_data 或缺包旁 improver-1.18.7 时会跳过）。
- 2026-07-29：CLI 示例脚本由 `anc_generate_...` 重命名为 `dsc_generate_orographic_smoothing_coefficients.py`，并同步相关导入与清单。
- 补充至 `NIMM/ancillaries/` 时需调整为仓库正式包路径。
