# 逐日降水频率匹配订正整理日志

## 原始算法信息

- 算法名称：`frequency_matching_rain24`
- 中文名称：逐日降水频率匹配订正
- 原始工程名：`qpf_fm_rain24`
- 原始路径：`D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\qpf_fm_rain24`
- 算法类型：`04single_calibration`
- 贡献人：郭云谦、陈荣、李东勇
- 整理日期：2026-06-29

## 算法理解

原始算法 `optimize_tp_24h` 针对 24 小时累积降水预报进行频率匹配订正。算法先基于历史模式场与当前模式场进行相似个例检索，再对切片区域执行光流位移订正和频率匹配，最后融合站点订正结果与模式背景场，生成订正后的站点和格点降水产品。

## 本次整理操作

- 在 `00temp/frequency_matching_rain24/` 下创建统一中间目录。
- 将原始 `src/`、`cli/`、`resource/`、`test/`、`nbs/`、`docs/`、`utils/` 复制到中间目录。
- 复制根目录 `README.md` 和 `requirements-cli.txt`，保留原工程说明和依赖信息。
- 将原始 `log/` 复制到 `resource/original_log/`，保留运行日志用于追溯。
- 过滤 `__pycache__`、`.pyc` 和 `.ipynb_checkpoints` 生成缓存，未删除或修改原始目录文件。
- 新增 `docs/逐日降水频率匹配订正.md`，补充算法功能、目录结构、入口、CLI 示例和当前限制。
- 更新 `NIMM_list.md`，追加该算法整理记录。

## 验证记录

- 使用 Codex 捆绑 Python 对中间目录全部 Python 文件执行 `compileall` 语法编译，结果通过。
- 使用 Python 导入 `utils.util_env.get_resolved_paths` 并读取路径配置，结果通过。
- 尝试导入 `src/correct_tp_24h.py` 主流程，因当前环境未安装 `meteva`，报 `ModuleNotFoundError: No module named 'meteva'`，未执行完整业务流程。
- 本次验证生成的 `__pycache__` 已清理。

## 中间目录结构

- 源码位置：`00temp/frequency_matching_rain24/src/`
- CLI位置：`00temp/frequency_matching_rain24/cli/`
- 资源位置：`00temp/frequency_matching_rain24/resource/`
- 测试位置：`00temp/frequency_matching_rain24/test/`
- Notebook位置：`00temp/frequency_matching_rain24/nbs/`
- 文档位置：`00temp/frequency_matching_rain24/docs/`
- 工具位置：`00temp/frequency_matching_rain24/utils/`

## 仍存在问题

- 核心入口为 `src/correct_tp_24h.py::mainProcess`，尚未封装为仓库规范中的算法插件类和 `process()` 方法。
- 完整运行依赖 `meteva`、真实模式 24 小时降水、站点实况、站点模板和掩码文件。
- `resource/plugin/*.json` 保留生产路径模板，正式运行前需改为目标环境路径。
- `resource/optimize_tp_24.ini` 当前默认包含回算起报时间，正式业务部署前需确认实时/回算配置。
- `src/verify_data/` 暂按原始结构保留，后续可考虑迁移到 `test_data/` 并调整测试引用。
- 尚未运行完整业务测试。
