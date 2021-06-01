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
    def syms(self):
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


def raster(version, year):
    if year not in years(version):
        raise RuntimeError("year (%d) not present in HYDE dataset)" % year)
    return {
        "hpd": Raster(
            "hpd",
            "netcdf:%s/luh2/hyde.nc:popd" % utils.outdir(),
            band=years().index(year),
        )
    }


def scale_grumps(year):
    rasters = {}
    if year not in years():
        raise RuntimeError("year %d not available in HYDE projection" % year)
    ref_band = years().index(REFERENCE_YEAR)
    year_band = years().index(year)
    rasters["grumps"] = Raster("grumps", "%s/luh2/gluds00ag.tif" % utils.outdir())
    rasters["hpd_ref"] = Raster(
        "hpd_ref", "netcdf:%s/luh2/hyde.nc:popd" % utils.outdir(), band=ref_band + 1
    )
    rasters["hpd_proj"] = Raster(
        "hpd_proj", "netcdf:%s/luh2/hyde.nc:popd" % utils.outdir(), band=year_band + 1
    )
    rasters["hpd"] = Hyde(year)
    return rasters
