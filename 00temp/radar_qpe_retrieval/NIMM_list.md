# NIMM 算法仓库整理清单

以表格形式记录已整理入本仓库的算法，便于检索、维护与后续补充。

> **说明**：一次「原始算法整理过程」对应 `00log/` 下的一份日志；中间数据放 `00temp/qpe/`。

---

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | 源码与配置位置 | CLI 入口 | 仍存在问题 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 观测相关处理 | **qpe** | 基于雷达反射率、KDP、比衰减和水凝物分类等网格数据估算降水率 | 2026-07-13 | 郭云谦、王亭波 | 见下表「qpe 目录明细」 | `python radar_qpe_retrieval/cli/qpe.py` | 见下表「qpe 待办」 |

---

## qpe 目录明细

| 类别 | 路径 | 作用 |
| --- | --- | --- |
| 核心算法 | `src/qpe.py` | QPEPlugin、EstimateRainRate*、est_rain_rate_* |
| 内部工具 | `src/utils/_freq.py` | A-R、KDP-R 频率关系系数 |
| 模块工具 | `utils/utils.py` | meteva_base 网格数据校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | PostProcessingPlugin 本地提供 |
| CLI | `cli/qpe.py` | QPE 统一入口 |
| CLI 辅助 | `cli/cinrad_meb.py`、`cli/cinrad_pyart_prep.py` | CINRAD 读数与网格预处理 |
| 文档 | `docs/qpe.md`、`docs/雷达降水定量反演QPE.md` | 算法说明 |
| notebook | `nbs/qpe.ipynb` | 示例与验证 |
| 测试 | `test/test_qpe.py`、`test/test_qpe_cli.py`、`test/test_qpe_plugin.py` | 单元测试 |
| 整理日志 | `00log/qpe_整理_20260713.log` | 本次整理过程记录 |
| 中间数据 | `00temp/qpe/` | 整理过程临时样本（当前为空） |

---

## qpe 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
| --- | --- | --- |
| 1 | 入库路径 | 补充至 NIMM/01obs_adustment/ 时需调整为仓库正式包路径 |
| 2 | PostProcessingPlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | test_data | 体量大，CLI 测试依赖 cli_input 样例，正式入库前筛选必要样例 |
| 4 | resource/ | 当前为空，正式补充时确认是否保留 |

---

## qpe 验证记录

| 环境 | 结果 | 日期 |
| --- | --- | --- |
| 原代码目录 `D:\workspace\pyart_nimm\qpe` | 全部测试通过 | 2026-07-13 |
| 中间目录 `00temp/radar_qpe_retrieval/` | 32 passed, 6 skipped（CLI 用例缺 test_data） | 2026-07-13 |
