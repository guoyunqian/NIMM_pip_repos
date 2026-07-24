# NIMM 算法仓库整理清单

以表格形式记录已整理入本仓库的算法，便于检索、维护与后续补充。

> **说明**：一次「原始算法整理过程」对应 `00log/` 下的一份日志；中间数据放 `00temp/wind_downscaling/`。

---

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | 源码与配置位置 | CLI 入口 | 仍存在问题 |
|----------|----------|----------|----------|--------|----------------|----------|------------|
| 空间降尺度 | **wind_downscaling** | 基于地形粗糙度、地形高度标准差和地形高度差进行风速空间降尺度与订正 | 2026-07-06 | 郭云谦、王亭波 | 见下表「wind_downscaling 目录明细」 | `python -m orographic_wind_downscaling.cli.dsc_wind_downscaling` | 见下表「wind_downscaling 待办」 |

---

## wind_downscaling 目录明细

| 类别 | 路径 | 作用 |
|------|------|------|
| 核心算法 | `src/wind_downscaling.py` | FrictionVelocity、RoughnessCorrectionUtilities、RoughnessCorrection |
| 模块工具 | `utils/utils.py` | meteva_base 网格数据校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI | `cli/dsc_wind_downscaling.py` | 风速降尺度示例调度 |
| 文档 | `docs/wind_downscaling.md、docs/orographic_wind_downscaling.md` | 算法说明 |
| notebook | `nbs/official_data_wind_calculations.ipynb` | 官方样例验证 |
| 测试 | `test/test_friction_velocity.py、test/test_official_wind_downscaling.py 等` | 单元测试与官方样例 |
| 整理日志 | `00log/wind_downscaling_整理_20260706.log` | 本次整理过程记录 |
| 中间数据 | `00temp/wind_downscaling/` | 整理过程临时样本（当前为空） |

---

## wind_downscaling 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
|------|------|----------|
| 1 | 入库路径 | 补充至 NIMM/00space_downscale/ 时需调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | resource/ | 当前为空，正式补充时确认是否保留 |
