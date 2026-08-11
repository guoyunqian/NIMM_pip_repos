"""Kalman element forecast correction plugins and workflow code.

Algorithm contributors: 郭云谦、曹勇、陈荣.
Software ownership: National Institute of Meteorological Sciences / NIMM.
"""

__all__ = ["KalmanFix", "KalmanME"]


def __getattr__(name):
    if name == "KalmanFix":
        from .kalman_fix_plugin import KalmanFix

        return KalmanFix
    if name == "KalmanME":
        from .kalman_me_plugin import KalmanME

        return KalmanME
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
