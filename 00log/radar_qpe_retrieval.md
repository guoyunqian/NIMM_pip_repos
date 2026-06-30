# 雷达降水定量反演QPE整理日志

## 原始算法信息

- 算法名称：`radar_qpe_retrieval`
- 中文名称：雷达降水定量反演QPE
- 原始工程位置：`pyart/retrieve`
- 原始路径：`D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\算法_王\pyart\retrieve`
- 算法类型：`01obs_adustment`
- 贡献人：郭云谦、王亭波
- 整理日期：2026-06-29

## 算法理解

原始算法从 Py-ART 的 QPE 逻辑迁移而来，用于基于雷达反射率、KDP、比衰减和水凝物分类等网格数据估算降水率。核心模块 `src/qpe.py` 已提供统一插件类 `QPEPlugin.process()` 和多个独立插件类，支持 `z`、`zpoly`、`kdp`、`a`、`zkdp`、`za`、`hydro`、`ztor` 等方法。

原始目录还包含回波分类 `echo_class` 相关代码、文档、notebook、测试和样例数据。本次按“雷达降水定量反演QPE”归档，回波分类相关内容作为 QPE 的依赖和相关功能上下文一并保留。

## 本次整理操作

- 在 `00temp/radar_qpe_retrieval/` 下创建统一中间目录。
- 将原始 `src/`、`cli/`、`resource/`、`test/`、`test_data/`、`nbs/`、`docs/`、`utils/` 复制到中间目录。
- 复制根目录 `__init__.py`，保留原始 `retrieve` 包入口。
- 过滤 `__pycache__`、`.pyc` 和 `.ipynb_checkpoints` 生成缓存，未删除或修改原始目录文件。
- 新增 `docs/雷达降水定量反演QPE.md`，补充算法功能、主要方法、目录结构、插件入口、CLI 示例和当前限制。
- 更新 `NIMM_list.md`，追加该算法整理记录。

## 验证记录

- 使用 Codex 捆绑 Python 对中间目录全部 Python 文件执行 `compileall` 语法编译，结果通过。
- 尝试导入 `src.qpe`，当前环境未安装 `xarray`，报 `ModuleNotFoundError: No module named 'xarray'`；同时检查到当前环境也缺少 `meteva_base`。
- 本次验证生成的 `__pycache__` 已清理。

## 中间目录结构

- 源码位置：`00temp/radar_qpe_retrieval/src/`
- CLI位置：`00temp/radar_qpe_retrieval/cli/`
- 资源位置：`00temp/radar_qpe_retrieval/resource/`
- 测试数据位置：`00temp/radar_qpe_retrieval/test_data/`
- 测试位置：`00temp/radar_qpe_retrieval/test/`
- Notebook位置：`00temp/radar_qpe_retrieval/nbs/`
- 文档位置：`00temp/radar_qpe_retrieval/docs/`
- 工具位置：`00temp/radar_qpe_retrieval/utils/`

## 仍存在问题

- 源码依赖原始上层 `pyart` 包上下文，特别是 `pyart.plugin_base` 和 `pyart.retrieve.utils` 等相对导入；正式入库时需调整包结构或导入路径。
- 原始目录同时包含 `echo_class` 回波分类功能，后续可确认是否拆分为独立算法。
- `resource/` 原始为空，当前仅按规范保留目录。
- `test_data/` 体量较大，正式入库时可筛选最小测试样例。
- 尚未运行完整测试。
