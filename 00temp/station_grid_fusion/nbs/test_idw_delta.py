import meteva_base as meb
import numpy as np
from datetime import datetime,timedelta
from nimm.sta_grid_interp.interp_sg_idw_delta_plugin import InterpSgIdwDelta


                    
sta=meb.read_stadata_from_csv(r'/data/code/nimm/demo_data/input/sta_grid_interp/sta.csv')
#print(sta)

grid=meb.read_griddata_from_nc(r'/data/code/nimm/demo_data/input/sta_grid_interp/grid.nc')
#print(grid)

grid_info=meb.get_grid_of_data(grid)
#print(grid_info)

result=InterpSgIdwDelta().process(sta,grid)
print(result)