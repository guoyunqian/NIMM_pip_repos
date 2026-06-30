"""Command line entry points for nimm_scd."""

from __future__ import annotations


def main() -> None:
    """List available SCD commands."""
    raise SystemExit(
        "\n".join(
            [
                "nimm_scd 命令行入口：",
                "  python -m nimm_scd.cli.split_qpf [START_UTC END_UTC]",
                "  python -m nimm_scd.cli.run_scd_fusion [START_UTC END_UTC]",
                "  python -m nimm_scd.cli.pad_fusion_output [START_UTC END_UTC]",
            ]
        )
    )
