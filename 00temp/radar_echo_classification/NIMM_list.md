# NIMM 算法仓库整理清单

> 一次原始算法整理过程对应 `00log/` 下的一份日志；中间数据放 `00temp/echo_class/`。

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | CLI 入口 |
| --- | --- | --- | --- | --- | --- |
| 观测相关处理 | **echo_class** | 雷达回波层状/对流分类、特征识别与半监督水凝物分类 | 2026-07-16 | 郭云谦、王亭波 | `python radar_echo_classification/cli/*_main.py` |

## echo_class 目录明细

| 类别 | 路径 | 作用 |
| --- | --- | --- |
| 核心算法 | `src/echo_class.py` | 四个插件类及对应分类算法函数 |
| 内部工具 | `src/utils/` | Steiner/特征、小波、水凝物、网格辅助 |
| 模块工具 | `utils/utils.py` | meteva_base 网格数据校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI | `cli/*_main.py` | 四个算法示例入口 |
| 文档 | `docs/echo_class.md`、`docs/雷达回波分类.md` | 算法说明 |
| notebook | `nbs/echo_class.ipynb` | 示例与验证 |
| 测试 | `test/` | 单元测试与 CLI 测试 |
| 整理日志 | `00log/echo_class_整理_20260716.log` | 本次整理过程记录 |

## echo_class 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
| --- | --- | --- |
| 1 | 入库路径 | 补充至 NIMM/01obs_adustment/ 时需调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | test_data | 体量大，CLI 测试依赖 cli_input 样例，正式入库前筛选必要样例 |
| 4 | resource/ | 当前为空，正式补充时确认是否保留 |

## echo_class 验证记录

| 环境 | 结果 | 日期 |
| --- | --- | --- |
| 中间目录 `00temp/radar_echo_classification/` | 13 passed, 4 skipped（CLI 用例缺 test_data） | 2026-07-16 |
| 原代码目录 `D:\workspace\pyart_nimm\echo_class` | 全部测试通过 | 2026-07-16 |
