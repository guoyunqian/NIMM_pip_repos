"""Orographic NWP 3D downscaling plugin exports.

Algorithm contributors: 曾晓青、丰硕、赵如奇.
Software ownership: National Institute of Meteorological Sciences / NIMM.
"""

__all__ = ["FastRefineInterpPlugin"]


def __getattr__(name):
    if name == "FastRefineInterpPlugin":
        from .fast_refine_interp_plugin import FastRefineInterpPlugin

        return FastRefineInterpPlugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
