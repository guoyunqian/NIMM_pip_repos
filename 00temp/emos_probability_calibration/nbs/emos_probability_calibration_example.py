#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Minimal EMOS probability calibration example.

Run from the algorithm intermediate directory:

    python nbs/emos_probability_calibration_example.py
"""

from pathlib import Path
import sys

import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.emos_calibration import ApplyEMOS, EstimateCoefficientsForEnsembleCalibration


def main() -> None:
    """Train coefficients on sample data and apply them to the latest forecast."""
    data_dir = ROOT / "test_data"
    historic_forecasts = xr.open_dataset(data_dir / "fo.nc")
    truths = xr.open_dataset(data_dir / "ob.nc")
    altitude = xr.open_dataset(data_dir / "delta_z.nc")["altitude"]

    trainer = EstimateCoefficientsForEnsembleCalibration(
        distribution="norm",
        predictor="mean",
        use_default_initial_guess=True,
        point_by_point=True,
    )
    coefficients = trainer.process(
        historic_forecasts=historic_forecasts,
        truths=truths,
        additional_fields=[altitude],
    )

    forecast = historic_forecasts.isel(time=-1)
    calibrated = ApplyEMOS().process(
        forecast=forecast,
        coefficients=coefficients,
        additional_fields=[altitude],
    )
    print(coefficients)
    print(calibrated)


if __name__ == "__main__":
    main()

