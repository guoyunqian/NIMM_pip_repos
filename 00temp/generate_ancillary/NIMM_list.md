# NIMM 算法仓库整理清单

> 一次原始算法整理过程对应 `00log/` 下的一份日志；中间数据放 `00temp/generate_ancillary/`。

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | CLI 入口 |
| --- | --- | --- | --- | --- | --- |
| 辅助功能 | **generate_ancillary** | 海陆掩码二值化与地形带掩码生成 | 2026-07-28 | 郭云谦、王亭波 | `cli/anc_generate_landmask_ancillary.py`、`cli/dsc_generate_topography_bands_mask.py` |

## generate_ancillary 目录明细

| 类别 | 路径 | 作用 |
| --- | --- | --- |
| 核心算法 | `src/generate_ancillary.py` | `CorrectLandSeaMask`、`GenerateOrographyBandAncils` |
| 模块工具 | `utils/utils.py` | meteva_base 网格数据校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI | `cli/anc_*.py`、`cli/dsc_*.py` | 海陆掩码与地形带示例调度 |
| 文档 | `docs/generate_ancillary.md`、`docs/generate_ancillary_overview.md` | 算法说明 |
| notebook | `nbs/generate_ancillary.ipynb` | 示例与验证 |
| 测试 | `test/` | 单元测试与官方样例对照 |
| 整理日志 | `00log/generate_ancillary_整理_20260728.log` | 本次整理过程记录 |

## generate_ancillary 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
| --- | --- | --- |
| 1 | 入库路径 | 补充至 NIMM/ancillaries/ 时需调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | test_data | 样例约 0.41MB（扁平路径 `generate-landmask/`、`generate-topography-bands-mask/`），中间目录未同步；可纳入 `NIMM_pip_testdata` 或正式入库前筛选 |
| 4 | resource/ | 当前为空，正式补充时确认是否保留 |

## generate_ancillary 验证记录

| 环境 | 结果 | 日期 |
| --- | --- | --- |
| 中间目录 `00temp/generate_ancillary/` | 26 passed, 3 skipped | 2026-07-28 |
| 原代码目录 `D:\workspace\improver\generate_ancillary` | 29 passed | 2026-07-28 |
