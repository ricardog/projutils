#!/usr/bin/env python3

import click
import math
import numpy as np
import rasterio

R_MAJOR = 6378137.0000
R_MINOR = 6356752.3142


def band_area(lats):
    rlats = np.radians(lats)
    e = math.sqrt(1 - (R_MINOR / R_MAJOR) ** 2)
    zm = 1 - e * np.sin(rlats)
    zp = 1 + e * np.sin(rlats)
    c = 2 * np.arctanh(e * np.sin(rlats))
    area = np.pi * R_MINOR ** 2 * (c / (2 * e) + np.sin(rlats) / (zp * zm))
    return area


def slice_area(lats):
    area = band_area(lats)
    return np.abs(np.diff(area, 1))


def cell_area(lats, lons):
    width = lons.shape[0] - 1
    height = lats.shape[0] - 1
    slices = slice_area(lats).reshape(height, 1)
    return (np.diff(lons, 1) / 360.0).reshape(1, width) * slices


def raster_cell_area(src, full=False):
    left, bottom, right, top = src.bounds
    lats = np.linspace(top, bottom, src.height + 1)
    if full:
        lons = np.linspace(left, right, src.width + 1)
    else:
        lons = np.linspace(left, left + src.transform[0], 2)
    return cell_area(lats, lons)


# An easy way to generate the latitude/longitude indexes
#
# gxform = src.transform.to_gdal()
# lat = np.arange(src.height) * gxform[5] + gxform[3]
# lon = np.arange(src.width) * gxform[1] + gxform[0]

@click.command()
@click.argument("source", type=click.Path(dir_okay=False))
@click.argument("output", type=click.Path(dir_okay=False))
def generate(source, output):
    with rasterio.open(source) as src:
        meta = src.meta.copy()
        meta.update(
            {
                "driver": "GTiff",
                "dtype": "float32",
                "nodata": -9999.0,
                "compress": "lzw",
                "predictpr": 3,
            }
        )
        with rasterio.open(output, "w", **meta) as dst:
            dst.write(raster_cell_area(src).astype("float32"), indexes=1)


if __name__ == "__main__":
    generate()
