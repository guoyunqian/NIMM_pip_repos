"""Module entry point for orographic temperature downscaling CLI."""


def main() -> None:
    lines = [
        "orographic_temperature_downscaling 提供两个 CLI 示例，请直接运行：",
        "  python cli/00space_downscale/orographic_temperature_downscaling/dsc_temp_lapse_rate_main.py",
        "  python cli/00space_downscale/orographic_temperature_downscaling/anc_lapse_rate_main.py",
        "",
        "官方样例预处理仍在中间目录：",
        "  python 00temp/orographic_temperature_downscaling/cli/preprocess_test_data.py",
    ]
    raise SystemExit("\n".join(lines))


if __name__ == "__main__":
    main()
