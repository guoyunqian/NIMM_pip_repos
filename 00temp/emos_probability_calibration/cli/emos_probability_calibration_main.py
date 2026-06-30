#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Command helpers for EMOS probability calibration.

This file is a thin wrapper around the original EMOS implementation. It keeps
the original import paths used in the intermediate directory and is intended as
an example CLI for the later repository integration step.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

import xarray as xr


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.emos_calibration import ApplyEMOS, EstimateCoefficientsForEnsembleCalibration


def _open_fields(paths: Optional[Iterable[str]]) -> list[xr.Dataset]:
    """Open optional auxiliary predictor files."""
    if not paths:
        return []
    return [xr.open_dataset(path) for path in paths]


def train_coefficients(
    historic_forecast_path: str,
    truth_path: str,
    output_path: str,
    *,
    additional_field_paths: Optional[Iterable[str]] = None,
    distribution: str = "norm",
    predictor: str = "mean",
    use_default_initial_guess: bool = True,
    point_by_point: bool = True,
) -> xr.Dataset:
    """Train EMOS coefficients from historic forecasts and truths."""
    historic_forecasts = xr.open_dataset(historic_forecast_path)
    truths = xr.open_dataset(truth_path)
    additional_fields = _open_fields(additional_field_paths)

    trainer = EstimateCoefficientsForEnsembleCalibration(
        distribution=distribution,
        predictor=predictor,
        use_default_initial_guess=use_default_initial_guess,
        point_by_point=point_by_point,
    )
    coefficients = trainer.process(
        historic_forecasts=historic_forecasts,
        truths=truths,
        additional_fields=additional_fields,
    )
    coefficients.to_netcdf(output_path)
    return coefficients


def apply_emos(
    forecast_path: str,
    coefficients_path: str,
    output_path: str,
    *,
    additional_field_paths: Optional[Iterable[str]] = None,
    predictor: str = "mean",
    realizations_count: Optional[int] = None,
) -> xr.Dataset:
    """Apply EMOS coefficients to a forecast and write calibrated output."""
    forecast = xr.open_dataset(forecast_path)
    coefficients = xr.open_dataset(coefficients_path)
    additional_fields = _open_fields(additional_field_paths)

    calibrated = ApplyEMOS().process(
        forecast=forecast,
        coefficients=coefficients,
        additional_fields=additional_fields,
        predictor=predictor,
        realizations_count=realizations_count,
    )
    calibrated.to_netcdf(output_path)
    return calibrated


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="EMOS probability calibration helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train = subparsers.add_parser("train", help="train EMOS coefficients")
    train.add_argument("--historic-forecast", required=True)
    train.add_argument("--truth", required=True)
    train.add_argument("--output", required=True)
    train.add_argument("--additional-field", action="append", default=[])
    train.add_argument("--distribution", default="norm", choices=["norm", "truncnorm"])
    train.add_argument("--predictor", default="mean", choices=["mean", "realizations"])
    train.add_argument("--no-default-initial-guess", action="store_true")
    train.add_argument("--not-point-by-point", action="store_true")

    apply = subparsers.add_parser("apply", help="apply EMOS coefficients")
    apply.add_argument("--forecast", required=True)
    apply.add_argument("--coefficients", required=True)
    apply.add_argument("--output", required=True)
    apply.add_argument("--additional-field", action="append", default=[])
    apply.add_argument("--predictor", default="mean", choices=["mean", "realizations"])
    apply.add_argument("--realizations-count", type=int, default=None)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    """Run the command line interface."""
    args = build_parser().parse_args(argv)
    if args.command == "train":
        train_coefficients(
            historic_forecast_path=args.historic_forecast,
            truth_path=args.truth,
            output_path=args.output,
            additional_field_paths=args.additional_field,
            distribution=args.distribution,
            predictor=args.predictor,
            use_default_initial_guess=not args.no_default_initial_guess,
            point_by_point=not args.not_point_by_point,
        )
    elif args.command == "apply":
        apply_emos(
            forecast_path=args.forecast,
            coefficients_path=args.coefficients,
            output_path=args.output,
            additional_field_paths=args.additional_field,
            predictor=args.predictor,
            realizations_count=args.realizations_count,
        )


if __name__ == "__main__":
    main()

