#!/usr/bin/env python

from copy import copy

import affine
import cartopy
import cartopy.crs as ccrs
import click
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import numpy.ma as ma
import rasterio
from rasterio.plot import plotting_extent
from rasterio.warp import Resampling, calculate_default_transform, reproject
import re

import projections.tiff_utils as tu

def get_min_max(fname):
  import gdal
  ds = gdal.Open(fname)
  min, max = tu.get_min_max(ds)
  del ds
  print('[%6.3f : %6.3f]' % (min, max))
  return min, max

def too_big(h, w):
  if h * w > 64<<20:
    return True
  return False

def read_array(src, band=1, window=None, max_width=2048):
  if window is None:
    window = src.window(*src.bounds)
  if too_big(window.height, window.width):
    scale = int(window.width / max_width)
  else:
    scale = 1.0
  transform = src.transform * affine.Affine.scale(scale)
  width = int(window.width // scale)
  height = int(window.height // scale)
  data = src.read(band, masked=True, window=window, out_shape=(height, width))
  return transform, data

def project(dst_crs, src, src_data, src_transform, *src_bounds):
  src_height, src_width = src_data.shape
  dst_transform, dst_width, dst_height = \
    calculate_default_transform(src.crs, dst_crs, src_width, src_height,
                                *src_bounds)
  dst_data = ma.zeros((dst_height, dst_width), src_data.dtype)
  dst_data.fill_value = src.nodata
  reproject(source=src_data.filled(), destination=dst_data,
            src_transform=src_transform, src_crs=src.crs,
            dst_transform=dst_transform, dst_crs=dst_crs,
            src_nodata=src.nodata, dst_nodata=src.nodata,
            resampling=Resampling.bilinear)
  return (dst_transform,
          ma.masked_equal(dst_data.astype(src_data.dtype),
                          src_data.fill_value))
            
@click.command()
@click.argument('fname', type=click.Path(dir_okay=False))
@click.option('-b', '--band', type=int, default=1,
              help='Which raster band to display (default: 1)')
@click.option('-s', '--save', type=click.Path(dir_okay=False),
              help='Save the resulting image to disk.')
@click.option('-t', '--title',
              help='Title of the image (default: file name)')
@click.option('--vmax', type=float,
              help='Upper bound for color display.  Any cells less than ' +
              'this value will be shown in red.  By default it will ' +
              'compute the maximum such that 98% of the cells are below ' +
              'this value.')
@click.option('--vmin', type=float,
              help='Lower bound for color display.  Any cells less than ' +
              'this value will be shown in black.  By default it will' +
              'compute the minimum such that 2% of the cells are above ' +
              'this value.')
@click.option('--colorbar/--no-colorbar', default=True,
              help='Display/hide a colorbar with the value range.')
@click.option('-p', '--projected',
              type=click.Choice(set(filter(lambda x: re.match('[A-Z][a-z]+', x), dir(ccrs)))))
def main(fname, band, title, save, vmax, vmin, colorbar, projected):
  if title is None:
    title = fname
  palette = copy(plt.cm.viridis)
  palette.set_over('r', 1.0)
  palette.set_under('k', 1.0)
  #palette.set_bad('#0e0e2c', 1.0)
  palette.set_bad('w', 1.0)
  
  src = rasterio.open(fname)
  new_transform, data = read_array(src, band)

  if True or too_big(src.height, src.width):
    rmin = np.nanmin(data)
    rmax = np.nanmax(data)
  else:
    rmin, rmax = get_min_max(fname)

  if vmax is None:
    vmax = rmax
  if vmin is None:
    vmin = rmin

  dpi = 100.0
  size = [data.shape[1] / dpi, data.shape[0] / dpi]
  if colorbar:
    size[1] += 70 / dpi
    cm_orientation = "vertical" if projected else "horizontal"

  globe = ccrs.Globe(datum='WGS84', ellipse='WGS84')
  if projected:
    crs = getattr(ccrs, projected)(globe=globe)
  else:
    crs = ccrs.PlateCarree(globe=globe)

  (dst_transform, dst_data) = project(crs.proj4_params, src, data,
                                      new_transform, *src.bounds)

  fig = plt.figure(figsize=size, dpi=dpi)
  ax = plt.axes(projection=crs)
  ax.set_global()
  ax.imshow(dst_data, origin='upper',
            extent=plotting_extent(dst_data, dst_transform),
            cmap=palette, vmin=vmin, vmax=vmax)
  ax.coastlines()
  ax.add_feature(cartopy.feature.BORDERS)
  if colorbar:
    sm = matplotlib.cm.ScalarMappable(cmap=palette,
                                      norm=plt.Normalize(vmin, vmax))
    sm._A = []
    cb = plt.colorbar(sm, orientation=cm_orientation)
    cb.set_label(title)
  if save:
    fig.savefig(save, transparent=False)
  plt.show()


if __name__ == '__main__':
  main()
