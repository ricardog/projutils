#!/usr/bin/env python

import click
from copy import copy
import rasterio
from rasterio.plot import show
import gdal
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

import pdb

import projections.tiff_utils as tu

def get_min_max(fname):
  ds = gdal.Open(fname)
  min, max = tu.get_min_max(ds)
  del ds
  print('[%6.3f : %6.3f]' % (min, max))
  return min, max

@click.command()
@click.argument('fname', type=click.Path(dir_okay=False))
@click.option('-b', '--band', type=int, default=1,
              help='Which raster band to display (default: 1)')
@click.option('-s', '--save', type=click.Path(dir_okay=False),
              help='Save the resulting image to disk.')
@click.option('-t', '--title',
              help='Title of the image (default: file name)')
@click.option('--max', type=float,
              help='Upper bound for color display.  Any cells less than ' +
              'this value will be shown in red.  By default it will ' +
              'compute the maximum such that 98% of the cells are below ' +
              'this value.')
@click.option('--min', type=float,
              help='Lower bound for color display.  Any cells less than ' +
              'this value will be shown in black.  By default it will' +
              'compute the minimum such that 2% of the cells are above ' +
              'this value.')
@click.option('--colorbar/--no-colorbar', default=True,
              help='Display/hide a colorbar with the value range.')
def main(fname, band, title, save, max, min, colorbar):
  rmin, rmax = get_min_max(fname)
  if max is None:
    max = rmax
  if min is None:
    min = rmin
  if title is None:
    title = fname
  palette = copy(plt.cm.viridis)
  palette.set_over('r', 1.0)
  palette.set_under('k', 1.0)
  #palette.set_bad('#0e0e2c', 1.0)
  palette.set_bad('w', 1.0)

  src = rasterio.open(fname)
  #data = src.read(band, masked=True)
  if save:
    fig = plt.figure()
    #plt.gca().set_title(title)
    ax = plt.gca()
    show((src, band), ax=ax, cmap=palette, title=title, vmin=min, vmax=max)
    fig.tight_layout()
    ax.axis('off')
    fig.savefig(save, transparent=True)
    plt.show()
  else:
    fig = plt.figure()
    ax = plt.gca()
    show((src, band), ax=ax, cmap=palette, title=title, vmin=min, vmax=max)
    if colorbar:
      divider = make_axes_locatable(ax)
      cax = divider.append_axes("bottom", size="5%", pad=0.25)
      plt.colorbar(ax.images[0], cax=cax, orientation='horizontal')
    plt.show()
    
if __name__ == '__main__':
  main()
