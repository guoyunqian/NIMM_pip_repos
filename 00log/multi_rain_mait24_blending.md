# multi_rain_mait24_blending 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `multi_rain_mait24_blending` |
| 中文名称 | 逐日多源自适应降水集成MAIT24 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\mait_24h` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、曹勇、陈荣 |
| 算法分类 | `05blending` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法是面向逐日 24 小时累积降水的多源自适应融合业务流程。主流程读取多模式历史样本、当前预报、实况、背景场和掩码，基于分区 TS 技巧评分和历史 beta 记忆自适应计算模式权重，完成站点降水集成与频率匹配订正，再插值生成格点产品。

核心源码包括：

- `src/mait_24h_cli.py`：主入口，负责配置准备、时效循环、多进程派发和产品写出。
- `src/mait_24_plugin.py`：提供 `AnalysisTsWeightProcess`、`StationDataInterp2GridDataProcess`、`DataFlgProcess` 等核心插件。
- `src/mait_24_plugin_util.py`：负责时间换算、历史/当前 Micaps 资料读取和背景场路径解析。
- `utils/util_new.py`：提供 TS 计算、频率匹配、Cressman 插值、Micaps 写出、beta 读写等工具。
- `utils/mai_24_plugin_context.py`：提供 `RunContext` 结构化上下文。

## 本次整理操作

已将原始目录内容复制到中间目录：

`00temp/multi_rain_mait24_blending/`

复制内容包括：

- `src/`：核心算法源码。
- `cli/`：命令行入口。
- `docs/`：原始程序说明文档，并新增 `multi_rain_mait24_blending.md`。
- `nbs/`：notebook 示例及相关图片。
- `resource/`：配置、站点表、掩码、样例 h5 和图片资源。
- `test/`：pytest 与业务测试脚本。
- `utils/`：算法内部工具函数。

新增内容包括：

- `test_data/README.md`：说明原始目录无独立 `test_data/`，正式入库前需筛选最小测试样例。

未执行操作：

- 未删除或移动任何原始文件。
- 未复制 `__pycache__`、`.pyc`、`.ipynb_checkpoints`、`.idea` 和原始 `log/` 运行日志目录。
- 未补充到正式 `NIMM/05blending/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/multi_rain_mait24_blending/src/` | 核心算法源码 |
| `00temp/multi_rain_mait24_blending/cli/` | CLI 调度入口 |
| `00temp/multi_rain_mait24_blending/resource/` | 配置、掩码、站点表和样例资源 |
| `00temp/multi_rain_mait24_blending/test/` | 测试脚本 |
| `00temp/multi_rain_mait24_blending/test_data/` | 测试数据说明，待补充最小样例 |
| `00temp/multi_rain_mait24_blending/nbs/` | notebook 示例 |
| `00temp/multi_rain_mait24_blending/docs/` | 文档 |
| `00temp/multi_rain_mait24_blending/utils/` | 算法内部工具函数 |

## 已发现问题与后续建议

1. 原始代码导入路径仍使用 `src` 和 `utils` 风格。当前中间目录保持原样，后续补充至正式仓库时需要统一调整为 `NIMM` 下的实际包路径。
2. 算法运行依赖完整 Micaps 业务数据路径、站点表、背景场、beta 目录和掩码文件，当前未运行完整业务流程测试。
3. `resource/` 中包含多份备份配置文件、样例 `h5`、图片和业务资源，正式入库前建议筛选必要最小资源集。
4. 原始测试中部分脚本依赖完整业务数据环境，正式测试策略需要区分单元测试、mock 流程测试和业务集成测试。
5. 依赖包括 `numpy`、`pandas`、`meteva_base`、`meteva`、`xarray`、`clize`；掩码制作工具还涉及 `geopandas`、`shapely`。

