#!/usr/bin/env python


try:
  from osgeo import gdal
except ImportError:
  import gdal

import click
import itertools
import os
import numpy as np
import pandas as pd
import platform
import re
import subprocess
import sys
import tarfile
import tempfile

from .. import geotools
from .. import utils
from .. import tiff_utils
from ..r2py import reval as reval
from ..r2py import rparser

LU = {'primary': 'gothr - gfvh1 - gfvh2',
      'secondary': 'max(gsecd - gfsh1 - gfsh2 - gfsh3, 0)',
      'cropland': 'gcrop',
      'pasture': 'gpast',
      'urban': 'gurbn',
      'plantation_pri': 'min(gothr, gfvh1 + gfvh2)',
      'plantation_sec': 'min(gsecd, gfsh1 + gfsh2 + gfsh3)',
}

funcs = {}
symbols = {}
trees = {}

def types():
  #return ['cropland', 'pasture', 'primary', 'secondary', 'urban']
  return sorted(LU.keys())

def scenarios():
  return ['aim', 'image', 'message', 'minicam', 'hyde']

def icew_mask():
  return os.path.join(utils.data_root(), 'rcp1.1/gicew.1700.txt')

def expr(lu):
  if lu not in LU:
    raise ValueError("unknown land use type: '%s'" % lu)
  return LU[lu]

def tree(lu):
  if lu not in trees:
    trees[lu] = reval.make_inputs(rparser.parse(expr(lu)))
  return trees[lu]
  
def func(lu):
  if lu not in funcs:
    lokals = {}
    exec reval.to_py(tree(lu), lu) in lokals
    funcs[lu] = lokals[lu + '_st']
  return funcs[lu]

def syms(lu):
  if lu not in symbols:
    root = tree(lu)
    symbols[lu] = reval.find_inputs(root)
  return symbols[lu]

def all_files(hh):
  files = []
  for lu in hh:
    files += syms(lu)
  return set(files)

def predictify(root, prefix):
  if isinstance(root, str) and re.match(prefix, root):
    newr = root.replace(prefix, '')
    newr = newr.replace(' Vegetation', '')
    newr = newr.replace(' forest', '_pri')
    newr = newr.lower()
    assert newr in types(), 'unknown land use type %s' % root
    return newr
  return root

def extract(fileobj, outdir, years):
  m = re.search('LUHa_u2(t1)?.v1(?:_([a-z]+).v\\d+(.\d+)?)?.tgz', fileobj.name)
  if m:
    scenario = m.group(2) if m.group(2) else 'hyde'
    series = '1700' if m.group(1) else '1500'
  else:
    raise ValueError("could not determine scenario for tar file '%s'" %
                     fileobj.name)
  click.echo('Extracting RCP land use data [%s|%s]' % (scenario, series))
  allfiles = all_files(LU)
  regexp = re.compile('updated_states/(' + '|'.join(allfiles) +
                        ').\d{4}.txt$')
  out_files = []
  with tarfile.open(fileobj=fileobj) as tf:
    members = tf.getmembers()
    files = filter(lambda x: re.search(regexp, x.name), members)

    with click.progressbar(files, length=len(files)) as bar:
      for entry in bar:
        if entry.type != tarfile.REGTYPE:
          continue
        fileobj = tf.extractfile(entry)
        dirn, name = os.path.split(entry.name)
        base, suffix = os.path.splitext(name)
        try:
          if years and int(base[-4:]) not in years:
            continue
        except:
          # if the file name doesn't end in a year, skip it
          continue
        ## NOTE: this messing around with temp files and then calling
        ## gdal_translate is necessary because gdal doesn't provide a
        ## way to work with file-like objects.  Ideally instead of this
        ## mess I should be able to say
        ##  gdal.Open(file_like_obj)
        ## and have it read from that file descriptor.  But this doesn't
        ## work because gdal doesn (?) provide a way to create a dataset
        ## using a file descriptor.
        tmpdir = os.path.join(outdir, scenario, dirn)
        utils.mkpath(tmpdir)
        temp = tempfile.NamedTemporaryFile(suffix = suffix)
        while True:
          d = fileobj.read(1<<16)
          if d:
            temp.write(d)
          else:
            break
        temp.flush()
        out_name = os.path.join(tmpdir, base + '.tif')
        subprocess.check_output(['gdal_translate', '-of', 'GTiff',
                                 '-co', 'COMPRESS=lzw', '-co', 'PREDICTOR=2',
                                 '-ot', 'Float32', temp.name, out_name])
  return out_files

def project(lu, in_dir, year, mask):
  df = pd.DataFrame()
  shape = mask.shape
  for name in syms(lu):
    fname = os.path.join(in_dir, '%s.%s.tif' % (name, year))
    ds = gdal.Open(fname)
    if ds is None:
      print("error reading input raster '%s'" % fname)
      sys.exit(1)
    band = ds.GetRasterBand(1)
    array = band.ReadAsArray()
    df[name] = array.reshape(-1)
    assert array.shape == shape
  res = func(lu)(df).values.reshape(shape)
  data = np.where(mask == 1, -9999, res)
  return data

def process(out_dir, years, maskf, what='all'):
  os.environ['GDAL_PAM_ENABLED'] = 'NO'
  geotiff = gdal.GetDriverByName("GTiff")
  in_dir = os.path.join(out_dir, 'updated_states')

  ## Get the mask and associated properties (geo transfer and projections).
  ## Use WGS84 if no projection present.
  mask_ds = gdal.Open(maskf.name)
  if mask_ds is None:
    raise RuntimeError("mask raster '%s' not found" % maskf.name)
  mask = mask_ds.GetRasterBand(1).ReadAsArray()
  geotrans = mask_ds.GetGeoTransform()
  geoproj = mask_ds.GetProjection()
  if geoproj == '':
    geoproj = geotools.WGS84_WKT
  xsize = mask_ds.RasterXSize
  ysize = mask_ds.RasterYSize
  utils.mkpath(out_dir)
  ## Iterate through types x years
  what = types() if what == 'all' else [what]
  combos = itertools.product(what, years)
  with click.progressbar(combos, length=len(years) * len(what)) as bar:
    for lu, year in bar:
      data = project(lu, in_dir, year, mask)
      #3 Write the data to a GeoTIFF file
      oname = os.path.join(out_dir, '%s_%d.tif' % (lu, year))
      tiff_utils.from_array(data, oname, xsize, ysize, trans=geotrans,
                            proj = geoproj)

def ref_to_path(ref_str):
  if ref_str[0:3] != 'rcp':
    raise ValueError("unknown reference string '%s'" % ref_str)
  comps = ref_str.split(':')
  if len(comps) == 1:
    return os.path.join('ds/lu/{0}/'.format(*comps))
  elif len(comps) == 2:
    return os.path.join('ds/lu/{0}/{1}/'.format(*comps))
  elif len(comps) == 3:
    return os.path.join('ds/lu/{0}/{1}/%%s_{2}.tif'.format(*comps))
  elif len(comps) == 4:
    return os.path.join('ds/lu/{0}/{1}/{3}_{2}.tif'.format(*comps))
  else:
    raise ValueError("unknown reference type '%s'" % ref_str)

def _ref_to_path(p):
  if p[0] == '/':
    p = p[1:]
  base = os.path.join(__name__.replace('.', '/'), p)
  return base

def some_test_func():
  print('some_test_func called')
  
if __name__ == '__main__':
  root_dir = os.path.join('ds', 'lu', 'rcp', 'minicam')
  tiff_dir = os.path.join(root_dir, 'rcp')
  mask = '../data/rcp1.1/gicew.1700.txt'
  process(tiff_dir, [2005, 2006, 2007], open(mask, 'rb'), root_dir)
