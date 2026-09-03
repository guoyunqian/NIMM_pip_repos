# -*- coding: utf-8 -*-
from datetime import datetime

from utils.io_meb import expand_data_path, resolve_existing_path


def test_expand_data_path_10_digit_hour_and_lead():
    tpl = "/data/rain03/YYYYMMDD/YYYYMMDDHH.VVV"
    dt = datetime(2026, 8, 20, 0, 0)
    path = expand_data_path(tpl, dt, 3)
    assert "20260820" in path
    assert path.endswith(".003")
    assert "2026082000" in path


def test_expand_data_path_12_digit_same_as_10():
    tpl = "/obs/YYYYMMDD/h03_YYYYMMDDHH00.m3"
    dt = datetime(2026, 8, 20, 8, 0)
    path = expand_data_path(tpl, dt, 0)
    assert path.endswith("h03_202608200800.m3")
    assert "/20260820/" in path.replace("\\", "/")


def test_resolve_existing_path_appends_m4(tmp_path):
    base = tmp_path / "2026082000.003"
    (tmp_path / "2026082000.003.m4").write_text("diamond 4", encoding="utf-8")
    found = resolve_existing_path(str(base), (".m4", ".nc"))
    assert found is not None
    assert found.endswith(".m4")


def test_resolve_existing_path_prefers_exact(tmp_path):
    exact = tmp_path / "file.m4"
    exact.write_text("x", encoding="utf-8")
    found = resolve_existing_path(str(exact), (".m4", ".nc"))
    assert found == str(exact)


def test_resolve_existing_path_missing_returns_none(tmp_path):
    assert resolve_existing_path(str(tmp_path / "no_such"), (".m4", ".nc")) is None


def test_describe_task_io_finds_m4_suffix(tmp_path):
    from runner import _describe_task_io

    dt = datetime(2026, 8, 20, 0, 0)
    model_dir = tmp_path / "20260820"
    model_dir.mkdir()
    (model_dir / "2026082000.003.m4").write_text("x", encoding="utf-8")
    model_tpl = str(tmp_path / "YYYYMMDD" / "YYYYMMDDHH.VVV")
    out_tpl = str(tmp_path / "out" / "YYYYMMDDHH.VVV")
    info = _describe_task_io(model_tpl, out_tpl, dt, 3)
    assert info["model_missing"] is False
    assert info["model_path"].endswith(".m4")
    assert info["output_exists"] is False


def test_grid_data_reads_path_without_m4_suffix(tmp_path):
    from utils.grid_data import GridData

    tokens = (
        "diamond 4 test 2026 08 20 00 00 003 "
        "1.0 1.0 110.0 111.0 30.0 31.0 2 2 a b c d e "
        "1.0 2.0 3.0 4.0"
    )
    (tmp_path / "field.m4").write_text(tokens + "\n", encoding="utf-8")
    gd = GridData(str(tmp_path / "field"))
    assert gd.xn == 2 and gd.yn == 2
    assert abs(float(gd.val[0, 0]) - 1.0) < 1e-6
