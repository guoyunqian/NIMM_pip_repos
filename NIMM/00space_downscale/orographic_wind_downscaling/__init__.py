"""Orographic wind downscaling plugin exports.

Algorithm contributors: 郭云谦、王亭波.
Software ownership: National Institute of Meteorological Sciences / NIMM.
"""

__all__ = ["FrictionVelocity", "RoughnessCorrection", "RoughnessCorrectionUtilities"]


def __getattr__(name):
    if name in {"FrictionVelocity", "RoughnessCorrection", "RoughnessCorrectionUtilities"}:
        from .wind_downscaling import (
            FrictionVelocity,
            RoughnessCorrection,
            RoughnessCorrectionUtilities,
        )

        mapping = {
            "FrictionVelocity": FrictionVelocity,
            "RoughnessCorrection": RoughnessCorrection,
            "RoughnessCorrectionUtilities": RoughnessCorrectionUtilities,
        }
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
