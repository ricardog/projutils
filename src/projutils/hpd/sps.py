
import datetime
import numpy.ma as ma
from pylru import lrudecorator
import rasterio

from .. import utils
from rasterset import Raster


REFERENCE_YEAR = 2010


class Sps(object):
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
def years(ssp):
    def days2year(days):
        return (datetime.datetime(1970, 1, 1) +
                datetime.timedelta(int(days))).year
    with rasterio.open("netcdf:%s/luh2/sps.nc:%s" % (utils.outdir(), ssp)) as ds:
        return tuple(map(lambda idx: days2year(ds.tags(idx)["NETCDF_DIM_time"]),
                         ds.indexes))


def raster(ssp, year, res="luh2"):
    if year < 2015 or year > 2100:
        raise RuntimeError("year outside bounds (2015 <= %d <= 2100)" % year)
    return {
        "hpd": Raster("netcdf:%s/%s/sps.nc:%s" % (utils.outdir(), res, ssp),
                      bands=year - 2009,
                      )
    }


def scale_grumps(ssp, year, res="luh2"):
    rasters = {}
    if year not in years(ssp):
        raise RuntimeError("year %d not available in %s projection" % (ssp, year))
    rasters["grumps"] = Raster(
        "%s/%s/historical-hpd-2010.tif" % (utils.outdir(), res)
    )
    rasters["hpd_ref"] = Raster(
        "netcdf:%s/%s/sps.nc:%s" % (utils.outdir(), res, ssp),
        bands=years(ssp).index(REFERENCE_YEAR) + 1,
    )
    rasters["hpd_proj"] = Raster(
        "netcdf:%s/%s/sps.nc:%s" % (utils.outdir(), res, ssp),
        bands=years(ssp).index(year) + 1,
    )
    rasters["hpd"] = Sps(year)
    return rasters
