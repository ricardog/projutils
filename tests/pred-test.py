#!/usr/bin/env python
import time
times = []
times.append(['', time.time()])

import cProfile
import gdal
import numpy as np
import pandas as pd
import rpy2.robjects as robjects

import env
import glm
import poly
import eval as myeval

times.append(['import', time.time()])

print("starting")
fname = "out/_d5ed9724c6cb2c78b59707f69b3044e6/cropland.rds"
models = robjects.r('models <- readRDS("%s")' % fname)
mod = glm.GLM(models[0])
times.append(['rds', time.time()])

times.append(['equation', time.time()])

print("reading rasters")
hpd_ds = gdal.Open('ds/hpd/wpp/high.tif')
hpd = hpd_ds.GetRasterBand(1).ReadAsArray()
cropland_ds = gdal.Open('ds/lu/rcp/aim/cropland_2010.tif')
cropland = cropland_ds.GetRasterBand(1).ReadAsArray()
unSub_ds = gdal.Open('../../data/un_subregions/')
unSub = unSub_ds.GetRasterBand(1).ReadAsArray()
df = pd.DataFrame.from_dict({'hpd': hpd.reshape(-1),
                             'unSub': unSub.reshape(-1),
                             'cropland': cropland.reshape(-1)})
df[df.hpd == hpd_ds.GetRasterBand(1).GetNoDataValue()] = np.nan
df[df.cropland == cropland_ds.GetRasterBand(1).GetNoDataValue()] = np.nan
df[df.unSub == unSub_ds.GetRasterBand(1).GetNoDataValue()] = np.nan
df[df.unSub == 0] = np.nan
df[df.unSub == 61] = np.nan
df = df.dropna()
times.append(['rasters', time.time()])

print("comparing poly results")
robjects.pandas2ri.activate()
pypoly_hpd, norm2, alpha = poly.ortho_poly_fit(np.log(df.hpd + 1), 3)
rpoly_hpd = robjects.pandas2ri.ri2py(robjects.r.poly(robjects.r.log(df.hpd + 1), 3))
assert np.allclose(pypoly_hpd[:, 1:], rpoly_hpd), "rpoly mismatch"

# Get norm2, alpha from fitted data
model_data = mod.data()
_, norm2, alpha = poly.ortho_poly_fit(np.log(model_data.hpd + 1), 3)
pypoly_hpd = poly.ortho_poly_predict(np.log(df.hpd + 1), norm2, alpha, 3)

pypoly_lu, norm2, alpha = poly.ortho_poly_fit(np.log(df.cropland + 1), 3)
rpoly_lu = robjects.pandas2ri.ri2py(robjects.r.poly(robjects.r.log(df.cropland + 1), 3))
assert np.allclose(pypoly_lu[:, 1:], rpoly_lu), "rpoly mismatch"

# Get norm2, alpha from fitted data
_, norm2, alpha = poly.ortho_poly_fit(np.log(model_data.cropland + 1), 3)
pypoly_lu = poly.ortho_poly_predict(np.log(df.cropland + 1), norm2, alpha, 3)
times.append(['poly check', time.time()])

print("starting R projection")
df.landUse = df.cropland
p3 = robjects.r.predict(models[0], df, type="response")
predicted3 = pd.DataFrame(p3.items(), index=map(str, p3.names),
                          columns=['idx', 'lui'])
times.append(['r predict', time.time()])

print("generating equation")
mod.equation
times.append(['equation', time.time()])

print("starting python projection")
predicted = mod.eval(df)
assert np.allclose(predicted, predicted3.lui, atol=1e-6), "python != r"
y_size = hpd_ds.RasterYSize
x_size = hpd_ds.RasterXSize
out = predicted.reindex(range(y_size * x_size)).as_matrix().reshape(y_size,
                                                                    x_size)
times.append(['optimized', time.time()])

print("writing output")
drv = gdal.GetDriverByName('GTiff')
dst_ds = drv.CreateCopy("cropland_2001.tif", cropland_ds, 0)
dst_ds.GetRasterBand(1).WriteArray(out)
del(dst_ds)

times.append(['write', time.time()])

width = max([len(x[0]) for x in times])
fmt = "%%-%ds: %%6.2f" % (width + 1)
total = 0
for i, t in enumerate(reversed(times)):
  if (i > 0):
    delta = times[i][1] - times[i - 1][1]
    print(fmt % (times[i][0], delta))
    total += delta
print(fmt % ('total', total))
