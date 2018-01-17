#!/usr/bin/env python3

import collections
import os
import re
import time
import sys

import click
from netCDF4 import Dataset
import numpy as np
import numpy.ma as ma
import osr
import rasterio

import pdb

from .. import geotools
from .. import utils

def adbc_conv(ss):
  m = re.match(r'(\d+)(ad)_pop.zip', ss, re.IGNORECASE)
  if m:
    y = int(m.group(1))
    if m.group(2) == 'bc':
      y *= -1
    return y
  return None

def get_years(hdir):
  return sorted(tuple(filter(lambda p: p is not None, map(adbc_conv,
                                                          os.listdir(hdir)))))

@click.command()
@click.option('--version', type=click.Choice(('32', '31_final')),
              default='32',
              help='Which version of HYDE to convert to NetCDF (default: 3.2)')
@click.option('--outdir', type=click.Path(file_okay=False),
              default='/out/hyde',
              help='Output directory (default: /out/hyde)')
@click.option('--start-year', type=int, default=0,
              help='Start from given year (default: 0AD)')
def main(version, outdir, start_year):
  oname = os.path.join(outdir, 'hyde-%s.nc' % version)
  variables = tuple([(layer, 'f4', 'ppl/km^2', -9999, 'time')
                     for layer in utils.hyde_variables()])
  years = tuple(filter(lambda yy: yy >= start_year,
                       get_years(utils.hyde_dir(version))))
  with Dataset(oname, 'w') as out:
    with rasterio.open(utils.hyde_area()) as area_ds:
      init_nc(out, area_ds, years, variables)
      with click.progressbar(years, length=len(years)) as bar:
        for year in bar:
          idx = years.index(year)
          for variable in utils.hyde_variables():
            with rasterio.open(utils.hyde_raw(version, year, variable)) as ds:
              data = ds.read(1, masked=True)
              out.variables[variable][idx, :, :] = data
          
def init_nc(dst_ds, src_ds, steps, variables):
  # Set attributes
  dst_ds.setncattr('Conventions', u'CF-1.5')
  dst_ds.setncattr('GDAL', u'GDAL 1.11.3, released 2015/09/16')

  # Create dimensions
  dst_ds.createDimension('time', len(steps))
  dst_ds.createDimension('lat', src_ds.height)
  dst_ds.createDimension('lon', src_ds.width)
  
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
  dst_ds.source = "hyde2nc.py"
  latitudes.units = "degrees_north"
  latitudes.long_name = 'latitude'
  longitudes.units = "degrees_east"
  longitudes.long_name = "longitude"
  times.units = "years since 0000-01-01 00:00:00.0"
  times.calendar = "gregorian"
  times.standard_name = "time"
  times.axis = 'T'

  # Assign data to variables
  ul = src_ds.affine * (0.5, 0.5)
  lr = src_ds.affine * (src_ds.width - 0.5, src_ds.height - 0.5)
  latitudes[:] = np.linspace(ul[1], lr[1], src_ds.height)
  longitudes[:] = np.linspace(ul[0], lr[0], src_ds.width)
  times[:] = steps

  srs = osr.SpatialReference()
  srs.ImportFromWkt(geotools.WGS84_WKT)
  src_trans = src_ds.affine.to_gdal()
  crs.grid_mapping_name = 'latitude_longitude'
  crs.spatial_ref = srs.ExportToWkt()
  crs.GetTransform = ' '.join(tuple(map(str, src_trans)))
  # FIXME: Attribute getters don't work in python3 or GDAL2
  crs.longitude_of_prime_meridian = geotools.srs_get_prime_meridian(srs)
  crs.semi_major_axis = geotools.srs_get_semi_major(srs)
  crs.inverse_flattening = geotools.srs_get_inv_flattening(srs)

  for name, dtype, units, fill, dimension in variables:
    dst_data = dst_ds.createVariable(name, dtype,
                                     (dimension, "lat","lon"), zlib = True,
                                     least_significant_digit = 4,
                                     fill_value = fill)
    dst_data.units = units
    dst_data.grid_mapping = 'crs'

if __name__ == '__main__':
  main()
  click.echo('done')

