#!/usr/bin/env python

import netCDF4
import numpy as np
import os
import sys

from ..mp4_utils import to_mp4

def main():
  if len(sys.argv) not in (3, 4):
    print("Usage: %s <file.nc> <var-name> [title]" % os.path.basename(sys.argv[0]))
    sys.exit(1)
  print(len(sys.argv))
  fname = sys.argv[1]
  vname = sys.argv[2]
  title = '%s from %s' % (vname, fname) if len(sys.argv) < 4 else sys.argv[3]
  oname = "%s.mp4" % vname
  print("converting %s from %s to mp4" % (vname, fname))
  nc_ds = netCDF4.Dataset(fname)
  years = nc_ds.variables['time'][:]
  if years[0] < 850:
    years = [int(y + 850) for y in years]
  else:
    years = map(int, years)

  for idx, img, text in to_mp4(title, oname, len(years),
                               nc_ds.variables[vname][0], str(years[0]), 10):
    data = nc_ds.variables[vname][idx]
    #img.set_array(np.power(data+1e-6, 0.2))
    #img.set_array(10 * np.log10(data / (ref + 1e-6)))
    img.set_array(data)
    text.set_text(str(years[idx]))
