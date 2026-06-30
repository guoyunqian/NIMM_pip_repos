"""cinrad_meb 元数据（频率等）。"""

from pathlib import Path

import cinrad
import numpy as np

from pyart.retrieve.utils.cinrad_meb import (
    apply_cref_quality_gatefilter,
    apply_meteva_gate_mask,
    build_cref_qc_aux_grids_from_cinrad,
    cinrad_cr_to_meteva_grid,
    cinrad_dtype_to_meteva_volume,
    cinrad_frequency_hz,
    pick_low_tilt_index,
)

Z9010 = (
    Path(__file__).resolve().parents[1]
    / "test_data"
    / "qpe"
    / "Z_RADR_I_Z9010_20250724192400_O_DOR_SAD_CAP_FMT.bin.bz2"
)


def test_cinrad_frequency_hz_from_z9010():
    f = cinrad.io.StandardData(str(Z9010))
    freq = cinrad_frequency_hz(f)
    assert freq is not None
    assert 2e9 <= freq <= 4e9
    assert abs(freq - 2.87e9) < 0.05e9


def test_volume_grid_carries_frequency_attr():
    f = cinrad.io.StandardData(str(Z9010))
    vol, _ = cinrad_dtype_to_meteva_volume(f, "REF", range_km=300, resolution=(80, 80))
    assert "frequency" in vol.attrs
    assert vol.attrs.get("frequency_units") == "Hz"
    assert vol.attrs.get("band") == "S"


def test_cref_quality_gatefilter_reduces_coverage():
    import cinrad.calc as cinrad_calc

    f = cinrad.io.StandardData(str(Z9010))
    cr_list = list(f.iter_tilt(300, "REF"))
    cr_ds = cinrad_calc.quick_cr(cr_list, resolution=(60, 60))
    cref = cinrad_cr_to_meteva_grid(cr_ds, cinrad_file=f)
    refl_low, rho_low, _ = build_cref_qc_aux_grids_from_cinrad(
        f, cref, range_km=300, max_low_tilt_deg=2.0,
    )
    cref_qc, _, included = apply_cref_quality_gatefilter(
        cref,
        refl_low=refl_low,
        rho_low=rho_low,
        min_refl_dbz=15.0,
        min_rho=0.85,
        min_cref_dbz=15.0,
    )
    assert int(included.sum()) < int(np.prod(included.shape))
    plane = np.asarray(cref_qc.values, dtype=np.float32).squeeze()
    assert np.all(np.isnan(plane[~included]))
    assert pick_low_tilt_index(f, "REF") >= 0
