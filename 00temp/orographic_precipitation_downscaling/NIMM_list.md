# NIMM 算法仓库整理清单

以表格形式记录已整理入本仓库的算法，便于检索、维护与后续补充。

> **说明**：一次「原始算法整理过程」对应 `00log/` 下的一份日志；中间数据放 `00temp/orographic_enhancement/`。

---

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | 源码与配置位置 | CLI 入口 | 仍存在问题 |
|----------|----------|----------|----------|--------|----------------|----------|------------|
| 空间降尺度 | **orographic_enhancement** | 基于温湿压、风场和地形抬升效应计算降水地形增强项，并支持叠加或扣除到降水场 | 2026-07-06 | 郭云谦、王亭波 | 见下表「orographic_enhancement 目录明细」 | `python -m orographic_precipitation_downscaling.cli.dsc_orographic_enhancement` | 见下表「orographic_enhancement 待办」 |

---

## orographic_enhancement 目录明细

| 类别 | 路径 | 作用 |
|------|------|------|
| 核心算法 | `src/orographic_enhancement.py` | MetaOrographicEnhancement、OrographicEnhancement |
| 应用算法 | `src/apply_orographic_enhancement.py` | ApplyOrographicEnhancement |
| 内部工具 | `src/utils/` | 网格、数值、饱和水汽压等 |
| 模块工具 | `utils/utils.py` | meteva_base 校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI | `cli/dsc_orographic_enhancement.py` | 地形增强项计算示例 |
| 文档 | `docs/orographic_enhancement.md 等` | 算法说明 |
| notebook | `nbs/orographic_enhancement_validation.ipynb` | 示例与验证 |
| 测试 | `test/test_orographic_enhancement.py` | 合成样例与官方样例对照 |
| 整理日志 | `00log/orographic_enhancement_整理_20260706.log` | 本次整理过程记录 |
| 中间数据 | `00temp/orographic_enhancement/` | 整理过程临时样本（当前为空） |

---

## orographic_enhancement 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
|------|------|----------|
| 1 | 入库路径 | 补充至 NIMM/00space_downscale/ 时需调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | test_data | 含结果或临时文件，正式入库前筛选必要样例 |
| 4 | resource/ | 当前为空，正式补充时确认是否保留 |
