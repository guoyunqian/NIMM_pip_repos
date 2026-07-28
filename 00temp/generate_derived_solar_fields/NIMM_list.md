# NIMM 算法仓库整理清单

> 一次原始算法整理过程对应 `00log/` 下的一份日志；中间数据放 `00temp/generate_derived_solar_fields/`。

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | CLI 入口 |
| --- | --- | --- | --- | --- | --- |
| 辅助功能 | **generate_derived_solar_fields** | 地方太阳时计算；指定时段晴空太阳辐射累计 | 2026-07-25 | 郭云谦、王亭波 | `cli/cal_generate_solar_time.py`、`cli/cal_generate_clearsky_solar_radiation.py` |

## generate_derived_solar_fields 目录明细

| 类别 | 路径 | 作用 |
| --- | --- | --- |
| 核心算法 | `src/generate_derived_solar_fields.py` | `GenerateSolarTime`、`GenerateClearskySolarRadiation` |
| 模块工具 | `src/utils/grid_mapping.py`、`src/utils/solar.py` | 网格映射与太阳天文计算 |
| 通用工具 | `utils/utils.py` | meteva_base 网格数据校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI | `cli/cal_generate_solar_time.py`、`cli/cal_generate_clearsky_solar_radiation.py` | 地方太阳时与晴空辐射示例调度 |
| 文档 | `docs/generate_derived_solar_fields.md`、`docs/generate_derived_solar_fields_overview.md` | 算法说明 |
| notebook | `nbs/generate_derived_solar_fields.ipynb` | 示例与验证 |
| 测试 | `test/` | 单元测试 |
| 整理日志 | `00log/generate_derived_solar_fields_整理_20260725.log` | 本次整理过程记录 |

## generate_derived_solar_fields 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
| --- | --- | --- |
| 1 | 入库路径 | 补充至 NIMM/ancillaries/ 时需调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | test_data | 样例约 0.67MB，中间目录未同步；可纳入 `NIMM_pip_testdata` 或正式入库前筛选 |
| 4 | resource/ | 当前为空，正式补充时确认是否保留 |

## generate_derived_solar_fields 验证记录

| 环境 | 结果 | 日期 |
| --- | --- | --- |
| 中间目录 `00temp/generate_derived_solar_fields/` | 10 passed | 2026-07-25 |
| 原代码目录 `D:\workspace\improver\generate_derived_solar_fields` | 10 passed | 2026-07-25 |
