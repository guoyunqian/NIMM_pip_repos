# 掩码分层邻域处理技术文档

## 1. 算法概述

`use_nbhood` 模块迁移自 IMPROVER 的 `improver.nbhood.use_nbhood`，核心类为 `ApplyNeighbourhoodProcessingWithAMask`。  
该算法用于在一组分层掩码上重复执行邻域处理，并可按权重将分层结果折叠回原网格场。

典型场景：地形带分层处理。  
输入掩码包含一个分层维（例如 `topographic_zone`），每层对应一张二维空间掩码。算法会逐层调用 `NeighbourhoodProcessing`，仅允许当前层有效点参与统计。

## 2. 核心算法说明

### 2.1 分层邻域处理

设输入数据为 `X`，分层掩码为 `M_k`，第 `k` 层处理结果记为 `Y_k`：

`Y_k = Neighbourhood(X, M_k)`

其中：

- `X`：输入网格场；
- `M_k`：第 `k` 个掩码层；
- `Y_k`：在第 `k` 层掩码约束下得到的邻域结果。

所有分层结果会沿掩码维拼接。

### 2.2 加权折叠

若提供分层权重 `W_k`，则沿分层维执行加权平均：

`Y = sum(Y_k * W_k) / sum(W_k)`

折叠时会忽略无效值（如 `NaN` / `Inf` / 被掩码值）。  
若某网格点有效权重和为 0，则该点输出为无效（`NaN` 或 masked）。

## 3. 组件说明

### 3.1 `ApplyNeighbourhoodProcessingWithAMask`

核心职责：

- 识别并规范化掩码分层维；
- 对每个掩码层重复执行邻域处理；
- 在提供权重时沿掩码分层维折叠；
- `xarray` 输入场景下尽量保持维度名与坐标信息。

### 3.2 `collapse_mask_coord`

该方法用于沿掩码分层维做加权折叠，处理流程包括：

- 广播分层结果与权重；
- 屏蔽无效值；
- 计算加权分子与分母；
- 对分母为 0 的点做无效处理。

## 4. 输入输出规范

### 4.1 初始化参数


| 参数                     | 类型                                  | 说明                            |
| ---------------------- | ----------------------------------- | ----------------------------- |
| `coord_for_masking`    | `str`                               | 掩码分层维名称，如 `topographic_zone`  |
| `neighbourhood_method` | `str`                               | 邻域方法，支持 `square` / `circular` |
| `radii`                | `float` 或 `list[float]`             | 邻域半径（米）                       |
| `lead_times`           | `list[int]` 或 `None`                | 与 `radii` 对应的时效（小时）           |
| `collapse_weights`     | `xr.DataArray` / `ndarray` / `None` | 分层折叠权重                        |
| `weighted_mode`        | `bool`                              | 是否启用圆形加权核                     |
| `sum_only`             | `bool`                              | 是否输出邻域和而非邻域平均                 |


### 4.2 `process` 输入参数


| 参数                 | 类型                                       | 说明               | 单位要求          |
| ------------------ | ---------------------------------------- | ---------------- | ------------- |
| `data`             | `xr.DataArray` 或 `ndarray`               | 输入数据，最后两维为 `y,x` | 由调用方保证        |
| `mask`             | `xr.DataArray` 或 `ndarray`               | 分层掩码             | `0` 无效，`1` 有效 |
| `input_lead_times` | `float` / `ndarray` / `None`             | 可变半径场景对应输入时效     | 小时            |
| `grid_spacing`     | `float` / `tuple[float, float]` / `None` | `numpy` 输入时网格分辨率 | 米             |


### 4.3 输出类型

- 输入为 `xarray.DataArray`：
  - 不折叠时返回 `xarray.DataArray`；
  - 折叠时返回 `xarray.DataArray`。
- 输入为 `numpy.ndarray`：
  - 返回 `numpy.ndarray` 或 `numpy.ma.MaskedArray`。

## 5. 输出形状规则

### 5.1 不折叠结果

未提供 `collapse_weights` 时，输出会在空间维前插入掩码分层维：

- 输入 `(y, x)` -> 输出 `(n_mask, y, x)`；
- 输入 `(*leading_dims, y, x)` -> 输出 `(*leading_dims, n_mask, y, x)`。

对 `xarray.DataArray`，不传 `collapse_weights` 时，输出不会保留 `topographic_zone` 维；而是将 `topographic_zone` 与输入 `member` 联合后映射到新的 `member` 维。

### 5.2 折叠结果

提供 `collapse_weights` 时，输出沿掩码分层维加权折叠，形状恢复为输入形状：

- 输入 `(y, x)` -> 输出 `(y, x)`；
- 输入 `(threshold, y, x)` -> 输出 `(threshold, y, x)`。

## 6. 掩码与权重规则

### 6.1 外部掩码语义

- `mask == 1`：当前层有效，参与邻域统计；
- `mask == 0`：当前层无效，不参与邻域统计。

### 6.2 内部掩码

若输入数据是 `numpy.ma.MaskedArray`，其内部掩码同样会被识别并参与无效点处理。

### 6.3 权重折叠

折叠权重要求可整理为 `(n_mask, y, x)`。  
算法在折叠时会自动按有效权重重归一化，避免部分分层无效导致整体结果偏差。

## 7. 与原算法关系

迁移版保留了以下核心行为：

- 按掩码分层重复执行邻域处理；
- 支持按权重折叠掩码分层维；
- 底层复用 `NeighbourhoodProcessing`。

主要差异：

- 去除 Iris Cube 依赖；
- 支持 `xarray.DataArray` 和 `numpy.ndarray`；
- `xarray` 输入时尽量保留维度名与坐标；
- 不处理 Iris `PostProcessingPlugin` 的元数据更新逻辑。

## 8. 使用示例

### 8.1 `numpy.ndarray` 输入，不折叠

```python
import numpy as np
from nbhood.src.use_nbhood import ApplyNeighbourhoodProcessingWithAMask

data = np.array(
    [[1, 1, 1],
     [1, 1, 0],
     [0, 0, 0]],
    dtype=np.float32,
)

mask = np.array(
    [
        [[0, 1, 0], [1, 1, 0], [0, 0, 0]],
        [[0, 0, 1], [0, 0, 1], [1, 1, 0]],
        [[0, 0, 0], [0, 0, 0], [0, 0, 1]],
    ],
    dtype=np.float32,
)

plugin = ApplyNeighbourhoodProcessingWithAMask(
    coord_for_masking="topographic_zone",
    neighbourhood_method="square",
    radii=1.0,
)

result = plugin.process(data, mask, grid_spacing=1.0)
```

### 8.2 `xarray.DataArray` 输入

该场景常用于“前导业务维 + 空间场 + 分层掩码”的生产输入。

关键要点：

- `data` 的最后两维应为空间维（示例中是 `y,x`）；
- `mask` 维度必须包含分层维（示例中是 `topographic_zone`）且空间维与 `data` 对齐；
- 建议 `y/x` 携带距离单位（`m`），便于网格间距推断；
- **不传** `collapse_weights` **时，输出不会保留** `topographic_zone` **维；而是将** `topographic_zone` **与输入** `member` **联合后映射到新的** `member` **维**；
- 输出中会附加用于还原联合关系的坐标/属性（如 `member_input_member`、`member_topographic_zone`、`member_is_stacked`）。

```python
import numpy as np
import xarray as xr
from nbhood.src.use_nbhood import ApplyNeighbourhoodProcessingWithAMask

# 1) 输入场（标准 meb 六维）
data = xr.DataArray(
    np.random.rand(2, 1, 1, 1, 3, 3).astype(np.float32),
    dims=("member", "level", "time", "dtime", "lat", "lon"),
    coords={
        "member": [0, 1],
        "level": [0.0],
        "time": [np.datetime64("2024-01-01T00:00:00")],
        "dtime": [0],
        "lat": xr.DataArray([30.0, 30.01, 30.02], dims=("lat",), attrs={"units": "degree_north"}),
        "lon": xr.DataArray([110.0, 110.01, 110.02], dims=("lon",), attrs={"units": "degree_east"}),
    },
    name="probability_of_event",
    attrs={"units": "1"},
)

# 2) 分层掩码（topographic_zone, lat, lon）
mask = xr.DataArray(
    np.array(
        [
            [[1, 1, 0], [1, 0, 0], [0, 0, 0]],
            [[0, 0, 1], [0, 1, 1], [1, 1, 0]],
            [[0, 0, 0], [0, 0, 0], [0, 0, 1]],
        ],
        dtype=np.float32,
    ),
    dims=("topographic_zone", "lat", "lon"),
    coords={
        "topographic_zone": [50.0, 100.0, 150.0],
        "lat": data.coords["lat"],
        "lon": data.coords["lon"],
    },
)

plugin = ApplyNeighbourhoodProcessingWithAMask(
    coord_for_masking="topographic_zone",
    neighbourhood_method="square",
    radii=1000.0,
    collapse_weights=None,  # 不折叠
)

result = plugin.process(data, mask)
print(result.dims)
print(result.shape)

# 当前实现下，输出示例：
# result.dims  -> ("member", "level", "time", "dtime", "lat", "lon")
# member 维长度 = 输入 member 数 * topographic_zone 层数
# 并通过附加坐标记录联合来源，例如：
#   result.coords["member_input_member"]
#   result.coords["member_topographic_zone"]
```

### 8.3 带权重折叠

该场景在分层处理后沿 `topographic_zone` 做加权折叠，得到与原输入同阶的输出。

关键要点：

- `collapse_weights` 的维度需可整理为 `(topographic_zone, y, x)`；
- 权重与分层结果逐层逐点相乘后再归一化；
- 折叠后 `topographic_zone` 维会被移除。

```python
import numpy as np
import xarray as xr
from nbhood.src.use_nbhood import ApplyNeighbourhoodProcessingWithAMask

# 复用 8.2 的 data 和 mask

weights = xr.DataArray(
    np.array(
        [
            [[0.8, 0.8, 0.0], [0.7, 0.0, 0.0], [0.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.6], [0.0, 0.6, 0.6], [0.5, 0.5, 0.0]],
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.4]],
        ],
        dtype=np.float32,
    ),
    dims=("topographic_zone", "y", "x"),
    coords=mask.coords,
    name="topographic_zone_weights",
    attrs={"units": "1"},
)

plugin = ApplyNeighbourhoodProcessingWithAMask(
    coord_for_masking="topographic_zone",
    neighbourhood_method="square",
    radii=1000.0,
    collapse_weights=weights,  # 启用折叠
    weighted_mode=False,
    sum_only=False,
)

collapsed = plugin.process(data, mask)
print(collapsed.dims)   # ("threshold", "y", "x")
print(collapsed.shape)  # (2, 3, 3)
```

## 9. CLI 应用说明

本文档相关示例脚本：


| 脚本                                           | 说明          |
| -------------------------------------------- | ----------- |
| `nbhood/cli/ens_nbhood_iterate_with_mask.py` | 按分层掩码逐层邻域处理 |
| `nbhood/cli/ens_nbhood_land_and_sea.py`      | 陆海分区邻域处理并合并 |


### 9.1 `ens_nbhood_iterate_with_mask.py`

用途：

- 按分层掩码逐层执行邻域处理；
- 可选按分层权重折叠输出。

运行内置示例（示例使用数据为方形邻域折叠相关数据）：

```bash
python -m nbhood.cli.ens_nbhood_iterate_with_mask
```

无权重（方形邻域）代码示例：

```python
from nbhood.cli.ens_nbhood_iterate_with_mask import process

#数据存放路径
base = "./nbhood/test_data/official_test_use_nbhood/iterate_with_mask/normalized_meb6d"
process(
    input_data_path=f"{base}/input.nc", 
    mask_path=f"{base}//mask.nc",
    coord_for_masking="topographic_zone",
    radii=[20000.0],
    output_path=f"{base}/cli_test_unfolded_square_result.nc",
    neighbourhood_shape="square",
)
```

带权重折叠示例：

```python
result = process(
    input_data_path=f"{base}/thresholded_input.nc",
    mask_path=f"{base}/orographic_bands_mask.nc",
    coord_for_masking="topographic_zone",
    radii=[10000.0],
    weights_path=f"{base}/orographic_bands_weights.nc",
    output_path=f"{base}/cli_test_iterated_result.nc",
)
```

`**process()` 参数说明**


| 参数                    | 类型          | 必填  | 默认值      | 说明                          |
| --------------------- | ----------- | --- | -------- | --------------------------- |
| `input_data_path`     | str         | 是   | -        | 主输入 nc 路径                   |
| `mask_path`           | str         | 是   | -        | 分层掩码 nc 路径                  |
| `coord_for_masking`   | str         | 是   | -        | 掩码分层维名，如 `topographic_zone` |
| `radii`               | list[float] | 是   | -        | 邻域半径（米）                     |
| `weights_path`        | str         | 否   | `None`   | 分层折叠权重 nc 路径                |
| `output_path`         | str         | 否   | `None`   | 输出 nc 路径                    |
| `neighbourhood_shape` | str         | 否   | `square` | `square` 或 `circular`       |
| `lead_times`          | list[int]   | 否   | `None`   | 与 `radii` 对应时效（小时）          |
| `area_sum`            | bool        | 否   | `False`  | `True` 输出邻域和                |


说明：传 `weights_path` 时会沿掩码分层维折叠；不传时 xarray 路径下分层维会与输入 member 联合映射到新 member。

### 9.2 `ens_nbhood_land_and_sea.py`

用途：

- 分别在陆地和海洋子域执行邻域处理；
- 合并陆海结果；
- 支持普通陆海掩码和地形带输入。

运行内置示例：

```bash
python -m nbhood.cli.ens_nbhood_land_and_sea
```

简单陆海掩膜代码示例：

```python
from nbhood.cli.ens_nbhood_land_and_sea import process

#数据存放路径
base = "./nbhood/test_data/official_test_use_nbhood/land_and_sea/normalized_meb6d"
process(
    input_data_path=f"{base}/input.nc",
    mask_path=f"{base}/ukvx_landmask.nc",
    radii=[10000.0],
    output_path=f"{base}/cli_test_circular_result.nc",
    neighbourhood_shape="square",
)
```

地形带输入示例：

```python
from nbhood.cli.ens_nbhood_land_and_sea import process

#数据存放路径
base = "./nbhood/test_data/official_test_use_nbhood/land_and_sea/normalized_meb6d"
process(
    input_data_path=f"{base}/input.nc",
    mask_path=f"{base}/topographic_bands_land.nc",
    weights_path=f"{base}/weights_land.nc",
    radii=[10000.0],
    output_path=f"{base}/cli_test_topographic_bands_result.nc",
    neighbourhood_shape="square",
)
```

`**process()` 参数说明**


| 参数                    | 类型          | 必填  | 默认值      | 说明                    |
| --------------------- | ----------- | --- | -------- | --------------------- |
| `input_data_path`     | str         | 是   | -        | 主输入 nc 路径             |
| `mask_path`           | str         | 是   | -        | 陆海掩码或地形带 nc 路径        |
| `radii`               | list[float] | 是   | -        | 邻域半径（米）               |
| `weights_path`        | str         | 否   | `None`   | 地形带权重 nc 路径           |
| `output_path`         | str         | 否   | `None`   | 输出 nc 路径              |
| `neighbourhood_shape` | str         | 否   | `square` | `square` 或 `circular` |
| `lead_times`          | list[int]   | 否   | `None`   | 与 `radii` 对应时效（小时）    |
| `area_sum`            | bool        | 否   | `False`  | `True` 输出邻域和          |


说明：纯陆海二值掩码通常可不传 `weights_path`；地形带场景建议成对提供 mask 与 weights。

## 10. 注意事项

### 10.1 输入前提

迁移版遵循“算法只处理已预处理好的输入数据”边界假设：

- 不自动识别 NetCDF `_FillValue`；
- 若输入存在填充值，应由调用方先转为 `NaN` 或 `MaskedArray`。

### 10.2 `numpy` 输入要求

- 需显式提供 `grid_spacing`；
- 若使用可变半径，需显式提供 `input_lead_times`；
- 默认使用倒数第三维作为掩码分层维。

### 10.3 当前限制

- 当前未迁移原算法“相邻相同二维切片复用结果”的缓存优化；
- 权重数组当前要求可整理为 `(n_mask, y, x)`；
- 不处理 Iris `PostProcessingPlugin` 的元数据更新逻辑。

### 10.4 测试数据

- 当前修改算法及CLI测试使用数据均在test_data/*/normalized_meb6d目录下；
- 只有主输入数据做了六维格式处理。但因为数据限制，为减少不必要的误差并未对原数据的投影坐标转换为经纬度；
- 其他辅助输入数据例如掩码数据并未做维度格式化。

