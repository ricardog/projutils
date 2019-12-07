#!/usr/bin/env python

from copy import copy

import click
import numpy as np
import numpy.ma as ma
import rasterio
from rasterio.plot import show, plotting_extent
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

import projections.tiff_utils as tu

def get_min_max(fname):
  import gdal
  ds = gdal.Open(fname)
  min, max = tu.get_min_max(ds)
  del ds
  print('[%6.3f : %6.3f]' % (min, max))
  return min, max

def too_big(src):
  if src.height * src.width > 64<<20:
    return True
  return False

def read_array(src, band):
  if too_big(src):
    width = 2880
    height = int(width * src.height * 1.0 / src.width)
  else:
    width = src.width
    height = src.height
  out = np.empty((height, width), dtype = src.dtypes[band - 1])
  src.read(band, masked=True, out=out)
  return ma.masked_equal(out, src.nodatavals[band - 1])

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
def main(fname, band, title, save, vmax, vmin, colorbar):
  if title is None:
    title = fname
  palette = copy(plt.cm.viridis)
  palette.set_over('r', 1.0)
  palette.set_under('k', 1.0)
  #palette.set_bad('#0e0e2c', 1.0)
  palette.set_bad('w', 1.0)

  src = rasterio.open(fname)
  data = read_array(src, band)
  if True or too_big(src):
    rmin = data.min()
    rmax = data.max()
  else:
    rmin, rmax = get_min_max(fname)

  if vmax is None:
    vmax = rmax
  if vmin is None:
    vmin = rmin

  dpi = 100.0
  size = [data.shape[2] / dpi, data.shape[1] / dpi]
  if colorbar:
    size[1] += 70 / dpi
    pass

  if save:
    fig = plt.figure(figsize=size, dpi=dpi)
    ax = plt.gca()
    show(data, ax=ax, cmap=palette, title=title, vmin=vmin, vmax=vmax,
         extent=plotting_extent(src))
    fig.tight_layout()
    #ax.axis('off')
    if colorbar:
      divider = make_axes_locatable(ax)
      cax = divider.append_axes("bottom", size="5%", pad=0.25)
      plt.colorbar(ax.images[0], cax=cax, orientation='horizontal')
    fig.savefig(save, transparent=False)
    plt.show()
  else:
    fig = plt.figure(figsize=size, dpi=dpi)
    ax = plt.gca()
    show(data, ax=ax, cmap=palette, title=title, vmin=vmin, vmax=vmax,
         extent=plotting_extent(src))
    if colorbar:
      divider = make_axes_locatable(ax)
      cax = divider.append_axes("bottom", size="5%", pad=0.25)
      plt.colorbar(ax.images[0], cax=cax, orientation='horizontal')
    plt.show()

if __name__ == '__main__':
  main()
