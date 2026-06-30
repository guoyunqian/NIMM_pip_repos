# optimize_tp_24h

24 小时降水频率匹配订正算法，目录结构与 `mait_24h` 一致。

## 目录结构

```
optimize_tp_24h/
├── cli/          # 命令行入口 (python -m cli)
├── docs/         # 程序说明文档
├── nbs/          # Jupyter 说明笔记本
├── resource/     # 配置文件、站点模板、掩码等
├── src/          # 核心算法与主程序
├── test/         # 测试
└── utils/        # 工具模块
```

## 快速开始

1. 安装依赖：`pip install -r requirements-cli.txt`
2. 修改 `resource/optimize_tp_24.ini` 运行参数
3. 修改 `resource/plugin/*.json` 数据路径
4. 将 `mask010.nc` 放入 `resource/` 目录
5. 配置起报时间并运行：

```bash
# 实时：ini 中 rpt_list 留空
python -m cli --plugin=resource/plugin/ecmwf.json

# 回算：先在 optimize_tp_24.ini 中设置 rpt_list=2025010100 或 rpt_list=2025010100,2025010112，再运行
python -m cli --plugin=resource/plugin/ecmwf.json
```

详细说明见 [docs/OPTIMIZE_TP_24H_程序说明.md](docs/OPTIMIZE_TP_24H_程序说明.md)。
