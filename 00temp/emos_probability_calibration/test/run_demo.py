"""Run EMOS training and apply on sample data in data/."""

from pathlib import Path

import iris
from iris.cube import DimCoord
from improver.calibration.emos_calibration import ApplyEMOS as ApplyEMOS_Iris
from improver.calibration.emos_calibration import EstimateCoefficientsForEnsembleCalibration as train_Iris
import xarray as xr
import numpy as np

from src.emos_calibration import ApplyEMOS, EstimateCoefficientsForEnsembleCalibration

DATA = Path(__file__).parent.parent / "test_data"

from utils.xarray_core import REALIZATION_DIM, SPOT_DIM

def create_prob_template_from_xarray(
        cube: xr.DataArray,
        thresholds: list,
        thresholds_operator: str,
        diagnostic_name: str = "air_temperature"
) -> xr.DataArray:
    """
    基于输入的 xarray DataArray 创建概率模板, 将 realization 维度替换为 threshold 坐标。

    Args:
       cube: 输入的预报数据（xr.DataArray，必须包含 REALIZATION_DIM 维度）
       thresholds: 目标阈值列表，如 [35.0, 37.0, 40.0]
       thresholds_operator: 阈值比较运算符，如 "above" 或 "below"
       diagnostic_name: 诊断变量名，用于构建长名称，默认 "air_temperature"

    Returns:
       prob_template: 可用于 ApplyEMOS 的概率模板 xr.DataArray
    """
    # 检查输入 DataArray 是否有 realization 维度
    if REALIZATION_DIM not in cube.dims:
        raise ValueError(f"输入数据必须包含 {REALIZATION_DIM} 维度")

    # 1. 计算除了 realization 之外的维度和形状
    # 假设输入维度类似 (realization, spot_index) 或 (realization, time, spot_index)
    other_dims = [d for d in cube.dims if d != REALIZATION_DIM]

    # 构建新数据的 Shape: (threshold, ...其他维度大小...)
    new_shape = [len(thresholds)] + [cube.sizes[d] for d in other_dims]
    prob_data = np.zeros(new_shape, dtype=np.float32)  # 仅作模板，填充为 0

    # 2. 构建新的坐标字典
    # 继承原 DataArray 中除 realization 外的所有坐标（包括维度坐标和辅助坐标）
    new_coords = {c: cube[c] for c in cube.coords if c != REALIZATION_DIM}

    # 3. 创建 threshold 坐标并赋予必要的属性
    threshold_attrs = {
        "units": cube.attrs.get("units", "1"),  # 保持与原数据相同的单位
        "spp__relative_to_threshold": thresholds_operator,
    }
    # 将 threshold 作为第一个维度坐标
    new_coords["threshold"] = ("threshold", np.array(thresholds, dtype=np.float32), threshold_attrs)

    # 4. 组装新维度的顺序
    new_dims = ["threshold"] + other_dims

    # 5. 构建元数据属性 (Attributes)
    new_attrs = cube.attrs.copy()
    new_attrs.update({
        "long_name": f"probability_of_{diagnostic_name}_{thresholds_operator}_threshold",
        "units": "1",  # 概率单位固定为 1
    })

    # 6. 生成概率模板 xr.DataArray
    prob_template = xr.DataArray(
        data=prob_data,
        dims=new_dims,
        coords=new_coords,
        attrs=new_attrs,
        name="probability",
    )

    return prob_template

def create_prob_template_from_cube(cube, thresholds, thresholds_operator):
    """
    基于输入的 cube 创建 prob_template,将 realization 替换为 threshold 坐标。

    Args:
       cube: 输入的预报数据（必须包含 realization 坐标）
       thresholds: 目标阈值列表，如 [35.0, 37.0, 40.0]
       thresholds_operator: 阈值比较运算符，如 "above" 或 "below"

    Returns:
       prob_template: 可用于 ApplyEMOS 的概率模板 Cube
    """
    # 检查输入 cube 是否有 realization 坐标
    if not cube.coords("realization"):
        raise ValueError("输入 cube 必须包含 realization 坐标")

    # 1. 提取除 realization 外的所有坐标
    coords_to_keep = []
    for coord in cube.dim_coords:
        if coord.name() != "realization":
            coords_to_keep.append(coord)

    # 2. 创建 threshold 坐标
    threshold_coord = DimCoord(
        thresholds,
        standard_name=None,  # 如果是风速，可以用 "wind_speed"
        long_name="threshold",
        units=cube.units,  # 保持与原数据相同的单位（如 'degC' 或 'm/s'）
        var_name="threshold",
        # 表示计算大于阈值的概率
        attributes={"spp__relative_to_threshold": thresholds_operator},
    )

    # 3. 构建维度结构
    # 新维度顺序: (threshold, ...其他坐标...)
    new_shape = (len(thresholds),) + cube.shape[1:]
    prob_data = np.zeros(new_shape, dtype=np.float32)  # 数据不重要，仅作模板

    # 4. 创建 prob_template
    prob_template = iris.cube.Cube(
        prob_data,
        long_name=f"probability_of_air_temperature_{thresholds_operator}_threshold",
        var_name="probability",
        units="1",  # 概率单位（0-1）
        dim_coords_and_dims=[(threshold_coord, 0)]
                            + [(coord, i + 1) for i, coord in enumerate(coords_to_keep)],
        attributes=cube.attributes.copy(),
    )

    # 5. 添加非维度坐标（如 forecast_period, forecast_reference_time 等）
    for aux_coord in cube.aux_coords:
        if aux_coord.name() != "realization":
            dims = cube.coord_dims(aux_coord)
            prob_template.add_aux_coord(aux_coord.copy(), dims)

    return prob_template

def main():
    fo = xr.open_dataset(DATA / "fo.nc")
    fo_iris = iris.load_cube(DATA / "fo.nc")
    ob = xr.open_dataset(DATA / "ob.nc")
    ob_iris = iris.load_cube(DATA / "ob.nc")

    fo_percentiles = xr.open_dataset(DATA / "fo_percentile.nc")
    fo_percentiles_iris = iris.load_cube(DATA / "fo_percentile.nc")[:,-1:,:]
    fo_percentiles_iris.attributes.update(
        {
            "title": "Uncalibrated forecast data",
            "source": "ECMWF-GEPS ensemble",
            "institution": "NMC",
        }
    )
    # print(fo_percentiles)
    fo_percentiles = fo_percentiles.isel(time=-1)
    # print(fo_percentiles)
    altitude = xr.open_dataset(DATA / "delta_z.nc")["altitude"]
    altitude_iris = iris.load(DATA / "delta_z.nc")
    trainer = EstimateCoefficientsForEnsembleCalibration(
        distribution="norm",
        predictor="mean",
        use_default_initial_guess=True,
        point_by_point=True
    )
    trainer_iris = train_Iris(
        distribution="norm",
        predictor="mean",
        use_default_initial_guess=True,
        point_by_point=True
    )
    coeffs = trainer.process(
        historic_forecasts=fo,
        truths=ob,
        additional_fields=[altitude],
    )

    coeffs_iris = trainer_iris.process(
        historic_forecasts=fo_iris,
        truths=ob_iris,
        additional_fields=altitude_iris
    )
    print("参数")
    # print(coeffs)
    print(coeffs['emos_coefficient_alpha'].values - coeffs_iris[0].data)
    print(coeffs['emos_coefficient_beta'].values - coeffs_iris[1].data)
    print(coeffs['emos_coefficient_gamma'].values - coeffs_iris[2].data)
    print(coeffs['emos_coefficient_delta'].values - coeffs_iris[3].data)
    # iris.save(coeffs_iris, DATA / "coeffs_iris.nc")
    # coeffs_iris = iris.load(DATA / "coeffs_iris.nc")
    apply_fc = fo.isel(time=-1)
    apply_fc_iris = fo_iris[:,-1:,:]
    apply_fc_iris.attributes.update(
        {
            "title": "Uncalibrated forecast data",
            "source": "ECMWF-GEPS ensemble",
            "institution": "NMC",
        }
    )
    # print(apply_fc)
    applier = ApplyEMOS()
    applier_iris = ApplyEMOS_Iris()
    # 建模参数
    # calibrated = applier.process(
    #     forecast=apply_fc,
    #     coefficients=coeffs,
    #     additional_fields=[altitude],
    #     return_parameters=True,
    # )
    # print('建模参数')
    # print(calibrated)

    # 集合预报
    calibrated = applier.process(
        forecast=apply_fc,
        coefficients=coeffs,
        additional_fields=[altitude]
    )
    calibrated_iris = applier_iris.process(
        forecast=apply_fc_iris,
        coefficients=coeffs_iris,
        additional_fields=altitude_iris
    )
    print('集合预报')
    print(calibrated['air_temperature'].values-np.squeeze(calibrated_iris.data))


    prob_template = create_prob_template_from_xarray(apply_fc, [35.0+273.15, 37.0+273.15, 40.0+273.15], "below")
    prob_template_iris = create_prob_template_from_cube(apply_fc_iris, [35.0+273.15, 37.0+273.15, 40.0+273.15], "below")
    # 阈值概率
    calibrated = applier.process(
        forecast=apply_fc,
        prob_template=prob_template,
        coefficients=coeffs,
        additional_fields=[altitude]
    )
    calibrated_iris = applier_iris.process(
        forecast=apply_fc_iris,
        prob_template=prob_template_iris,
        coefficients=coeffs_iris,
        additional_fields=altitude_iris
    )
    print('阈值概率')
    print(calibrated['probability_of_air_temperature_below_threshold'].values - np.squeeze(calibrated_iris.data))

    # 分位值
    applier = ApplyEMOS((np.array([1/52*100, 10, 25, 50, 75, 90, 95, 100]) * 0.98).tolist())
    applier_iris = ApplyEMOS_Iris((np.array([1/52*100, 10, 25, 50, 75, 90, 95, 100]) * 0.98).tolist())
    calibrated = applier.process(
        forecast=fo_percentiles,
        coefficients=coeffs,
        additional_fields=[altitude],
        realizations_count = 51
    )
    calibrated_iris = applier_iris.process(
        forecast=fo_percentiles_iris,
        coefficients=coeffs_iris,
        additional_fields=altitude_iris,
        realizations_count=51
    )
    print('分位值')
    print(calibrated['air_temperature'].values-np.squeeze(calibrated_iris.data))

if __name__ == "__main__":
    main()
