# NIMM 算法仓库整理清单

以表格形式记录已整理入本仓库的算法，便于检索、维护与后续补充。

> **说明**：一次「原始算法整理过程」对应 `00log/` 下的一份日志；中间数据放 `00temp/<算法代号>/`。

---

## 已整理算法列表

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | 源码与配置位置 | CLI 入口 | 仍存在问题 |
|----------|----------|----------|----------|--------|----------------|----------|------------|
| 短临预报 · 降水集成 | **mait_1h** | 1 小时多模式 Micaps3 站点降水 TS 动态加权集成；频率匹配订正；Cressman 插值至格点；输出 Micaps3 站点 + Micaps4/NC 格点产品 | 2026-07-03 | 待补充 | 见下表「mait_1h 目录明细」 | `python -m cli --time-inputs=...`<br>`python -m cli verify ts --h5-file=...` | 见下表「mait_1h 待办」 |

---

## mait_1h 目录明细

| 类别 | 路径 | 作用 |
|------|------|------|
| 主入口 | `src/mait_1h.py` | `process()` / `RunProcess` / 预报集成 CLI |
| 检验 CLI | `cli/verify.py` | prepare / result / ts / plot-dt |
| CLI 路由 | `cli/__main__.py` | `python -m cli` 统一入口 |
| 算法核心 | `src/mait_1_plugin.py` | TS 权重、DataFlg、Cressman 插值 |
| 读数 | `src/mait_1_plugin_util.py` | Micaps3/M4/NC 读数、background、时间回溯 |
| 运行上下文 | `src/utils/util_context.py` | `RunContext`、`build_run_context`、`dt_search_base` |
| 配置 | `src/utils/util_env.py` | `resource/mait_1.ini` 解析 |
| I/O | `src/utils/util_new.py` | 掩码、Micaps 写出、频率匹配、全 0 背景 |
| 插件 | `utils/base_plugin.py`、`utils/multipro_plugin.py` | 插件基类、多进程 |
| 检验辅助 | `utils/data_prepare_plugin.py` | meteva 检验数据集准备 |
| 配置资源 | `resource/mait_1.ini`、`resource/para*.ini`、`resource/para_1_background.ini`、`resource/sta.info` | 路径、模式、站点、背景格点 |
| 文档 | `docs/MAIT_1H_程序说明.md`、`nbs/mait_1h_说明.ipynb` | 程序说明与原理 notebook |
| 测试 | `test/test_run_context.py`、`test/mait_1_nimm_test.py` | 单元测试与批量业务脚本 |
| 整理日志 | `00log/mait_1h_整理_20260703.log` | 本次整理过程记录 |
| 中间数据 | `00temp/mait_1h/` | 整理过程临时样本（当前为空） |

---

## mait_1h 待办（需人工补充）

| 序号 | 问题 | 建议处理 |
|------|------|----------|
| 1 | 贡献人、原始代码来源未登记 | 补全本表与 `00log/mait_1h_整理_20260703.log` |
| 2 | `requirements-cli.txt` 缺失 | 根据 meteva / clize 等依赖生成并入库 |
| 3 | 文档部分路径过时 | 统一 docs / notebook 中入口与 utils 路径描述 |
| 4 | `src/utils/` 与根 `utils/` 双包 | 评估合并或重命名根目录插件包 |
| 5 | 生产数据路径不在仓库内 | 部署时配置 `para_1.ini` 与 background；本地仅跑单元测试 |
| 6 | `resource/mask010.dat` | **已入库**（`resource/mask010.dat`、`mask010.nc` 均存在）；部署时确认路径与 `mait_1.ini` 一致即可 |
| 7 | §8 改造前后对比未在新结构复验 | 在目标环境重跑 notebook 对比段 |
| 8 | 默认 `para_ini=resource/local.ini` | 生产改为 `para_1.ini` 或 CLI `--para-path` |
| 9 | 文档/docstring 路径过时 | `docs/`、`nbs/`、`src/mait_1h.py` docstring 仍引用 `mait_1h_cli.py` 等 |
| 10 | 仓库未初始化 git | 建议 `git init` 以便后续 diff 追踪 |

---

## 新增算法登记模板

整理新算法时，复制下表一行并创建对应 log / temp 子目录：

| 算法种类 | 算法代号 | 算法功能 | 更新时间 | 贡献人 | 源码与配置位置 | CLI 入口 | 仍存在问题 |
|----------|----------|----------|----------|--------|----------------|----------|------------|
| （填写） | （填写） | （填写） | YYYY-MM-DD | （填写） | （填写） | （填写） | （填写） |

同时新增：

- `00log/<算法代号>_整理_<YYYYMMDD>.log`
- `00temp/<算法代号>/`
