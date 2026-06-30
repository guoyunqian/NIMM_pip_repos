# 雷达降水定量反演QPE

## 基本信息

- 算法名称：`radar_qpe_retrieval`
- 原始工程位置：`pyart/retrieve`
- 算法类型：`01obs_adustment`
- 贡献人：郭云谦、王亭波
- 原始路径：`D:\temp\202301_zhinengwangge\20230206_unitycode\NIMM_pip_repos\TEMP\260625\算法_王\pyart\retrieve`

## 算法功能

该算法从 Py-ART 的定量降水估算逻辑迁移而来，面向雷达网格数据执行 QPE 降水率反演。算法以 `meteva_base.grid_data` 风格的 `xarray.DataArray` 为输入输出，支持反射率、KDP、比衰减和水凝物分类等多种雷达变量，输出降水率网格，通常单位为 `mm/h`。

## 主要方法

- `est_rain_rate_z`：基于反射率和幂律 Z-R 关系估算降水率。
- `est_rain_rate_zpoly`：基于反射率多项式经验关系估算降水率。
- `est_rain_rate_kdp`：基于 KDP 估算降水率。
- `est_rain_rate_a`：基于比衰减估算降水率。
- `est_rain_rate_zkdp`：融合反射率和 KDP 估算降水率。
- `est_rain_rate_za`：融合反射率和比衰减估算降水率。
- `est_rain_rate_hydro`：结合水凝物分类、反射率和比衰减估算降水率。
- `ZtoR`：使用经典 `Z = aR^b` 关系反算降水率。

## 目录说明

- `src/`：核心算法源码，包含 QPE 和回波分类相关算法。
- `cli/`：QPE 与回波分类命令行函数入口。
- `test_data/`：QPE 和回波分类测试数据，包含雷达网格 NetCDF、CINRAD/雷达体扫样例及 CLI 输出样例。
- `test/`：QPE、插件、CLI 和回波分类测试脚本。
- `nbs/`：QPE 和回波分类 notebook 示例。
- `docs/`：原始 QPE/回波分类说明和本整理说明。
- `utils/`：雷达资料读取、投影、绘图和网格处理辅助函数。
- `resource/`：原始目录为空，按仓库规范保留。

## 插件入口

统一插件类：

```python
from pyart.retrieve.src.qpe import QPEPlugin

rain_rate = QPEPlugin(method="z").process(refl=refl_grid)
```

也提供与每个算法对应的独立插件类，如 `EstimateRainRateZ`、`EstimateRainRateKdp`、`EstimateRainRateHydro` 和 `EstimateZtoR`。

## CLI 示例

```python
from pyart.retrieve.cli.qpe import qpeplugin

qpeplugin(
    "z",
    refl_path="test_data/qpe/input/ACHN_CREF000_20240612_070000.nc",
    output_path="test_data/qpe/cli_output/qpeplugin_z.nc",
)
```

## 依赖与运行条件

完整运行依赖 `numpy`、`xarray`、`meteva_base` 以及原始 `pyart` 包上下文中的 `plugin_base`、`retrieve.utils` 等模块。部分测试还依赖 CINRAD/雷达体扫样例数据和 NetCDF 文件。

## 当前限制

- 原始目录同时包含 `qpe` 和 `echo_class` 两类功能；本次按“雷达降水定量反演QPE”整理，回波分类代码作为相关依赖与测试上下文一并保留。
- 源码使用 `from ...plugin_base import PostProcessingPlugin` 等相对导入，正式入库或独立运行时需保留/补齐上层 `pyart` 包结构。
- `test_data/` 体量较大，正式入库时可筛选最小样例数据。
- `resource/` 原始为空，当前仅按规范保留目录。
