# samos_probability_calibration 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `samos_probability_calibration` |
| 中文名称 | SAMOS 概率订正 |
| 整理日期 | 2026-09-28（补记容器冒烟约定） |
| 算法分类 | `07probability` |
| 当前状态 | 已整理至中间目录；依赖兄弟包 `emos_probability_calibration` |

## 2026-09-28 更新

- 容器冒烟约定：新增 `cli/__init__.py`、`cli/__main__.py` 与包根 `__init__.py`；子命令 `samos`；`run_samos.main()` 默认使用 `resource/cli_input`（spot CSV）写出至 `resource/cli_output`。
- 写入最小 spot 样例；仿真容器冒烟通过（依赖 `pygam` 等，且需同级 `emos_probability_calibration`）。
- 包内文档补充 `python -m cli samos`（示例路径未改）。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/07probability/` 时需调整为仓库正式包路径。
2. 运行时依赖兄弟包 `emos_probability_calibration`；正式入库时确认包路径与依赖声明。
3. `resource/` 已含容器冒烟最小样例；正式入库时确认是否保留或再筛选。
