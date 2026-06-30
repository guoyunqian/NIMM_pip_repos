"""Command line entry points for optical_flow_nowcast."""


def main() -> None:
    """List available command modules."""
    raise SystemExit(
        "\n".join(
            [
                "optical_flow_nowcast command modules:",
                "  Core plugins are available from optical_flow_nowcast.src.",
                "  Business CLI scripts from the original NIMM package were not included.",
            ]
        )
    )

