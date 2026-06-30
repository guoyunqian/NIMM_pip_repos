# (C) Crown Copyright, Met Office. All rights reserved.
#
# EMOS calibration plugins using xarray (spot-only; no iris dependency).
#
# Simplifications vs IMPROVER 1.18.7:
# - Spot data only (spot_index dimension; wmo_id auxiliary coordinate).
# - desired_units removed; inputs must already share compatible units.
# - Gridded x/y domains are not supported.
import warnings
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import xarray as xr
from numpy import ndarray
from scipy.optimize import OptimizeResult, minimize
from scipy.stats import norm

from src.base_init import BasePlugin, PostProcessingPlugin
from utils.xarray_ecc import (
    ConvertLocationAndScaleParametersToPercentiles,
    ConvertLocationAndScaleParametersToProbabilities,
    ConvertProbabilitiesToPercentiles,
    EnsembleReordering,
    RebadgePercentilesAsRealizations,
    ResamplePercentiles,
)
from utils.xarray_probabilistic import find_percentile_coordinate, get_forecast_type
from src.calibration_utilities import (
    broadcast_data_to_time_coord,
    check_data_sufficiency,
    check_forecast_consistency,
    check_predictor,
    convert_cube_data_to_2d,
    create_unified_frt_coord,
    filter_non_matching_cubes,
    flatten_ignoring_masked_data,
    forecast_coords_match,
    merge_land_and_sea,
)
from utils.xarray_core import (
    REALIZATION_DIM,
    SPOT_DIM,
    TIME_DIM,
    as_dataarray,
    as_dataset,
    collapsed,
    create_new_diagnostic_dataarray,
    extract_coefficient,
    generate_mandatory_attributes,
    get_diagnostic_name,
    is_spot_data,
    mask_dataarray,
    to_output_dataset,
)
from utils.xarray_core import enforce_coordinate_ordering

PredictorList = List[xr.DataArray]
InputField = Union[xr.DataArray, xr.Dataset]
AdditionalFields = Optional[List[InputField]]


def _as_list_of_dataarrays(fields: AdditionalFields) -> PredictorList:
    if not fields:
        return []
    return [as_dataarray(f) for f in fields]


def _predictor_name(da: xr.DataArray) -> str:
    return get_diagnostic_name(da)


class ContinuousRankedProbabilityScoreMinimisers(BasePlugin):
    TOLERATED_PERCENTAGE_CHANGE = 5
    BAD_VALUE = np.float64(999999)

    def __init__(
        self,
        predictor: str,
        tolerance: float = 0.02,
        max_iterations: int = 1000,
        point_by_point: bool = False,
    ) -> None:
        self.minimisation_dict = {
            "norm": self.calculate_normal_crps,
            "truncnorm": self.calculate_truncated_normal_crps,
        }
        self.predictor = check_predictor(predictor)
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.point_by_point = point_by_point

    def _normal_crps_preparation(
        self, initial_guess, forecast_predictor, truth, forecast_var
    ):
        aa, bb, gamma, delta = (
            initial_guess[0],
            initial_guess[1:-2],
            initial_guess[-2],
            initial_guess[-1],
        )
        if self.predictor == "mean":
            a_b = np.array([aa, *np.atleast_1d(bb)], dtype=np.float64)
        else:
            bb = bb * bb
            a_b = np.array([aa] + bb.tolist(), dtype=np.float64)
        new_col = np.ones(truth.shape, dtype=np.float32)
        all_data = np.column_stack((new_col, forecast_predictor))
        mu = np.dot(all_data, a_b)
        sigma = np.sqrt(gamma * gamma + delta * delta * forecast_var)
        xz = (truth - mu) / sigma
        return mu, sigma, xz, norm.cdf(xz), norm.pdf(xz)

    def calculate_normal_crps(self, initial_guess, forecast_predictor, truth, forecast_var, sqrt_pi):
        mu, sigma, xz, normal_cdf, normal_pdf = self._normal_crps_preparation(
            initial_guess, forecast_predictor, truth, forecast_var
        )
        if np.isfinite(np.min(mu / sigma)):
            return np.nanmean(
                sigma * (xz * (2 * normal_cdf - 1) + 2 * normal_pdf - 1 / sqrt_pi)
            )
        return self.BAD_VALUE

    def calculate_truncated_normal_crps(
        self, initial_guess, forecast_predictor, truth, forecast_var, sqrt_pi
    ):
        mu, sigma, xz, normal_cdf, normal_pdf = self._normal_crps_preparation(
            initial_guess, forecast_predictor, truth, forecast_var
        )
        x0 = mu / sigma
        normal_cdf_0 = norm.cdf(x0)
        normal_cdf_root_two = norm.cdf(np.sqrt(2) * x0)
        if np.isfinite(np.min(mu / sigma)) or (np.min(mu / sigma) >= -3):
            return np.nanmean(
                (sigma / (normal_cdf_0 * normal_cdf_0))
                * (
                    xz * normal_cdf_0 * (2 * normal_cdf + normal_cdf_0 - 2)
                    + 2 * normal_pdf * normal_cdf_0
                    - normal_cdf_root_two / sqrt_pi
                )
            )
        return self.BAD_VALUE

    def _calculate_percentage_change_in_last_iteration(self, allvecs):
        last_iteration_percentage_change = (
            np.absolute((allvecs[-1] - allvecs[-2]) / allvecs[-2]) * 100
        )
        if np.any(last_iteration_percentage_change > self.TOLERATED_PERCENTAGE_CHANGE):
            warnings.warn(
                f"Final iteration change {last_iteration_percentage_change} exceeds "
                f"{self.TOLERATED_PERCENTAGE_CHANGE}% threshold."
            )

    def _minimise_caller(
        self, minimisation_function, initial_guess, forecast_predictor_data, truth_data, forecast_var_data, sqrt_pi
    ):
        return minimize(
            minimisation_function,
            initial_guess,
            args=(forecast_predictor_data, truth_data, forecast_var_data, sqrt_pi),
            method="Nelder-Mead",
            tol=self.tolerance,
            options={"maxiter": self.max_iterations, "return_all": True},
        )

    def _prepare_forecasts(self, forecast_predictors: PredictorList) -> ndarray:
        preserve = self.predictor == "realizations"
        broadcasted = broadcast_data_to_time_coord(forecast_predictors)
        flattened = [
            flatten_ignoring_masked_data(d, preserve_leading_dimension=preserve)
            for d in broadcasted
        ]
        if len(flattened) > 1:
            return np.ma.vstack(flattened)
        return flattened[0]

    def _process_points_independently(
        self, minimisation_function, initial_guess, forecast_predictors, truth, forecast_var, sqrt_pi
    ):
        if SPOT_DIM not in truth.dims:
            raise ValueError("point_by_point requires spot_index dimension")
        optimised_coeffs = []
        for spot in truth[SPOT_DIM].values:
            truth_slice = truth.sel({SPOT_DIM: spot})
            fv_slice = forecast_var.sel({SPOT_DIM: spot})
            fp_slice = [fp.sel({SPOT_DIM: spot}) for fp in forecast_predictors]
            fp_data = self._prepare_forecasts(fp_slice)
            idx = int(spot) if len(initial_guess.shape) > 1 else 0
            ig = initial_guess[idx] if initial_guess.ndim > 1 else initial_guess
            if np.all(np.isnan(truth_slice.values)):
                optimised_coeffs.append(np.array(ig, dtype=np.float32))
            else:
                optimised_coeffs.append(
                    self._minimise_caller(
                        minimisation_function, ig, fp_data.T, truth_slice.values, fv_slice.values, sqrt_pi
                    ).x.astype(np.float32)
                )
        n_coeff = len(optimised_coeffs[0])
        return np.transpose(np.array(optimised_coeffs)).reshape(
            (n_coeff, len(truth[SPOT_DIM].values))
        )

    def _process_points_together(
        self, minimisation_function, initial_guess, forecast_predictors, truth, forecast_var, sqrt_pi
    ):
        truth_data = flatten_ignoring_masked_data(truth.values)
        forecast_var_data = flatten_ignoring_masked_data(forecast_var.values)
        forecast_predictor_data = self._prepare_forecasts(forecast_predictors)
        optimised_coeffs = self._minimise_caller(
            minimisation_function,
            initial_guess,
            forecast_predictor_data.T,
            truth_data,
            forecast_var_data,
            sqrt_pi,
        )
        if not optimised_coeffs.success:
            warnings.warn(
                f"Minimisation did not converge after {self.max_iterations} iterations."
            )
        self._calculate_percentage_change_in_last_iteration(optimised_coeffs.allvecs)
        return optimised_coeffs.x.astype(np.float32)

    def process(
        self,
        initial_guess: ndarray,
        forecast_predictors: PredictorList,
        truth: xr.DataArray,
        forecast_var: xr.DataArray,
        distribution: str,
    ) -> ndarray:
        minimisation_function = self.minimisation_dict[distribution]
        if self.predictor == "realizations":
            forecast_predictors = [
                enforce_coordinate_ordering(fp, REALIZATION_DIM) for fp in forecast_predictors
            ]
        initial_guess = np.array(initial_guess, dtype=np.float64)
        forecast_predictors = [fp.astype(np.float64) for fp in forecast_predictors]
        forecast_var = forecast_var.astype(np.float64)
        truth = truth.astype(np.float64)
        sqrt_pi = np.sqrt(np.pi)
        if self.point_by_point:
            return self._process_points_independently(
                minimisation_function, initial_guess, forecast_predictors, truth, forecast_var, sqrt_pi
            )
        return self._process_points_together(
            minimisation_function, initial_guess, forecast_predictors, truth, forecast_var, sqrt_pi
        )


class EstimateCoefficientsForEnsembleCalibration(BasePlugin):
    coeff_names = ["alpha", "beta", "gamma", "delta"]

    def __init__(
        self,
        distribution: str,
        point_by_point: bool = False,
        use_default_initial_guess: bool = False,
        desired_units: Optional[Any] = None,
        predictor: str = "mean",
        tolerance: float = 0.02,
        max_iterations: int = 1000,
        proportion_of_nans: float = 0.5,
    ) -> None:
        if desired_units is not None:
            raise ValueError(
                "desired_units is not supported in the xarray implementation. "
                "Convert historic forecasts and truths to the same units before calling."
            )
        self.distribution = distribution
        self.point_by_point = point_by_point
        self.use_default_initial_guess = use_default_initial_guess
        self.predictor = check_predictor(predictor)
        self._validate_distribution()
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.proportion_of_nans = proportion_of_nans
        self.minimiser = ContinuousRankedProbabilityScoreMinimisers(
            self.predictor, tolerance, max_iterations, point_by_point
        )

    def _validate_distribution(self):
        valid = ContinuousRankedProbabilityScoreMinimisers(self.predictor).minimisation_dict
        if self.distribution not in valid:
            raise ValueError(f"Distribution {self.distribution} not in {list(valid)}")

    def _set_attributes(self, historic_forecasts: xr.DataArray) -> Dict[str, Any]:
        attrs = {
            "diagnostic_standard_name": get_diagnostic_name(historic_forecasts),
            "distribution": self.distribution,
            "title": "Ensemble Model Output Statistics coefficients",
        }
        if self.distribution == "truncnorm":
            attrs["shape_parameters"] = np.array([0, np.inf], dtype=np.float32)
        return attrs

    def _template_for_coefficients(self, historic_forecasts: xr.DataArray) -> xr.DataArray:
        drop = [REALIZATION_DIM, TIME_DIM]
        tmpl = historic_forecasts
        for d in drop:
            if d in tmpl.dims:
                tmpl = tmpl.isel({d: 0}, drop=True)
        if not self.point_by_point and SPOT_DIM in tmpl.dims:
            tmpl = tmpl.isel({SPOT_DIM: 0}, drop=True)
        return tmpl

    def _add_predictor_coords(
        self, template: xr.DataArray, forecast_predictors: PredictorList
    ) -> Tuple[List[str], List[str]]:
        names = [_predictor_name(fp) for fp in forecast_predictors]
        return list(range(len(names))), names

    def _build_coefficient_array(
        self,
        coeff_name: str,
        coeff_data: ndarray,
        template: xr.DataArray,
        historic_forecasts: xr.DataArray,
        forecast_predictors: PredictorList,
    ) -> xr.DataArray:
        if self.point_by_point and SPOT_DIM in historic_forecasts.dims:
            tmpl = historic_forecasts.isel({TIME_DIM: 0, REALIZATION_DIM: 0}, drop=True)
        else:
            tmpl = self._template_for_coefficients(historic_forecasts)
        units = historic_forecasts.attrs.get("units", "1")
        if coeff_name not in ("alpha", "gamma"):
            units = "1"
        data = np.array(coeff_data, dtype=np.float32)
        dims = list(tmpl.dims)
        coords = {d: tmpl[d] for d in dims}
        for c in tmpl.coords:
            if c not in dims:
                coords[c] = tmpl[c]
        if coeff_name == "beta":
            pidx, pnames = self._add_predictor_coords(tmpl, forecast_predictors)
            if self.predictor == "realizations":
                dims = [REALIZATION_DIM] + dims
                coords[REALIZATION_DIM] = historic_forecasts[REALIZATION_DIM]
            dims = ["predictor_index"] + dims
            coords["predictor_index"] = ("predictor_index", np.array(pidx, dtype=np.int8))
            coords["predictor_name"] = ("predictor_index", np.array(pnames, dtype=object))
            shape = [len(pidx)] + [tmpl.sizes[d] for d in tmpl.dims]
            data = np.reshape(data, shape)
        frt = create_unified_frt_coord(historic_forecasts)
        coords["forecast_reference_time"] = frt
        if "forecast_period" in historic_forecasts.coords:
            coords["forecast_period"] = historic_forecasts["forecast_period"]
        attrs = generate_mandatory_attributes([historic_forecasts])
        attrs.update(self._set_attributes(historic_forecasts))
        return xr.DataArray(
            data,
            dims=dims,
            coords=coords,
            attrs=attrs,
            name=f"emos_coefficient_{coeff_name}",
        )

    def create_coefficients_dataset(
        self,
        optimised_coeffs: Union[List[float], ndarray],
        historic_forecasts: InputField,
        forecast_predictors: PredictorList,
    ) -> xr.Dataset:
        hf = as_dataarray(historic_forecasts)
        if self.predictor == "realizations" or len(forecast_predictors) > 1:
            optimised_coeffs = [
                optimised_coeffs[0],
                optimised_coeffs[1:-2],
                optimised_coeffs[-2],
                optimised_coeffs[-1],
            ]
        if len(optimised_coeffs) != len(self.coeff_names):
            raise ValueError("Coefficient count mismatch")
        data_vars = {}
        for coeff, name in zip(optimised_coeffs, self.coeff_names):
            data_vars[f"emos_coefficient_{name}"] = self._build_coefficient_array(
                name, coeff, self._template_for_coefficients(hf), hf, forecast_predictors
            )
        ds = xr.Dataset(data_vars)
        ds.attrs.update(self._set_attributes(hf))
        return ds

    def compute_initial_guess(
        self, truths, forecast_predictor, predictor, number_of_realizations
    ):
        default = (
            self.use_default_initial_guess
            or np.any(np.isnan(truths))
            or np.any(np.isnan(forecast_predictor))
        )
        if predictor == "mean" and default:
            initial_beta = np.repeat(1.0 / forecast_predictor.shape[0], forecast_predictor.shape[0]).tolist()
            initial_guess = [0] + initial_beta + [0, 1]
        elif predictor == "realizations" and default:
            initial_beta = np.repeat(
                np.sqrt(1.0 / number_of_realizations), number_of_realizations
            ).tolist()
            initial_guess = [0] + initial_beta + [0, 1]
        elif not self.use_default_initial_guess:
            import statsmodels.api as sm

            truths_flat = flatten_ignoring_masked_data(truths)
            fp_flat = flatten_ignoring_masked_data(
                forecast_predictor, preserve_leading_dimension=True
            )
            val = sm.add_constant(fp_flat.T, has_constant="add").astype(np.float64)
            est = sm.OLS(truths_flat.astype(np.float64), val).fit()
            initial_guess = [est.params[0].astype(np.float32)] + est.params[1:].astype(np.float32).tolist() + [0, 1]
        else:
            initial_guess = [0, 1, 0, 1]
        return np.array(initial_guess, dtype=np.float32)

    def guess_and_minimise(
        self, truths, historic_forecasts, forecast_predictors, forecast_var, number_of_realizations
    ) -> xr.Dataset:
        if self.point_by_point and not self.use_default_initial_guess:
            initial_guess = []
            for spot in truths[SPOT_DIM].values:
                t_slice = truths.sel({SPOT_DIM: spot})
                fp_slice = [fp.sel({SPOT_DIM: spot}) for fp in forecast_predictors]
                if self.predictor == "realizations":
                    fp_data = fp_slice[0].values
                else:
                    fp_data = np.ma.stack(broadcast_data_to_time_coord(fp_slice))
                initial_guess.append(
                    self.compute_initial_guess(
                        t_slice.values, fp_data, self.predictor, number_of_realizations
                    )
                )
            initial_guess = np.array(initial_guess)
        else:
            if self.predictor == "realizations":
                fp_data = forecast_predictors[0].values
            else:
                fp_data = np.ma.stack(broadcast_data_to_time_coord(forecast_predictors))
            initial_guess = self.compute_initial_guess(
                truths.values, fp_data, self.predictor, number_of_realizations
            )
            if self.point_by_point:
                initial_guess = np.broadcast_to(
                    initial_guess,
                    (len(truths[SPOT_DIM]), len(initial_guess)),
                )
        optimised = self.minimiser(
            initial_guess, forecast_predictors, truths, forecast_var, self.distribution.lower()
        )
        return self.create_coefficients_dataset(
            optimised, historic_forecasts, forecast_predictors
        )

    def process(
        self,
        historic_forecasts: InputField,
        truths: InputField,
        additional_fields: AdditionalFields = None,
        landsea_mask: Optional[InputField] = None,
    ) -> xr.Dataset:
        if landsea_mask and self.point_by_point:
            raise NotImplementedError("landsea_mask with point_by_point is not implemented")
        hf = as_dataarray(historic_forecasts)
        tr = as_dataarray(truths)
        if hf is None or tr is None:
            raise ValueError("historic_forecasts and truths must be provided")
        hf, tr = filter_non_matching_cubes(hf, tr)
        check_forecast_consistency(hf)
        check_data_sufficiency(hf, tr, self.point_by_point, self.proportion_of_nans)
        add_fields = _as_list_of_dataarrays(additional_fields)
        if add_fields:
            if self.predictor == "realizations":
                raise NotImplementedError("additional_fields with realizations predictor unsupported")
            for af in add_fields:
                for c in ("forecast_period", "forecast_reference_time", REALIZATION_DIM, TIME_DIM):
                    if c in af.dims:
                        raise ValueError(f"Static predictor {get_diagnostic_name(af)} contains {c}")
        if hf.attrs.get("units") != tr.attrs.get("units"):
            raise ValueError("Historic forecast and truth units must match")
        number_of_realizations = None
        if self.predictor == "mean":
            forecast_predictors = [collapsed(hf, REALIZATION_DIM, "mean")]
        else:
            number_of_realizations = hf.sizes[REALIZATION_DIM]
            hf = enforce_coordinate_ordering(hf, REALIZATION_DIM)
            forecast_predictors = [hf]
        forecast_predictors.extend(add_fields)
        forecast_var = collapsed(hf, REALIZATION_DIM, "var")
        if landsea_mask:
            mask = as_dataarray(landsea_mask)
            forecast_predictors = [mask_dataarray(fp, mask) for fp in forecast_predictors]
            forecast_var = mask_dataarray(forecast_var, mask)
            tr = mask_dataarray(tr, mask)
        return self.guess_and_minimise(tr, hf, forecast_predictors, forecast_var, number_of_realizations)


class CalibratedForecastDistributionParameters(BasePlugin):
    def __init__(self, predictor: str = "mean") -> None:
        self.predictor = check_predictor(predictor)
        self.coefficients = None
        self.current_forecast = None
        self.additional_fields = None

    def _diagnostic_match(self):
        diag = self.coefficients.attrs.get(
            "diagnostic_standard_name",
            list(self.coefficients.data_vars.values())[0].attrs.get("diagnostic_standard_name"),
        )
        if get_diagnostic_name(self.current_forecast) != diag:
            raise ValueError(
                f"Forecast diagnostic {get_diagnostic_name(self.current_forecast)} "
                f"!= coefficients diagnostic {diag}"
            )

    def _spatial_domain_match(self):
        if not is_spot_data(self.current_forecast):
            return
        for var in self.coefficients.data_vars:
            coeff = self.coefficients[var]
            if SPOT_DIM not in coeff.dims:
                continue
            if not np.array_equal(
                self.current_forecast[SPOT_DIM].values, coeff[SPOT_DIM].values
            ):
                raise ValueError("spot_index on forecast and coefficients do not match")
            if "wmo_id" in self.current_forecast.coords and "wmo_id" in coeff.coords:
                if not np.array_equal(
                    self.current_forecast["wmo_id"].values, coeff["wmo_id"].values
                ):
                    raise ValueError("wmo_id on forecast and coefficients do not match")

    def _calculate_location_parameter_from_mean(self) -> ndarray:
        fps = [collapsed(self.current_forecast, REALIZATION_DIM, "mean")]
        if self.additional_fields:
            fps.extend(self.additional_fields)
        beta = extract_coefficient(self.coefficients, "emos_coefficient_beta")
        alpha = extract_coefficient(self.coefficients, "emos_coefficient_alpha").values
        if len(fps) != beta.sizes.get("predictor_index", len(fps)):
            raise ValueError("Predictor count must match beta coefficients")
        location = np.zeros(fps[0].shape, dtype=np.float32)
        pnames = list(beta.coords.get("predictor_name", beta["predictor_index"]).values)
        for i, fp in enumerate(fps):
            pname = _predictor_name(fp)
            idx = pnames.index(pname) if pname in pnames else i
            b = beta.isel(predictor_index=idx).values
            while b.ndim < fp.values.ndim:
                b = np.expand_dims(b, axis=0)
            location += b * fp.values
        return (location + alpha).astype(np.float32)

    def _calculate_location_parameter_from_realizations(self) -> ndarray:
        beta = extract_coefficient(self.coefficients, "emos_coefficient_beta")
        alpha = extract_coefficient(self.coefficients, "emos_coefficient_alpha").values
        beta_values = np.atleast_2d(beta.values * beta.values)
        if beta.values.ndim != 1:
            beta_values = np.atleast_2d(np.squeeze(beta_values.T))
        a_and_b = np.hstack((np.atleast_2d(alpha).T, beta_values))
        fp_flat = convert_cube_data_to_2d(self.current_forecast)
        xy_shape = self.current_forecast.isel({REALIZATION_DIM: 0}).shape
        ones_and_pred = np.column_stack(
            (np.ones(np.prod(xy_shape), dtype=np.float32), fp_flat)
        )
        return (
            np.sum(ones_and_pred * a_and_b, axis=-1).reshape(xy_shape).astype(np.float32)
        )

    def _calculate_scale_parameter(self) -> ndarray:
        forecast_var = collapsed(self.current_forecast, REALIZATION_DIM, "var")
        gamma = extract_coefficient(self.coefficients, "emos_coefficient_gamma").values
        delta = extract_coefficient(self.coefficients, "emos_coefficient_delta").values
        return np.sqrt(gamma * gamma + delta * delta * forecast_var.values).astype(np.float32)

    def _create_output_dataset(self, location, scale) -> xr.Dataset:
        tmpl = self.current_forecast.isel({REALIZATION_DIM: 0}, drop=True)
        mandatory = generate_mandatory_attributes([self.current_forecast])
        loc = create_new_diagnostic_dataarray(
            "location_parameter",
            tmpl.attrs.get("units", "1"),
            tmpl,
            mandatory,
            data=location,
        )
        sc = create_new_diagnostic_dataarray(
            "scale_parameter",
            tmpl.attrs.get("units", "1"),
            tmpl,
            mandatory,
            data=scale,
        )
        return xr.Dataset({"location_parameter": loc, "scale_parameter": sc})

    def process(
        self,
        current_forecast: InputField,
        coefficients: Union[xr.Dataset, InputField],
        additional_fields: AdditionalFields = None,
        landsea_mask: Optional[InputField] = None,
        tolerate_time_mismatch: bool = False,
    ) -> xr.Dataset:
        self.current_forecast = as_dataarray(current_forecast)
        self.coefficients = coefficients if isinstance(coefficients, xr.Dataset) else as_dataset(coefficients)
        self.additional_fields = _as_list_of_dataarrays(additional_fields)
        self._diagnostic_match()
        if not tolerate_time_mismatch:
            for var in self.coefficients.data_vars:
                forecast_coords_match(self.coefficients[var], self.current_forecast)
        self._spatial_domain_match()
        if self.predictor == "mean":
            location = self._calculate_location_parameter_from_mean()
        else:
            location = self._calculate_location_parameter_from_realizations()
        scale = self._calculate_scale_parameter()
        out = self._create_output_dataset(location, scale)
        if landsea_mask:
            flip = np.logical_not(as_dataarray(landsea_mask).values.astype(bool))
            for v in out.data_vars:
                out[v].values = np.ma.masked_where(flip, out[v].values)
        return out


class ApplyEMOS(PostProcessingPlugin):
    def __init__(self, percentiles: Optional[Sequence] = None):
        self.percentiles = [np.float32(p) for p in percentiles] if percentiles is not None else None

    def _check_additional_field_sites(self, forecast, additional_fields):
        if not additional_fields or SPOT_DIM not in forecast.dims:
            return
        if "wmo_id" not in forecast.coords:
            return
        for ap in additional_fields:
            if not np.array_equal(ap["wmo_id"].values, forecast["wmo_id"].values):
                raise ValueError("Forecast and additional predictors have mismatching wmo_id")

    def process(
        self,
        forecast: InputField,
        coefficients: xr.Dataset,
        additional_fields: AdditionalFields = None,
        land_sea_mask: Optional[InputField] = None,
        prob_template: Optional[InputField] = None,
        realizations_count: Optional[int] = None,
        ignore_ecc_bounds: bool = True,
        tolerate_time_mismatch: bool = False,
        predictor: str = "mean",
        randomise: bool = False,
        random_seed: Optional[int] = None,
        return_parameters: bool = False,
    ) -> xr.Dataset:
        fc = as_dataarray(forecast)
        self.input_forecast_type = get_forecast_type(fc)
        self.output_forecast_type = "probabilities" if prob_template is not None else self.input_forecast_type
        if land_sea_mask and self.input_forecast_type != self.output_forecast_type:
            raise ValueError("land_sea_mask requires input and output forecast types to match")
        add = _as_list_of_dataarrays(additional_fields)
        self._check_additional_field_sites(fc, add)
        fc_real = fc.copy(deep=True)
        if self.input_forecast_type != "realizations":
            fc_real = convert_to_realizations(fc_real, realizations_count, ignore_ecc_bounds)
        params = CalibratedForecastDistributionParameters(predictor=predictor)(
            fc_real,
            coefficients,
            additional_fields=add,
            landsea_mask=land_sea_mask,
            tolerate_time_mismatch=tolerate_time_mismatch,
        )
        if return_parameters:
            return params
        distribution = {
            "name": get_attribute_from_coefficients(coefficients, "distribution"),
            "location": params["location_parameter"],
            "scale": params["scale_parameter"],
            "shape": get_attribute_from_coefficients(
                coefficients, "shape_parameters", optional=True
            ),
        }
        template = as_dataarray(prob_template) if prob_template is not None else fc
        result = generate_forecast_from_distribution(
            distribution, template, self.percentiles, randomise, random_seed
        )
        if land_sea_mask:
            merge_land_and_sea(result, fc)
        return to_output_dataset(result)


def convert_to_realizations(forecast, realizations_count, ignore_ecc_bounds):
    ftype = get_forecast_type(forecast)
    if not realizations_count:
        raise ValueError(f"realizations_count required for {ftype} input")
    if ftype == "probabilities":
        plugin = ConvertProbabilitiesToPercentiles(ecc_bounds_warning=ignore_ecc_bounds)
    elif ftype == "percentiles":
        plugin = ResamplePercentiles(ecc_bounds_warning=ignore_ecc_bounds)
    else:
        return forecast
    pct = plugin(forecast, no_of_percentiles=realizations_count)
    return RebadgePercentilesAsRealizations.process(pct)


def get_attribute_from_coefficients(coefficients, attribute_name, optional=False):
    attrs = []
    for var in coefficients.data_vars:
        if attribute_name in coefficients[var].attrs:
            attrs.append(str(coefficients[var].attrs[attribute_name]))
    if attribute_name in coefficients.attrs:
        attrs.append(str(coefficients.attrs[attribute_name]))
    if not attrs and optional:
        return None
    if not attrs:
        raise AttributeError(f"{attribute_name} must be on all coefficient variables")
    if len(set(attrs)) == 1:
        val = coefficients.attrs.get(attribute_name, coefficients[list(coefficients.data_vars)[0]].attrs[attribute_name])
        return val
    raise AttributeError(f"Inconsistent {attribute_name}: {attrs}")


def generate_forecast_from_distribution(distribution, template, percentiles, randomise, random_seed):
    template = as_dataarray(template)
    output_type = get_forecast_type(template)
    if output_type == "probabilities":
        plugin = ConvertLocationAndScaleParametersToProbabilities(
            distribution=distribution["name"], shape_parameters=distribution["shape"]
        )
        return plugin(distribution["location"], distribution["scale"], template)
    plugin = ConvertLocationAndScaleParametersToPercentiles(
        distribution=distribution["name"], shape_parameters=distribution["shape"]
    )
    if output_type == "percentiles":
        perc_coord = find_percentile_coordinate(template)
        perc = percentiles if percentiles else template[perc_coord].values
        result = plugin(distribution["location"], distribution["scale"], template, percentiles=list(perc))
    else:
        n = template.sizes[REALIZATION_DIM]
        pct = plugin(
            distribution["location"], distribution["scale"], template, no_of_percentiles=n
        )
        result = EnsembleReordering().process(
            pct, template, random_ordering=randomise, random_seed=random_seed
        )
    return result
