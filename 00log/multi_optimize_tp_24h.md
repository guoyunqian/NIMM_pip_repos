# multi_optimize_tp_24h 整理日志（仓库索引）

> 包内完整过程日志：`00temp/multi_optimize_tp_24h/00log/multi_optimize_tp_24h_整理_20260723.log`  
> 清单：`00temp/multi_optimize_tp_24h/NIMM_list.md`  
> 中间数据：`00temp/multi_optimize_tp_24h/00temp/multi_optimize_tp_24h/`

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `multi_optimize_tp_24h`（原 `optimize_tp_24h`） |
| 中文名称 | 24小时降水频率匹配订正 |
| 原始路径 | optimize_TP_24H / optimize_tp_24h（详见包内 docs；绝对路径待补） |
| 整理日期 | 2026-07-23 |
| 算法贡献人 | 马劲松 |
| 算法分类 | 短临预报 · 降水订正 |
| 当前状态 | 已整理至 `00temp/multi_optimize_tp_24h/`；`process` 可模块调度；CLI 在 `cli/` |

## 算法理解

对**单一数值模式**的约 36–252 h、24 小时累积降水预报做统计订正：历史相似个例检索 → 切片光流/平流 → 频率匹配；输出 MICAPS3 站点与 MICAPS4/NC 格点。

## 目录对应关系

| 路径 | 内容说明 |
| --- | --- |
| `00temp/multi_optimize_tp_24h/src/correct_tp_24h.py` | **主程序** `process` / `mainProcess` |
| `00temp/multi_optimize_tp_24h/cli/__main__.py` | `python -m cli` → `process`（中文参数说明） |
| `00temp/multi_optimize_tp_24h/src/cal_*.py`、`interpolation.py` | 核心算法 |
| `00temp/multi_optimize_tp_24h/src/utils/` | 本包工具 |
| `00temp/utils/` | 共享 `multipro_plugin` / `data_prepare_plugin` |
| `00temp/multi_optimize_tp_24h/00temp/` | **整理中间数据** |
| `00temp/multi_optimize_tp_24h/00log/` | **整理过程日志**（一次整理一份） |
| `00temp/multi_optimize_tp_24h/NIMM_list.md` | **算法清单表**（种类、功能、目录、待办） |

## 2026-07-23 整理要点

- 工具迁入 `src/utils`；共享插件走 `00temp/utils`。
- 抽出 `process`；CLI 调度主程序并补充中文参数说明。
- 外层多进程改为 `SimpleParallelTool`，任务粒度仍为「起报×时效」。
- 目录代号更名为 `multi_optimize_tp_24h`。

## 仍存在问题（需人工补充）

与包内日志第四节、`NIMM_list.md` 待办表一致，摘要如下：

1. 原始绝对路径待补全。  
2. `resource/` 样例过大；plugin 绝对路径需按部署修改。  
3. `test_compare_version.py` 硬编码外盘路径。  
4. 未迁入正式 NIMM；业务端到端未复跑。  
5. `00temp/multi_optimize_tp_24h/` 仅占位；`nbs` 旧文案待核对。  
