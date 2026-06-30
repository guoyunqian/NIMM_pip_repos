# frequency_matching_rain01 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `frequency_matching_rain01` |
| 中文名称 | 逐小时降水频率匹配订正 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\qpf_fm_rain01` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、陈荣、李东勇 |
| 算法分类 | `04single_calibration` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法面向单一数值模式逐 1 小时降水预报的业务型统计订正。主流程读取模式预报、MICAPS3 实况、站点表和掩膜资源，按 1-48 小时时效循环构建历史同期样本库，在空间分块内通过 TS+BIAS 筛选相似个例，结合光流位移订正和频率匹配强度订正生成站点订正产品，再经 Cressman 插值和二次频率匹配输出格点产品。

核心源码包括：

- `src/runner.py`：主入口，负责配置解析、时次/时效循环、历史样本构建、分块订正和产品写出。
- `src/proc/frequency_match.py`：CDF 分位数映射频率匹配算法。
- `src/proc/ensemble.py`：TS+BIAS 相似个例筛选。
- `src/proc/optical_flow.py`：光流风场估计。
- `src/proc/rain_extrapolation.py`：半拉格朗日降水平流。
- `src/proc/spatial_analysis.py`：Cressman 插值和站点约束。
- `src/data/types.py`：站点、格点、线条数据结构和业务格式读写。
- `utils/`：路径配置、日志、字符串模板和并行工具。

## 本次整理操作

已将原始目录内容整理到中间目录：

`00temp/frequency_matching_rain01/`

整理内容包括：

- `src/`：核心业务流程、算法模块、数据结构、验证脚本和验证样例数据。
- `cli/`：命令行入口。
- `docs/`：原始程序说明，并新增 `frequency_matching_rain01.md`。
- `resource/`：路径配置、网格配置、站点表和掩膜资源。
- `test/`：频率匹配、配置解析、路径解析和版本对比测试脚本。
- `nbs/`：notebook 示例和图片。
- `utils/`：工具函数。
- `test_data/README.md`：说明原始目录未提供独立测试数据目录，验证样例保留在 `src/verify_data/`。

未执行操作：

- 未删除或移动任何原始文件。
- 未复制原始 `log/` 运行日志目录。
- 已清理复制过程中带入的 `__pycache__`、`.pyc` 和 `.ipynb_checkpoints` 缓存文件。
- 未补充到正式 `NIMM/04single_calibration/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/frequency_matching_rain01/src/` | 核心算法源码和验证样例 |
| `00temp/frequency_matching_rain01/cli/` | CLI 调度入口 |
| `00temp/frequency_matching_rain01/resource/` | 配置、站点表和掩膜资源 |
| `00temp/frequency_matching_rain01/test/` | 测试脚本 |
| `00temp/frequency_matching_rain01/test_data/` | 测试数据说明 |
| `00temp/frequency_matching_rain01/nbs/` | notebook 示例 |
| `00temp/frequency_matching_rain01/docs/` | 文档 |
| `00temp/frequency_matching_rain01/utils/` | 算法工具函数 |

## 已发现问题与后续建议

1. 原始代码仍使用 `src`、`proc`、`data` 和 `utils` 直接导入，正式补充至算法仓库时需要统一包路径。
2. 原始代码未提供仓库规范中的插件类和 `process` 方法，目前以 `src/runner.py::main` 作为主流程入口；后续可补充插件封装。
3. `resource/path.json`、`path_local.json` 和 `path_bck.json` 中保留生产或本地业务路径，离线测试前需要替换为可访问的样例路径。
4. `src/verify_data/` 包含验证样例数据，但完整业务流程仍依赖真实模式预报、MICAPS3 实况、站点表、掩膜和输出目录。
5. 原始 `test/test_compare_version.py` 和 `src/verify.py` 包含旧工程路径 `D:/Work/QpfFrequencyMatch_Rain01/...`，正式测试前需改为仓库相对路径或配置项。
6. 依赖包括 `numpy`、`h5py`、`meteva.base`、`pytest`，业务流程还依赖 MICAPS 数据文件和本地文件系统路径。

## 校验记录

- 已完成中间目录复制和缓存文件清理。
- 已补充算法说明文档和测试数据说明。
- 已使用 Codex 捆绑 Python 完成 27 个 Python 文件的语法解析校验。
- 尝试执行频率匹配最小断言时，当前 Codex 捆绑 Python 环境缺少 `meteva.base`，在导入 `src/data/types.py` 时中止；正式测试前需补齐 `meteva` 等业务依赖。
