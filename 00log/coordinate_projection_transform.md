# 坐标投影转换整理日志

## 原始算法信息

- 算法名称：`coordinate_projection_transform`
- 中文名称：坐标投影转换
- 原始目录名：`00_lambert_transform`
- 原始路径：`D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\00_lambert_transform`
- 算法类型：`ancillaries`
- 贡献人：郭云谦、陈荣
- 整理日期：2026-06-29

## 算法理解

原始算法提供经纬度网格、Lambert 等距投影网格、`iris.cube.Cube` 与 `meteva_base.grid_data` 之间的转换能力。核心插件入口包括 `CubeLonlatToEqual.process()`、`TransMetevaToCube.process()` 和 `TransCubeToMeteva.process()`；底层还提供 `proj_convert_kdtreeN()`，用于基于投影坐标和 KDTree 的数组插值转换。

## 本次整理操作

- 在 `00temp/coordinate_projection_transform/` 下创建统一中间目录。
- 将原始 `.py` 文件复制到 `src/`。
- 将原始 notebook 文件复制到 `nbs/`。
- 新增轻量 CLI：`cli/coordinate_projection_transform_main.py`。
- 新增基础结构测试：`test/test_coordinate_projection_transform.py`。
- 新增说明文档：`docs/坐标投影转换.md`。
- 保留空 `resource/` 与 `utils/` 目录以满足仓库规范。
- 更新 `NIMM_list.md`，追加该算法整理记录。

## 验证记录

- 使用 Codex 捆绑 Python 对中间目录全部 Python 文件执行 `compileall` 语法编译，结果通过。
- 运行 `python -m cli.coordinate_projection_transform_main --mode summary`，结果通过。
- 当前环境未安装 `pytest`，未执行 pytest；改用 Python 直接调用基础结构测试函数，结果通过。
- 尝试运行 `--mode lonlat-to-equal`，因当前环境缺少 `xarray`，报 `ModuleNotFoundError: No module named 'xarray'`。同时检查到 `iris`、`cartopy`、`cf_units`、`improver`、`meteva_base`、`xarray`、`scipy` 均未在当前运行时安装。
- 本次验证生成的 `__pycache__` 已清理。

## 中间目录结构

- 源码位置：`00temp/coordinate_projection_transform/src/`
- CLI位置：`00temp/coordinate_projection_transform/cli/`
- 资源位置：`00temp/coordinate_projection_transform/resource/`
- 测试位置：`00temp/coordinate_projection_transform/test/`
- Notebook位置：`00temp/coordinate_projection_transform/nbs/`
- 文档位置：`00temp/coordinate_projection_transform/docs/`
- 工具位置：`00temp/coordinate_projection_transform/utils/`

## 仍存在问题

- 原始代码依赖上层 `nimm` 包结构，正式入库时需统一导入路径。
- 完整运行依赖 `iris`、`cartopy`、`cf_units`、`improver`、`meteva_base`、`xarray` 和 `scipy`。
- 原始 notebook 体量较大且可能包含旧业务数据路径。
- 原始目录无独立小样例资源数据，当前 `resource/` 为空。
- 尚未运行完整投影转换业务测试。
