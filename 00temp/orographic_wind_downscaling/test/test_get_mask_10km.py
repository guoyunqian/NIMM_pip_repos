import meteva_base as meb
import numpy as np

def get_mask():
    # 读取NC文件
    grd = meb.read_griddata_from_nc(r"D:\Work\nimm_improver\wind_calculations\resource\COVER_10KM_CHINA.nc")

    data = grd.values.copy()
    data[data > -1] = 1
    data[data <= -1] = 0
    grd.values = data

    # 生成nc掩码文件
    meb.write_griddata_to_nc(grd, r"D:\Work\nimm_improver\wind_calculations\resource\MASK_10KM_CHINA.nc")


def get_wind_speed_degree(u, v):
    """
    计算风向风速

    参数:
    u: 东向风分量（可以是标量或NumPy数组）
    v: 北向风分量（可以是标量或NumPy数组）

    返回:
    speed: 风速
    angle: 风向（度），从正北开始顺时针计算
    """
    # 计算风速
    speed = np.sqrt(u * u + v * v)

    # 计算风向
    # 使用np.arctan2处理数组，避免除零错误
    angle = np.arctan2(v, u) * 180 / np.pi

    # 将角度转换为从正北开始的风向（0-360度）
    # 气象上的风向是风来的方向，所以需要调整
    angle = 90 - angle
    # 确保角度在0-360度范围内
    angle = angle % 360

    return speed, angle

def get_wind():
    # 读取风场数据
    u_grd = meb.read_griddata_from_nc(r"D:\Work\nimm_improver\wind_calculations\resource\U_2025062800.012.nc")
    v_grd = meb.read_griddata_from_nc(r"D:\Work\nimm_improver\wind_calculations\resource\V_2025062800.012.nc")
    # print(u_grd.values)

    # 定义目标网格信息
    grd0 = meb.grid([70, 135, 0.1], [17, 55, 0.1], gtime=u_grd.time.values, dtime_list=u_grd.dtime.values)

    # 计算风速风向
    u_data = u_grd.values.copy()
    v_data = v_grd.values.copy()
    s_data, r_data = get_wind_speed_degree(u_data, v_data)
    # print(s_data.shape)
    # print(s_data)

    # 插值到目标网格信息
    u_grd.values = s_data
    s_grd = meb.interp_gg_linear(u_grd, grd0)
    # print(s_grd)
    # print(s_grd.values.shape)
    print(s_grd.values.squeeze())

    meb.write_griddata_to_nc(s_grd, r"D:\Work\nimm_improver\wind_calculations\resource\WIND_SPEED_10KM_CHINA.nc")
