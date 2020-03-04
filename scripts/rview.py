#!/usr/bin/env python

from copy import copy

import cartopy
import cartopy.crs as ccrs
import click
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import re


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
  width = int(window.width // scale)
  height = int(window.height // scale)
  return src.read(band, masked=True, window=window, out_shape=(height, width))

            
def plotting_extent(crs, src_bounds, src_crs):
  #pc_crs = ccrs.PlateCarree()
  x, y = crs.boundary.coords.xy
  points = src_crs.transform_points(crs, np.array(x), np.array(y))
  points = points[np.all(np.isfinite(points), axis=1)]
  mins = points.min(axis=0)
  maxs = points.max(axis=0)
  if not np.all(np.isfinite(points)):
    x1, y1 = src_crs.boundary.coords.xy
    points1 = crs.transform_points(src_crs, np.array(x1), np.array(y1))
    x = points1[:, 0]
    y = points1[:, 1]
    points = src_crs.transform_points(crs, np.array(x), np.array(y))
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
  return (max(mins[0], src_bounds.left),
          max(mins[1], src_bounds.bottom),
          min(maxs[0], src_bounds.right),
          min(maxs[1], src_bounds.top))
  

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
@click.option('--coastline/--no-coastline', default=False,
              help='Display/hide a line showing coastlines.')
@click.option('--borders/--no-borders', default=False,
              help='Display/hide country borders.')
@click.option('-p', '--projected',
              type=click.Choice(set(filter(lambda x:
                                           re.match('[A-Z][a-z]+', x),
                                           dir(ccrs))).union({'OSGB', 'OSNI'})))
@click.option('-c', '--colormap',
              type=click.Choice(sorted(set(filter(lambda x:
                                                  re.match('[A-Z][a-z]+', x),
                                                  dir(plt.cm))))))
@click.option('-e', '--epsg', type=int)
def main(fname, band, title, save, vmax, vmin, colorbar, coastline,
         borders, projected, epsg, colormap):
  if title is None:
    title = fname
  if colormap:
    palette = copy(getattr(plt.cm, colormap))
  else:
    palette = copy(plt.cm.viridis)
  palette.set_over('r', 1.0)
  palette.set_under('k', 1.0)
  #palette.set_bad('#0e0e2c', 1.0)
  palette.set_bad('w', 1.0)

  if projected in('OSGB', 'OSNI'):
    crs = getattr(ccrs, projected)()
  elif projected:
    crs = getattr(ccrs, projected)()
  elif epsg:
    try:
      crs = ccrs.epsg(epsg)
    except ValueError:
      print('EPSG code %d does not define a projection')
      return
  else:
    crs = ccrs.PlateCarree()

  src = rasterio.open(fname)
  if src.crs is None or src.crs == {} or src.crs.to_epsg() == 4326:
    src_crs = ccrs.PlateCarree()
  else:
    src_crs = ccrs.epsg(src.crs.to_epsg())
  extent = plotting_extent(crs, src.bounds, src_crs)
  data = read_array(src, band, window=src.window(*extent))

  if vmax is None:
    vmax = np.nanmax(data)
  if vmin is None:
    vmin = np.nanmin(data)

  dpi = 100.0
  size = [data.shape[1] / dpi, data.shape[0] / dpi]
  if colorbar:
    size[1] += 70 / dpi
  
  fig = plt.figure(figsize=size, dpi=dpi)
  ax = plt.axes(projection=crs)
  ax.set_global()
  ax.imshow(data, origin='upper', transform=src_crs,
            extent=(extent[0], extent[2], extent[1], extent[3]),
            cmap=palette, vmin=vmin, vmax=vmax)
  auto_scaler = cartopy.feature.AdaptiveScaler('110m', (('50m', 50),
                                                        ('10m', 15)))
  scale = auto_scaler.scale_from_extent([extent[0], extent[2],
                                         extent[1], extent[3]])
  if coastline:
    ax.coastlines(resolution=scale)
  if borders:
    ax.add_feature(cartopy.feature.BORDERS.with_scale(scale))
  if colorbar:
    sm = matplotlib.cm.ScalarMappable(cmap=palette,
                                      norm=plt.Normalize(vmin, vmax))
    sm._A = []
    cb = plt.colorbar(sm, orientation='vertical')
    cb.set_label(title)
  if save:
    fig.savefig(save, transparent=False)
  plt.show()


if __name__ == '__main__':
  main()
