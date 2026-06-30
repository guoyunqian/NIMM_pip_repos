#!/usr/bin/env markdown

# `correct.region_dealias` 使用说明

## 1. 模块作用

`correct.region_dealias` 用于将 Py-ART 中基于区域连通关系的多普勒速度退模糊算法迁移到 `meteva_base.grid_data` 输入输出体系中。

迁移后的实现保留原算法核心流程：

- 按 Nyquist 区间对速度场分段。
- 在二维 sweep 平面上识别连通区域。
- 根据相邻区域边界关系逐步合并并展开速度。
- 在提供参考速度场时，对结果进行整体或分区锚定。

当前模块提供三个主要入口：


| 入口                          | 类型   | 作用                                        |
| --------------------------- | ---- | ----------------------------------------- |
| `dealias_region_based(...)` | 函数   | 核心区域退模糊算法，输入输出均为 `meteva_base.grid_data`。 |
| `RegionDealiasPlugin`       | 插件类  | 封装核心算法调用，并可附加门点经纬度或重映射到规则经纬网格。            |
| `GridGateFilter`            | 过滤器类 | 为 `meteva_base.grid_data` 构造退模糊所需的门限过滤掩码。 |


## 2. 输入输出约定

### 2.1 网格结构

输入数据必须是 `meteva_base.grid_data` 风格的 `xarray.DataArray`，维度为：

```text
member, level, time, dtime, lat, lon
```

算法会对每个 `member/level/time/dtime` 切片独立执行二维退模糊。

### 2.2 空间维语义

虽然容器维度名仍为 `lat/lon`，但当前算法语义仍对应原始雷达 sweep 的极坐标门结构：


| 维度名   | 当前语义  | 说明                      |
| ----- | ----- | ----------------------- |
| `lat` | 方位角方向 | 对应原始雷达 ray / azimuth 维。 |
| `lon` | 径距方向  | 对应原始雷达 range gate 维。    |


因此，当前版本默认输入保留“方位角 × 径距”的极坐标拓扑，而不是普通规则经纬度网格。

### 2.3 输出

`dealias_region_based(...)` 返回退模糊后的 `meteva_base.grid_data`。

若通过 `RegionDealiasPlugin` 启用地理后处理，则结果可能额外包含：

- `gate_lon`
- `gate_lat`

若启用规则经纬网格重映射，则返回的 `lat/lon` 会变成真实规则经纬度坐标。

## 3. `dealias_region_based` 接口

### 3.1 函数签名

```python
dealias_region_based(
    velocity,
    ref_velocity=None,
    interval_splits=3,
    interval_limits=None,
    skip_between_rays=100,
    skip_along_ray=100,
    centered=True,
    nyquist_velocity=None,
    gatefilter=False,
    refl=None,
    ncp=None,
    rhv=None,
    min_ncp=0.5,
    min_rhv=None,
    min_refl=-20.0,
    max_refl=100.0,
    rays_wrap_around=None,
    keep_original=False,
    set_limits=True,
    data_name="corrected_velocity",
    attrs=None,
)
```

### 3.2 参数说明


| 参数                  | 类型                                | 默认值                    | 说明                                                                                                          |
| ------------------- | --------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------- |
| `velocity`          | `xr.DataArray`                    | 必填                     | 待退模糊径向速度场，必须为 `meteva_base.grid_data`。                                                                      |
| `ref_velocity`      | `xr.DataArray` 或 `None`           | `None`                 | 参考速度场，用于结果锚定。若提供，网格坐标必须与 `velocity` 一致。                                                                     |
| `interval_splits`   | `int`                             | `3`                    | 每个 Nyquist 区间内的初始分段数。                                                                                       |
| `interval_limits`   | array-like 或 `None`               | `None`                 | 自定义速度分段边界。未提供时由 Nyquist 速度自动生成。                                                                             |
| `skip_between_rays` | `int`                             | `100`                  | 跨射线方向连接区域时允许跨越的最大缺测间隔。                                                                                      |
| `skip_along_ray`    | `int`                             | `100`                  | 沿径向方向连接区域时允许跨越的最大缺测间隔。                                                                                      |
| `centered`          | `bool`                            | `True`                 | 是否将整体展开圈数居中到 0 附近。                                                                                          |
| `nyquist_velocity`  | `float`、array-like 或 `None`       | `None`                 | Nyquist 速度。可为标量，也可与 `velocity.shape[:4]` 一致；若不传，则从 `attrs["nyquist_velocity"]` 或 `attrs["nyquist_vel"]` 读取。 |
| `gatefilter`        | `None`、`False` 或 `GridGateFilter` | `False`                | 门限过滤器。`False` 表示不启用自动过滤；`None` 表示基于 `refl/ncp/rhv` 自动构造；`GridGateFilter` 表示使用显式过滤器。                         |
| `refl`              | `xr.DataArray` 或 `None`           | `None`                 | 反射率场，仅在 `gatefilter=None` 时用于自动过滤。                                                                          |
| `ncp`               | `xr.DataArray` 或 `None`           | `None`                 | 归一化相干功率场，仅在 `gatefilter=None` 时用于自动过滤。                                                                      |
| `rhv`               | `xr.DataArray` 或 `None`           | `None`                 | 相关系数字段，仅在 `gatefilter=None` 时用于自动过滤。                                                                        |
| `min_ncp`           | `float` 或 `None`                  | `0.5`                  | 自动过滤时保留的 NCP 最小阈值。                                                                                          |
| `min_rhv`           | `float` 或 `None`                  | `None`                 | 自动过滤时保留的 RhoHV 最小阈值。                                                                                        |
| `min_refl`          | `float` 或 `None`                  | `-20.0`                | 自动过滤时保留的反射率下限。                                                                                              |
| `max_refl`          | `float` 或 `None`                  | `100.0`                | 自动过滤时保留的反射率上限。                                                                                              |
| `rays_wrap_around`  | `bool` 或 `None`                   | `None`                 | 是否将方位向首尾视为相邻。`None` 时按 `scan_type` / `sweep_mode` 推断。                                                       |
| `keep_original`     | `bool`                            | `False`                | 被过滤格点是否保留原始速度值。`False` 时输出缺测。                                                                               |
| `set_limits`        | `bool`                            | `True`                 | 是否在输出属性中写入 `valid_min` 和 `valid_max`。                                                                       |
| `data_name`         | `str`                             | `"corrected_velocity"` | 输出数据名称。                                                                                                     |
| `attrs`             | `dict` 或 `None`                   | `None`                 | 附加到输出结果的额外属性。                                                                                               |


### 3.3 输出属性


| 属性                        | 说明                                  |
| ------------------------- | ----------------------------------- |
| `long_name`               | 输出字段长名称。                            |
| `units`                   | 继承输入速度场单位。                          |
| `nyquist_velocity`        | 使用的 Nyquist 速度；若所有切片一致则为标量，否则保留为数组。 |
| `_FillValue`              | 输出缺测填充值，优先继承输入属性。                   |
| `valid_min` / `valid_max` | 当 `set_limits=True` 时写入的有效范围。       |


## 4. `RegionDealiasPlugin` 接口

### 4.1 插件定位

`RegionDealiasPlugin` 只做参数收口、核心算法调用和可选地理后处理，不重复实现退模糊逻辑。

### 4.2 初始化参数

`RegionDealiasPlugin.__init__` 的参数可分为两类：


| 参数                          | 类型                                | 默认值                    | 说明                                 |
| --------------------------- | --------------------------------- | ---------------------- | ---------------------------------- |
| `interval_splits`           | `int`                             | `3`                    | 转发给 `dealias_region_based`。        |
| `interval_limits`           | array-like 或 `None`               | `None`                 | 转发给 `dealias_region_based`。        |
| `skip_between_rays`         | `int`                             | `100`                  | 转发给 `dealias_region_based`。        |
| `skip_along_ray`            | `int`                             | `100`                  | 转发给 `dealias_region_based`。        |
| `centered`                  | `bool`                            | `True`                 | 转发给 `dealias_region_based`。        |
| `nyquist_velocity`          | `float`、array-like 或 `None`       | `None`                 | 转发给 `dealias_region_based`。        |
| `gatefilter`                | `None`、`False` 或 `GridGateFilter` | `False`                | 转发给 `dealias_region_based`。        |
| `min_ncp`                   | `float` 或 `None`                  | `0.5`                  | 转发给 `dealias_region_based`。        |
| `min_rhv`                   | `float` 或 `None`                  | `None`                 | 转发给 `dealias_region_based`。        |
| `min_refl`                  | `float` 或 `None`                  | `-20.0`                | 转发给 `dealias_region_based`。        |
| `max_refl`                  | `float` 或 `None`                  | `100.0`                | 转发给 `dealias_region_based`。        |
| `rays_wrap_around`          | `bool` 或 `None`                   | `None`                 | 转发给 `dealias_region_based`。        |
| `keep_original`             | `bool`                            | `False`                | 转发给 `dealias_region_based`。        |
| `set_limits`                | `bool`                            | `True`                 | 转发给 `dealias_region_based`。        |
| `data_name`                 | `str`                             | `"corrected_velocity"` | 转发给 `dealias_region_based`。        |
| `attrs`                     | `dict` 或 `None`                   | `None`                 | 转发给 `dealias_region_based`。        |
| `radar_lon` / `radar_lat`   | `float` 或 `None`                  | `None`                 | 雷达站点经纬度，用于附加门点经纬度或重映射。             |
| `elevation_deg`             | `float`                           | `0.0`                  | 仰角，用于门点经纬度转换。                      |
| `azimuth_deg`               | array-like 或 `None`               | `None`                 | 显式方位角序列；未传时使用输入 `lat` 轴。           |
| `range_m`                   | array-like 或 `None`               | `None`                 | 显式径距序列，单位为米；未传时从输入 `lon` 轴及单位属性推断。 |
| `target_lon` / `target_lat` | array-like 或 `None`               | `None`                 | 目标规则经纬网格坐标。若提供，则执行规则经纬网格重映射。       |
| `geo_method`                | `str`                             | `"nearest"`            | 门点到规则经纬网格的插值方法。                    |
| `geo_resolution_deg`        | `float` 或 `None`                  | `0.01`                 | 自动生成目标经纬网格时使用的分辨率。                 |
| `geo_nlon` / `geo_nlat`     | `int` 或 `None`                    | `None`                 | 自动生成目标经纬网格时使用的格点数。                 |
| `auto_remap_to_latlon`      | `bool`                            | `False`                | 是否自动根据门点经纬度范围生成规则经纬网格并重映射。         |


### 4.3 `process` 参数


| 参数             | 类型                      | 默认值    | 说明                |
| -------------- | ----------------------- | ------ | ----------------- |
| `velocity`     | `xr.DataArray`          | 必填     | 待退模糊速度场。          |
| `ref_velocity` | `xr.DataArray` 或 `None` | `None` | 可选参考速度场。          |
| `refl`         | `xr.DataArray` 或 `None` | `None` | 自动过滤时使用的反射率场。     |
| `ncp`          | `xr.DataArray` 或 `None` | `None` | 自动过滤时使用的 NCP 场。   |
| `rhv`          | `xr.DataArray` 或 `None` | `None` | 自动过滤时使用的 RhoHV 场。 |


### 4.4 地理重映射说明

插件地理后处理分为两步：


| 步骤         | 触发条件                                                     | 结果                                       |
| ---------- | -------------------------------------------------------- | ---------------------------------------- |
| 附加门点经纬度    | 提供或可从属性推断 `radar_lon/radar_lat`                          | 输出保留原极坐标拓扑，并附加二维 `gate_lon/gate_lat` 坐标。 |
| 重映射到规则经纬网格 | 提供 `target_lon/target_lat`，或 `auto_remap_to_latlon=True` | 输出变为规则经纬网格，覆盖范围外固定掩码处理。                  |


覆盖范围外的目标格点没有业务意义，因此当前实现始终进行掩码处理。

## 5. `GridGateFilter` 接口

### 5.1 类说明

`GridGateFilter` 是参考 Py-ART `GateFilter` 思路，为 `meteva_base.grid_data` 构建的轻量过滤器。它不全量复刻雷达对象相关功能，只保留当前退模糊所需的过滤能力。

### 5.2 构造与属性


| 接口                                                                 | 说明                           |
| ------------------------------------------------------------------ | ---------------------------- |
| `GridGateFilter(velocity, exclude_based=True, gate_excluded=None)` | 基于速度场创建过滤器。                  |
| `GridGateFilter.from_mask(velocity, mask)`                         | 基于布尔掩码创建过滤器；`True` 表示该格点被过滤。 |
| `copy()`                                                           | 返回过滤器副本。                     |
| `gate_excluded`                                                    | 被过滤格点布尔数组副本。                 |
| `gate_included`                                                    | 参与计算格点布尔数组副本。                |


`mask` 可以是二维平面掩码，也可以是与 `velocity` 完全同形状的六维掩码。若使用六维掩码，算法会在逐切片计算时自动取出当前二维过滤平面。

### 5.3 常用过滤方法


| 方法                                    | 作用                   |
| ------------------------------------- | -------------------- |
| `exclude_below(grid_data, value)`     | 过滤小于阈值的格点。           |
| `exclude_above(grid_data, value)`     | 过滤大于阈值的格点。           |
| `exclude_inside(grid_data, v1, v2)`   | 过滤区间内格点。             |
| `exclude_outside(grid_data, v1, v2)`  | 过滤区间外格点。             |
| `exclude_equal(grid_data, value)`     | 过滤等于指定值的格点。          |
| `exclude_not_equal(grid_data, value)` | 过滤不等于指定值的格点。         |
| `exclude_masked(grid_data)`           | 过滤掩码格点。              |
| `exclude_invalid(grid_data)`          | 过滤 `NaN`、`Inf` 等非法值。 |
| `exclude_gates(mask)`                 | 按外部布尔数组过滤格点。         |
| `exclude_all()` / `exclude_none()`    | 过滤全部格点 / 清空过滤状态。     |
| `include_below(grid_data, value)`     | 仅保留小于阈值的格点。          |
| `include_above(grid_data, value)`     | 仅保留大于阈值的格点。          |
| `include_inside(grid_data, v1, v2)`   | 仅保留区间内格点。            |
| `include_outside(grid_data, v1, v2)`  | 仅保留区间外格点。            |
| `include_equal(grid_data, value)`     | 仅保留等于指定值的格点。         |
| `include_not_equal(grid_data, value)` | 仅保留不等于指定值的格点。        |
| `include_not_masked(grid_data)`       | 仅保留非掩码格点。            |
| `include_valid(grid_data)`            | 仅保留有限值格点。            |
| `include_gates(mask)`                 | 按外部布尔数组保留格点。         |
| `include_all()` / `include_none()`    | 清空过滤状态 / 过滤全部格点。     |


## 6. 缺测值处理


| 阶段               | 处理方式                                                  |
| ---------------- | ----------------------------------------------------- |
| 输入掩码             | 通过 `GridGateFilter.exclude_masked(...)` 排除。           |
| 输入 `NaN` / `Inf` | 通过 `GridGateFilter.exclude_invalid(...)` 排除。          |
| 数值型填充值           | 读取 `_FillValue` / `missing_value`，并在核心计算前排除。          |
| 输出缺测             | 优先继承输入 `_FillValue` / `missing_value`，否则使用 `-9999.0`。 |
| 地理重映射插值          | 插值前剔除 `NaN`、`_FillValue`、`missing_value`。             |
| 覆盖范围外格点          | 固定掩码处理，不作为可选参数暴露。                                     |


## 7. 使用示例

### 7.1 直接调用核心函数

```python
from pyart.correct import dealias_region_based

corrected = dealias_region_based(
    velocity=velocity,
    centered=False,
)
```

### 7.2 使用显式过滤器

```python
import numpy as np

from pyart.correct import GridGateFilter, dealias_region_based

mask = np.load("grid_gatefilter_mask_sweep0.npy").astype(bool)
gatefilter = GridGateFilter.from_mask(velocity, mask)

corrected = dealias_region_based(
    velocity=velocity,
    gatefilter=gatefilter,
    centered=False,
)
```

### 7.3 自动构造过滤器

```python
corrected = dealias_region_based(
    velocity=velocity,
    gatefilter=None,
    refl=refl,
    ncp=ncp,
    rhv=rhv,
    min_ncp=0.5,
    min_refl=0.0,
    max_refl=80.0,
)
```

### 7.4 插件调用

```python
from pyart.correct import RegionDealiasPlugin

plugin = RegionDealiasPlugin(
    centered=False,
    gatefilter=gatefilter,
)

corrected = plugin.process(
    velocity=velocity,
    ref_velocity=ref_velocity,
)
```

### 7.5 插件输出规则经纬网格

```python
plugin = RegionDealiasPlugin(
    centered=False,
    gatefilter=gatefilter,
    radar_lon=116.0,
    radar_lat=40.0,
    auto_remap_to_latlon=True,
    geo_resolution_deg=0.001,
)

corrected_geo = plugin.process(
    velocity=velocity,
    ref_velocity=ref_velocity,
)
```

## 8. CLI 应用

CLI 入口位于 `pyart/correct/cli/region_dealias.py` 的 `process()` 函数。

```python
from pyart.correct.cli.region_dealias import process

process(
    "pyart/correct/test_data/region_dealias/input/velocity_sweep0.nc",
    ref_velocity_path="pyart/correct/test_data/region_dealias/input/ref_velocity_sweep0.nc",
    gatefilter_path="pyart/correct/test_data/region_dealias/input/grid_gatefilter_mask_sweep0.npy",
    data_name="corrected_velocity_cli",
    output_path="pyart/correct/test_data/region_dealias/cli_output/region_dealias_cli.nc",
)
```

也可直接运行示例脚本：

```powershell
python pyart/correct/cli/region_dealias.py
```

### 8.1 CLI 参数表


| 参数                            | 类型        | 默认值                    | 说明                               |
| ----------------------------- | --------- | ---------------------- | -------------------------------- |
| `velocity_path`                    | 路径        | 必填                     | 待退模糊速度场文件。                  |
| `ref_velocity_path`              | 路径        | `None`                 | 参考速度场文件。                         |
| `gatefilter_path`                | `.npy` 路径 | `None`                 | 显式过滤掩码文件，读取后构造 `GridGateFilter`。 |
| `refl_path`                      | 路径        | `None`                 | 自动过滤所需反射率场。                      |
| `ncp_path`                       | 路径        | `None`                 | 自动过滤所需 NCP 场。                    |
| `rhv_path`                       | 路径        | `None`                 | 自动过滤所需 RhoHV 场。                  |
| `interval_splits`           | `int`     | `3`                    | 初始速度分段数。                         |
| `interval_limits`           | 序列或逗号分隔浮点  | `None`                 | 自定义速度分段边界。                       |
| `skip_between_rays`         | `int`     | `100`                  | 跨射线方向允许跨越的最大缺测间隔。                |
| `skip_along_ray`            | `int`     | `100`                  | 沿径向方向允许跨越的最大缺测间隔。                |
| `centered`                  | `bool`    | `True`                 | 是否对整体展开圈数做居中调整。                  |
| `nyquist_velocity`          | `float`   | `None`                 | 显式 Nyquist 速度。                   |
| `min_ncp`                   | `float`   | `0.5`                  | 自动过滤的 NCP 最小阈值。                  |
| `min_rhv`                   | `float`   | `None`                 | 自动过滤的 RhoHV 最小阈值。                |
| `min_refl`                  | `float`   | `-20.0`                | 自动过滤的反射率下限。                      |
| `max_refl`                  | `float`   | `100.0`                | 自动过滤的反射率上限。                      |
| `rays_wrap_around`          | `bool`    | `None`                 | 是否将方位向首尾视为相邻。                    |
| `keep_original`             | `bool`      | `False`                | 过滤格点是否保留原始值。                     |
| `set_limits`                | `bool`    | `True`                 | 是否写入 `valid_min/valid_max`。      |
| `data_name`                 | `str`     | `"corrected_velocity"` | 输出数据名称。                          |
| `radar_lon` / `radar_lat` | `float`   | `None`                 | 雷达站点经纬度。                         |
| `elevation_deg`             | `float`   | `0.0`                  | 仰角。                              |
| `geo_resolution_deg`        | `float`   | `0.01`                 | 自动规则经纬网格分辨率。                     |
| `geo_nlon` / `geo_nlat`   | `int`     | `None`                 | 自动规则经纬网格格点数。                     |
| `auto_remap_to_latlon`      | `bool`      | `False`                | 是否自动重映射到规则经纬网格。                  |
| `output_path`                    | 路径        | `None`              | 输出 NetCDF 文件路径。                  |


### 8.2 CLI 示例

极坐标拓扑输出：

```python
from pyart.correct.cli.region_dealias import process

process(
    "pyart/correct/test_data/region_dealias/input/velocity_sweep0.nc",
    ref_velocity_path="pyart/correct/test_data/region_dealias/input/ref_velocity_sweep0.nc",
    gatefilter_path="pyart/correct/test_data/region_dealias/input/grid_gatefilter_mask_sweep0.npy",
    data_name="corrected_velocity_cli",
    output_path="pyart/correct/test_data/region_dealias/cli_output/region_dealias_cli.nc",
)
```

规则经纬网格输出：

```python
process(
    "pyart/correct/test_data/region_dealias/input/velocity_sweep0.nc",
    ref_velocity_path="pyart/correct/test_data/region_dealias/input/ref_velocity_sweep0.nc",
    gatefilter_path="pyart/correct/test_data/region_dealias/input/grid_gatefilter_mask_sweep0.npy",
    data_name="corrected_velocity_cli_geo",
    auto_remap_to_latlon=True,
    geo_resolution_deg=0.001,
    output_path="pyart/correct/test_data/region_dealias/cli_output/region_dealias_cli_geo.nc",
)
```

## 9. 与原始 Py-ART 的主要差异


| 项目         | 原始 Py-ART          | 当前迁移版                                        |
| ---------- | ------------------ | -------------------------------------------- |
| 输入对象       | `Radar`            | `meteva_base.grid_data`                      |
| 输出对象       | 字段字典               | `meteva_base.grid_data`                      |
| 过滤器        | `GateFilter`       | `GridGateFilter`                             |
| 多 sweep 处理 | Radar 内部按 sweep 处理 | 通过 `member/level/time/dtime` 切片逐个处理          |
| 缺测处理       | 掩码数组与字段元数据         | 掩码、`NaN`、`_FillValue` / `missing_value` 统一处理 |
| 地理坐标       | Radar 自带雷达几何信息     | 插件层按属性或参数附加门点经纬度                             |
| 规则经纬网格     | 非核心算法输出            | 插件层可选后处理                                     |


## 10. 当前限制

当前迁移版虽然使用 `meteva_base.grid_data` 作为数据容器，但核心算法仍依赖雷达极坐标门的邻接关系。

因此：

- 输入的二维空间维应保留单个 sweep 的“方位角 × 径距”拓扑。
- 若输入是真实规则经纬度网格，算法即使能运行，也不能保证结果在退模糊意义上正确。
- `skip_between_rays`、`skip_along_ray`、`rays_wrap_around` 等参数都建立在“射线 × 距离门”的前提下。
- 对真实经纬网格的兼容需要后续增加专门的拓扑重建或极坐标逆变换处理。

## 11. 验证说明

当前测试重点覆盖：

- 输出结构保持 `meteva_base.grid_data`。
- 显式 `GridGateFilter` 与自动过滤逻辑。
- `keep_original`、`gatefilter=None`、`gatefilter=False` 等关键分支。
- 多 level 切片独立处理。
- 插件附加门点经纬度与规则经纬网格重映射。
- 重映射后雷达覆盖范围外格点固定掩码处理。

