# Echo Class 算法使用说明

本文档说明 `pyart.retrieve.src.echo_class` 的已迁移算法、插件类以及 CLI 应用使用方式。当前实现以 `meteva_base` 六维网格数据（`grid_data`）作为统一输入输出格式。

## 1. 模块定位

`echo_class` 模块用于雷达回波分类与结构识别，包含层状/对流分类、特征识别和半监督水凝物分类等算法。迁移过程中保留原 Py-ART 主要计算逻辑，重点适配 `meteva_base.grid_data` 输入输出。

当前公开入口包括：


| 入口     | 说明                                       |
| ------ | ---------------------------------------- |
| 算法函数   | 直接调用单个算法函数，适合调试和精细集成。                    |
| 插件类    | 每个算法对应一个插件类，便于在 NIMM 插件体系中统一调用。          |
| CLI 应用 | 通过 `pyart/retrieve/cli/echo_class.py` 中的 Python 函数读取网格文件并输出 nc。 |


## 2. 输入输出约定

输入数据应为 `xarray.DataArray`，并符合 `meteva_base.grid_data` 六维结构：

```text
member, level, time, dtime, lat, lon
```

输出保持 `xarray.DataArray` 或 `dict[str, xarray.DataArray]`（由具体算法决定）。

需要注意：


| 项目   | 说明                                               |
| ---- | ------------------------------------------------ |
| 单场约束 | 当前实现默认 `member/time/dtime` 为单值场，算法会进行上下文检查。      |
| 缺测值  | 建议在调用前清洗 `_FillValue`、`missing_value` 和异常极值。     |
| 空间坐标 | 若不传 `dx/dy`，部分算法会根据 `lat/lon` 自动估算；坐标应尽量等距。      |
| 时间类型 | `time` 建议为 `datetime64`，避免 `meteva_base` 网格反推失败。 |


## 3. 算法函数清单


| 函数                          | 主要输入                           | 功能              |
| --------------------------- | ------------------------------ | --------------- |
| `steiner_conv_strat`        | `refl`                         | Steiner 层状/对流分类 |
| `feature_detection`         | `field_data`                   | 自适应特征识别，支持多输出   |
| `conv_strat_yuter`          | `refl`                         | Yuter 层状/对流分类入口 |
| `hydroclass_semisupervised` | `refl,zdr,rhv,kdp,(temp/iso0)` | 半监督水凝物分类        |
| `conv_strat_raut`           | `refl`                         | Raut 小波层状/对流分类  |


## 4. 计算公式

下文约定：$Z_{\mathrm{dBZ}}$ 表示反射率（dBZ）；$Z = 10^{Z_{\mathrm{dBZ}}/10}$ 为线性反射率因子；$R_{\mathrm{bkg}}$ 表示背景场；$r$ 为水平距离（m 或 km，随上下文注明）。公式使用 `$...$` / `$$...$$` 书写，与源码实现一致；部分算法含分段查表或形态学后处理，表中只写核心判据。

### 4.1 `steiner_conv_strat` — Steiner 层状/对流分类

在工作高度 `work_level` 对应的 `level` 层上取二维反射率场 $Z_{\mathrm{dBZ}}(x,y)$，对每个格点 $(i,j)$ 在背景半径 $R_{\mathrm{bkg}}$（默认 11000 m）内计算背景平均反射率（先在线性 $Z$ 空间平均，再转回 dBZ）：

$$
Z_{\mathrm{bkg}} = 10 \log_{10} \left( \frac{1}{n} \sum_{r \le R_{\mathrm{bkg}}} 10^{Z_{\mathrm{dBZ}}/10} \right)
$$

根据 $Z_{\mathrm{bkg}}$ 查表得到对流影响半径 $R_{\mathrm{conv}}$（`area_relation`：`small`/`medium`/`large`/`sgp`）和峰值阈值 $\Delta Z_{\mathrm{peak}}$（`peak_relation`：`default`/`sgp`）。`default` 峰值关系为：

$$
\Delta Z_{\mathrm{peak}} =
\begin{cases}
10, & Z_{\mathrm{bkg}} < 0 \\
10 - Z_{\mathrm{bkg}}^{2}/180, & 0 \le Z_{\mathrm{bkg}} < 42.43 \\
0, & Z_{\mathrm{bkg}} \ge 42.43
\end{cases}
$$

对流判据（满足其一即标为对流，并向 $R_{\mathrm{conv}}$ 范围内扩张）：

$$
Z_{\mathrm{dBZ}} \ge Z_{\mathrm{intense}} \quad (\texttt{use\_intense}=\texttt{True},\ \text{默认 } Z_{\mathrm{intense}}=42\ \mathrm{dBZ})
$$

$$
Z_{\mathrm{dBZ}} - Z_{\mathrm{bkg}} \ge \Delta Z_{\mathrm{peak}}
$$

否则该格点为层状。输出编码：0 = 未定义，1 = 层状，2 = 对流。

> 实现说明：`steiner_class_buff` 内部调用 `_steiner_conv_strat` 时固定 $R_{\mathrm{bkg}}=11000$ m、`use_intense=True`；`steiner_conv_strat` 形参中的 `bkg_rad`、`use_intense` 当前不传入底层计算。

### 4.2 `feature_detection` / `conv_strat_yuter` — 自适应特征识别

二者核心计算相同（`conv_strat_yuter` 为 Yuter 风格封装，调用同一 `_feature_detection`）。在目标高度对应单层上，先以半径 $R_{\mathrm{bkg}}$（`bkg_rad_km`，默认 11 km）的圆形窗口求背景场。`dB_averaging=True`（默认）时：

$$
Z_{\mathrm{bkg}} = 10 \log_{10} \left( \mathrm{mean}_{\mathrm{footprint}} \left( 10^{Z_{\mathrm{dBZ}}/10} \right) \right)
$$

**核心识别**（`use_cosine=True` 为默认，Yuter & Houze 1997 余弦判据）：

$$
\Delta Z(x,y) = a \cos\!\left( \frac{\pi \, Z_{\mathrm{bkg}}}{2 b} \right), \quad \Delta Z \leftarrow \max(\Delta Z,\, 0)
$$

其中 $a$ = `max_diff`（默认 5），$b$ = `zero_diff_cos_val`（默认 55）。$Z_{\mathrm{bkg}}<0$ 时令 $\Delta Z = a$。核心格点：

$$
Z_{\mathrm{dBZ}} \ge Z_{\mathrm{core}} \quad \lor \quad Z_{\mathrm{dBZ}} - Z_{\mathrm{bkg}} \ge \Delta Z
$$

$Z_{\mathrm{core}}$ = `always_core_thres`（默认 42 dBZ）。

`use_cosine=False` 时使用标量差值判据（`use_addition=True` 时 $\Delta Z = a$；`False` 时 $\Delta Z = \max(a \cdot Z_{\mathrm{bkg}} - Z_{\mathrm{bkg}},\, 0)$）。

**半径扩张**：按 $Z_{\mathrm{bkg}}$ 分段赋予扩张半径 $R_{\mathrm{feat}}$（km，最大 `max_rad_km`，默认 5 km），对核心做二值膨胀，将邻域标为特征回波。

**最终分类**（默认标签值）：先赋背景 `bkgd_val`=1；核心及扩张区为 `feat_val`=2；$Z_{\mathrm{dBZ}} < \texttt{weak\_echo\_thres}$（默认 5）为 `weakecho`=3；$Z_{\mathrm{dBZ}} < \texttt{min\_val\_used}$（默认 5）为 `nosfcecho`=0。

`estimate_flag=True` 时，另对 $Z_{\mathrm{dBZ}} \pm \texttt{estimate\_offset}$（默认 5 dBZ）各运行一次，输出 `feature_under` / `feature_over`。

### 4.3 `hydroclass_semisupervised` — 半监督水凝物分类

对 `var_names` 中每个变量先标准化到 $[-1,1]$，再与各类质心 $\mathbf{c}_k$ 计算加权欧氏距离，取最近质心为类别。

**相对高度 `relH`**（由温度场构造，`temp_ref=temperature`）：

$$
\mathrm{relH} = T \cdot \frac{1000}{\texttt{lapse\_rate}}, \quad \hat{x} = \frac{2}{1 + e^{-0.005 \cdot \mathrm{relH}}} - 1
$$

默认 `lapse_rate` = $-6.5$ °C/km。

**Zh、ZDR**（线性缩放到 $[-1,1]$，超出界截断）：

$$
\hat{x} = 2 \cdot \frac{x - x_{\min}}{x_{\max} - x_{\min}} - 1
$$

默认界：Zh $x_{\max}=60,\ x_{\min}=-10$；ZDR $5,\ -1.5$。

**KDP**（先截断再对数变换，再线性缩放）：

$$
\mathrm{KDP}' = \max(\mathrm{KDP},\, -0.5), \quad x' = 10 \log_{10}(\mathrm{KDP}' + 0.6)
$$

**RhoHV**：

$$
\rho' = \min(\rho_{\mathrm{HV}},\, 1), \quad x' = 10 \log_{10}(1.0000000000001 - \rho')
$$

**加权距离与分类**（$w_j$ = `weights`，默认 $(1, 1, 1, 0.75, 0.5)$）：

$$
d_k = \sqrt{ \sum_{j} w_j \left( \hat{x}_j - c_{k,j} \right)^2 }
$$

$$
H = \arg\min_k d_k + 1 \quad (\text{缺测格点 } H=0)
$$

质心矩阵 `mass_centers` 未给定时，按输入 `frequency`（Hz）或 `radar_freq` 选择 S/C/X 频段默认质心；无法识别时用 C 波段。

**可选熵场**（`compute_entropy=True`）：先计算各类变换系数 $t_k$（由质心间次小距离与 `value` 默认 50 确定，$t_k = \ln(\texttt{value})/d_{k,2}$），再得各类占比

$$
p_k = \frac{\exp(-t_k \, d_k)}{\sum_j \exp(-t_j \, d_j)}, \quad
S = -\sum_k \frac{p_k \ln p_k}{\ln N_{\mathrm{class}}}
$$

`output_distances=True` 时输出 $100 \cdot p_k$（%）作为各类比例场。类别编号 1–9 对应 `hydro_names`（AG、CR、LR、RP、RN、VI、WS、MH、IH/HDG）。

### 4.4 `conv_strat_raut` — Raut 小波层状/对流分类

在 `cappi_level` 对应层上，先将 dBZ 经 Z-R 关系转为雨强（默认 Marshall 形式 $Z = a R^b$，$a$=`zr_a`=200，$b$=`zr_b`=1.6）：

$$
R = \left( \frac{10^{Z_{\mathrm{dBZ}}/10}}{a} \right)^{1/b}
$$

对 $R$ 做二维平稳小波变换（ATWT），累加尺度 $1 \ldots s_{\mathrm{break}}$ 的小波系数得 $W$：

$$
W = \sum_{s=1}^{s_{\mathrm{break}}} \mathrm{WT}_s(R)
$$

尺度分界（`conv_scale_km` 默认 25 km，分辨率 $\Delta x$ 单位 m）：

$$
s_{\mathrm{break}} = \mathrm{round}\!\left( \frac{\ln(L_{\mathrm{conv}} / (\Delta x/1000))}{\ln 2} + 1 \right)
$$

分类判据（按源码 `label_classes` 顺序求值；默认阈值；`override_checks=False` 时部分阈值会被夹紧到推荐范围）：

| 条件 | 类别 |
| ---- | ---- |
| $W \ge W_{\mathrm{core}}$ 且 $Z_{\mathrm{dBZ}} \ge Z_{\mathrm{conv\_min}}$ | 3 对流核心 |
| $W_{\mathrm{conv}} \le W < W_{\mathrm{core}}$ 且 $Z_{\mathrm{dBZ}} \ge Z_{\mathrm{conv\_min}}$ | 2 过渡混合 |
| 以上均不满足且 $Z_{\mathrm{dBZ}} \ge Z_{\mathrm{min}}$ | 1 层状 |
| 其他 | 0 未分类（缺测掩膜） |

默认：$W_{\mathrm{core}}$=`core_wt_threshold`=5，$W_{\mathrm{conv}}$=`conv_wt_threshold`=1.5，$Z_{\mathrm{min}}$=`min_reflectivity`=5，$Z_{\mathrm{conv\_min}}$=`conv_min_refl`=25 dBZ。`conv_core_threshold`（默认 42 dBZ）在实现中会被后续判据覆盖，一般不单独生效。

## 5. 插件类说明

当前插件类（位于 `pyart.retrieve.src.echo_class`）：


| 插件类                              | 对应算法函数                      | 说明               |
| -------------------------------- | --------------------------- | ---------------- |
| `SteinerConvStratPlugin`         | `steiner_conv_strat`        | Steiner 分类插件。    |
| `FeatureDetectionPlugin`         | `feature_detection`         | 特征识别插件，返回多字段字典。  |
| `HydroclassSemisupervisedPlugin` | `hydroclass_semisupervised` | 水凝物分类插件，返回多字段字典。 |
| `ConvStratRautPlugin`            | `conv_strat_raut`           | 小波层状/对流分类插件。     |


统一说明：

- 插件类仅做参数转发，不新增算法计算逻辑。
- 插件类参数与对应算法函数参数保持一致（或一一映射），可按算法函数参数语义理解插件参数。

### 5.1 插件类参数对照

#### a) `SteinerConvStratPlugin`


| 插件参数            | 对应算法函数参数                            | 说明               |
| --------------- | ----------------------------------- | ---------------- |
| `dx`, `dy`      | `steiner_conv_strat(dx, dy)`        | 网格分辨率（米），可空自动估算。 |
| `intense`       | `steiner_conv_strat(intense)`       | 强对流阈值（dBZ）。      |
| `work_level`    | `steiner_conv_strat(work_level)`    | 计算高度（米）。         |
| `peak_relation` | `steiner_conv_strat(peak_relation)` | 峰值关系方案。          |
| `area_relation` | `steiner_conv_strat(area_relation)` | 面积关系方案。          |
| `bkg_rad`       | `steiner_conv_strat(bkg_rad)`       | 背景半径（米）。         |
| `use_intense`   | `steiner_conv_strat(use_intense)`   | 是否启用强对流快速判别。     |


#### b) `FeatureDetectionPlugin`


| 插件参数                                                                                       | 对应算法函数参数                             | 说明           |
| ------------------------------------------------------------------------------------------ | ------------------------------------ | ------------ |
| `dx`, `dy`, `level_m`                                                                      | `feature_detection(dx, dy, level_m)` | 空间分辨率与目标高度。  |
| `always_core_thres`, `bkg_rad_km`                                                          | `feature_detection(...)`             | 强核心阈值与背景半径。  |
| `use_cosine`, `max_diff`, `zero_diff_cos_val`, `scalar_diff`, `use_addition`, `calc_thres` | `feature_detection(...)`             | 阈值修正相关参数。    |
| `weak_echo_thres`, `min_val_used`, `dB_averaging`                                          | `feature_detection(...)`             | 弱回波与平均策略参数。  |
| `remove_small_objects`, `min_km2_size`, `binary_close`                                     | `feature_detection(...)`             | 小目标过滤与形态学参数。 |
| `val_for_max_rad`, `max_rad_km`                                                            | `feature_detection(...)`             | 半径控制参数。      |
| `core_val`, `nosfcecho`, `weakecho`, `bkgd_val`, `feat_val`                                | `feature_detection(...)`             | 输出标签值参数。     |
| `estimate_flag`, `estimate_offset`                                                         | `feature_detection(...)`             | 估算输出控制参数。    |


#### c) `HydroclassSemisupervisedPlugin`


| 插件参数                              | 对应算法函数参数                                      | 说明                        |
| --------------------------------- | --------------------------------------------- | ------------------------- |
| `hydro_names`                     | `hydroclass_semisupervised(hydro_names)`      | 输出类别名序列。                  |
| `var_names`                       | `hydroclass_semisupervised(var_names)`        | 参与分类变量序列。                 |
| `mass_centers`                    | `hydroclass_semisupervised(mass_centers)`     | 分类质心矩阵。                   |
| `weights`                         | `hydroclass_semisupervised(weights)`          | 变量权重，长度需与 `var_names` 一致。 |
| `value`, `lapse_rate`, `temp_ref` | `hydroclass_semisupervised(...)`              | 温度构造与引用参数。                |
| `radar_freq`                      | `hydroclass_semisupervised(radar_freq)`       | 雷达频率（Hz）。                 |
| `compute_entropy`                 | `hydroclass_semisupervised(compute_entropy)`  | 是否输出熵场。                   |
| `output_distances`                | `hydroclass_semisupervised(output_distances)` | 是否输出距离场。                  |
| `vectorize`                       | `hydroclass_semisupervised(vectorize)`        | 是否使用矢量化路径。                |


#### d) `ConvStratRautPlugin`


| 插件参数                                                       | 对应算法函数参数                             | 说明                |
| ---------------------------------------------------------- | ------------------------------------ | ----------------- |
| `cappi_level`                                              | `conv_strat_raut(cappi_level)`       | 计算层号/层位。          |
| `zr_a`, `zr_b`                                             | `conv_strat_raut(zr_a, zr_b)`        | Z-R 关系系数。         |
| `core_wt_threshold`                                        | `conv_strat_raut(core_wt_threshold)` | 小波核心阈值。           |
| `conv_wt_threshold`                                        | `conv_strat_raut(conv_wt_threshold)` | 对流阈值。             |
| `conv_scale_km`                                            | `conv_strat_raut(conv_scale_km)`     | 对流尺度参数（km）。       |
| `min_reflectivity`, `conv_min_refl`, `conv_core_threshold` | `conv_strat_raut(...)`               | 反射率与核心判据阈值。       |
| `override_checks`                                          | `conv_strat_raut(override_checks)`   | 是否跳过部分检查。         |
| `dx`, `dy`                                                 | `conv_strat_raut(dx, dy)`            | 网格分辨率（米），若空则自动估算。 |


### 5.2 插件调用示例

```python
import meteva_base as meb
from pyart.retrieve.src.echo_class import (
    SteinerConvStratPlugin,
    FeatureDetectionPlugin,
    HydroclassSemisupervisedPlugin,
    ConvStratRautPlugin,
)

refl = meb.read_griddata_from_nc(
    "pyart/retrieve/test_data/echo_class/input/ACHN_CREF000_20240612_070000_small.nc"
)

# Steiner
steiner = SteinerConvStratPlugin(work_level=3000.0)
steiner_cls = steiner(refl)

# Feature detection
feat = FeatureDetectionPlugin(level_m=3000.0)
feat_dict = feat(refl)
feat_main = feat_dict["feature_detection"]

# Hydroclass (4-variable mode, no temp)
refl_sgp = meb.read_griddata_from_nc("pyart/retrieve/test_data/echo_class/input/sgp_refl.nc")
zdr_sgp = meb.read_griddata_from_nc("pyart/retrieve/test_data/echo_class/input/sgp_zdr.nc")
kdp_sgp = meb.read_griddata_from_nc("pyart/retrieve/test_data/echo_class/input/sgp_kdp.nc")
rhv_sgp = meb.read_griddata_from_nc("pyart/retrieve/test_data/echo_class/input/sgp_rhv.nc")

hydro_plugin = HydroclassSemisupervisedPlugin(
    var_names=("Zh", "ZDR", "KDP", "RhoHV"),
    weights=(1.0, 1.0, 1.0, 0.75),
    mass_centers=None,
    vectorize=True,
)
hydro_dict = hydro_plugin(refl=refl_sgp, zdr=zdr_sgp, kdp=kdp_sgp, rhv=rhv_sgp)
hydro = hydro_dict["hydro"]

# Raut
raut = ConvStratRautPlugin(cappi_level=0)
raut_cls = raut(refl)
```

## 6. 直接调用算法函数

```python
from pyart.retrieve.src.echo_class import (
    steiner_conv_strat,
    feature_detection,
    hydroclass_semisupervised,
    conv_strat_raut,
)

steiner_cls = steiner_conv_strat(refl, work_level=3000.0)
feat_dict = feature_detection(refl, level_m=3000.0)
hydro_dict = hydroclass_semisupervised(refl, zdr, rhv, kdp, temp=temp)
raut_cls = conv_strat_raut(refl, cappi_level=0)
```

## 7. CLI 应用

CLI 入口位于 `pyart/retrieve/cli/echo_class.py`，提供以下 Python 函数：

- `steiner_conv_strat`
- `feature_detection`
- `hydroclass_semisupervised`
- `conv_strat_raut`

也可直接运行示例脚本：

```powershell
python pyart/retrieve/cli/echo_class.py
```

### 7.1 steiner_conv_strat 示例

```python
from pyart.retrieve.cli.echo_class import steiner_conv_strat

steiner_conv_strat(
    "pyart/retrieve/test_data/echo_class/input/ACHN_CREF000_20240612_070000_small.nc",
    work_level=0,
    intense=42,
    peak_relation="default",
    area_relation="medium",
    bkg_rad=11000,
    use_intense=True,
    output_path="pyart/retrieve/test_data/echo_class/cli_output/achn_steiner_cli.nc",
)
```

### 7.2 feature_detection 示例

```python
from pyart.retrieve.cli.echo_class import feature_detection

feature_detection(
    "pyart/retrieve/test_data/echo_class/input/ACHN_CREF000_20240612_070000_small.nc",
    remove_small_objects=True,
    binary_close=True,
    result_key="feature_detection",
    output_path="pyart/retrieve/test_data/echo_class/cli_output/achn_feature_cli.nc",
)
```

### 7.3 conv_strat_raut 示例

```python
from pyart.retrieve.cli.echo_class import conv_strat_raut

conv_strat_raut(
    "pyart/retrieve/test_data/echo_class/input/ACHN_CREF000_20240612_070000_small.nc",
    cappi_level=0,
    output_path="pyart/retrieve/test_data/echo_class/cli_output/achn_raut_cli.nc",
)
```

### 7.4 hydroclass_semisupervised（5 变量）示例

```python
from pyart.retrieve.cli.echo_class import hydroclass_semisupervised

hydroclass_semisupervised(
    refl_path="pyart/retrieve/test_data/echo_class/input/sgp_refl.nc",
    zdr_path="pyart/retrieve/test_data/echo_class/input/sgp_zdr.nc",
    kdp_path="pyart/retrieve/test_data/echo_class/input/sgp_kdp.nc",
    rhv_path="pyart/retrieve/test_data/echo_class/input/sgp_rhv.nc",
    temp_path="pyart/retrieve/test_data/echo_class/input/hydro_temperature.nc",
    var_names=("Zh", "ZDR", "KDP", "RhoHV", "relH"),
    weights=(1.0, 1.0, 1.0, 0.75, 0.5),
    output_path="pyart/retrieve/test_data/echo_class/cli_output/sgp_hydro_cli.nc",
)
```

### 7.5 CLI 参数说明（按函数）


| 函数                         | 必需输入参数                    | 关键可选参数                                                                                                   |
| --------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------- |
| `steiner_conv_strat`        | `refl_path`                  | `dx` `dy` `intense` `work_level` `peak_relation` `area_relation` `bkg_rad` `use_intense` |
| `feature_detection`         | `field_data_path`            | `result_key` `dx` `dy` `level_m` `remove_small_objects` `binary_close` 等                     |
| `conv_strat_raut`           | `refl_path`                  | `cappi_level` `dx` `dy` 及各阈值参数                                                                     |
| `hydroclass_semisupervised` | 多变量输入（至少与 `var_names` 对齐） | `var_names` `weights` `mass_centers_path` `radar_freq` `vectorize` `result_key`                   |


说明：

- 布尔参数直接以 Python 关键字传入，例如 `use_intense=True`、`binary_close=True`。
- `feature_detection`、`hydroclass_semisupervised` 默认输出多字段；如需单字段输出请使用 `result_key`。

### 7.6 CLI 参数详表

#### a) `steiner_conv_strat`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `refl_path` | 文件路径 | 是 | - | 反射率网格数据文件（单要素）。 |
| `dx` | `float` | 否 | `None` | 网格 x 向分辨率（米），为空时自动估算。 |
| `dy` | `float` | 否 | `None` | 网格 y 向分辨率（米），为空时自动估算。 |
| `intense` | `float` | 否 | `42.0` | 强对流阈值（dBZ）。 |
| `work_level` | `float` | 否 | `3000.0` | 分类工作高度（米）。 |
| `peak_relation` | `str` | 否 | `default` | 峰值关系方案。 |
| `area_relation` | `str` | 否 | `medium` | 面积关系方案。 |
| `bkg_rad` | `float` | 否 | `11000.0` | 背景半径（米）。 |
| `use_intense` | `bool` | 否 | `True` | 是否启用强对流快速判别。 |
| `output_path` | 文件路径 | 否 | - | 输出 nc 路径。 |

#### b) `feature_detection`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `field_data_path` | 文件路径 | 是 | - | 主输入网格数据（通常反射率）。 |
| `overest_field_path` | 文件路径 | 否 | `None` | 过估辅助场。 |
| `underest_field_path` | 文件路径 | 否 | `None` | 低估辅助场。 |
| `result_key` | `str` | 否 | `None` | 指定后仅输出单字段（如 `feature_detection`）。 |
| `remove_small_objects` | `bool` | 否 | `True` | 是否移除小目标。 |
| `binary_close` | `bool` | 否 | `False` | 是否执行闭运算。 |
| `output_path` | 文件路径 | 否 | - | 输出 nc 路径。 |

#### c) `hydroclass_semisupervised`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `refl_path` / `zdr_path` / `rhv_path` / `kdp_path` | 文件路径 | 按 `var_names` | `None` | 参与分类的主变量输入。 |
| `temp_path` / `iso0_path` | 文件路径 | 否 | `None` | 温度或 0℃层输入。 |
| `var_names` | 序列或逗号分隔字符串 | 否 | `Zh,ZDR,KDP,RhoHV,relH` | 分类变量序列。 |
| `mass_centers_path` | 文件路径 | 否 | `None` | 质心文件（`.npy/.txt/.csv`）。 |
| `weights` | 序列或逗号分隔浮点 | 否 | `1,1,1,0.75,0.5` | 变量权重。 |
| `result_key` | `str` | 否 | `None` | 指定后仅输出单字段。 |
| `output_path` | 文件路径 | 否 | - | 输出 nc 路径。 |

#### d) `conv_strat_raut`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `refl_path` | 文件路径 | 是 | - | 反射率网格数据文件。 |
| `cappi_level` | `float` | 否 | `0` | 参与计算层号/层位。 |
| `zr_a` / `zr_b` | `float` | 否 | `200` / `1.6` | Z-R 关系系数。 |
| `output_path` | 文件路径 | 否 | - | 输出 nc 路径。 |

## 8. 数据预处理建议

建议将原始数据预处理为标准 `meteva_base.grid_data` 后再调用算法/CLI：


| 内容    | 建议                                             |
| ----- | ---------------------------------------------- |
| 维度补齐  | 统一为 `member, level, time, dtime, lat, lon`。    |
| 坐标处理  | 保持坐标单调、尽量等间隔，避免明显浮点尾差。                         |
| 缺测清洗  | 将 `_FillValue`、`missing_value` 和异常极值清洗为 `NaN`。 |
| 单要素文件 | CLI 推荐单文件单物理量，避免歧义。                            |


## 9. 验证与示例

当前验证链路：


| 内容     | 说明                            |
| ------ | ----------------------------- |
| 算法对比   | 官方 Py-ART vs 迁移算法（函数/插件）逐格对比。 |
| CLI 对比 | CLI 输出 vs 官方/插件结果对比（含差值图）。    |
| 数据集    | ACHN（反射率子区域）与 SGP（多变量）样例。     |


建议记录指标：

- 一致率（分类值完全相同的格点比例）
- 差异格点数
- 有效格点数
- 差值图（CLI-Official 或 Plugin-Official）

