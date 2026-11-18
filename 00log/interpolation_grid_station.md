# interpolation_grid_station 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `interpolation_grid_station` |
| 中文名称 | 格点→站点插值 |
| 原始路径 | `D:\workspace\test\00temp\interpolation_grid_station`（新包） |
| 整理日期 | 2026-11-18 |
| 算法贡献人 | 郭云谦、王亭波 |
| 算法分类 | `ancillaries`（与 gg/sg 插值包统一） |
| 当前状态 | 已同步至中间目录 `00temp/interpolation_grid_station`；待正式补充至算法仓库 |

## 算法理解

将源格点场插值到站点位置，面向 `meteva_base` 六维场。算法对齐 `00temp/utils/interpolating.py` 中的 `interp_gs_*`，封装为插件：

- `InterpGsNearest` / `InterpGsLinear` / `InterpGsCubic`
- 统一 `process(grd, sta)`

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/interpolation_grid_station/src/` | 三插件 + `gs_helpers` |
| `00temp/interpolation_grid_station/cli/` | `python -m cli` |
| `00temp/interpolation_grid_station/resource/` | `conf.ini` 与小样例 nc/csv |
| `00temp/interpolation_grid_station/test/` | 配置与插件测试 |
| `00temp/interpolation_grid_station/nbs/` | `interpolation_grid_station_说明.ipynb` |
| `00temp/interpolation_grid_station/docs/` | `interpolation_grid_station.md` |
| `00temp/interpolation_grid_station/utils/` | `util_env.py` |

## 2026-11-18 首次同步

- 自 `D:\workspace\test\00temp\interpolation_grid_station` 同步至 `00temp/interpolation_grid_station/`；未修改、未删除源目录。
- 未同步 `__pycache__`、`.pytest_cache`、`.ipynb_checkpoints`；无 >5MB 数据需跳过。
- 文本/代码哈希校验：17 个 `.py`/`.md`/`.ini`/`.ipynb` 一致；另复制小样例数据；合计 20 文件。
- 注：`frequency_matching_rain24` 的格点→站点仍走 `meteva.base.interp_gs_linear`，未强制改接本包。

## 仍存在问题（需人工补充）

1. 正式入库时改为 `NIMM/ancillaries/` 包路径。
2. 是否让频率匹配等业务改接本包 `InterpGsLinear` 需另定。
