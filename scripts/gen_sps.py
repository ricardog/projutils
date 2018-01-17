#!/usr/bin/env python

import click
from copy import copy
from netCDF4 import Dataset
import numpy as np
import numpy.ma as ma
import os
import rasterio
import rasterio.warp as rwarp
import time
import osr

from .. import geotools
from .. import utils

def earth_radius():
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)
  return srs.GetSemiMajor()
  
def init_nc(dst_ds, transform, lats, lons, years, variables):
  # Set attributes
  dst_ds.setncattr('Conventions', u'CF-1.5')
  dst_ds.setncattr('GDAL', u'GDAL 1.11.3, released 2015/09/16')

  # Create dimensions
  dst_ds.createDimension('time', None)
  dst_ds.createDimension('lat', len(lats))
  dst_ds.createDimension('lon', len(lons))

  # Create variables
  times = dst_ds.createVariable("time", "f8", ("time"), zlib=True,
                                least_significant_digit=3)
  latitudes = dst_ds.createVariable("lat", "f4", ("lat"), zlib=True,
                                    least_significant_digit = 3)
  longitudes = dst_ds.createVariable("lon", "f4", ("lon"), zlib=True,
                                     least_significant_digit=3)
  crs = dst_ds.createVariable('crs', "S1", ())

  # Add metadata
  dst_ds.history = "Created at " + time.ctime(time.time())
  dst_ds.source = "gen-sps.py"
  latitudes.units = "degrees_north"
  latitudes.long_name = 'latitude'
  longitudes.units = "degrees_east"
  longitudes.long_name = "longitude"
  times.units = "years since 2010-01-01 00:00:00.0"
  times.calendar = "gregorian"
  times.standard_name = "time"
  times.axis = 'T'

  # Assign data to variables
  latitudes[:] = lats
  longitudes[:] = lons
  times[:] = years

  srs = osr.SpatialReference()
  srs.ImportFromWkt(geotools.WGS84_WKT)
  crs.grid_mapping_name = 'latitude_longitude'
  crs.spatial_ref = srs.ExportToWkt()
  crs.GeoTransform = ' '.join(map(str, transform))
  crs.longitude_of_prime_meridian = srs.GetPrimeMeridian()
  crs.semi_major_axis = srs.GetSemiMajor()
  crs.inverse_flattening = srs.GetInvFlattening()

  out = {}
  for name, dtype, units, fill in variables:
    dst_data = dst_ds.createVariable(name, dtype,
                                     ("time", "lat","lon"), zlib = True,
                                     least_significant_digit = 4,
                                     fill_value = fill)
    dst_data.units = units
    dst_data.grid_mapping = 'crs'
    out[name] = dst_data
  return out

def get_transform(r1, r2):
  # Get the geo transform using r1 resolution but r2 bounds
  dst = rasterio.open(r1)
  src = rasterio.open(r2)
  #src_bounds = np.around(src.bounds, decimals=3)
  affine, width, height = rwarp.calculate_default_transform(src.crs,
                                                            dst.crs,
                                                            src.width,
                                                            src.height,
                                                            *src.bounds,
                                                            resolution=dst.res)
  ul = affine * (0.5, 0.5)
  lr = affine * (width - 0.5, height - 0.5)
  lats = np.linspace(ul[1], lr[1], height)
  lons = np.linspace(ul[0], lr[0], width)
  cratio = np.prod(dst.res) / np.prod(src.res)
  #cratio = 1.0
  static = rasterio.open(utils.luh2_static('carea'))
  carea = static.read(1, window=static.window(*src.bounds))
  rcs = (np.sin(np.radians(lats + dst.res[0] / 2.0)) -
         np.sin(np.radians(lats - dst.res[0] / 2.0))) * \
         (dst.res[0] * np.pi/180) * earth_radius() ** 2 / 1e6
  #carea *= rcs.reshape(carea.shape[0], 1)
  return affine, lats, lons, dst.res, cratio# / carea

def mixing(year):
  if year % 10 == 0:
    return [year]
  y0 = year - (year % 10)
  return (y0, y0 + 10)

def resample(ds, bidx, resolution, resampling, out):
  arr = ds.read(bidx, masked=True)
  nodata = ds.nodatavals[bidx - 1]
  if nodata is None:  #"'nodata' must be set!"
    nodata = -9999
  if ds.crs.data == {}:
    crs = ds.crs.from_string(u'epsg:4326')
  else:
    crs = ds.crs
  newaff, width, height = rwarp.calculate_default_transform(crs, crs, ds.width,
                                                            ds.height,
                                                            *ds.bounds,
                                                            resolution=resolution)
  out.mask.fill(False)
  rwarp.reproject(arr, out,
                  src_transform = ds.affine,
                  dst_transform = newaff,
                  width = width,
                  height = height,
                  src_nodata = nodata,
                  dst_nodata = nodata,
                  src_crs = crs,
                  resampling = resampling)
  out.mask = np.where(out == nodata, 1, 0)

def main():
  years = range(2010, 2101)
  ssps = ['ssp%d' % i for i in range(1, 6)]
  variables = [(ssp, 'f4', 'ppl/km^2', -9999) for ssp in ssps]
  fname = '%s/luh2/un_codes-full.tif' % utils.outdir()
  affine, lats, lons, res, cfudge = get_transform(fname,
                                                  utils.sps(ssps[0], 2010))
  arr = (ma.empty((len(lats), len(lons)), fill_value=-9999),
         ma.empty((len(lats), len(lons)), fill_value=-9999))
  oname = '%s/luh2/sps.nc' % utils.outdir()
  with Dataset(oname, 'w') as out:
    data = init_nc(out, affine.to_gdal(), lats, lons, years, variables)

    for ssp in ssps:
      print(ssp)
      with click.progressbar(enumerate(years), length=len(years)) as bar:
        for idx, year in bar:
          yy = mixing(year)
          files = map(lambda y: utils.sps(ssp, y), yy)
          rasters = map(rasterio.open, files)
          if len(rasters) == 1:
            resample(rasters[0], 1, res,
                      rwarp.Resampling.average, arr[0])
            data[ssp][idx, :, :] = np.clip(arr[0], 0, None) * cfudge
          else:
            f0 = (year % 10) / 10.0
            resample(rasters[0], 1, res,
                      rwarp.Resampling.average, arr[0])
            resample(rasters[1], 1, res,
                      rwarp.Resampling.average, arr[1])
            data[ssp][idx, :, :] = ((1 - f0) * np.clip(arr[0], 0, None) +
                                    f0 * np.clip(arr[1], 0, None)) * cfudge

if __name__ == '__main__':
  main()
