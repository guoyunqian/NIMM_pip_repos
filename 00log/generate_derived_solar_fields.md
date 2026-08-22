# generate_derived_solar_fields 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `generate_derived_solar_fields` |
| 中文名称 | 太阳衍生场生成 |
| 原始路径 | `D:\workspace\improver\generate_derived_solar_fields`（原包名 `generate_derived_solar_fields`） |
| 整理日期 | 2026-07-25（NIMM 标准化目录结构整理）；2026-08-22（原目录增量同步） |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `ancillaries` |
| 当前状态 | 已整理至中间目录；导入已统一为模块名；待正式入库 |

## 算法理解

该算法包用于生成太阳衍生场，面向 `xarray.DataArray` / meteva_base 六维单场网格；支持经纬坐标与投影坐标（投影输入需 `attrs["grid_mapping_attrs"]`）。

- `GenerateSolarTime`：按目标网格与指定时刻（`datetime`）计算地方太阳时场（小时，0–24）。
- `GenerateClearskySolarRadiation`：按累积时段与可选海拔、Linke 浑浊度，基于 Ineichen-Perez 晴空模型积分得到累计辐射（W s m-2）。
- CLI `cli/cal_generate_solar_time.py`、`cli/cal_generate_clearsky_solar_radiation.py`：文件式示例调度。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/generate_derived_solar_fields/src/generate_derived_solar_fields.py` | 核心算法与插件 |
| `00temp/generate_derived_solar_fields/src/utils/` | 网格映射与太阳天文计算 |
| `00temp/generate_derived_solar_fields/cli/` | 地方太阳时、晴空辐射与预处理 CLI |
| `00temp/generate_derived_solar_fields/utils/` | 本地 `BasePlugin` |
| `00temp/generate_derived_solar_fields/test/`、`docs/`、`nbs/` | 测试、文档与 notebook |

## 2026-08-22 更新

- 从 `D:\workspace\improver\generate_derived_solar_fields` 增量同步：
  - `src/generate_derived_solar_fields.py`：改用 `meb.checkout_griddata()`，移除本地 `check_for_meb_griddata()`。
  - 补齐 `cli/preprocess_test_data.py`（官方投影样例预处理）。
  - 同步 `docs/generate_derived_solar_fields.md`、`nbs/generate_derived_solar_fields.ipynb`、`src/__init__.py`、`cli/__init__.py`。
  - 为 `cli/cal_generate_solar_time.py`、`cli/cal_generate_clearsky_solar_radiation.py` 的 `process()` 补充参数说明。
- 删除包内 `00log/`、`00temp/`、`NIMM_list.md` 和原目录没有的 `utils/utils.py`。
- 未同步 `test_data/`（约 1.25MB、23 文件）；CLI / 预处理缺样例时提示而不崩溃。
- 原目录 pytest：10 passed；中间目录 pytest：10 passed（2026-08-22）。

## 2026-07-25 更新

- NIMM 标准化：自 improver/generate_derived_solar_fields 同步 `src/`、`utils/`、`cli/`、`test/`、`docs/`、`nbs/`。
- 导入路径保持 `generate_derived_solar_fields`（包内绝对导入）。
- 未同步 `test_data/`；CLI 直启缺样例时提示而非崩溃。
- 原代码目录 pytest：10 passed；中间目录：10 passed（2026-07-25）。

## 仍存在问题（需人工补充）

1. 补充至正式 `NIMM/ancillaries/` 时需调整为仓库正式包路径。
2. `BasePlugin` 正式入库时评估是否改为仓库统一基类。
3. `test_data` 样例约 1.25MB，中间目录未同步；是否纳入 `NIMM_pip_testdata` / 正式仓库后续决定。
4. `resource/` 当前为空，正式补充时确认是否保留。
