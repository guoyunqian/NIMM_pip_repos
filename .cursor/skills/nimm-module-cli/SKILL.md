---
name: nimm-module-cli
description: >-
  Build or convert a NIMM 00temp submodule CLI onto CliBase so it can be
  started with python -m cli and by running the *_cli.py script, and called
  from Python. Use when adding a submodule command line, migrating an existing
  cli/__main__.py, wiring --config, or the user mentions CliBase, 模块名_cli,
  python -m cli, or 子模块命令行.
---

# NIMM 子模块命令行

基类是 `00temp/utils/cli_base.py` 的 `CliBase`。它不读 ini。没传的参数保持声明时的默认值，约定为 `None`，由入口函数再读 ini / 预设。

对照实现：`00temp/frequency_matching_rain24/cli/frequency_matching_rain24_cli.py`。

## 何时用哪一种入口

- 包只有一条业务命令：`python -m cli` 就是这条命令。写成 `cli/{包名}_cli.py`。
- 包里已有多条 argparse 命令：保留 `python -m cli` 的菜单或 `--module` 分发。每条命令各自一个 `CliBase`，文件保持原名（如 `weight_blending_cli.py`）。
- `main()` 里写死样例路径、没有参数解析的脚本：改成路径传参并接到 `CliBase`。`process` 已有的路径/数值参数全部做成命令行 flag；必填路径用 `required=True`；去掉脚本底部的样例硬编码。`python -m cli` 可继续做子命令菜单，但要把剩余 argv 转给对应入口。`preprocess_test_data.py` 这类仅预处理工具可不动，除非用户点名。

## 命名

模块名是包目录名；多命令包用该命令文件的主干（去掉已有的 `_cli`）。

| 模块名 | 类 | 入口函数 | 文件 |
|---|---|---|---|
| `frequency_matching_rain24` | `FrequencyMatchingRain24Cli` | `frequency_matching_rain24_cli` | `cli/frequency_matching_rain24_cli.py` |
| `weight_blending` | `WeightBlendingCli` | `weight_blending_cli` | 原 `*_cli.py` |
| `dB_trans` | `DBTransCli` | `dB_trans_cli` | 原文件 |

`run` 是基类要求的业务方法。对外入口是 `{模块}_cli`，不要改成泛名 `main` 作为唯一名字。`cli/__main__.py` 里可以保留 `main(argv=None)`，转调 `{模块}_cli`，让已有测试和 `python -m cli` 继续可用。

## 文件职责

`cli/{模块}_cli.py` 自己能被直接运行，所以里面不要写相对导入。

1. 沿用该包现有的 `sys.path` 引导，不要另起一套顺序。引导完成后再 `from utils.cli_base import CliBase`。
2. 本地 `utils` 包还没把 `00temp/utils` 并进 `__path__` 时，按 `00temp/wind_fft_blending/utils/__init__.py` 追加，不要删已有路径。
3. 子类只写 `description`、`epilog`、`add_arguments`、`run`。
4. 入口函数：

```python
def frequency_matching_rain24_cli(argv=None) -> int:
    return FrequencyMatchingRain24Cli().main(argv)

if __name__ == "__main__":
    raise SystemExit(frequency_matching_rain24_cli())
```

单命令包的 `cli/__main__.py`：

```python
from .frequency_matching_rain24_cli import _build_parser, frequency_matching_rain24_cli

def main(argv=None):
    return frequency_matching_rain24_cli(argv)

if __name__ == "__main__":
    raise SystemExit(main())
```

测试若从 `cli.__main__` 导入 `_build_parser` 或 `_build_arg_parser`，在新文件里保留同名函数，返回 `TheClass().build_parser()`，并由 `__main__.py` 再导出。旧的 `*_main.py` 只再导出新入口，不要留第二份参数表。

## 参数

- 入口函数已有的参数全部做成命令行参数。已有 flag 的名字、`dest`、类型、默认值和帮助文字保持不变。
- 省略项默认 `None`。`None` 表示交给 ini / 预设，基类不填业务默认值。
- 布尔开关若原来是 `--is-multi true/false`，保持取值形式。新建的可选布尔才用 `CliBase.add_optional_bool`（同时登记 `--flag` 与 `--no-flag`，省略时为 `None`）。
- 增加 `--config`，`dest` 为 `config`，默认 `None`。帮助写明：运行配置文件，传给入口；相对路径按项目根解析；省略则用包内默认 ini。
- `run` 把 `config` 和其余参数传给 `process` 或 `resolve_args`。`call()` 的关键字必须是参数 `dest`（`grid_distance`，不是 `grid-distance`）。
- 多命令或子命令原样保留。`--config` 加在能覆盖到该次调用的解析器上。

`run` 返回 `None` 或 `0` 表示成功，其它整数原样作为退出码。原来把返回值映射成 0/1 的逻辑留在 `run` 里。未捕获异常由基类打 traceback 并返回 1。`--help` 和参数错误仍由 argparse 以 0 或 2 退出。

## 配置文件

入口函数增加 `config=None`。有值时，本次调用改读该文件，结束后恢复默认 ini。

- key=value 缓存（`_RAW_INI_CACHE`、`_main_ini_abs_path`）：按 `frequency_matching_rain24/src/utils/util_env.py` 的 `set_main_ini` 增加覆盖路径并清空缓存。文件不存在则 `FileNotFoundError`。
- `configparser`（`_INI_PATH`、`_CACHE`）：同样用 `set_main_ini` 覆盖路径并清空 `_CACHE`，解析时读覆盖后的路径。
- 谁调用 `set_main_ini`，谁在 `finally` 里 `set_main_ini(None)`。只在最外层恢复一次，避免内层提前恢复。
- 入口函数若在 import 时把 ini 抄进模块全局量，切换后要按这次调用重新装载，并在 `finally` 里装回默认值。只读缓存的函数不必重写全局量。
- 包没有 ini 读取器时，仍接收并传给入口，不要假装它改了路径。

省略 `--config` 时，行为与改前一致。

## 文档字符串里的两种启动

在包目录执行：

```text
python -m cli --plugin=resource/CMA_MESO.json
python cli/frequency_matching_rain24_cli.py --plugin=resource/CMA_MESO.json
```

多命令包的菜单里，每条 `python -m cli.xxx_cli` 旁边写上 `python cli/xxx_cli.py`。`prog` 用该命令原来的字符串；单命令包保持 `python -m cli`。

Python 调用：

```python
from cli.frequency_matching_rain24_cli import FrequencyMatchingRain24Cli
FrequencyMatchingRain24Cli.call(plugin="resource/CMA_MESO.json", pro_count=8)
```

## 做完要核对

在包目录执行，两边都要退出码 0，帮助里同时有 `--config` 和原来的 flag：

```text
python -m cli --help
python cli/{模块}_cli.py --help
```

多命令包改为对每条命令执行 `python <文件>.py --help` 和 `python -m cli.<模块> --help`。已有解析测试要能导入原来的 parser 名字。
