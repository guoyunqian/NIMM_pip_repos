# time_split_linear 整理日志

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 算法名称 | `time_split_linear` |
| 中文名称 | 预报时效线性拆分 |
| 原始路径 | `D:\workspace\test\00temp\time_split_linear` |
| 路径说明 | 由算法仓库 `00temp/00_forecast_time_split` 本地修改并重命名而来；旧目录已由用户删除 |
| 整理日期 | 2026-11-06（入仓）；2026-11-11（按当前实现刷新日志） |
| 算法贡献人 | cheny |
| 算法分类 | `00time_downscale` |
| 当前状态 | 已整理至中间目录；包名保留 `time_split_linear`；待正式入库 |

## 算法理解（当前实现）

该算法只处理预报场的时间维：把粗时间坐标线性插值成细时间坐标。不改空间网格，不做要素订正。

当前包收敛为**单一插件 + 一条 CLI**：

- `TimeSplit`（`src/cal_griddata_TimeSplit_plugin.py`）  
  - 只处理**内存中的**格点场；不读路径、不解析 `input_fh`。  
  - `process(fcst, uv=None)`：沿 `index="dtime"`（预报时效）或 `index="time"`（起报时间）插值。  
  - `is_Min`：输出坐标按分钟；沿 `dtime` 时源时效先乘 60。  
  - 可选：U/V 合成风速、`delta` 累计差分（单位随 `is_Min`；差分后细场负值裁 0）、按 `output_fmt` 写 nc。  
  - 目标超出源坐标两端时按斜率外推。

- CLI（`cli/cal_griddata_TimeSplit_plugin_cli.py`）  
  - 模块级 `process(...)` 为入口核心：补齐参数 → `utils.grid_combine.read_multi_griddata` 读拼 → 构造 `TimeSplit` 插值。  
  - `index=dtime`：`is_ob=False`（一报多时效）；`index=time`：`is_ob=True`（多钟点沿 `time` 拼）。  
  - `is_fill0` 仅影响读数侧时效 0；与插件内补时效 0 逻辑分层。

多时效读拼不在本包插件内，见共享工具 `00temp/utils/grid_combine.py`（`read_multi_griddata` / `concat_griddata`）。

已从本包移除（测试亦断言不存在）：`timesplit_hourtomin_plugin`、`readdata_fromtime_plugin` 及其 CLI。

## 目录对应关系

| 中间目录 | 内容说明 |
| --- | --- |
| `00temp/time_split_linear/src/cal_griddata_TimeSplit_plugin.py` | `TimeSplit` 插件 |
| `00temp/time_split_linear/cli/cal_griddata_TimeSplit_plugin_cli.py` | 唯一业务 CLI（`process` + CliBase） |
| `00temp/time_split_linear/resource/conf.ini` | 默认运行配置 |
| `00temp/time_split_linear/resource/EC/APCP/` | 小样例 nc |
| `00temp/time_split_linear/test/` | 布局与配置解析测试 |
| `00temp/time_split_linear/nbs/` | 方法说明与命令行示例 |
| `00temp/time_split_linear/docs/预报时效拆分.md` | 算法说明（已对齐当前实现） |
| `00temp/time_split_linear/utils/` | ini 读取；并入仓库共享 `utils`（含 `grid_combine`） |

## 2026-11-11 更新

- 按用户当前实现刷新本整理日志与根目录 `NIMM_list.md`（不改算法公式以外的业务语义描述）。
- 相对 2026-11-06 入仓时的理解，当前实现要点：
  - 职责拆分：读数/拼接在 CLI `process`，插值在 `TimeSplit`。
  - 支持 `index=dtime|time`、`is_min`、参数名 `delta`（替代旧 `delta_hour` 语义入口）。
  - 依赖共享 `utils.grid_combine.read_multi_griddata`，不再在插件内直接调 `meb.read_multi_griddata` 拼装。
  - 包内仅保留 TimeSplit 一条链路；hourtomin / readdata 插件与 CLI 已删除。
- `resource/conf.ini` 仍残留旧节 `[hourtomin]` / `[read]` 及键名 `delta_hour`，与当前 `util_env`（读 `delta`、仅 `timesplit` 模块）不完全一致，需后续清理配置。
- 用户已删除旧目录 `00temp/00_forecast_time_split/`；仓库中间目录仅保留 `time_split_linear`。

## 2026-11-06 更新

- 自 `D:\workspace\test\00temp\time_split_linear` 复制到 `00temp/time_split_linear/`。未修改、未删除该原始路径。
- 保留重命名后的包名 `time_split_linear`。当时仓库中旧包 `00temp/00_forecast_time_split/` 尚未删除；其后已由用户删除。
- 当时相对旧包差异包括：时效序列含终点、修正 `np.arrage`、`meb` 读数/风速合成、`PostProcessingPlugin`、`hourtomin` 可配 `interp_method` 等。
- 贡献人按源码作者记为 cheny。

## 仍存在问题（需人工补充）

1. 正式入库到 `NIMM/00time_downscale/` 时需调整包路径。
2. `resource/conf.ini` 需与当前参数对齐（去掉无用节；`delta_hour` → `delta`；补 `is_min` / `index` 等）。
3. CLI `run` 仍经 `**params` 转发；配置键已在模块级 `process` 具名，但 CliBase 子类侧可再收紧。
4. 配置/布局测试依赖 `meteva_base`（经 `grid_combine` 导入）；缺依赖时无法收集用例。
5. 除 `resource/EC/APCP` 小样例外，完整业务读写回归仍待补充。
