"""cinrad Py-ART 预处理测试。"""

from pathlib import Path
from types import SimpleNamespace

import cinrad
import numpy as np

from pyart.retrieve.utils.cinrad_meb import cinrad_frequency_hz
from pyart.retrieve.utils.cinrad_pyart_prep import _attach_radar_frequency

Z9010 = (
    Path(__file__).resolve().parents[1]
    / "test_data"
    / "qpe"
    / "Z_RADR_I_Z9010_20250724192400_O_DOR_SAD_CAP_FMT.bin.bz2"
)


def test_attach_radar_frequency_from_cinrad():
    """应能从 cinrad 文件回填 Py-ART Radar 的频率字段。"""
    cinrad_file = cinrad.io.StandardData(str(Z9010))
    radar = SimpleNamespace(instrument_parameters=None)

    expected = cinrad_frequency_hz(cinrad_file)
    assert expected is not None

    radar = _attach_radar_frequency(radar, cinrad_file)

    assert radar.instrument_parameters is not None
    assert "frequency" in radar.instrument_parameters

    freq = np.asarray(radar.instrument_parameters["frequency"]["data"], dtype=np.float64).ravel()
    assert freq.size == 1
    assert np.isfinite(freq[0])
    assert abs(float(freq[0]) - float(expected)) < 1e6


def test_attach_radar_frequency_keeps_existing_value():
    """若 Radar 已有有效频率字段，不应被回填逻辑覆盖。"""
    cinrad_file = cinrad.io.StandardData(str(Z9010))
    preset = 9.99e9
    radar = SimpleNamespace(
        instrument_parameters={
            "frequency": {
                "data": np.array([preset], dtype=np.float32),
                "units": "Hz",
            }
        }
    )

    radar = _attach_radar_frequency(radar, cinrad_file)
    freq = np.asarray(radar.instrument_parameters["frequency"]["data"], dtype=np.float64).ravel()
    assert freq.size == 1
    assert abs(float(freq[0]) - float(np.float32(preset))) < 1.0
