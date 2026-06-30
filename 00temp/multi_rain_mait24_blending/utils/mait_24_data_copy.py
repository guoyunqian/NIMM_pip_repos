import os
import shutil

dates = ["20250701", "20250702", "20250703", "20250704", "20250705", "20250706", "20250707", "20250708"]

inputs = [
    "ecmwf",
    "ncep_gfs_hr",
    "grapes_gfs",
    "german_gfs_hr",
    "shanghai_mr",
    "grapes_3km",
    "beijing_mr",
    "guangzhou_mr",
    "ecmwf_aifs",
    "fengqing",
]

for date in dates:
    for input in inputs:
        input_dir = os.path.join("/mnt/sm_qpf/v2021/rain24", input, "sfc", date)
        if input in ["ecmwf_aifs", "fengqing"]:
            input_dir = os.path.join("/mnt/245sm_qpf/rain24_py", input, date)

        output_dir = os.path.join("/mnt/data1/tmp/mait24_input_data", input, "sfc", date)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 复制目录下所有文件
        if os.path.exists(input_dir):
            for f in os.listdir(input_dir):
                shutil.copy2(os.path.join(input_dir, f), output_dir)
        else:
            print(f"缺失: {input_dir}")

ob_output_dir = os.path.join("/mnt/data1/tmp/mait24_input_data", "Observation", "r24", "sfc")
if not os.path.exists(ob_output_dir):
    os.makedirs(ob_output_dir)

for date in dates:
    for i in range(24):
        ob_input = f"/mnt/Observation/r24/sfc/{date[2:]}{i:02d}.000"
        if os.path.exists(ob_input):
            shutil.copy2(ob_input, ob_output_dir)
        else:
            print(f"缺失: {ob_input}")