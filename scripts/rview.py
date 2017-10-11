#!/usr/bin/env python

import click
from copy import copy
import rasterio
from rasterio.plot import show
import gdal
import matplotlib.pyplot as plt

import projections.tiff_utils as tu

def get_min_max(fname):
  ds = gdal.Open(fname)
  min, max = tu.get_min_max(ds)
  del ds
  print '[%6.3f : %6.3f]' % (min, max)
  return min, max

@click.command()
@click.argument('fname', type=click.Path(dir_okay=False))
@click.option('-b', '--band', type=int, default=1)
@click.option('-s', '--save', type=click.Path(dir_okay=False))
@click.option('-t', '--title')
def main(fname, band, title, save):
  min, max = get_min_max(fname)
  if title is None:
    title = fname
  palette = copy(plt.cm.viridis)
  #palette.set_over('g', 1.0)
  #palette.set_under('r', 1.0)
  palette.set_bad('#0e0e2c', 1.0)

  src = rasterio.open(fname)
  #data = src.read(band, masked=True)
  if save:
    fig = plt.figure()
    #plt.gca().set_title(title)
    ax = plt.gca()
    show((src, band), cmap=palette, ax=ax)
    fig.tight_layout()
    ax.axis('off')
    fig.savefig(save, transparent=True)
    plt.show()
  else:
    ax = show((src, band), cmap=palette, title=title)

if __name__ == '__main__':
  main()
