import os

from pylru import lrudecorator
import rasterio

from ..rasterset import Raster
from ..simpleexpr import SimpleExpr
from .. import utils

REFERENCE_YEAR = 2000

@lrudecorator(10)
def years():
  with rasterio.open('netcdf:%s/luh2/hyde.nc:popd' % utils.outdir()) as ds:
    return tuple(map(lambda idx: int(ds.tags(idx)['NETCDF_DIM_time']),
                     ds.indexes))

def raster(version, year):
  if year not in years(version):
    raise RuntimeError('year (%d) not present in HYDE dataset)' % year)
  return {'hpd':
          Raster('hpd', 'netcdf:%s/luh2/hyde.nc:popd' % utils.outdir(),
                 band=years().index(year))}

def scale_grumps(year):
  rasters = {}
  ref_band = years().index(REFERENCE_YEAR)
  year_band = years().index(year)
  print("ref : %d" % ref_band)
  print("year: %d" % year_band)
  rasters['grumps'] = Raster('grumps', '%s/luh2/gluds00ag.tif' % utils.outdir())
  rasters['hpd_ref'] = Raster('hpd_ref',
                              'netcdf:%s/luh2/hyde.nc:popd' % utils.outdir(),
                              band=ref_band)
  rasters['hpd_proj'] = Raster('hpd_proj',
                               'netcdf:%s/luh2/hyde.nc:popd' % utils.outdir(),
                               band=year_band)
  rasters['hpd'] = SimpleExpr('hpd',
                              'grumps * (hpd_proj / (hpd_ref + 0.01))')
  return rasters
