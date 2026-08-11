"""Command line entry points for Kalman element forecast correction."""

from __future__ import annotations

from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> None:
    """List available CLI entry points."""
    lines = [
        "Kalman element forecast correction CLI:",
        "  python -m cli.04single_calibration.kalman_element_forecast_correction.kalman_data_main [START_YYYYMMDD END_YYYYMMDD]",
        "  python -m cli.04single_calibration.kalman_element_forecast_correction.trans_data_main [YYYYMMDD]",
    ]
    print("\n".join(lines))
