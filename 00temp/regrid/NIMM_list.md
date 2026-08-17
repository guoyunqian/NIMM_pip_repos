# NIMM 算法仓库整理清单

> 一次原始算法整理过程对应 `00log/` 下的一份日志；中间稿存放 `00temp/regrid/`。

## 已整理算法列表

| 算法种类 | 算法名称 | 算法功能 | 整理时间 | 贡献人 | CLI 入口 |
| --- | --- | --- | --- | --- | --- |
| 辅助场 | **regrid** | 将源场重网格到目标空间网格，可选海陆掩膜感知以避免陆取海值 / 海取陆值 | 2026-08-17 | 郭云谦、王亭波 | `cli/preprocess_test_data.py`、`cli/tran_regrid.py` |

## regrid 目录明细

| 类别 | 路径 | 内容 |
| --- | --- | --- |
| 核心算法 | `src/landsea.py`、`src/landsea2.py` | `RegridLandSea`、`AdjustLandSeaPoints`、`RegridWithLandSeaMask` |
| 模块工具 | `src/utils/` | 双线性 / 最近邻 / IDW / 网格与邻近域 |
| 通用工具 | `utils/utils.py` | meteva_base 六维场校验与辅助封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI | `cli/preprocess_test_data.py`、`cli/tran_regrid.py` | 文件式示例入口 |
| 文档 | `docs/regrid_landsea.md`、`docs/regrid_overview.md` | 算法说明 |
| notebook | `nbs/regrid_landsea_validation.ipynb` | 示例与验证 |
| 测试 | `test/` | 单元、官方回归与 CLI 冒烟 |
| 整理日志 | `00log/regrid_整理_20260817.log` | 本次增量同步过程记录 |

## regrid 待办（供人工填写）

| 序号 | 事项 | 建议处理 |
| --- | --- | --- |
| 1 | 导入路径 | 迁入正式 NIMM/ancillaries/ 时调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | test_data | 约 1.7MB、27 文件；中间目录未同步；可放入 NIMM_pip_testdata 并在正式入库前筛选 |
| 4 | resource/ | 当前为空；正式入库时确认是否需要 |

## regrid 验证记录

| 范围 | 结果 | 日期 |
| --- | --- | --- |
| 中间目录 `00temp/regrid/` | 25 passed, 13 skipped | 2026-08-17 |
| 原始算法目录 `D:\workspace\improver\regrid` | 38 passed（improver venv） | 2026-08-17 |
