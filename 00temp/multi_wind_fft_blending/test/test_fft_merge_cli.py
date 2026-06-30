# -*- coding: utf-8 -*-
"""fft_merge_cli 示例流程测试。"""
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from cli import fft_merge_cli


def test_process_sample_a():
    assert fft_merge_cli.process("a") is True
    res_dir = os.path.join(_REPO, "resource")
    assert os.path.isfile(os.path.join(res_dir, "sample_a_fft_uv.nc"))
    assert os.path.isfile(os.path.join(res_dir, "sample_a_fft_uv.m11"))
    assert os.path.isfile(os.path.join(res_dir, "sample_a_line_uv.nc"))


def test_process_sample_b():
    assert fft_merge_cli.process("b") is True
    res_dir = os.path.join(_REPO, "resource")
    assert os.path.isfile(os.path.join(res_dir, "sample_b_fft_uv.m11"))


def test_invalid_sample():
    assert fft_merge_cli.process("x") is False


if __name__ == "__main__":
    test_process_sample_a()
    test_process_sample_b()
    test_invalid_sample()
    print("all tests passed")
