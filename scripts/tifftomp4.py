#!/usr/bin/env python

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as colors

import argparse
import itertools
import json
import math
import numpy as np
import os
import rasterio
import tempfile
import shutil
import subprocess
import sys

from ..progressbar import ProgressBar
from ..mp4_utils import to_mp4
from .. import tiff_utils

def get_stats(files):
  import gdal
  low = []
  high = []
  bands = []
  x_size = None
  y_size = None
  for f in files:
    ds = gdal.Open(f)
    if ds is None:
      print "Error: failed to open '%s" % f
      sys.exit(1)
    if x_size is None:
      x_size = ds.RasterXSize
      y_size = ds.RasterYSize
    else:
      if (x_size != ds.RasterXSize or y_size != ds.RasterYSize):
        print "raster have mismatched sizes (%d = %d; %d = %d)" % (x_size,
                                                                   ds.RasterXSize,
                                                                   y_size,
                                                                   ds.RasterYSize)
        sys.exit(1)
    l, h = tiff_utils.get_min_max(ds)
    low.append(l)
    high.append(h)
    bands.append(ds.RasterCount)
  print "min: %.2f / max: %.2f [%d x %d] : %d" % (min(low),
                                                  max(high),
                                                  x_size,
                                                  y_size,
                                                  sum(bands))
  return(min(low), max(high), x_size, y_size, bands)

def convert(title, fps, palette, band, oname, files):
  #stats = get_stats(files)
  #bands = stats[4]
  #nframes = sum(bands)
  nframes = len(files)
  cnorm = colors.Normalize(vmin=3.5, vmax=5.0)
  with rasterio.open(files[0]) as src:
    data = src.read(band, masked=True)
  for idx, img, text in to_mp4(title, oname, nframes,
                               data, 'year', fps, cnorm=cnorm):
    ds = rasterio.open(files[idx])
    data = ds.read(band, masked=True)
    img.set_array(data)
    text.set_text('year')

def parse_args():
  parser = argparse.ArgumentParser(description='Convert a series of raster ' +
                                   'maps into a video sequence.',
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('--fps', type=int, default=10,
                      help='frames per second for output video. ' +
                      'you can control the speed of playback by increasing ' +
                      'or decreasing the FPS.')
  parser.add_argument('-o', '--out', type=str, required=True,
                      help='name of output file.')
  parser.add_argument('-t', '--title', default='',
                      help='title for the video')
  parser.add_argument('-p', '--palette', default='green',
                      choices=['blue', 'green', 'orange', 'red'],
                      help='name of color palette to use')
  parser.add_argument('-b', '--band', type=int,
                      help='which band in input raster files to use')
  parser.add_argument('-f', '--files', type=str, nargs='+',
                       required=True, help='GeoTIFF raster files to process')
  parser.add_argument('-s', '--stats', action='store_true',
                      help='Print max/min stats for all files and exit')
  return parser.parse_args()

def main():
  args = parse_args()
  if args.stats:
    stats = get_stats(args.files)
    return
  convert(args.title, args.fps, args.palette, args.band, args.out, args.files)

if __name__ == '__main__':
  main()
