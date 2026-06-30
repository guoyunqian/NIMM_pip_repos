# 邻域处理算法技术说明

## 1. 概述

`nbhood` 模块迁移自 Improver 的 `improver.nbhood.nbhood`，用于二维空间网格上的邻域统计计算。

当前迁移版包含以下核心组件：

- `check_radius_against_distance`
- `circular_kernel`
- `BaseNeighbourhoodProcessing`
- `NeighbourhoodProcessing`
- `GeneratePercentilesFromANeighbourhood`

说明：

- 算法层未迁移 `MetaNeighbourhood` 类。
- 原 `MetaNeighbourhood` 的编排逻辑在 CLI 层实现（`nbhood/cli/ens_nbhood.py`）。

## 2. 输入输出总览

### 2.1 输入类型

- 支持 `xarray.DataArray`
- 支持 `numpy.ndarray`

### 2.2 输出类型

- 输入为 `numpy.ndarray`：输出为 `numpy.ndarray`（某些路径可能是 `numpy.ma.MaskedArray`）。
- 输入为 `xarray.DataArray`：
  - 当输入是标准 meb 六维（`member, level, time, dtime, lat, lon`）时，输出会重组为标准 meb 六维 `xarray.DataArray`。
  - 当输入不是标准 meb 六维时，默认会在输入校验阶段报错。

## 3. 核心类说明

### 3.1 BaseNeighbourhoodProcessing

职责：

- 校验 `radii` 与 `lead_times` 参数一致性；
- 按输入时效匹配或插值当前半径；
- 检查未掩码输入数据中的 `NaN`；
- 对 `xarray.DataArray` 输入执行网格格式检查。

主函数：

- `process(data, input_lead_times=None) -> data`

初始化参数表：


| 参数名          | 类型                      | 必填  | 默认值    | 说明                                        |
| ------------ | ----------------------- | --- | ------ | ----------------------------------------- |
| `radii`      | `float` 或 `list[float]` | 是   | -      | 邻域半径，单位米。可传单值或多值。                         |
| `lead_times` | `list[int]` 或 `None`    | 否   | `None` | 与 `radii` 对应的时效序列（小时）。若提供需与 `radii` 一一对应。 |


`process` 输入参数表：


| 参数名                | 类型                                   | 必填  | 默认值    | 说明                         |
| ------------------ | ------------------------------------ | --- | ------ | -------------------------- |
| `data`             | `xarray.DataArray` 或 `numpy.ndarray` | 是   | -      | 输入数据，最后两维应为空间维。            |
| `input_lead_times` | `float` 或 `numpy.ndarray` 或 `None`   | 否   | `None` | 本次处理对应的输入时效（小时），用于匹配或插值半径。 |


说明：

- 该类只负责公共前置校验与半径准备，不直接执行邻域统计。

### 3.2 NeighbourhoodProcessing

功能：

- 执行邻域平均或邻域求和；
- 支持方形邻域（`square`）与圆形邻域（`circular`）；
- 支持圆形核加权（`weighted_mode`，仅 `circular` 有效）；
- 支持外部掩码和结果重掩码。

主函数：

- `process(data, mask=None, input_lead_times=None, grid_spacing=None)`

初始化参数表：


| 参数名                    | 类型                      | 必填  | 默认值     | 说明                             |
| ---------------------- | ----------------------- | --- | ------- | ------------------------------ |
| `neighbourhood_method` | `str`                   | 是   | -       | 邻域形状，支持 `square` 或 `circular`。 |
| `radii`                | `float` 或 `list[float]` | 是   | -       | 邻域半径，单位米。                      |
| `lead_times`           | `list[int]` 或 `None`    | 否   | `None`  | 与 `radii` 对应的时效序列（小时）。         |
| `weighted_mode`        | `bool`                  | 否   | `False` | 是否使用加权圆核，仅 `circular` 有效。      |
| `sum_only`             | `bool`                  | 否   | `False` | `True` 输出邻域和，`False` 输出邻域平均。   |
| `re_mask`              | `bool`                  | 否   | `True`  | 是否将输入掩码重新应用到输出。                |


`process` 输入参数表：


| 参数名                | 类型                                            | 必填  | 默认值    | 说明                                  |
| ------------------ | --------------------------------------------- | --- | ------ | ----------------------------------- |
| `data`             | `xarray.DataArray` 或 `numpy.ndarray`          | 是   | -      | 输入数据，最后两维为空间维。                      |
| `mask`             | `xarray.DataArray` 或 `numpy.ndarray` 或 `None` | 否   | `None` | 外部掩码，`0` 表示无效点。                     |
| `input_lead_times` | `float` 或 `numpy.ndarray` 或 `None`            | 否   | `None` | 输入时效（小时），用于时效半径映射。                  |
| `grid_spacing`     | `float` 或 `tuple[float, float]` 或 `None`      | 否   | `None` | `numpy` 路径必传，单位米；`xarray` 路径通常自动推断。 |


要点：

- 对高维输入按“前导维逐片 + 最后两维空间场”处理。
- `xarray` 路径自动推断网格间距并做半径范围检查。
- `numpy` 路径需显式提供 `grid_spacing`。

### 3.3 GeneratePercentilesFromANeighbourhood

功能：

- 在圆形邻域内计算百分位；
- 支持多百分位批量计算。

主函数：

- `process(data, input_lead_times=None, grid_spacing=None)`

初始化参数表：


| 参数名           | 类型                      | 必填  | 默认值                   | 说明                     |
| ------------- | ----------------------- | --- | --------------------- | ---------------------- |
| `radii`       | `float` 或 `list[float]` | 是   | -                     | 邻域半径，单位米。              |
| `lead_times`  | `list[int]` 或 `None`    | 否   | `None`                | 与 `radii` 对应的时效序列（小时）。 |
| `percentiles` | `float` 或 `list[float]` | 否   | `DEFAULT_PERCENTILES` | 目标百分位序列。               |


`process` 输入参数表：


| 参数名                | 类型                                       | 必填  | 默认值    | 说明                                  |
| ------------------ | ---------------------------------------- | --- | ------ | ----------------------------------- |
| `data`             | `xarray.DataArray` 或 `numpy.ndarray`     | 是   | -      | 输入数据，最后两维为空间维。                      |
| `input_lead_times` | `float` 或 `numpy.ndarray` 或 `None`       | 否   | `None` | 输入时效（小时），用于时效半径映射。                  |
| `grid_spacing`     | `float` 或 `tuple[float, float]` 或 `None` | 否   | `None` | `numpy` 路径必传，单位米；`xarray` 路径通常自动推断。 |


要点：

- 仅支持圆形邻域。
- 输入若为 masked array 会抛 `NotImplementedError`。
- `numpy` 路径输出首轴为 `percentile`。
- `xarray + meb 六维` 路径输出会重组为 meb 六维。

## 4. 百分位（GeneratePercentilesFromANeighbourhood）输出

### 4.1 numpy 路径

输出首轴固定为 `percentile`：

- 输入 `(y, x)` -> 输出 `(n_percentiles, y, x)`
- 输入 `(*batch, y, x)` -> 输出 `(n_percentiles, *batch, y, x)`

### 4.2 xarray + 标准 meb 六维路径

将`percentile`维度与输入数据的`member`维度联合后映射到新的 `member` 维。输出维度为标准六维：

- `member, level, time, dtime, lat, lon`

百分位信息通过以下坐标/属性保留：

- 坐标：`member_percentile`
- 坐标：`member_input_member`
- 属性：`member_is_stacked="True"`
- 属性：`member_stack_dims="member,percentile"`
- 属性：`member_units="%"`

## 5. 空间坐标与网格间距

### 5.1 xarray 路径

`_infer_grid_spacing_from_xarray` 按坐标单位分支处理：

- 距离单位（如 `m/km`）：
  - 直接换算到米；
  - 检查等间距与 x/y 一致性。
- 经纬度单位（`degree_*`）：
  1. 优先尝试基于 `grid_mapping` 投影到米坐标；
  2. 投影不可用时，回退局地近似换算（纬向常数，经向乘 `cos(mean_lat)`）。

两条路径都会执行：

- 网格等间距检查；
- 半径是否超过空间域允许范围检查。

### 5.2 numpy 路径

- 必须传入 `grid_spacing`（标量或 `(dy, dx)`），单位米。

## 6. 关键函数说明

### 6.1 check_radius_against_distance

用于检查邻域半径不超过空间域尺度，支持两类输入：

- `(y_coords, x_coords)`
- `(shape, grid_spacing)`

### 6.2 circular_kernel

用于生成圆形核：

- `weighted_mode=False`：二值核
- `weighted_mode=True`：中心权重更大、边缘权重更小

## 7. CLI 用法

示例脚本：`nbhood/cli/ens_nbhood.py`

### 7.1 运行方式

```bash
python -m nbhood.cli.ens_nbhood
```

在代码中调用（方形邻域概率示例）：

```python
from nbhood.cli.ens_nbhood import process

#数据存放路径
base = "./nbhood/test_data/official_test_nbhood/normalized_meb6d/basic"
result = process(
    input_data_path=f"{base}/input.nc",
    neighbourhood_output="probabilities",
    radii=[20000.0],
    mask_path=None,
    output_path=f"{base}/cli_nbhood_square_result.nc",
    neighbourhood_shape="square",
)
```

邻域百分位示例：

```python
from nbhood.cli.ens_nbhood import process

#数据存放路径
base = "./nbhood/test_data/official_test_nbhood/normalized_meb6d/percentile"
process(
    input_data_path=f"{base}/input_circular_percentile.nc",
    neighbourhood_output="percentiles",
    radii=[20000.0],
    percentiles=[25.0, 50.0, 75.0],
    output_path=f"{base}/cli_nbhood_percentiles.nc",
)
```

### 7.2 `process()` 主要参数


| 参数                     | 类型          | 必填  | 默认值      | 说明                              |
| ---------------------- | ----------- | --- | -------- | ------------------------------- |
| `input_data_path`      | str         | 是   | -        | 输入 nc 路径                        |
| `neighbourhood_output` | str         | 是   | -        | `probabilities` 或 `percentiles` |
| `radii`                | list[float] | 是   | -        | 邻域半径（米）                         |
| `mask_path`            | str         | 否   | `None`   | 外部掩码 nc 路径                      |
| `output_path`          | str         | 否   | `None`   | 输出 nc 路径                        |
| `neighbourhood_shape`  | str         | 否   | `square` | `square` 或 `circular`           |
| `lead_times`           | list[int]   | 否   | `None`   | 与 `radii` 对应时效（小时）              |
| `weighted_mode`        | bool        | 否   | `False`  | 仅 `circular` 概率邻域有效             |
| `area_sum`             | bool        | 否   | `False`  | `True` 输出邻域和                    |
| `percentiles`          | list[float] | 否   | 模块默认     | 百分位模式参数                         |
| `degrees_as_complex`   | bool        | 否   | `False`  | 角度场转复数后再处理                      |
| `halo_radius`          | float       | 否   | `None`   | 结果去 halo 半径（米）                  |


PowerShell 直接运行内置方形邻域示例：

```powershell
python -m nbhood.cli.ens_nbhood
```

## 8. 插件类调用示例

### 8.1 NeighbourhoodProcessing（xarray 输入）

```python
import numpy as np
import xarray as xr
from nbhood.src.nbhood import NeighbourhoodProcessing

da = xr.DataArray(
    np.random.rand(1, 1, 1, 1, 50, 60).astype(np.float32),
    dims=("member", "level", "time", "dtime", "lat", "lon"),
    coords={
        "member": [0],
        "level": [0.0],
        "time": [np.datetime64("2024-01-01T00:00:00")],
        "dtime": [0],
        "lat": np.linspace(30.0, 35.0, 50),
        "lon": np.linspace(110.0, 116.0, 60),
    },
    attrs={"units": "1"},
)

plugin = NeighbourhoodProcessing("square", radii=20000.0, sum_only=False, re_mask=False)
result = plugin.process(da)
print(result.dims, result.shape)
```

### 8.2 NeighbourhoodProcessing（numpy 输入）

```python
import numpy as np
from nbhood.src.nbhood import NeighbourhoodProcessing

arr = np.random.rand(50, 60).astype(np.float32)
plugin = NeighbourhoodProcessing("circular", radii=3000.0)
result = plugin.process(arr, grid_spacing=1000.0)
print(type(result), result.shape)
```

### 8.3 GeneratePercentilesFromANeighbourhood（xarray 输入）

```python
import numpy as np
import xarray as xr
from nbhood.src.nbhood import GeneratePercentilesFromANeighbourhood

da = xr.DataArray(
    np.random.rand(2, 1, 1, 1, 50, 60).astype(np.float32),
    dims=("member", "level", "time", "dtime", "lat", "lon"),
    coords={
        "member": [0, 1],
        "level": [0.0],
        "time": [np.datetime64("2024-01-01T00:00:00")],
        "dtime": [0],
        "lat": np.linspace(30.0, 35.0, 50),
        "lon": np.linspace(110.0, 116.0, 60),
    },
    attrs={"units": "1"},
)

plugin = GeneratePercentilesFromANeighbourhood(radii=20000.0, percentiles=[25.0, 50.0, 75.0])
result = plugin.process(da)
print(result.dims, result.shape)
print("coords:", [c for c in result.coords if "percentile" in c or "member" in c])
```

### 8.4 GeneratePercentilesFromANeighbourhood（numpy 输入）

```python
import numpy as np
from nbhood.src.nbhood import GeneratePercentilesFromANeighbourhood

arr = np.random.rand(4, 50, 60).astype(np.float32)
plugin = GeneratePercentilesFromANeighbourhood(radii=20000.0, percentiles=[10.0, 50.0, 90.0])
result = plugin.process(arr, grid_spacing=1000.0)
print(result.shape)  # (3, 4, 50, 60)
```

## 9. 注意事项

- `NeighbourhoodProcessing` 在 `square` 路径支持复数输入；`circular` 路径不支持复数输入。
- 百分位算法当前不支持 masked 输入。
- 若需要 meb 六维输出，请确保输入是标准 meb 六维 `xarray.DataArray`。

