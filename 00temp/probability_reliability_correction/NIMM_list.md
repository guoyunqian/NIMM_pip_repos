# NIMM 算法仓库整理清单

> 一次原始算法整理过程对应 `00log/` 下的一份日志；中间稿存放 `00temp/probability_reliability_correction/`。

## 已整理算法列表

| 算法种类 | 算法名称 | 算法功能 | 整理时间 | 贡献人 | CLI 入口 |
| --- | --- | --- | --- | --- | --- |
| 概率 | **probability_reliability_correction** | 用历史概率预报与实况构建可靠性表并订正待发布概率场（网格/站点） | 2026-08-08 | 郭云谦、王亭波 | `cli/prb_*.py`、`cli/preprocess_test_data.py` |

## probability_reliability_correction 目录明细

| 类别 | 路径 | 内容 |
| --- | --- | --- |
| 核心算法 | `src/reliability_calibration.py` | Construct / Aggregate / Manipulate / Apply 四插件 |
| 模块工具 | `src/utils/` | 建表、整理、应用与网格/站点适配 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin / PostProcessingPlugin |
| CLI | `cli/prb_*.py`、`cli/io.py`、`cli/preprocess_test_data.py` | 文件式示例入口 |
| 文档 | `docs/reliability_calibration.md`、`docs/probability_reliability_correction.md` | 算法说明 |
| notebook | `nbs/reliability_calibration_validation.ipynb` | 示例与验证 |
| 测试 | `test/` | 网格/站点单元与 CLI I/O |
| 整理日志 | `00log/probability_reliability_correction_整理_20260808.log` | 整理过程记录 |

## probability_reliability_correction 待办（供人工填写）

| 序号 | 事项 | 建议处理 |
| --- | --- | --- |
| 1 | 导入路径 | 迁入正式 NIMM/07probability/ 时调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | test_data | 约 1.32MB、54 文件；中间目录未同步；可放入 NIMM_pip_testdata 并在正式入库前筛选 |
| 4 | resource/ | 当前为空；正式入库时确认是否需要 |

## probability_reliability_correction 验证记录

| 范围 | 结果 | 日期 |
| --- | --- | --- |
| 中间目录 `00temp/probability_reliability_correction/` | 18 passed | 2026-08-08 |
| 原始算法目录 `D:\workspace\improver\reliability_calibration` | 18 passed（improver venv） | 2026-08-08 |
