# 雷达风场退模糊算法说明

## 算法概述

雷达风场退模糊算法用于多普勒雷达径向速度的 Nyquist 速度折叠订正。当前实现迁移自 Py-ART 的区域连通关系退模糊流程，面向 `meteva_base.grid_data` 风格的 `xarray.DataArray` 输入输出，并提供插件封装、门限过滤器和可选地理后处理能力。

## 核心能力

- 按 Nyquist 区间对径向速度场进行初始分段。
- 在单个 sweep 的二维平面上识别连通区域。
- 根据相邻区域边界速度差逐步合并区域并展开速度。
- 支持参考速度场锚定，减少整体或分区折叠偏移。
- 支持基于反射率、NCP、RhoHV 或显式掩码的门点过滤。
- 支持为门点附加经纬度，并可重映射到规则经纬网格。

## 主要入口

| 入口 | 类型 | 说明 |
| --- | --- | --- |
| `src/region_dealias.py::dealias_region_based` | 函数 | 基于区域连通关系的核心退模糊算法 |
| `src/region_dealias.py::RegionDealiasPlugin` | 插件类 | 封装核心算法和地理后处理，提供 `process()` 方法 |
| `src/grid_gate_filter.py::GridGateFilter` | 过滤器类 | 构造退模糊所需的门点过滤掩码 |
| `cli/region_dealias.py::process` | CLI 函数 | 从 NetCDF 和 `.npy` 文件读取输入并输出 NetCDF |

## 目录结构

| 路径 | 内容 |
| --- | --- |
| `src/` | 核心退模糊算法、门限过滤器和辅助函数 |
| `cli/` | 命令行和文件式调用入口 |
| `test_data/` | NetCDF、MDV、CDF 和 `.npy` 测试样例 |
| `test/` | 单元测试 |
| `nbs/` | notebook 示例 |
| `docs/` | 说明文档 |
| `utils/` | 地理坐标、网格转换和通用工具 |
| `resource/` | 原始目录保留的资源目录，当前无文件 |

## 使用示例

直接调用：

```python
from pyart.correct import dealias_region_based

corrected = dealias_region_based(
    velocity=velocity,
    centered=False,
)
```

插件调用：

```python
from pyart.correct import RegionDealiasPlugin

plugin = RegionDealiasPlugin(centered=False)
corrected = plugin.process(velocity=velocity, ref_velocity=ref_velocity)
```

文件式调用：

```python
from pyart.correct.cli.region_dealias import process

process(
    "test_data/region_dealias/input/velocity_sweep0.nc",
    ref_velocity_path="test_data/region_dealias/input/ref_velocity_sweep0.nc",
    gatefilter_path="test_data/region_dealias/input/grid_gatefilter_mask_sweep0.npy",
    output_path="test_data/region_dealias/cli_output/region_dealias_cli.nc",
)
```

## 注意事项

1. 算法依赖雷达 sweep 的“方位角 × 径距”拓扑关系。若输入是真实规则经纬度网格，退模糊物理意义需要额外确认。
2. 当前代码保留 `pyart.correct` 包路径和相对导入，正式补充到算法仓库时需统一导入路径。
3. 核心代码依赖 `numpy`、`scipy`、`xarray`、`meteva_base` 等环境。
4. `test_data/region_dealias/cli_output/` 中保留原始 CLI 输出样例，可作为回归参考；运行 CLI 时注意避免覆盖参考输出。
