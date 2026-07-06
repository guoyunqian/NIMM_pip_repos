# NIMM 算法仓库整理清单

以表格形式记录已整理入本仓库的算法，便于检索、维护与后续补充。

> **说明**：一次「原始算法整理过程」对应 `00log/` 下的一份日志；中间数据放 `00temp/feels_like_temperature/`。

---

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | 源码与配置位置 | CLI 入口 | 仍存在问题 |
|----------|----------|----------|----------|--------|----------------|----------|------------|
| 诊断相关 | **feels_like_temperature** | 根据气温、10 米风速、相对湿度和气压综合风寒与显温，计算体感温度诊断场 | 2026-07-06 | 郭云谦、王亭波 | 见下表「feels_like_temperature 目录明细」 | `python -m feels_like_temperature.cli.der_feel_like_temp` | 见下表「feels_like_temperature 待办」 |

---

## feels_like_temperature 目录明细

| 类别 | 路径 | 作用 |
|------|------|------|
| 核心算法 | `src/feels_like_temperature.py` | CalculateWindChill、calculate_feels_like_temperature |
| 内部工具 | `src/utils/_feels_like.py` | 饱和水汽压、风寒、显温及融合逻辑 |
| 模块工具 | `utils/utils.py` | meteva_base 网格数据校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI | `cli/der_feel_like_temp.py` | 体感温度计算示例调度 |
| CLI 路由 | `cli/__main__.py` | 模块 CLI 入口 |
| 文档 | `docs/feels_like_temperature.md` | 算法说明 |
| notebook | `nbs/feels_like_temperature.ipynb` | 示例与验证 |
| 测试 | `test/test_feels_like_temperature.py 等` | 单元测试与官方样例对照 |
| 整理日志 | `00log/feels_like_temperature_整理_20260706.log` | 本次整理过程记录 |
| 中间数据 | `00temp/feels_like_temperature/` | 整理过程临时样本（当前为空） |

---

## feels_like_temperature 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
|------|------|----------|
| 1 | 入库路径 | 补充至 NIMM/02diagnostic/ 时需调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | resource/ | 当前为空，正式补充时确认是否保留 |
