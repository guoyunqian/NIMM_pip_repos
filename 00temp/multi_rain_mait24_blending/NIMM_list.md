# NIMM 算法仓库整理列表

记录已整理入库的原始算法。每新增或更新一个算法，请同步修改本表，并在 `00log/` 下保留对应整理日志。

---

## 算法总览

| 算法名称 | 算法种类 | 算法功能 | 更新时间 | 贡献人 | 仍存在问题 |
|----------|----------|----------|----------|--------|------------|
| MAIT 24h | 降水集成 | 多模式 24 小时累积降水自适应集成（TS 权重 + 站点融合 + 格点插值输出 Micaps3/4） | 2026-07-06 | 郝书剑、赵如奇、杨宸源 | 见下表「待办」列；整理日志 `00log/mait_24h_整理_20260706.log` |

---

## MAIT 24h — 目录位置

| 类别 | 路径 | 说明 |
|------|------|------|
| 主入口 | `src/mait_24h.py` | `process` / `RunProcess`；Clize 命令行 |
| CLI | `cli/__main__.py` | `python -m cli` → 主程序；`python -m cli verify` → 检验 |
| 算法插件 | `src/mait_24_plugin.py` | TS 权重、站点→格点插值 |
| 读数工具 | `src/mait_24_plugin_util.py` | 模式/实况/背景场读取 |
| 运行上下文 | `src/utils/util_context.py` | `RunContext`、`build_run_context` |
| 环境与配置 | `src/utils/util_env.py` | `resource/mait_24.ini` 解析 |
| 数据处理 I/O | `src/utils/util_new.py` | INI、掩码、Micaps、beta 读写 |
| 掩码辅助 | `src/utils/util_mask_file.py` | GeoJSON/矢量 → 掩码栅格 |
| 多进程 | `utils/multipro_plugin.py` | `SimpleParallelTool` |
| 插件基类 | `utils/base_plugin.py` | `PostProcessingPlugin` |
| 数据准备（扩展） | `utils/data_prepare_plugin.py` | 检验数据准备 |
| 检验 CLI | `cli/verify.py` | TS/HFMC 检验与出图 |
| 运行配置 | `resource/mait_24.ini` | 日志、路径、默认运行项 |
| 模式配置 | `resource/para_24.ini` | 模式路径、实况、输出模板 |
| 背景场配置 | `resource/para_24_background.ini` | Micaps4 背景路径 |
| 程序说明 | `docs/MAIT_24H_程序说明.md` | 架构与运行说明 |
| 中间数据 | `00temp/` | 整理过程临时文件 |
| 整理日志 | `00log/` | 单次整理一条日志 |

> **导入约定**：`src/utils/` 与根目录 `utils/` 合并为同一 `utils` 包（见 `utils/__init__.py`）；统一使用 `from utils.xxx import ...`。

---

## MAIT 24h — 待办 / 已知问题

| 序号 | 项 | 说明 | 状态 |
|------|-----|------|------|
| 1 | 文档路径同步 | `docs/`、`nbs/`、`README.md` 中部分文件名仍为旧称 | 待处理 |
| 2 | 生产数据路径 | `para_24.ini` 等需在目标环境按实际挂载路径修改 | 部署时处理 |
| 3 | 扩展插件 | `data_distribute_pulgin.py` 等未纳入主流程 CI | 可选 |

---

## 新增算法登记模板

复制下表新增一行：

| 算法名称 | 算法种类 | 算法功能 | 更新时间 | 贡献人 | 仍存在问题 |
|----------|----------|----------|----------|--------|------------|
| （名称） | | | YYYY-MM-DD | | |

并在 `00log/` 新建 `<算法名>_整理_<YYYYMMDD>.log`。
