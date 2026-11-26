# 时间滞后集合

## 算法实现原理

`time_lagging` 改写自 IMPROVER（Integrated Model post-PROcessing and VERification，综合模式后处理与检验）的时间滞后集合。它把不同起报时次、但有效时间一致的集合成员拼成一个更大的集合。集合变大之后可以再估计概率；这一步本身不做阈值概率转换。

有效时间是起报时间 `time` 加上时效 `dtime`。处理顺序：

1. 检查每份输入的有效时间集合是否相同。不一致就停止。
2. 找到最新的起报时间，把所有输入的 `time` 改成这个时次。
3. 重算 `dtime`，使有效时间保持不变。例如 00 时起报的 12 小时时效，统一到 06 时之后变成 6 小时时效。
4. 若不同输入使用了相同的 member 编号，按输入顺序从 0 重新编号。
5. 沿 member 拼接。层次、经纬度和时效坐标必须能够对齐。

只有一个起报时次时给出警告，并原样返回。

格点是 `member, level, time, dtime, lat, lon` 六维数据。站点表的固定列是 `level, time, dtime, id, lon, lat`。不同起报时次要分成不同文件或不同数据对象。

## 算法参数说明

| 参数 | 含义 |
| --- | --- |
| `inputs` | 预报文件列表，或逗号分隔的路径。至少一份。格点用 nc，站点用 csv |
| `output` | 输出路径。省略时，输入为 nc 则写 `time_lagging_ensemble.nc`，否则写 csv |
| `config` | 本次使用的 ini。省略则读 `resource/conf.ini`。留空项不覆盖调用参数 |

`resource/conf.ini` 的键与 `process` 具名参数一致。空值不改变现有默认行为。

## 算法调用示例

在本包目录：

```text
python -m cli inputs=testdata/cycle_00.nc,testdata/cycle_06.nc output=time_lagging_ensemble.nc
python cli/time_lagging_cli.py
```

在 `00temp`：

```text
python -m time_lagging inputs=time_lagging/testdata/cycle_00.nc,time_lagging/testdata/cycle_06.nc output=time_lagging_ensemble.nc
```

Python：

```python
from cli.time_lagging_cli import process

result = process(
    inputs=["testdata/cycle_00.nc", "testdata/cycle_06.nc"],
    output="time_lagging_ensemble.nc",
)
```

`process` 先读入各文件，再调用 `TimeLaggingPlugin.process`，最后按后缀写出 nc 或 csv。nc 属于格点结果；站点结果为 csv。
