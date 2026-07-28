# 地形辅助场生成

## 基本信息

- 算法名称：`generate_ancillary`
- 原始路径：`D:\workspace\improver\generate_ancillary`
- 算法类型：`ancillaries`
- 贡献人：郭云谦、王亭波

## 算法功能

生成地形相关辅助场：对插值后的海陆掩码做 0/1 二值化纠正，并按阈值配置将地形高度场分带输出各带二值掩码。面向 `xarray.DataArray` / `numpy.ndarray`，兼容 meteva_base 六维网格。

## 主要方法

| 方法 | 功能 |
| --- | --- |
| `CorrectLandSeaMask` | 海陆掩码二值化纠正 |
| `GenerateOrographyBandAncils` | 地形带掩码生成 |
| `cli/anc_generate_landmask_ancillary.py` | 海陆掩码 CLI |
| `cli/dsc_generate_topography_bands_mask.py` | 地形带掩码 CLI |

## 目录说明

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| 核心源码 | `src/generate_ancillary.py` | 插件类与阈值配置 |
| CLI | `cli/anc_*.py`、`cli/dsc_*.py` | 示例入口 |
| 测试 | `test/` | 单元测试与官方样例对照 |
| 文档 | `docs/generate_ancillary.md` | 详细算法说明 |
| notebook | `nbs/generate_ancillary.ipynb` | 示例 |

## 当前整理状态

- 已从原目录同步源码、CLI、测试、文档与 notebook；模块名保持 `generate_ancillary`。
- 2026-07-28：补齐 `CorrectLandSeaMask` 测试数据；`test_data` 现为 `generate-landmask/`、`generate-topography-bands-mask/`（约 0.41MB，中间目录未同步）；notebook / 海陆掩码 CLI 示例已覆盖该方法。
- 原目录 pytest 29 passed；中间目录 26 passed, 3 skipped（2026-07-28）。
- 补充至 `NIMM/ancillaries/` 时需调整为仓库正式包路径。
