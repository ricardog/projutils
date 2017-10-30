#!/usr/bin/env python

import numpy as np
import pandas as pd
import os
import rasterio
import sys

def error(msg, exit=True):
  print(msg)
  if exit:
    sys.exit(1)
  
if len(sys.argv) != 3:
  error("Usage: %s <raster1> <raster2>" % os.path.basename(sys.argv[0]))

r1 = rasterio.open(sys.argv[1])
r2 = rasterio.open(sys.argv[2])

if r1.width != r2.width:
  error('width mismatch (%d != %d)' (r1.width, r2.width))
if r1.height != r2.height:
  error('height mismatch (%d != %d)' (r1.height, r2.height))
if r1.crs != r2.crs:
  error('crs mismatch (%s != %s)' (r1.crs, r2.crs))
if r1.transform != r2.transform:
  ## FiXME: this is likely broken
  error('transform mismatch (%s != %s)' (r1.transform, r2.transform))
if r1.count != r2.count:
  error('count mismatch (%d != %d)' (r1.count, r2.count))

rval = 0
atol=1e-5
for b in xrange(r1.count):
  df = pd.DataFrame({'b1': r1.read(b + 1).reshape(-1),
                     'b2': r2.read(b + 1).reshape(-1)})
  df = df[df.b1 != r1.nodatavals[b]]
  df = df[df.b2 != r2.nodatavals[b]]
  df = df.dropna()
  if not np.allclose(df.b1, df.b2, equal_nan=True, atol=atol):
    mismatch = df[~np.isclose(df.b1, df.b2, equal_nan=True, atol=atol)]
    print('band %d: %d data mismatched' % (b + 1,
                                           len(mismatch.index)))
    print(mismatch)
          
    #import pdb; pdb.set_trace()
    rval = 1
sys.exit(rval)
