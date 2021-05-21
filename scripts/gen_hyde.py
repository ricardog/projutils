#!/usr/bin/env python3

import time

import click
from netCDF4 import Dataset
import numpy as np
import numpy.ma as ma

import osr
import rasterio
import rasterio.warp as rwarp

import pdb

# from .. import geotools
# from .. import utils
import projections.utils as utils
import projections.geotools as geotools


def get_transform(r1, r2):
    # Get the geo transform using r1 resolution but r2 bounds
    dst = rasterio.open(r1)
    src = rasterio.open(r2)
    # src_bounds = np.around(src.bounds, decimals=3)
    affine, width, height = rwarp.calculate_default_transform(
        src.crs, dst.crs, src.width, src.height, *src.bounds, resolution=dst.res
    )
    ul = affine * (0.5, 0.5)
    lr = affine * (width - 0.5, height - 0.5)
    lats = np.linspace(ul[1], lr[1], height)
    lons = np.linspace(ul[0], lr[0], width)
    cratio = np.prod(dst.res) / np.prod(src.res)
    return affine, lats, lons, dst.res, cratio


def resample(ds, bidx, resolution, resampling, out):
    arr = ds.read(bidx, masked=True)
    nodata = ds.nodatavals[bidx - 1]
    if nodata is None:  # "'nodata' must be set!"
        nodata = -9999
    if ds.crs.data == {}:
        crs = ds.crs.from_string(u"epsg:4326")
    else:
        crs = ds.crs
    newaff, width, height = rwarp.calculate_default_transform(
        crs, crs, ds.width, ds.height, *ds.bounds, resolution=resolution
    )
    out.mask.fill(False)
    rwarp.reproject(
        arr,
        out,
        src_transform=ds.affine,
        dst_transform=newaff,
        width=width,
        height=height,
        src_nodata=nodata,
        dst_nodata=nodata,
        src_crs=crs,
        resampling=resampling,
    )
    out.mask = np.where(out == nodata, 1, 0)


def init_nc(dst_ds, transform, lats, lons, years, variables):
    # Set attributes
    dst_ds.setncattr("Conventions", u"CF-1.5")
    dst_ds.setncattr("GDAL", u"GDAL 1.11.3, released 2015/09/16")

    # Create dimensions
    dst_ds.createDimension("time", None)
    dst_ds.createDimension("lat", len(lats))
    dst_ds.createDimension("lon", len(lons))

    # Create variables
    times = dst_ds.createVariable(
        "time", "f8", ("time"), zlib=True, least_significant_digit=3
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
    dst_ds.source = "foo.py"
    latitudes.units = "degrees_north"
    latitudes.long_name = "latitude"
    longitudes.units = "degrees_east"
    longitudes.long_name = "longitude"
    times.units = "years since 0000-01-01 00:00:00.0"
    times.calendar = "gregorian"
    times.standard_name = "time"
    times.axis = "T"

    # Assign data to variables
    latitudes[:] = lats
    longitudes[:] = lons
    times[:] = years

    srs = osr.SpatialReference()
    srs.ImportFromWkt(geotools.WGS84_WKT)
    crs.grid_mapping_name = "latitude_longitude"
    crs.spatial_ref = srs.ExportToWkt()
    crs.GeoTransform = " ".join(map(str, transform))
    crs.longitude_of_prime_meridian = geotools.srs_get_prime_meridian(srs)
    crs.semi_major_axis = geotools.srs_get_semi_major(srs)
    crs.inverse_flattening = geotools.srs_get_inv_flattening(srs)

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


@click.command()
@click.option(
    "--version",
    type=click.Choice(("32", "31_final")),
    default="32",
    help="Which version of HYDE to convert to NetCDF (default: 3.2)",
)
def main(version):
    fname = "%s/hyde/hyde-%s.nc" % (utils.outdir(), version)
    # fname = 'netcdf:%s/hyde/hyde-%s.nc:popc' % (utils.outdir(), version)
    uncodes = "%s/luh2/un_codes-full.tif" % utils.outdir()
    oname = "%s/luh2/hyde.nc" % utils.outdir()
    variables = [("popd", "f4", "ppl/km^2", -9999)]
    affine, lats, lons, res, cfudge = get_transform(
        uncodes, "netcdf:" + fname + ":popc"
    )
    arr = ma.empty((len(lats), len(lons)), fill_value=-9999)

    with rasterio.open(utils.luh2_static("carea")) as carea_ds:
        carea = carea_ds.read(1, masked=True)

    with rasterio.open("netcdf:" + fname + ":popc") as ds:
        years = tuple(map(lambda idx: int(ds.tags(idx)["NETCDF_DIM_time"]), ds.indexes))
        with Dataset(oname, "w") as out:
            init_nc(out, affine.to_gdal(), lats, lons, years, variables)
            print(ds.name)
            print(years)
            # with click.progressbar(enumerate(years), length=len(years)) as bar:
            # for idx, year in bar:
            for idx, year in zip(ds.indexes, years):
                # pdb.set_trace()
                # time.sleep(100)
                print(idx, year)
                resample(ds, idx, res, rwarp.Resampling.average, arr)
                out.variables["popd"][idx - 1, :, :] = arr * cfudge / carea


if __name__ == "__main__":
    main()
