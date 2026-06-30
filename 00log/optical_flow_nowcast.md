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

## 已发现问题与后续建议

1. 完整运行依赖 `scipy`、`scikit-image`、`opencv-python`、`pandas`、`xarray`、`meteva-base` 等环境；当前运行时未安装这些依赖。
2. `temp_demo.py` 和 notebook 中仍保留原始 `/home/nimm` 与 `nimm.cli.nimm.*` 示例路径，正式入库前建议改写为仓库内 CLI 或删除生产路径示例。
3. 原始目录没有独立 CLI、docs、test、resource、utils 结构，本次已补齐基础归档骨架，但业务 CLI 仍需后续按仓库规范补充。
4. 当前归档目录尚未补充到正式 `NIMM/03nowcast/` 目录。

## 校验记录

- 使用 Codex bundled Python 执行 `python -m compileall -q .`，语法编译通过。
- 包根和 `optical_flow_nowcast.src` 懒加载入口导入通过。
- 直接导入核心 `extrapolation` 模块时，当前运行时缺少 `scipy`，未能继续执行核心 smoke test。
