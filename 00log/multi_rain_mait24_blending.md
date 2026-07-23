# multi_rain_mait24_blending 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `multi_rain_mait24_blending` |
| 中文名称 | 逐日多源自适应降水集成MAIT24 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\mait_24h` |
| 整理日期 | 2026-06-29（初整）；2026-07-06（NIMM 标准化）；2026-07-23（CLI / process 职责分离） |
| 算法贡献人 | 郭云谦、曹勇、陈荣（初整）；算法包清单另记郝书剑、赵如奇、杨宸源 |
| 算法分类 | `05blending` |
| 当前状态 | 已整理至中间目录；`process` 可模块调度；CLI 在 `cli/`；待正式入库 |

## 算法理解

该算法是面向逐日 24 小时累积降水的多源自适应融合业务流程。主流程读取多模式历史样本、当前预报、实况、背景场和掩码，基于分区 TS 技巧评分和历史 beta 记忆自适应计算模式权重，完成站点降水集成与频率匹配订正，再插值生成格点产品。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/multi_rain_mait24_blending/src/mait_24h.py` | `process` 供模块引用；`__main__` 直接传参运行 |
| `00temp/multi_rain_mait24_blending/cli/__main__.py` | `python -m cli` 解析参数 → `mait_24h.process` |
| `00temp/multi_rain_mait24_blending/cli/verify.py` | 检验子命令 |
| `00temp/multi_rain_mait24_blending/src/mait_24_plugin.py` 等 | 算法核心与读数 |
| `00temp/multi_rain_mait24_blending/test/` | 单元测试与业务脚本 |
| `00temp/multi_rain_mait24_blending/docs/`、`nbs/` | 文档与 notebook |
| `00temp/multi_rain_mait24_blending/00temp/` | 整理过程中间数据（`mait_24h/`） |
| `00temp/multi_rain_mait24_blending/00log/` | 整理过程日志（一次整理一份） |
| `00temp/multi_rain_mait24_blending/NIMM_list.md` | 算法包内整理清单 |

## 2026-07-23 更新

- Clize 从 `src/mait_24h.py` 迁至 `cli/__main__.py`；参数补充中文说明。
- `src/mait_24h.py` 仅保留可调度 `process`；`__main__` 中直接给 `process` 传参。
- 详细过程见：`00temp/multi_rain_mait24_blending/00log/mait_24h_整理_20260723.log`。

## 2026-07-06 更新

- NIMM 标准化：模块拆分、CLI、单元测试等。
- 详见：`00temp/multi_rain_mait24_blending/00log/mait_24h_整理_20260706.log`。

## 仍存在问题（需人工补充）

1. docs / nbs / README 中旧入口文案需人工核对。
2. 生产路径与 `resource/` 最小资源集需部署/入库前筛选。
3. 尚未补充到正式 `NIMM/05blending/` 目录。
4. 未做完整业务数据试跑与结果对比。
5. `00temp/mait_24h/` 仅占位，对照中间文件待按需归档。
