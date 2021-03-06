import numpy.ma as ma
from pylru import lrudecorator
import rasterio

from rasterset import Raster
from .. import utils

REFERENCE_YEAR = 2000


class Hyde(object):
    def __init__(self, year):
        self._year = year
        return

    @property
    def year(self):
        return self._year

    @property
    def inputs(self):
        return ["grumps", "hpd_ref", "hpd_proj"]

    def eval(self, df):
        div = ma.where(df["hpd_ref"] == 0, 1, df["hpd_ref"])
        return ma.where(
            df["hpd_ref"] == 0, df["hpd_proj"], df["grumps"] * df["hpd_proj"] / div
        )


@lrudecorator(10)
def years():
    with rasterio.open("netcdf:%s/luh2/hyde.nc:popd" % utils.outdir()) as ds:
        return tuple(map(lambda idx: int(ds.tags(idx)["NETCDF_DIM_time"]), ds.indexes))


def raster(year):
    if year not in years():
        raise RuntimeError("year (%d) not present in HYDE dataset)" % year)
    return {
        "hpd": Raster(
            "netcdf:%s/luh2/hyde.nc:popd" % utils.outdir(),
            bands=years().index(year),
            decode_times=False
        )
    }


def scale_grumps(year):
    rasters = {}
    if year not in years():
        raise RuntimeError("year %d not available in HYDE projection" % year)
    ref_band = years().index(REFERENCE_YEAR)
    year_band = years().index(year)
    rasters["grumps"] = Raster("%s/luh2/gluds00ag.tif" % utils.outdir())
    rasters["hpd_ref"] = Raster(
        "netcdf:%s/luh2/hyde.nc:popd" % utils.outdir(), bands=ref_band + 1,
        decode_times=False
    )
    rasters["hpd_proj"] = Raster(
        "netcdf:%s/luh2/hyde.nc:popd" % utils.outdir(), bands=year_band + 1,
        decode_times=False
    )
    rasters["hpd"] = Hyde(year)
    return rasters
