# -*- coding: utf-8 -*-
"""基础结构与环境测试。"""


def test_project_layout():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for name in ("cli", "docs", "nbs", "resource", "src", "test", "utils"):
        assert (root / name).is_dir(), f"missing directory: {name}"


def test_import_core_modules():
    import config
    import correct_tp_24h
    from cli import __main__ as cli_main
    from utils import util_env

    assert hasattr(config, "fact_level")
    assert hasattr(correct_tp_24h, "mainProcess")
    assert hasattr(cli_main, "main")
    assert hasattr(util_env, "get_resolved_paths")


def test_cli_help():
    import pytest
    from cli import __main__ as cli_main

    with pytest.raises(SystemExit):
        cli_main.main(["--help"])


def test_resolved_paths():
    from utils.util_env import get_resolved_paths

    paths = get_resolved_paths()
    assert "station_info" in paths
    assert "mask_nc" in paths
    assert "default_plugin" in paths
    assert paths["station_info"].endswith("sta.m3")
