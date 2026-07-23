# multi_qpf_fm_rain01 整理日志（仓库索引）

> 包内完整过程日志：`00temp/multi_qpf_fm_rain01/00log/multi_qpf_fm_rain01_整理_20260723.log`  
> 清单：`00temp/multi_qpf_fm_rain01/NIMM_list.md`  
> 中间数据：`00temp/multi_qpf_fm_rain01/00temp/multi_qpf_fm_rain01/`

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `multi_qpf_fm_rain01`（原 `qpf_fm_rain01`） |
| 中文名称 | 逐1小时降水频率匹配订正 |
| 原始路径 | 原版 `QPFFrequencyMatch_Rain01`（详见包内 docs；绝对路径待补） |
| 整理日期 | 2026-07-23 |
| 算法贡献人 | 曹勇 |
| 算法分类 | 短临预报 · 降水订正 |
| 当前状态 | 已整理至 `00temp/multi_qpf_fm_rain01/`；`process` 可模块调度；CLI 在 `cli/` |

## 算法理解

对**单一数值模式**的 1–48 h 逐小时降水预报做统计订正：构建历史同期模式–实况样本库，空间分块内做 TS+BIAS 相似筛选、光流位移与频率匹配，输出 MICAPS3 站点场与 MICAPS4 格点场。

## 目录对应关系

| 路径 | 内容说明 |
| --- | --- |
| `00temp/multi_qpf_fm_rain01/src/runner.py` | **主程序** `process`；`__main__` 直接传参 |
| `00temp/multi_qpf_fm_rain01/cli/__main__.py` | `python -m cli` → `runner.process` |
| `00temp/multi_qpf_fm_rain01/src/proc/` | 相似 / 光流 / 平流 / 频率匹配 / Cressman |
| `00temp/multi_qpf_fm_rain01/src/utils/` | 本包工具（types / verify / log / util_*） |
| `00temp/utils/` | 共享 `multipro_plugin` / `data_prepare_plugin` |
| `00temp/multi_qpf_fm_rain01/00temp/` | **整理中间数据** |
| `00temp/multi_qpf_fm_rain01/00log/` | **整理过程日志**（一次整理一份） |
| `00temp/multi_qpf_fm_rain01/NIMM_list.md` | **算法清单表**（种类、功能、目录、待办） |

## 2026-07-23 整理要点

- 抽出 `process`；CLI 迁至 `cli/`；`__main__` 直接传参。
- 共享 `00temp/utils`；算法工具在 `src/utils`。
- 目录代号更名为 `multi_qpf_fm_rain01`。
- 单元测试：`test_runner_config` / `test_multi_qpf_fm_rain01` / `test_util_env` 通过。

## 仍存在问题（需人工补充）

与包内日志第五节、`NIMM_list.md` 待办表一致，摘要如下：

1. 贡献人 / 原始绝对路径待补全。  
2. `docs/`、`nbs/` 旧入口与旧代号文案待同步。  
3. `requirements.txt` 缺失。  
4. `resource/data/` 样例过大，入库前筛选。  
5. 未迁入正式 NIMM 目录；业务端到端未复跑。  
6. `00temp/multi_qpf_fm_rain01/` 仅占位。  
