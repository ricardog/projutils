#!/usr/bin/env python

import click
import gdal
import math
import numpy as np
import numpy.ma as ma
import os
from osgeo import ogr
import sys
import time

from ..geotools import GeoLocation
from .. import tiff_utils
from .. import utils

def create_fields(layer, db):
  '''Add new fields according to layers in DB file.

  @param layer      Input layer to add fields to (OGRLayer)
  @param db         Input DB file
  @return           True on success, False on any error
  '''

  # list to store layers'names
  class_list = [db.GetLayerByIndex(idx).GetName()
                for idx in range(db.GetLayerCount())]

  # Sorted
  class_list.sort()

  # printing
  for feats_class in class_list:
    print(feats_class)
    short_name = feats_class[:10]
    field_def = ogr.FieldDefn(short_name, ogr.OFTReal)
    field_def.SetWidth(18)
    field_def.SetPrecision(8)
    if layer.CreateField(field_def) != 0:
      print("Can't create field %s" % field_def.GetNameRef())
      return False
  return True

def open_db(db_file):
  '''Open a DB file.

  @param db_file    Name of input GDB file
  @return           DB object (OpenFileGDB)
  '''

  # Get the driver by name
  driverName = "OpenFileGDB"
  drv = ogr.GetDriverByName(driverName)
  if drv is None:
    print("%s driver not available.\n" % driverName)
    sys.exit(1)
  # Second argument 0 means read-only
  try:
    db = drv.Open(db_file, 0)
  except Exception as e:
    raise e
  if db is None:
    raise RuntimeError("Failed to opeb GDB directory: %s" % db_file)

  layer = db.GetLayer()
  print("Features in DB layer %s: %d" % (layer.GetName(),
                                         layer.GetFeatureCount()))
  return db

def distance_to_feature(p, layer, radius):
  pgeom = ogr.CreateGeometryFromWkt("POINT(%s %s)" % (p.deg_lat, p.deg_lon))
  SW, NE = p.bounding_locations(radius)
  linearRing = ogr.Geometry(ogr.wkbLinearRing)
  linearRing.AddPoint(SW.deg_lon, SW.deg_lat)
  linearRing.AddPoint(NE.deg_lon, SW.deg_lat)
  linearRing.AddPoint(NE.deg_lon, NE.deg_lat)
  linearRing.AddPoint(SW.deg_lon, NE.deg_lat)
  linearRing.AddPoint(SW.deg_lon, SW.deg_lat)
  polygon = ogr.Geometry(ogr.wkbPolygon)
  polygon.AddGeometry(linearRing)

  layer.ResetReading()
  layer.SetSpatialFilter(polygon)
  nroads = layer.GetFeatureCount()
  if nroads == 0:
    return None

  roads = []
  for road in layer:
    roads.append(road)
  if len(roads) == 0:
    return None
  distances = [road.GetGeometryRef().Distance(pgeom) for road in roads]
  min_d = min(distances)
  return min_d

def process(layer, db, quiet):
  db_layer = db.GetLayer()
  count = layer.GetFeatureCount()
  i = 0
  shortName = db_layer.GetName()[:10]
  start = time.time()
  radii = [10, 100, 1000]
  retries = {r: 0 for r in radii}
  with click.progressbar(layer, label='Computing distance to road',
                         length=layer.GetFeatureCount()) as bar:
    for feature in bar:
      p = GeoLocation.from_degrees(float(feature.GetField('Latitude')),
                                   float(feature.GetField('Longitude')))
      for radius in radii:
        distance = distance_to_feature(p, db_layer, radius)
        if distance is not None:
          break
        retries[radius] += 1
      # If we don't find a road, set the value to a known code
      if distance is None:
        distance = -9999
      feature.SetField(shortName, distance)
      if layer.SetFeature(feature) != 0:
        print('Failed to update feature.')
        sys.exit(1)

  if not quiet:
    print('\nCompleted in %.2f sec' % (time.time() - start))
    print('Retries:')
    for r in radii:
      print("%4d: %4d" % (r, retries[r]))

def compute_distance(gdb_dir, shapefile):
  '''For every point in `shapefile' find the diatance to the neartest
  feature (in our case a road) and save it in a new field.  The field
  has the same name as the layer in the feature file (perhaps truncated
  due to length).

  '''

  # FIXME: What is this?
  gdal.AllRegister()

  # Use OGR specific exceptions
  ogr.UseExceptions()

  # Open DB directory
  db = open_db(gdb_dir)

  # try to open source shapefile
  if int(gdal.VersionInfo()) > 1990000:
    shape = ogr.Open(shapefile.name, gdal.OF_VECTOR )
  else:
    shape = ogr.Open(shapefile.name, 1)
  if shape is None:
    print('Unable to open shapefile', in_shapefile)
    sys.exit(1)

  layer = shape.GetLayer(0)
  # add new fields to the shapefile
  create_fields(layer, db)
  process(layer, db, False)

  # clean close
  del db

def rasterize(gdb_dir, resolution, raster_fn):
  '''Rasterize the groads database.'''

  # Define pixel_size and NoData value of new raster
  x_res = y_res = resolution
  nodata = -9999

  # Open the data source and read in the extent
  gdb = open_db(gdb_dir)
  source_layer = gdb.GetLayer()
  source_srs = source_layer.GetSpatialRef()
  x_min, x_max, y_min, y_max = source_layer.GetExtent()

  # Round bounds to a multiple of the resolution
  # FIXME: shoud I use round or ceil?
  x_min = round(x_min / x_res) * x_res
  x_max = round(x_max / x_res) * x_res
  y_min = round(y_min / y_res) * y_res
  y_max = round(y_max / y_res) * y_res

  # Create the destination data source
  x_size = int(round((x_max - x_min) / x_res))
  y_size = int(round((y_max - y_min) / y_res))
  target_ds = gdal.GetDriverByName('GTiff').Create(raster_fn,
                                                   x_size,
                                                   y_size,
                                                   2, # self + prox
                                                   gdal.GDT_Float32,
                                                   ['COMPRESS=lzw',
                                                    'PREDICTOR=3'])
  target_ds.SetGeoTransform((x_min, x_res, 0, y_max, 0, -y_res))
  target_ds.GetRasterBand(2).SetNoDataValue(nodata)
  if source_srs:
    target_ds.SetProjection(source_layer.GetSpatialRef().ExportToWkt())

  target_ds.GetRasterBand(2).Fill(-9999)

  # Rasterize (store rasterized data in band 2)
  err = gdal.RasterizeLayer(target_ds, [2], source_layer, burn_values=[1],
                            options = ['ALL_TOUCHED=TRUE'])

  if err != 0:
    raise RuntimeError('error rasterizing layer: %s' % err)
  #gdal.RasterizeLayer(target_ds, [1], source_layer, None, None, [1], ['ALL_TOUCHED=TRUE'])

def proximitize(raster_fn, src_band, dst_band):
  target_ds = gdal.Open(raster_fn, gdal.GA_Update)
  if target_ds is None:
    print("Error: could not open raster file '%s'" % raster_fn)
  src = target_ds.GetRasterBand(src_band)
  dst = target_ds.GetRasterBand(dst_band)
  options = ['NODATA=-9999', 'DISTUNITS=GEO', 'VALUES=1']
  gdal.ComputeProximity(src, dst, options)

def proximity(gdb_dir, resolution, raster_fn):
  rasterize(gdb_dir, resolution, raster_fn)
  proximitize(raster_fn, 2, 1)

def regularize(src_fn, dst_fn, src_band=1, offset=1.0, low=0.0, high=1):
  tiff_utils.regularize(src_fn, dst_fn, src_band, offset, low, high)

def ref_to_path(ref_str):
  if ref_str[0:5] != 'roads':
    raise ValueError("unknown reference string '%s'" % ref_str)
  comps = ref_str.split(':')
  if len(comps) == 1:
    raise ValueError("unknown hpd specification '%s'" % ref_str)
  if comps[1] == 'base':
    return os.path.join('ds', 'roads', 'roads.tif')
  if comps[1] == 'log':
    return os.path.join('ds', 'roads', 'roads-final.tif')
  raise ValueError("unknown roads reference type '%s'" % ref_str)

if __name__ == '__main__':
  # These should come from parsing command-line arguments
  quiet = False
  args = parse_args()
  if args.rasterize:
    proximitize(args.gdb_dir, args.output.name)
  elif args.scale:
    regularize(args.scale.name, args.output.name)
  else:
    compute_distance(args.gdb_dir, args.shapefile)
