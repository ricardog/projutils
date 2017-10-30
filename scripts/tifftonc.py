#!/usr/bin/env python

import datetime
import gdal
import netCDF4 as nc
import numpy as np
import os
import osr
import sys
import time

import geotools

def main():
  if len(sys.argv) != 2:
    print("Usage: %s <raster-file>" % sys.argv[0])
    sys.exit()

  src_ds = gdal.Open(sys.argv[1])
  if src_ds is None:
    print("Error: could not open file '%s'" % sys.argv[1])
    sys.exit()
  src_data = src_ds.GetRasterBand(1).ReadAsArray()
  src_nodata = src_ds.GetRasterBand(1).GetNoDataValue()
  src_data = np.where(np.isclose(src_data,
                                 src_ds.GetRasterBand(1).GetNoDataValue()),
                      -9999, src_data)
  (y, x) = src_data.shape
  src_trans = src_ds.GetGeoTransform()
  srs = osr.SpatialReference()
  srs.ImportFromWkt(src_ds.GetProjection())

  name = os.path.splitext(sys.argv[1])[0]
  print(name)
  ofile = name + '.nc'

  dst_drv = gdal.GetDriverByName('netCDF')
  if dst_drv is None:
    print("Error: could not get driver '%s'" % 'netCDF')
    sys.exit()

  dst_ds = dst_drv.CreateCopy('foo.nc', src_ds, 0)

  # Create output dataset
  dst_ds = nc.Dataset(ofile, 'w')

  # Set attributes
  dst_ds.setncattr('Conventions', u'CF-1.5')
  dst_ds.setncattr('GDAL', u'GDAL 1.11.3, released 2015/09/16')

  # Create dimensions
  dst_ds.createDimension('time', None)
  dst_ds.createDimension('lat', y)
  dst_ds.createDimension('lon', x)

  # Create variables
  times = dst_ds.createVariable("time", "f8", ("time"), zlib=True,
                                least_significant_digit=3)
  latitudes = dst_ds.createVariable("lat", "f4", ("lat"), zlib=True,
                                    least_significant_digit = 3)
  longitudes = dst_ds.createVariable("lon", "f4", ("lon"), zlib=True,
                                     least_significant_digit=3)
  crs = dst_ds.createVariable('crs', "S1", ())
  dst_data = dst_ds.createVariable(name, "f4" ,("time", "lat","lon"), zlib = True,
                                   least_significant_digit = 3,
                                   fill_value = -9999)

  # Add metadata
  dst_ds.history = "Created at " + time.ctime(time.time())
  dst_ds.source = "tif2nc"
  latitudes.units = "degrees_north"
  latitudes.long_name = 'latitude'
  longitudes.units = "degrees_east"
  longitudes.long_name = "longitude"
  dst_data.units = "ppl/km^2"
  dst_data.grid_mapping = 'crs'
  times.units = "hours since 2001-01-01 00:00:00.0"
  times.calendar = "gregorian"

  # Assign data to variables
  latitudes[:] = np.linspace(src_trans[3] + src_trans[5] / 2 + src_trans[4],
                          src_trans[3] + y * src_trans[5] - src_trans[5] / 2, y)
  longitudes[:] = np.linspace(src_trans[0] + src_trans[1] / 2 + src_trans[2],
                           src_trans[0] + x * src_trans[1] - src_trans[1] / 2, x)
  for y in range(100):
    dst_data[y, :, :] = src_data + y

  dates = [datetime.datetime(2001 + n, 1, 1) for n in range(dst_data.shape[0])]
  times[:] = nc.date2num(dates, units=times.units, calendar=times.calendar)
  crs.grid_mapping_name = 'latitude_longitude'
  crs.spatial_ref = src_ds.GetProjection()
  crs.GetTransform = ' '.join([str(x) for x in src_trans])
  crs.longitude_of_prime_meridian = srs.GetPrimeMeridian()
  crs.semi_major_axis = srs.GetSemiMajor()
  crs.inverse_flattening = srs.GetInvFlattening()

  dst_ds.close()

