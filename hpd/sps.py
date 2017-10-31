import os

from ..rasterset import Raster
from ..simpleexpr import SimpleExpr
from .. import utils

def raster(ssp, year):
  if year < 2010 or year > 2100:
    raise RuntimeError('year outside bounds (2010 <= %d <= 2100)' % year)
  return {'hpd':
          Raster('hpd', 'netcdf:%s/luh2/sps.nc:%s' % (utils.outdir(), ssp),
                 band = year - 2009)}
  
def scale_grumps(ssp, year):
  rasters = {}
  rasters['grumps'] = Raster('grumps', '%s/luh2/gluds00ag.tif' % utils.outdir())
  rasters['hpd_ref'] = Raster('hpd_ref',
                              'netcdf:%s/luh2/sps.nc:%s' % (utils.outdir(),
                                                            ssp),
                              band = 1)
  rasters['hpd_proj'] = Raster('hpd_proj',
                               'netcdf:%s/luh2/sps.nc:%s' % (utils.outdir(),
                                                             ssp),
                               band = year - 2009)
  rasters['hpd'] = SimpleExpr('hpd',
                              'grumps * (hpd_proj / (hpd_ref + 0.01))')
  return rasters
