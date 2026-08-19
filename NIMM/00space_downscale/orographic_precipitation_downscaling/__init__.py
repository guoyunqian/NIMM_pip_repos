"""Orographic precipitation downscaling plugin exports.

Algorithm contributors: 郭云谦、王亭波.
Software ownership: National Institute of Meteorological Sciences / NIMM.
"""

__all__ = [
    "ResolveWindComponents",
    "MetaOrographicEnhancement",
    "OrographicEnhancement",
    "ApplyOrographicEnhancement",
]


def __getattr__(name):
    if name in {"ResolveWindComponents", "MetaOrographicEnhancement", "OrographicEnhancement"}:
        from .orographic_enhancement import (
            ResolveWindComponents,
            MetaOrographicEnhancement,
            OrographicEnhancement,
        )

        mapping = {
            "ResolveWindComponents": ResolveWindComponents,
            "MetaOrographicEnhancement": MetaOrographicEnhancement,
            "OrographicEnhancement": OrographicEnhancement,
        }
        return mapping[name]
    if name == "ApplyOrographicEnhancement":
        from .apply_orographic_enhancement import ApplyOrographicEnhancement

        return ApplyOrographicEnhancement
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
