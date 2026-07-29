# generate_orographic_smoothing_coefficients 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `generate_orographic_smoothing_coefficients` |
| 中文名称 | 地形平滑系数生成 |
| 原始路径 | `D:\workspace\improver\generate_orographic_smoothing_coefficients`（原包名 `generate_orographic_smoothing_coefficients`） |
| 整理日期 | 2026-07-28（NIMM 标准化目录结构整理） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `ancillaries` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法基于地形邻接梯度生成递归滤波所用的 x/y 方向平滑系数；可选掩码将系数置零。面向 `xarray.DataArray` / meteva_base 六维单场网格；支持投影米制坐标与经纬球面路径。

- `OrographicSmoothingCoefficients`：由地形邻接梯度与幂次、限幅参数生成 x/y 平滑系数场（中点坐标）。
- 可选掩码：按 `use_mask_boundary` / `invert_mask` 将掩码区域或边界处系数置零。
- CLI `cli/dsc_generate_orographic_smoothing_coefficients.py`：文件式示例调度。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/generate_orographic_smoothing_coefficients/src/generate_orographic_smoothing_coefficients.py` | 核心算法与插件 |
| `00temp/generate_orographic_smoothing_coefficients/src/utils/` | 邻接梯度（投影米制 / 经纬球面） |
| `00temp/generate_orographic_smoothing_coefficients/cli/` | 地形平滑系数 CLI |
| `00temp/generate_orographic_smoothing_coefficients/utils/` | 网格校验工具与本地 `BasePlugin` |
| `00temp/generate_orographic_smoothing_coefficients/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |
| `00temp/generate_orographic_smoothing_coefficients/00temp/`、`00log/` | 中间数据与包内整理日志 |
| `00temp/generate_orographic_smoothing_coefficients/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-28 更新

- NIMM 标准化：从 improver/generate_orographic_smoothing_coefficients 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 导入路径保持 `generate_orographic_smoothing_coefficients`（包内绝对导入）；建立算法内脚手架。
- 未同步 `test_data/`（约 1.7MB）；缺样例时官方回归与 CLI 默认冒烟 skip；CLI 直启缺样例时中文提示而非崩溃。
- 与原 Improver 对照的用例依赖包旁 `improver-1.18.7`；中间目录通常不具备时 skip（不硬编码本机路径）。
- 原代码目录 pytest：19 passed；中间目录：8 passed, 11 skipped（2026-07-28）。
- 详细过程见：`00temp/generate_orographic_smoothing_coefficients/00log/generate_orographic_smoothing_coefficients_整理_20260728.log`。


## 2026-07-29 更新

- 聚焦刷新：CLI 示例脚本由 `cli/anc_generate_orographic_smoothing_coefficients.py` 重命名为 `cli/dsc_generate_orographic_smoothing_coefficients.py`，并同步测试/文档/notebook 路径导入。
- 自原目录覆盖同步 `src/`、`utils/`、`cli/`、`test/`、`nbs/` 与算法说明文档；保留算法内脚手架。
- CLI 直启缺示例输入时中文提示；缺 test_data 或缺包旁 improver-1.18.7 时相关用例会跳过。
- 原代码目录 pytest：19 passed；中间目录：8 passed, 11 skipped（缺 test_data 或缺包旁 improver-1.18.7 时会跳过）。
- 详细过程见：`00temp/generate_orographic_smoothing_coefficients/00log/generate_orographic_smoothing_coefficients_整理_20260729.log`。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/ancillaries/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `test_data` 样例约 1.7MB，中间目录未同步；是否纳入 `NIMM_pip_testdata` / 正式仓库后续决定。
4. `resource/` 当前为空，正式补充时确认是否保留。
