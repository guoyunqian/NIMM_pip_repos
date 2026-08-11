# 气温地形降尺度(三维插值)整理日志

## 原始算法信息

- 算法名称：`orographic_nwp_3d_downscaling`
- 中文名称：气温地形降尺度(三维插值)
- 原始工程名：`g_interp_zxq`
- 原始路径：`D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\g_interp_zxq`
- 算法类型：`00space_downscale`
- 贡献人：曾晓青、丰硕、赵如奇
- 整理日期：2026-06-29

## 算法理解

原始算法封装 `g_interp` 快速精细化插值流程，主要用于基于模式场、地形、站点或格点配置开展气温等近地面要素的三维插值、细网格/站点插值，以及可选的最优参数求解。当前工程已提供 `FastRefineInterpPlugin` 插件包装和 `cli/fast_refine_interp.py` 命令行入口。

## 本次整理操作

- 在 `00temp/orographic_nwp_3d_downscaling/` 下创建统一中间目录。
- 将原始 `src/`、`cli/`、`resource/`、`test/`、`nbs/`、`docs/`、`utils/` 复制到中间目录。
- 复制 `pyproject.toml`、`setup.cfg`、`setup.py`、`pytest.ini` 和根 `__init__.py`，保留原工程的包配置上下文。
- 过滤 `__pycache__` 和 `.pyc` 生成缓存，未删除或修改原始目录文件。
- 新增 `docs/气温地形降尺度三维插值.md`，补充算法功能、目录结构、入口、CLI 示例和当前限制。
- 更新 `NIMM_list.md`，追加该算法整理记录。

## 验证记录

- 使用 Codex 捆绑 Python 对 `src/fast_refine_interp_plugin.py`、`src/fast_refine_interp.py`、`cli/fast_refine_interp.py` 进行语法编译，结果通过。
- 尝试执行 `python -m pytest test/test_fast_refine_interp.py -q`，当前环境未安装 `pytest`，未能运行 pytest。
- 使用 Python 直接导入 `nimm_g_interp.src.fast_refine_interp_plugin.FastRefineInterpPlugin`，因当前中间目录不是 `nimm_g_interp` 包，报 `ModuleNotFoundError: No module named 'nimm_g_interp'`。该问题已列入正式入库前需处理事项。

## 中间目录结构

- 源码位置：`00temp/orographic_nwp_3d_downscaling/src/`
- CLI位置：`00temp/orographic_nwp_3d_downscaling/cli/`
- 资源位置：`00temp/orographic_nwp_3d_downscaling/resource/`
- 测试位置：`00temp/orographic_nwp_3d_downscaling/test/`
- Notebook位置：`00temp/orographic_nwp_3d_downscaling/nbs/`
- 文档位置：`00temp/orographic_nwp_3d_downscaling/docs/`
- 工具位置：`00temp/orographic_nwp_3d_downscaling/utils/`

## 仍存在问题

- `00temp/` 中间目录仍保留原始 `nimm_g_interp` 包名；正式归档目录已调整为仓库内相对导入或动态导入。
- 完整运行依赖真实模式资料、地形数据、站点文件、实况数据和业务 `Parameter/lib` 目录，当前仅保留最小配置模板。
- `src/core/Module_Micaps_RW.so` 为二进制扩展，跨平台和跨 Python 版本兼容性需人工确认。
- 原始文档提示默认环境可能缺少 `eccodes` 等依赖，完整业务测试尚未执行。
- 当前测试仅覆盖插件构造，不覆盖完整插值流程。

## 2026-08-11 更新与正式归档操作

本次以 `D:\nimm-file\cli_code\nimm_g_interp` 为整理源，将用户改进后的版本同步到算法仓库。未修改原始算法计算逻辑，主要进行结构归档、导入路径调整和清单同步。

本次操作包括：

- 将新版 `nimm_g_interp` 复制更新到 `00temp/orographic_nwp_3d_downscaling/`，复制时排除 `__pycache__` 和 `.pyc` 缓存文件。
- 将核心源码归档到 `NIMM/00space_downscale/orographic_nwp_3d_downscaling/`。
- 将 CLI 调度入口归档到 `cli/00space_downscale/orographic_nwp_3d_downscaling/`，并按规范命名为 `fast_refine_interp_main.py`、`server_minimal_runner_main.py`。
- 将资源模板、测试、文档、notebook 说明归档到对应的 `resource/`、`test/`、`docs/`、`nbs/` 分类目录。
- 正式目录代码已移除原始 `nimm_g_interp` 导入路径，改为相对导入或 `importlib.import_module()` 动态导入，以兼容 `00space_downscale` 数字开头目录名。
- 在正式核心源码中补充算法贡献人和软件产权说明。
- 已运行 `test/00space_downscale/orographic_nwp_3d_downscaling/test_fast_refine_interp.py` 的最小插件构造测试。

正式归档目录如下：

| 正式目录 | 内容说明 |
| --- | --- |
| `NIMM/00space_downscale/orographic_nwp_3d_downscaling/` | 核心插件、快速精细化插值流程和原核心模块 |
| `cli/00space_downscale/orographic_nwp_3d_downscaling/` | CLI 调度入口 |
| `resource/00space_downscale/orographic_nwp_3d_downscaling/` | 最小配置模板和资源说明 |
| `test/00space_downscale/orographic_nwp_3d_downscaling/` | 最小测试脚本 |
| `docs/00space_downscale/orographic_nwp_3d_downscaling/` | 算法文档 |
| `nbs/00space_downscale/orographic_nwp_3d_downscaling/` | notebook 示例说明 |

仍需后续补充或人工确认：

- 当前测试仍只覆盖插件构造，不覆盖 `process()` 的完整业务运行。
- 完整业务流程仍依赖真实模式资料、地形数据、站点文件、实况数据、`Parameter/lib` 目录和 `eccodes` 等运行环境。
- `Module_Micaps_RW.so` 为二进制扩展，跨平台和 Python 版本兼容性需人工确认。
- 独立小样例输入/输出数据尚未补充到 `NIMM_pip_testdata`，完整端到端业务测试尚未运行。
