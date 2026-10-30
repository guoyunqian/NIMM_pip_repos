---
name: nimm-conf-entry
description: >-
  Align each NIMM 00temp submodule resource/conf.ini key with a named
  parameter of that command's entry (process or CLI run). Resolution is
  explicit argument, then ini, then the code preset. Use when checking or
  adding conf.ini keys, 配置参数, 入口函数, process 参数, overlay_none,
  预设值, or when a config key is only reachable through **params,
  **kwargs, or **threshold.
---

# 配置项对齐入口参数

命令行外壳见 [nimm-module-cli](../nimm-module-cli/SKILL.md)。本文只规定配置键如何进入口函数。不改算法公式。

优先级（原文）：

> 运行指定的参数大于配置文件中的值 大于定义的预设值，没有显性传参找配置文件，配置文件没有再使用默认；默认常量参数预设值和配置文件可以设置一致

## 取值

省略的参数默认 `None`，表示没传。`None` 再读 ini 的非空项；ini 空或缺这一项，再用代码预设。显式非 `None` 始终赢。预设和 ini 写成同一个值是允许的。

不要把预设写成参数默认值。默认值不是 `None` 时，调用方省略该参数就不会再读 ini。

`config=None` 用包内 `resource/conf.ini`。传入非空路径时，这次调用改读该文件，结束后恢复。谁调用 `set_main_ini`，谁在最外层 `finally` 里 `set_main_ini(None)`。调用期覆盖（rain24 的路径、时效）同样在 `finally` 清掉。

空字符串是显式值（linear_scd）。只有 `None` 表示未设置。

## 什么叫已经定义

配置键必须出现在该命令入口的具名参数里。`**params`、`**kwargs`、`**conf`、`**threshold` 不算。

入口是谁：

- 单命令：`process` 和 CLI `run` 都要带上全部配置键。`run` 把每个 dest 传给 `process` 或 `resolve_args`。
- 业务函数在 `cli/*.py` 的模块级 `process`，CLI `run(self, **params)` 只是转给它：名字写在 `process` 上即可。
- 没有这种 `process`、配置直接进 CLI `run`（`00_blend`、坐标投影、站点格点融合、FY-4B）：名字写在 `run` 上。插件里的 `process(**kwargs)` 不是配置入口。
- 多命令：每条命令的入口只带自己那一节的键。`module` 只负责选命令。总调度 `run(self, config=None, module=None, **params)` 不算这些键已定义；子命令的 `run` 或 `process` 才算。
- 吃数据立方的算法 `process`、`*_bck.py`、测试和 notebook 不是配置入口。

`config` 是切换 ini 的参数，不必出现在 ini 里。

## 改的时候

1. 读 `resource/conf.ini`（以及同包仍在用的 `resource/*.ini`）。按节记下键。注释和空行忽略。
2. 对照上面的入口。缺的键加成形参，默认 `None`。
3. 解析顺序写进该包的读取函数：非 `None` → ini 非空 → 预设。ini 改名后，读取器仍接受旧键。
4. 测试断言的解析结果字典键保持原名。例如 mait 的 `paths["para_ini"]`、`db_trans` 返回的 `"lambda"`、wind_fft 的 `get_run_defaults()` 里的 `main_uv` / `ass_uv`。
5. CLI 已有 flag 的字符串不动。`dest` 等于入口参数名。新的可选布尔用 `CliBase.add_optional_bool`。
6. 在包目录跑该包已有的配置测试。不要启动完整预报。本环境没有 `nimm_g_interp` 和 `eccodes`，地形订正插件的完整算法测试收集不了。

共享填空：`00temp/utils/conf_ini.py` 的 `overlay_none` 只填仍为 `None` 的项。

## 已经定过的名字

| 包 | 入口参数 / ini 新键 | 仍要能读的旧键 | 不要动的内部名 |
|---|---|---|---|
| mait24 | `para_path`，`beta_path`，`is_obs_bjt`，`split_lon` | `para_ini`，`bate_file`，`is_obs_bj`，`split_lin` | 解析字典仍是 `para_ini` |
| mait01 | 同上；另有 `mask_dat` | `para_ini`，`beta_path_template`，`is_obs_bj` | 预设文件名仍是 `local.ini` |
| mait03 | `background_path`，`para_path`，`beta_path`，`is_obs_bjt` | `background_ini`，`para_ini`，`beta_path_template`，`is_obs_bj` | |
| wind_fft | `main_uv_path`，`ass_uv_path`；另有 `weight_value`，`power_model`，`l_scale`，`reflect_pad` | `main_uv`，`ass_uv` | `get_run_defaults()` 仍返回 `main_uv`、`ass_uv`。flag 仍是 `--main-uv` / `--ass-uv` |
| db_trans | 参数和 ini 键都是 `lam` | `lambda` | 变换用的字典键仍是 `"lambda"`。flag 仍是 `--lambda` |
| grid_stat_merge | `b_use_heatflux_equation` | `use_heatflux` | flag 仍是 `--grid`、`--use-heatflux` |
| rain24 | `plugin` 优先于 `default_plugin`；`rpt_times` 优先于 `rpt_list` | | `clip_coords` 是四个浮点，要像 `get_runtime_config` 一样改 `slon` / `elon` / `slat` / `elat` |
| 地形三维 | `maxmin_update`，`maxmin_validate` | | 已有 `--update` 是业务 0/1 开关，不是 `MaxMinInfo.update`。`InstantInfo.validate` 才是 `validate` |

`[threshold]` 的要素名（`2t`、`2rh`、`10ws`、`10u`、`10v` 及 `*_max` / `*_min`）要写成具名参数。放进 `**threshold` 不算定义。

## 尚未对齐

这三处的配置键还不在入口的具名参数里：

- `optical_flow_nowcast`：五条命令都是 `run(self, **params)`。
- `00_forecast_time_split`：三条命令都是 `run(self, config=None, **params)`。键在 `[timesplit]`、`[hourtomin]`、`[read]`。
- `orographic_nwp_3d_downscaling`：`[threshold]` 的十个要素键只在 `**threshold`。

其余带 `resource/conf.ini` 的包，配置键已经在对应入口上。FY-4B 的插件 `process` 仍是 `**kwargs`，配置入口是 CLI `run`，不要把它当成漏项。

## 对照

- 单命令 `process` + `run` 都具名：`00temp/multi_rain_mait24_blending/src/mait_24h.py`
- ini 覆盖与恢复：`00temp/frequency_matching_rain24/src/utils/util_env.py` 的 `set_main_ini`
- 只填 `None`：`00temp/utils/conf_ini.py` 的 `overlay_none`
- 旧键回退：`00temp/db_trans/utils/util_env.py`
