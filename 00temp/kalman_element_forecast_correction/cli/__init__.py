"""Command line entry points for nimm_kalman."""

from __future__ import annotations

from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> None:
    """List available CLI entry points."""
    lines = [
        "nimm_kalman 命令行入口：",
        "  python -m nimm_kalman.cli.kalman_data [START_YYYYMMDD END_YYYYMMDD]",
        "  python -m nimm_kalman.cli.trans_data [YYYYMMDD]",
    ]
    raise SystemExit("\n".join(lines))
