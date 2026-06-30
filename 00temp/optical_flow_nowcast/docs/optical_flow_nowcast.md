# 临近光流法外推预报

## 算法概述

本算法用于基于光流和半拉格朗日平流的临近外推预报。原始目录包含 Lucas-Kanade 光流平流估计、外推预报，以及 LINDA、S-PROG、STEPS 等相关临近预报方法。

本次归档重点对应用户提供的“临近光流法外推预报”：

- `LK`：基于 Lucas-Kanade 特征追踪计算二维平流速度场。
- `Extrapolation`：基于输入降水场和平流速度场进行半拉格朗日外推。
- `linda`、`sprog`、`steps`：同一原始目录内的相关临近预报算法，作为上下游或扩展能力一并保留。

## 目录说明

| 目录 | 内容 |
| --- | --- |
| `src/` | 光流、外推和相关临近预报核心源码 |
| `nbs/` | 原始 notebook 示例 |
| `test_data/` | 原始输出样例数据 |
| `cli/` | 归档占位入口，原始目录未提供独立 CLI |
| `docs/` | 归档说明文档 |
| `resource/` | 资源说明 |
| `test/` | 最小测试脚本 |
| `utils/` | 工具说明目录 |

## 公开插件

```python
from optical_flow_nowcast.src import Extrapolation, LK
```

`LK.process(...)` 输出平流速度场和时间间隔，`Extrapolation.process(...)` 使用平流速度场对最近一次降水场进行多时效外推。

## 整理说明

原始代码依赖 NIMM 业务环境中的 `nimm.PostProcessingPlugin` 和 `nimm.nowcast.*` 包路径。归档副本已提供轻量 `PostProcessingPlugin` 兼容基类，并将内部算法引用调整为 `optical_flow_nowcast.src.*`，核心计算逻辑未做业务性改写。

