# 网格站点融合算法说明

## 算法概述

网格站点融合算法用于将站点观测信息融合到规则格点产品中。算法包含无背景场的站点到格点反距离权重插值，以及有背景场时的站点-格点偏差扩散订正，可用于要素精细化、观测订正或主客观一致协调处理。

## 核心能力

- `InterpSgIdw`：基于球面距离 KDTree 的反距离权重站点到格点插值。
- `InterpSgIdwDelta`：先计算站点观测与背景场插值值之间的偏差，再用 IDW 和高斯距离权重将偏差扩散到格点并叠加背景场。
- `InterpSgDeltaGaussian`：将单站最近邻偏差按高斯半径扩散到周边格点并叠加背景场。
- `InterpSgTotal`：综合调度入口，无背景场时调用站点到格点插值，有背景场时执行偏差订正融合。
- `interp_station_to_grid_renew.py`：保留函数式实现、业务流程示例、时间处理和并行辅助函数。

## 目录结构

| 路径 | 内容 |
| --- | --- |
| `src/` | 核心插件类和函数式业务流程源码 |
| `cli/` | CLI 说明，原始目录未提供独立入口 |
| `resource/` | 资源说明，原始目录未提供资源文件 |
| `test/` | 测试说明，原始目录未提供单元测试 |
| `test_data/` | 测试数据说明，原始目录未提供样例数据 |
| `nbs/` | 原始示例脚本和 notebook |
| `docs/` | 算法说明文档 |
| `utils/` | 工具说明，原始目录未提供独立工具文件 |

## 主要入口

```python
from station_grid_fusion.src import InterpSgTotal

result = InterpSgTotal().process(sta, to_grid, grid_background=grid_background)
```

无背景场插值：

```python
from station_grid_fusion.src import InterpSgIdw

result = InterpSgIdw(effectR=1000, nearNum=8, decrease=2).process(sta, grid_info)
```

有背景场偏差订正：

```python
from station_grid_fusion.src import InterpSgIdwDelta

result = InterpSgIdwDelta(effectR=1000, nearNum=8, decrease=2).process(sta, grid_background)
```

## 注意事项

1. 原始代码依赖 `nimm.PostProcessingPlugin`、`meteva_base`、`meteva`、`numpy`、`scipy`、`pandas` 等环境。
2. 示例脚本保留 `/data/code/nimm/...`、`D:\Desktop\...`、`/home/...` 和共享盘路径，正式测试前需要替换为仓库相对样例路径。
3. `InterpSgTotal` 当前硬编码 `sys.path.append('/data/code/nimm/nimm/sta_grid_interp')`，并在有背景场分支调用未显式导入的 `interp_sg_idw_delta`，正式入库前需要修正导入路径。
4. 原始目录未提供独立测试数据和单元测试，只保留示例脚本与 notebook。
