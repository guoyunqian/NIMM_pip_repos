# fy4b_argi_l1_decoder 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `fy4b_argi_l1_decoder` |
| 中文名称 | FY4卫星ARGI的L1数据解码 |
| 原始路径 | `D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\FY4B_code` |
| 整理日期 | 2026-06-29 |
| 算法贡献人 | 郭云谦、丰硕 |
| 算法分类 | `basic_data` |
| 当前状态 | 已整理至中间目录，待补充至算法仓库 |

## 算法理解

该算法用于 FY-4B AGRI L1 HDF 数据解码。核心流程包括读取 HDF 中的通道 DN 数据和定标表，将 DN 转为反射率或亮温，并将 FY-4 静止卫星固定网格重采样到规则经纬度网格，最终按通道写出 NetCDF 文件。

原始代码、README 和包名均使用 `AGRI`。本次根据用户确认使用 `argi` 作为算法目录名和清单名，但保留源码包名 `fy4agri`，避免在原始整理阶段改变导入逻辑。

核心源码包括：

- `src/fy4agri/metadata.py`：通道元数据、HDF 属性解析、通道选择解析。
- `src/fy4agri/projection.py`：FY-4 静止卫星投影和经纬度转换。
- `src/fy4agri/reader.py`：通道定标和重采样。
- `src/fy4_latlon_channel_plugin.py`：单文件插件。
- `src/fy4_batch_latlon_channel_plugin.py`：批处理插件。

## 本次整理操作

已将原始目录内容整理到中间目录：

`00temp/fy4b_argi_l1_decoder/`

整理内容包括：

- `src/`：核心源码包和插件脚本。
- `cli/`：批处理运行示例。
- `docs/`：原始 README，并新增 `fy4b_argi_l1_decoder.md`。
- `test/`：新增不依赖真实 HDF 的最小测试。
- `resource/`、`test_data/`、`nbs/`、`utils/`：新增说明文件，标注原始目录未提供对应内容。

未执行操作：

- 未删除或移动任何原始文件。
- 未补充到正式 `NIMM/basic_data/` 目录。
- 未修改原始算法逻辑。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/fy4b_argi_l1_decoder/src/` | 核心算法源码和插件 |
| `00temp/fy4b_argi_l1_decoder/cli/` | 批处理示例脚本 |
| `00temp/fy4b_argi_l1_decoder/resource/` | 资源说明，原始目录未提供资源 |
| `00temp/fy4b_argi_l1_decoder/test/` | 最小测试脚本 |
| `00temp/fy4b_argi_l1_decoder/test_data/` | 测试数据说明，原始目录未提供 HDF 样例 |
| `00temp/fy4b_argi_l1_decoder/nbs/` | notebook 说明，原始目录未提供 notebook |
| `00temp/fy4b_argi_l1_decoder/docs/` | 文档 |
| `00temp/fy4b_argi_l1_decoder/utils/` | 工具目录说明，原始工具位于 `src/fy4agri/` |

## 已发现问题与后续建议

1. 原始目录没有真实 FY-4B AGRI L1 HDF 样例数据，因此当前只能做参数校验、文件名解析和通道元数据测试，无法验证真实定标和重采样结果。
2. 原始代码依赖 `h5py`、`numpy`、`scipy`、`xarray`。正式补充前需要确认环境依赖。
3. 输出为规则经纬度重采样产品，不是原始 FY-4 固定网格数据。
4. 正式补充到 `NIMM/basic_data/` 时需要统一导入路径。
5. 算法名称使用 `argi`，源码和 FY-4 传感器名称使用 `agri`，后续如需统一命名，应由人工确认。

## 校验记录

- 已完成 Python 语法解析校验：8 个 Python 文件语法正常。
- 尝试运行新增 pytest 测试时，当前 Python 环境缺少 `pytest`，未执行成功。
- 改用直接导入核心模块进行最小断言时，当前 Python 环境缺少 `h5py`，插件模块无法导入；正式测试前需补齐依赖。
