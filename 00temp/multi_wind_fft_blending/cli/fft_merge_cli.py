# !/usr/bin/python
# -*-coding:utf-8 -*-
"""
测试依赖
click>=8.1.7
"""
import os
import time
import shutil
from meteva import base as meb
from src import fft_merge
import click

PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(PROJ_DIR, "resource")


@click.command()
@click.option("--sample", default="b", help="sample:a,b, default=a")
def main(sample):
    """
    示例应用，采用示例数据演示对应算法的效果及使用方法\n
    命令行执行查看帮助：python cli/fft_merge_cli.py --help\n
    命令行执行示例代码： python cli/fft_merge_cli.py --sample a\n

    :param sample: str, a或者b
    """
    if sample not in ["a", "b"]:
        print("暂时只提供了两个sample：a, b")
        return False
    return process(sample)


def _netcdf_encoding(da):
    name = da.name if da.name else "data0"
    return {name: {"dtype": "int32", "scale_factor": 0.001, '_FillValue': -9999, "zlib": True}}


def process(sample: str):
    if sample not in ["a", "b"]:
        print("暂时只提供了两个sample：a, b")
        return False
    output_dir = RES_DIR
    print(f"使用示例[sample_{sample}]执行示例代码")
    print(f"执行结果保存目录：{output_dir}")
    # 读取示例数据
    uv1_path = os.path.join(RES_DIR, f"sample_{sample}1_uv.m11")
    uv2_path = os.path.join(RES_DIR, f"sample_{sample}2_uv.m11")
    print("******开始读取示例数据")
    uv1_da = meb.read_gridwind_from_micaps11(uv1_path)
    print(f"读取完成：{uv1_path}")
    uv2_da = meb.read_gridwind_from_micaps11(uv2_path)
    print(f"读取完成：{uv2_path}")

    # FFT融合
    muv_path = os.path.join(output_dir, f"sample_{sample}_fft_uv.nc")
    muv_m11_path = os.path.join(output_dir, f"sample_{sample}_fft_uv.m11")
    ms_path = os.path.join(output_dir, f"sample_{sample}_fft_s.nc")
    del_dir_or_file(muv_path)
    del_dir_or_file(muv_m11_path)
    del_dir_or_file(ms_path)
    print("******开始进行FFT融合")
    s_time = time.time()
    fft_c = fft_merge.FFTMergePlugin()
    muv_da = fft_c(uv1_da, [uv2_da], feature_border=128)
    muv_da.to_netcdf(muv_path, encoding=_netcdf_encoding(muv_da))
    print(f"FFT融合结果保存成功: {muv_path}")
    print(f"FFT融合完成, 耗时：{round(time.time() - s_time, 4)}s")
    meb.write_griddata_to_micaps11(muv_da, muv_m11_path)
    print(f"FFT风速结果micaps11保存成功（为了方便对比结果）:{muv_m11_path}")

    # 线性插值结果，此部分代码是用来对比使用的
    luv_path = os.path.join(output_dir, f"sample_{sample}_line_uv.nc")
    luv_m11_path = os.path.join(output_dir, f"sample_{sample}_line_uv.m11")
    ls_path = os.path.join(output_dir, f"sample_{sample}_line_s.nc")
    del_dir_or_file(luv_path)
    del_dir_or_file(luv_m11_path)
    del_dir_or_file(ls_path)
    print("******开始进行线性插值")
    s_time = time.time()
    luv_da = (uv1_da + uv2_da) / 2.0
    luv_da.to_netcdf(luv_path, encoding=_netcdf_encoding(luv_da))
    print(f"线性插值结果保存成功: {luv_path}")
    print(f"线性插值执行完成, 耗时：{round(time.time() - s_time, 4)}s")
    meb.write_griddata_to_micaps11(luv_da, luv_m11_path)
    print(f"线性插值风速micaps11结果保存成功（为了方便对比结果）:{luv_m11_path}")
    print("示例代码执行完毕")
    return True


def del_dir_or_file(src_path):
    """
    删除文件或者文件夹
    """
    try:
        if not os.path.exists(src_path):
            return True
        if os.path.isdir(src_path):
            shutil.rmtree(src_path, ignore_errors=True)
        else:
            os.remove(src_path)
    except:
        pass


if __name__ == '__main__':
    main()
