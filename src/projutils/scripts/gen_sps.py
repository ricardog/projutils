#!/usr/bin/env python

from affine import Affine
import click
import datetime
import math
from netCDF4 import Dataset
import numpy as np
import numpy.ma as ma
import rasterio
from rasterio.crs import CRS
from rasterio.transform import rowcol
from rasterio.windows import Window
import rasterio.warp as rwarp
import time
from osgeo import osr

from .. import geotools
from .. import utils


def init_nc(dst_ds, transform, lats, lons, years, variables):
    # Set attributes
    dst_ds.setncattr("Conventions", "CF-1.5")
    dst_ds.setncattr("GDAL", "GDAL 1.11.3, released 2015/09/16")

    # Create dimensions
    dst_ds.createDimension("time", None)
    dst_ds.createDimension("lat", len(lats))
    dst_ds.createDimension("lon", len(lons))

    # Create variables
    times = dst_ds.createVariable(
        "time", "i4", ("time"), zlib=True
    )
    latitudes = dst_ds.createVariable(
        "lat", "f4", ("lat"), zlib=True, least_significant_digit=3
    )
    longitudes = dst_ds.createVariable(
        "lon", "f4", ("lon"), zlib=True, least_significant_digit=3
    )
    crs = dst_ds.createVariable("crs", "S1", ())

    # Add metadata
    dst_ds.history = "Created at " + time.ctime(time.time())
    dst_ds.source = "gen-sps.py"
    latitudes.units = "degrees_north"
    latitudes.long_name = "latitude"
    longitudes.units = "degrees_east"
    longitudes.long_name = "longitude"
    times.units = "days since 1970-01-01 00:00:00.0"
    times.calendar = "gregorian"
    times.standard_name = "time"
    times.axis = "T"

    # Assign data to variables
    latitudes[:] = lats
    longitudes[:] = lons
    epoch = datetime.datetime(1970, 1, 1)
    times[:] = [(datetime.datetime(y, 1, 1) - epoch).days for y in years]

    crs.grid_mapping_name = "latitude_longitude"
    crs.spatial_ref = CRS.from_epsg(4326).to_wkt()
    crs.GeoTransform = " ".join(map(str, transform))
    crs.longitude_of_prime_meridian = 0

    out = {}
    for name, dtype, units, fill in variables:
        dst_data = dst_ds.createVariable(
            name,
            dtype,
            ("time", "lat", "lon"),
            zlib=True,
            least_significant_digit=4,
            fill_value=fill,
        )
        dst_data.units = units
        dst_data.grid_mapping = "crs"
        out[name] = dst_data
    return out


def round_window(win):
    return win.round_offsets('floor').round_lengths('ceil')


def calc_window(xform, left, top, right, bottom):
    rows, cols = rowcol(xform,
                        [left, right, right, left],
                        [top, top, bottom, bottom],
                        op=float)
    row_start, row_stop = min(rows), max(rows)
    col_start, col_stop = min(cols), max(cols)
    win = Window(col_off=col_start,
                 row_off=row_start,
                 width=max(col_stop - col_start, 0.0),
                 height=max(row_stop - row_start, 0.0),
                 )
    return round_window(win)


def get_transform(bounds, res):
    xform = (Affine.translation(bounds.left, bounds.top) *
                 Affine.scale(res[0], res[1] * -1) *
                 Affine.identity())
    window = calc_window(xform, *bounds)
    return xform, window.width, window.height


def get_transform2(dst, src):
    bounds = [-180.0, -90.0, 180.0, 90.0]
    affine, width, height = rwarp.calculate_default_transform(
        src.crs,
        dst.crs,
        int(360 / src.res[0]),
        int(180 / src.res[0]),
        *bounds,
        resolution=dst.res,
    )
    affine, width, height = rwarp.aligned_target(affine, width, height, dst.res)
    return affine, width, height


def get_lat_lon(affine, width, height):
    ul = affine * (0.5, 0.5)
    lr = affine * (width - 0.5, height - 0.5)
    lats = np.linspace(ul[1], lr[1], height)
    lons = np.linspace(ul[0], lr[0], width)
    return lats, lons


def mixing(year):
    if year % 10 == 0:
        return [year]
    y0 = year - (year % 10)
    return (y0, y0 + 10)


def resample(data, width, height, factor):
    return data.reshape(height, factor, width, factor).sum(3).sum(1)


@click.command()
@click.argument("resolution", type=click.Choice(("rcp", "luh2")))
@click.option("-d", "--density", is_flag=True, default=False)
def main(resolution, density):
    years = range(2010, 2101)
    ssps = ["ssp%d" % i for i in range(1, 6)]
    variables = [(ssp, "f4", "ppl", -9999) for ssp in ssps]
    factor = 2 if resolution == 'luh2' else 4

    fname = f"%s/{resolution}/un_codes-full.tif" % utils.outdir()
    with rasterio.open(fname) as ref:
        res = ref.res
    with rasterio.open(utils.sps(ssps[0], 2010)) as src:
        xform, width, height = get_transform(src.bounds, res)
        window = Window(col_off=0, row_off=0,
                        width=math.ceil(src.width / factor) * factor,
                        height=math.ceil(src.height / factor) * factor)
        
    lats, lons = get_lat_lon(xform, width, height)
    oname = f"%s/{resolution}/sps.nc" % utils.outdir()
    with Dataset(oname, "w") as out:
        data = init_nc(out, xform.to_gdal(), lats, lons, years, variables)

        for ssp in ssps:
            print(ssp)
            source = {}
            with click.progressbar(enumerate(years), length=len(years)) as bar:
                for idx, year in bar:
                    yy = mixing(year)
                    for yyy in yy:
                        if yyy not in source:
                            ds = rasterio.open(utils.sps(ssp, yyy))
                            source[yyy] = ds.read(1, masked=True,
                                                  window=window,
                                                  boundless=True)
                    if len(yy) == 1:
                        mixed = source[yy[0]]
                    else:
                        f0 = (year % 10) / 10.0
                        # This is the equivalent of a linear mix in log-space, i.e.
                        # exp((1 - f) * ln(a) + f * ln(b))
                        mixed = ma.power(source[yy[0]], 1 - f0) * ma.power(
                            source[yy[1]], f0
                        )
                    arr = resample(mixed, width, height, factor)
                    arr.set_fill_value(-9999)
                    # arr = ma.masked_equal(arr, -9999)
                    data[ssp][idx, :, :] = arr
    return


if __name__ == "__main__":
    main()
