# 分位数回归随机森林

## 算法实现原理

`quantile_regression_random_forest` 用历史集合预报和对应实况训练分位数回归森林，再对一份新的集合预报输出指定分位数。集合的条件分布来自 Meinshausen 的分位数回归森林（quantile regression forest）：每棵树仍按均方误差划分，预测时用叶节点里的实况样本估计分位数，而不是只给出均值。

参考文献：Meinshausen, N., 2006: Quantile Regression Forests. *Journal of Machine Learning Research*, 7, 983–999.（分位数回归森林）

特征由配置字典给出。键是预报列名，值是该列要计算的统计：

- `mean`、`std`、`min`、`max`：沿集合成员统计
- `percentile_50`：沿成员取百分位
- `members_below_273.15`、`members_above_0`：统计过阈值的成员数
- `static`：原列直接作为特征，例如海拔
- `day_of_year`、`hour_of_day` 及其正弦、余弦，由有效时间 `time + dtime` 计算

`log`、`log10`、`sqrt`、`cbrt` 会先作用于目标列，预测出的分位数再反变换。

格点是六维 `member, level, time, dtime, lat, lon`。订正时每个经纬度格点当作一个站点，默认站点键是 `lat, lon`。站点订正默认使用 `id`。不同层次不混在同一次统计里。

输出仍是格点或站点。原来的集合成员被替换为分位数，起报时间、时效、层次和位置保持为输入预报的值。

## 算法参数说明

| 参数 | 含义 |
| --- | --- |
| `command` | `train` 训练并写出模型；`apply` 或 `predict` 读取模型并订正 |
| `forecast` | 预报文件，多个路径用逗号分隔 |
| `truth` | 训练用实况 |
| `feature_config` | 特征配置 JSON |
| `target` | 目标列名，默认 `air_temperature` |
| `var_names` | 与预报文件一一对应的变量名 |
| `output` | 模型或订正结果路径 |
| `n_estimators` | 树的数量，默认 100 |
| `max_depth` | 树深 |
| `max_samples` / `max_features` | 每棵树的样本比例、特征比例 |
| `random_state` | 随机种子，默认 0 |
| `transformation` | 目标变换：`log`、`log10`、`sqrt`、`cbrt` |
| `pre_transform_addition` | 变换前加上的常数 |
| `site_keys` | 站点分组键 |
| `model` | `apply` 时的模型文件 |
| `quantiles` | 逗号分隔的分位数，默认 `0.1,0.5,0.9` |
| `config` | 外部 ini。省略则读 `resource/conf.ini` |

空的配置项不覆盖函数预设。模型文件是 pickle，订正结果按输入后缀写 nc 或 csv。

## 算法调用示例

在本包目录：

```text
python -m cli train forecast=testdata/forecast_sta.csv truth=testdata/truth_sta.csv feature_config=testdata/feature_config.json output=quantile_regression_random_forest_model.pkl
python -m cli apply model=quantile_regression_random_forest_model.pkl quantiles=0.1,0.5,0.9 output=quantile_regression_random_forest_calibrated.csv
python cli/quantile_regression_random_forest_cli.py
```

Python：

```python
from cli.quantile_regression_random_forest_cli import process

process(
    command="train",
    forecast="testdata/forecast_sta.csv",
    truth="testdata/truth_sta.csv",
    feature_config="testdata/feature_config.json",
)
process(
    command="apply",
    forecast="testdata/forecast_sta.csv",
    model="quantile_regression_random_forest_model.pkl",
    quantiles="0.1,0.5,0.9",
)
```

`process` 读 meteva 预报（和训练时的实况），调用 `QuantileRegressionRandomForestPlugin.process`，再写出模型或订正结果。
