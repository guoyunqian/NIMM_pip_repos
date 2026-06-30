"""Public SCD plugin classes."""

__all__ = ["QpfSplitPlugin", "ScdFusionPlugin"]


def __getattr__(name):
    if name == "QpfSplitPlugin":
        from nimm_scd.src.qpf_split_plugin import QpfSplitPlugin

        return QpfSplitPlugin
    if name == "ScdFusionPlugin":
        from nimm_scd.src.scd_fusion_plugin import ScdFusionPlugin

        return ScdFusionPlugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
