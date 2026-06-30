"""Ensemble Copula Coupling plugins using xarray (spot-only, no iris)."""

from __future__ import annotations

import warnings
from typing import List, Optional, Union

import numpy as np
import xarray as xr
from numpy import ndarray
from scipy import stats

import utils._scipy_continuous_distns as scipy_cont_distns
from src.base_init import BasePlugin
from utils.xarray_utilities import (
    choose,
    choose_set_of_percentiles,
    concatenate_2d_array_with_2d_array_endpoints,
    create_dataarray_with_percentiles,
    get_bounds_of_distribution,
    insert_lower_and_upper_endpoint_to_1d_array,
    interpolate_multiple_rows_same_x,
    interpolate_multiple_rows_same_y,
    manipulate_n_realizations,
    restore_non_percentile_dimensions,
)
from utils.xarray_probabilistic import (
    find_percentile_coordinate,
    find_threshold_coordinate,
    get_diagnostic_cube_name_from_probability_name,
    get_threshold_coord_name_from_probability_name,
    probability_is_above_or_below,
)
from src.calibration_utilities import convert_cube_data_to_2d, enforce_coordinate_ordering
from utils.xarray_core import as_dataarray, get_diagnostic_name


class RebadgePercentilesAsRealizations(BasePlugin):
    @staticmethod
    def process(
        da: Union[xr.DataArray, xr.Dataset],
        ensemble_realization_numbers: Optional[ndarray] = None,
    ) -> xr.DataArray:
        cube = as_dataarray(da)
        perc_name = find_percentile_coordinate(cube)
        if "realization" in cube.coords or "realization" in cube.dims:
            raise ValueError(
                "Cannot rebadge percentile coordinate to realization "
                "because a realization coordinate already exists."
            )
        percentiles = np.sort(np.unique(np.append(cube[perc_name].values, [0, 100])))
        diffs = np.diff(percentiles)
        if not np.isclose(np.max(diffs), np.min(diffs)):
            raise ValueError(
                "The percentile array cannot be rebadged as ensemble realizations. "
                f"The percentiles provided were {cube[perc_name].values}"
            )
        if ensemble_realization_numbers is None:
            ensemble_realization_numbers = np.arange(
                cube.sizes[perc_name], dtype=np.int32
            )
        out = cube.rename({perc_name: "realization"})
        out = out.assign_coords(
            realization=("realization", ensemble_realization_numbers.astype(np.int32))
        )
        out["realization"].attrs["units"] = "1"
        return out


class ResamplePercentiles(BasePlugin):
    def __init__(self, ecc_bounds_warning: bool = False, skip_ecc_bounds: bool = False):
        self.ecc_bounds_warning = ecc_bounds_warning
        self.skip_ecc_bounds = skip_ecc_bounds

    def _add_bounds_to_percentiles_and_forecast_at_percentiles(
        self, percentiles, forecast_at_percentiles, bounds_pairing
    ):
        lower_bound, upper_bound = bounds_pairing
        percentiles = insert_lower_and_upper_endpoint_to_1d_array(percentiles, 0, 100)
        forecast = concatenate_2d_array_with_2d_array_endpoints(
            forecast_at_percentiles, lower_bound, upper_bound
        )
        if np.any(np.diff(forecast) < 0):
            msg = (
                "Forecast values exist that fall outside the expected extrema "
                f"values {bounds_pairing}."
            )
            if self.ecc_bounds_warning:
                warnings.warn(msg + " Exceeded values will be used as new bounds.")
                if upper_bound < forecast.max():
                    upper_bound = forecast.max()
                if lower_bound > forecast.min():
                    lower_bound = forecast.min()
                forecast = concatenate_2d_array_with_2d_array_endpoints(
                    forecast_at_percentiles, lower_bound, upper_bound
                )
            else:
                raise ValueError(msg)
        if np.any(np.diff(percentiles) < 0):
            raise ValueError(f"Percentiles must be ascending. Got {percentiles}")
        return percentiles, forecast

    def _interpolate_percentiles(self, forecast_at_percentiles, desired_percentiles, perc_name):
        original_percentiles = forecast_at_percentiles[perc_name].values
        forecast_at_reshaped = convert_cube_data_to_2d(
            enforce_coordinate_ordering(forecast_at_percentiles, perc_name), perc_name
        )
        if not self.skip_ecc_bounds:
            bounds = get_bounds_of_distribution(
                get_diagnostic_name(forecast_at_percentiles),
                forecast_at_percentiles.attrs.get("units", "1"),
            )
            original_percentiles, forecast_at_reshaped = (
                self._add_bounds_to_percentiles_and_forecast_at_percentiles(
                    original_percentiles, forecast_at_reshaped, bounds
                )
            )
        interpolated = interpolate_multiple_rows_same_x(
            np.array(desired_percentiles, dtype=np.float64),
            original_percentiles.astype(np.float64),
            forecast_at_reshaped.astype(np.float64),
        )
        interpolated = np.transpose(interpolated)
        template = forecast_at_percentiles.isel({perc_name: 0}, drop=True)
        data = restore_non_percentile_dimensions(
            interpolated, template, len(desired_percentiles)
        )
        return create_dataarray_with_percentiles(
            desired_percentiles, template, data, forecast_at_percentiles.attrs.get("units")
        )

    def process(
        self,
        forecast_at_percentiles: Union[xr.DataArray, xr.Dataset],
        no_of_percentiles: Optional[int] = None,
        sampling: Optional[str] = "quantile",
        percentiles: Optional[List] = None,
    ) -> xr.DataArray:
        fc = as_dataarray(forecast_at_percentiles)
        perc_name = find_percentile_coordinate(fc)
        if percentiles is None:
            if no_of_percentiles is None:
                no_of_percentiles = fc.sizes[perc_name]
            percentiles = choose_set_of_percentiles(no_of_percentiles, sampling=sampling)
        return self._interpolate_percentiles(fc, percentiles, perc_name)


class ConvertProbabilitiesToPercentiles(BasePlugin):
    def __init__(
        self,
        ecc_bounds_warning: bool = False,
        mask_percentiles: bool = False,
        skip_ecc_bounds: bool = False,
    ):
        self.ecc_bounds_warning = ecc_bounds_warning
        self.mask_percentiles = mask_percentiles
        self.skip_ecc_bounds = skip_ecc_bounds

    def _add_threshold_endpoints(self, threshold_points, probabilities_for_cdf, bounds_pairing):
        lower_bound, upper_bound = bounds_pairing
        tp = insert_lower_and_upper_endpoint_to_1d_array(
            threshold_points, lower_bound, upper_bound
        )
        probs = concatenate_2d_array_with_2d_array_endpoints(probabilities_for_cdf, 0, 1)
        if np.any(np.diff(tp) < 0):
            msg = f"Threshold values {tp} not ascending relative to bounds {bounds_pairing}"
            if self.ecc_bounds_warning:
                warnings.warn(msg)
            else:
                raise ValueError(msg)
        return tp, probs

    def _probabilities_to_percentiles(self, forecast_probabilities, percentiles):
        thresh_name = find_threshold_coordinate(forecast_probabilities)
        threshold_points = forecast_probabilities[thresh_name].values
        enforce_coordinate_ordering(forecast_probabilities, thresh_name)
        prob_slices = convert_cube_data_to_2d(forecast_probabilities, coord=thresh_name)
        prob_slices = np.around(prob_slices, 9)
        relation = probability_is_above_or_below(forecast_probabilities)
        if relation == "above":
            probabilities_for_cdf = 1 - prob_slices
        elif relation == "below":
            probabilities_for_cdf = prob_slices
        else:
            raise NotImplementedError(f"Unsupported threshold relation {relation}")
        if not self.skip_ecc_bounds:
            phenom = get_threshold_coord_name_from_probability_name(
                get_diagnostic_name(forecast_probabilities)
            )
            bounds = get_bounds_of_distribution(
                phenom, forecast_probabilities.attrs.get("units", "1")
            )
            threshold_points, probabilities_for_cdf = self._add_threshold_endpoints(
                threshold_points, probabilities_for_cdf, bounds
            )
        result_slices = interpolate_multiple_rows_same_y(
            np.array(percentiles, dtype=np.float64) / 100.0,
            probabilities_for_cdf.astype(np.float64),
            threshold_points.astype(np.float64),
        )
        template = forecast_probabilities.isel({thresh_name: 0}, drop=True)
        data = restore_non_percentile_dimensions(
            np.transpose(result_slices), template, len(percentiles)
        )
        diag_name = get_diagnostic_cube_name_from_probability_name(
            get_diagnostic_name(forecast_probabilities)
        )
        out = create_dataarray_with_percentiles(
            percentiles, template, data, forecast_probabilities.attrs.get("units")
        )
        out.attrs["standard_name"] = diag_name
        out.name = diag_name
        return out

    def process(
        self,
        forecast_probabilities: Union[xr.DataArray, xr.Dataset],
        no_of_percentiles: Optional[int] = None,
        percentiles: Optional[List[float]] = None,
    ) -> xr.DataArray:
        fc = as_dataarray(forecast_probabilities)
        if percentiles is None:
            if no_of_percentiles is None:
                raise ValueError("Provide no_of_percentiles or percentiles")
            percentiles = choose_set_of_percentiles(no_of_percentiles)
        return self._probabilities_to_percentiles(fc, percentiles)


class ConvertLocationAndScaleParameters:
    def __init__(self, distribution: str = "norm", shape_parameters: Optional[ndarray] = None):
        if distribution == "truncnorm":
            self.distribution = scipy_cont_distns.truncnorm
        else:
            self.distribution = getattr(stats, distribution)
        if shape_parameters is None:
            if self.distribution.name == "truncnorm":
                raise ValueError("truncnorm requires shape_parameters")
            shape_parameters = []
        self.shape_parameters = list(shape_parameters)

    def _rescale_shape_parameters(self, location_parameter, scale_parameter):
        if self.distribution.name == "truncnorm":
            self.shape_parameters = [
                (v - location_parameter) / scale_parameter for v in self.shape_parameters
            ]


class ConvertLocationAndScaleParametersToPercentiles(
    BasePlugin, ConvertLocationAndScaleParameters
):
    def _location_and_scale_parameters_to_percentiles(
        self, location_parameter, scale_parameter, template, percentiles
    ):
        loc = as_dataarray(location_parameter)
        scale = as_dataarray(scale_parameter)
        tmpl = as_dataarray(template)
        location_data = np.ma.filled(loc.values, 1).flatten()
        scale_data = np.ma.filled(scale.values, 1).flatten()
        fractions = np.array([x / 100.0 for x in percentiles], dtype=np.float32)
        result = np.zeros((len(fractions), location_data.shape[0]), dtype=np.float32)
        self._rescale_shape_parameters(location_data, scale_data)
        dist = self.distribution(*self.shape_parameters, loc=location_data, scale=scale_data)
        for index, percentile in enumerate(fractions):
            result[index, :] = dist.ppf(np.repeat(percentile, len(location_data)))
            if np.any(scale_data <= 0):
                nan_index = np.argwhere(np.isnan(result[index, :]))
                result[index, nan_index] = location_data[nan_index]
            if np.any(np.isnan(result)):
                raise ValueError(f"NaNs in result for percentile index {index}")
        result = result.reshape((len(percentiles),) + loc.shape)
        tmpl_slice = tmpl
        for d in ("realization", "percentile"):
            if d in tmpl_slice.dims:
                tmpl_slice = tmpl_slice.isel({d: 0}, drop=True)
        mask = np.logical_or(np.ma.getmaskarray(loc.values), np.ma.getmaskarray(scale.values))
        out = create_dataarray_with_percentiles(
            percentiles, tmpl_slice, result, loc.attrs.get("units")
        )
        if np.any(mask):
            mask_array = np.stack([mask] * len(percentiles))
            out = out.where(~mask_array)
        return out

    def process(
        self,
        location_parameter,
        scale_parameter,
        template_cube,
        no_of_percentiles: Optional[int] = None,
        percentiles: Optional[List[float]] = None,
    ) -> xr.DataArray:
        if no_of_percentiles and percentiles:
            raise ValueError("Specify either no_of_percentiles or percentiles, not both")
        if no_of_percentiles:
            percentiles = choose_set_of_percentiles(no_of_percentiles)
        return self._location_and_scale_parameters_to_percentiles(
            location_parameter, scale_parameter, template_cube, percentiles
        )


class ConvertLocationAndScaleParametersToProbabilities(
    BasePlugin, ConvertLocationAndScaleParameters
):
    def process(self, location_parameter, scale_parameter, probability_template):
        loc = as_dataarray(location_parameter)
        scale = as_dataarray(scale_parameter)
        tmpl = as_dataarray(probability_template)
        thresh_name = find_threshold_coordinate(tmpl)
        thresholds = tmpl[thresh_name].values
        location_data = np.ma.filled(loc.values, 0).flatten()
        scale_data = np.ma.filled(scale.values, 1).flatten()
        self._rescale_shape_parameters(location_data, scale_data)
        dist = self.distribution(*self.shape_parameters, loc=location_data, scale=scale_data)
        relation = probability_is_above_or_below(tmpl)
        probs = []
        for t in thresholds:
            if relation == "above":
                # 📢 【核心修复二】：如果是超越概率，使用 sf() 计算大于阈值的概率 (即 1 - cdf)
                probs.append(dist.sf(np.full_like(location_data, t)))
            elif relation == "below":
                # 如果是低于/等于概率，依然保持使用 cdf()
                probs.append(dist.cdf(np.full_like(location_data, t)))
            else:
                raise NotImplementedError(f"Unsupported threshold relation {relation}")
            # probs.append(dist.cdf(np.full_like(location_data, t)))
        data = np.array(probs, dtype=np.float32).reshape((len(thresholds),) + loc.shape)
        tmpl_slice = tmpl.isel({thresh_name: 0}, drop=True)
        coords = dict(tmpl_slice.coords)
        coords[thresh_name] = ("threshold", thresholds)
        dims = ["threshold"] + list(tmpl_slice.dims)
        out = xr.DataArray(
            data,
            dims=dims,
            coords={k: v for k, v in coords.items() if k in dims},
            attrs=tmpl.attrs,
            name=get_diagnostic_name(tmpl),
        )
        return out


class EnsembleReordering(BasePlugin):
    @staticmethod
    def _recycle_raw_ensemble_realizations(post_processed, raw_forecast, percentile_coord_name):
        plen = post_processed.sizes[percentile_coord_name]
        raw = as_dataarray(raw_forecast)
        if raw.sizes["realization"] == plen:
            return raw
        return manipulate_n_realizations(raw, plen)

    @staticmethod
    def _rank_slice(cal, raw, perc_name, random_ordering, rng, tie_break):
        cal = enforce_coordinate_ordering(cal, perc_name)
        raw = enforce_coordinate_ordering(raw, "realization")
        if random_ordering:
            ranking = np.argsort(rng.rand(*raw.values.shape), axis=0)
        else:
            if tie_break == "random":
                tie_data = rng.rand(*raw.values.shape)
            elif tie_break == "realization":
                reals = raw["realization"].values
                tie_data = np.broadcast_to(
                    reals.reshape(-1, *([1] * (raw.ndim - 1))), raw.values.shape
                )
            else:
                raise ValueError(f'tie_break must be "random" or "realization", not {tie_break}')
            sorting_index = np.lexsort((tie_data, raw.values), axis=0)
            ranking = np.argsort(sorting_index, axis=0)
        mask = np.ma.getmask(cal.values)
        reordered = choose(ranking, cal.values)
        if mask is not np.ma.nomask:
            reordered = np.ma.MaskedArray(reordered, mask, dtype=np.float32)
        return cal.copy(data=reordered)

    @staticmethod
    def rank_ecc(
        post_processed_forecast_percentiles,
        raw_forecast_realizations,
        random_ordering=False,
        random_seed=None,
        tie_break="random",
    ):
        if random_seed is not None:
            random_seed = int(random_seed)
        rng = np.random.RandomState(random_seed)
        cal = as_dataarray(post_processed_forecast_percentiles)
        raw = as_dataarray(raw_forecast_realizations)
        perc_name = find_percentile_coordinate(cal)
        if "time" in cal.dims and "time" in raw.dims:
            results = []
            for t in cal["time"].values:
                cal_t = cal.sel(time=t)
                raw_t = raw.sel(time=t) if t in raw["time"].values else raw.isel(time=0)
                results.append(
                    EnsembleReordering._rank_slice(
                        cal_t, raw_t, perc_name, random_ordering, rng, tie_break
                    )
                )
            return xr.concat(results, dim="time")
        return EnsembleReordering._rank_slice(
            cal, raw, perc_name, random_ordering, rng, tie_break
        )

    def process(
        self,
        post_processed_forecast,
        raw_forecast,
        random_ordering=False,
        random_seed=None,
        tie_break="random",
    ) -> xr.DataArray:
        cal = as_dataarray(post_processed_forecast)
        raw = as_dataarray(raw_forecast)
        perc_name = find_percentile_coordinate(cal)
        raw = self._recycle_raw_ensemble_realizations(cal, raw, perc_name)
        reordered = self.rank_ecc(cal, raw, random_ordering, random_seed, tie_break)
        return RebadgePercentilesAsRealizations.process(
            reordered, ensemble_realization_numbers=raw["realization"].values
        )
