"""Orographic temperature downscaling plugin exports.

Algorithm contributors: 郭云谦、王亭波.
Software ownership: National Institute of Meteorological Sciences / NIMM.
"""

__all__ = ["LapseRate", "ApplyGriddedLapseRate", "compute_lapse_rate_adjustment"]


def __getattr__(name):
    if name in {"LapseRate", "ApplyGriddedLapseRate", "compute_lapse_rate_adjustment"}:
        from .lapse_rate import (
            LapseRate,
            ApplyGriddedLapseRate,
            compute_lapse_rate_adjustment,
        )

        mapping = {
            "LapseRate": LapseRate,
            "ApplyGriddedLapseRate": ApplyGriddedLapseRate,
            "compute_lapse_rate_adjustment": compute_lapse_rate_adjustment,
        }
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
