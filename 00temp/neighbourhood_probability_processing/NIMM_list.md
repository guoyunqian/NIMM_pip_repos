# NIMM 算法仓库整理清单

以表格形式记录已整理入本仓库的算法，便于检索、维护与后续补充。

> **说明**：一次「原始算法整理过程」对应 `00log/` 下的一份日志；中间数据放 `00temp/nbhood/`。

---

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | 源码与配置位置 | CLI 入口 | 仍存在问题 |
|----------|----------|----------|----------|--------|----------------|----------|------------|
| 集合及概率预报 | **nbhood** | 邻域概率处理、邻域百分位生成、陆海/地形带分区和分层掩码概率处理 | 2026-07-09 | 郭云谦、王亭波 | 见下表「nbhood 目录明细」 | `python neighbourhood_probability_processing/cli/ens_nbhood.py` 等 | 见下表「nbhood 待办」 |

---

## nbhood 目录明细

| 类别 | 路径 | 作用 |
|------|------|------|
| 核心算法 | `src/nbhood.py` | NeighbourhoodProcessing、GeneratePercentilesFromANeighbourhood |
| 掩码邻域 | `src/use_nbhood.py` | ApplyNeighbourhoodProcessingWithAMask |
| 内部工具 | `src/utils/` | 网格、核函数、可变半径、halo、重网格等 |
| 模块工具 | `utils/utils.py` | meteva_base 网格数据校验与输出封装 |
| 插件基类 | `utils/base_plugin.py` | BasePlugin 本地提供 |
| CLI I/O | `cli/io.py` | 掩码/权重 nc 读取 |
| CLI | `cli/ens_nbhood.py` | 邻域概率与百分位 |
| CLI | `cli/ens_nbhood_iterate_with_mask.py` | 分层掩码迭代 |
| CLI | `cli/ens_nbhood_land_and_sea.py` | 陆海/地形带分区 |
| 文档 | `docs/nbhood.md`、`docs/use_nbhood.md` | 算法说明 |
| notebook | `nbs/nbhood.ipynb`、`nbs/use_nbhood.ipynb` | 示例与验证 |
| 测试 | `test/test_nbhood.py`、`test/test_use_nbhood.py` | 单元测试 |
| 整理日志 | `00log/nbhood_整理_20260709.log` | 本次整理过程记录 |
| 中间数据 | `00temp/nbhood/` | 整理过程临时样本（当前为空） |

---

## nbhood 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
|------|------|----------|
| 1 | 入库路径 | 补充至 NIMM/07probability/ 时需调整为仓库正式包路径 |
| 2 | BasePlugin | 正式入库时评估是否改为仓库统一基类 |
| 3 | test_data | 体量大且含 CLI 输出结果，正式入库前筛选必要样例 |
| 4 | resource/ | 当前为空，正式补充时确认是否保留 |
