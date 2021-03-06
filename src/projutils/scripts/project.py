#!/usr/bin/env python
# -*- mode: python -*-

import click
import os
import urllib
from urllib.parse import urlparse

import rasterset

from ..roads import groads
from .. import hpd
from .. import abundance as ab
from .. import lu
from .. import lui
from .. import utils


class YearRangeParamType(click.ParamType):
    name = "year range"

    def convert(self, value, param, ctx):
        try:
            try:
                return [int(value)]
            except ValueError:
                l, h = value.split(":")
                return range(int(l), int(h))
        except ValueError:
            self.fail("%s is not a valid year range" % value, param, ctx)


YEAR_RANGE = YearRangeParamType()


class RasterSet(click.ParamType):
    name = "raster set"

    def convert(self, value, param, ctx):
        def _str_to_module(mname, parent=None):
            for p in mname.split("."):
                mod = None
                if parent is None:
                    if p in globals():
                        mod = globals()[p]
                else:
                    mod = getattr(parent, p)

                if mod is None:
                    raise ValueError("module not found '%s'" % mname)
                parent = mod
            return parent

        u = urllib.parse(value)
        try:
            return rasterset.RasterSet(u.netloc, u.path, urlparse.parse_qs(u.query))
        except ValueError:
            print("RasterSet(%s).__init__ failed" % value)
            self.fail("%s is not a valid raster set" % value, param, ctx)
        return

        try:
            u = urlparse.urlparse(value)
            mod = _str_to_module(u.netloc)
            func = getattr(mod, "_ref_to_path")
            value = func(u.path, urlparse.parse_qs(u.query))
            print(value)
            return value[0]
        except ValueError as e:
            print("in exception handler")
            print(e)
            self.fail("%s is not a valid raster set" % value, param, ctx)


RASTER_SET = RasterSet()


@click.group()
def cli():
    pass


#
# Human population density
#
@cli.group()
def population():
    pass


@population.command()
@click.option(
    "--years", type=YEAR_RANGE, help="range of years to project, e.g. 2010 or 1970:2050"
)
@click.argument("xls", type=click.File(mode="rb"))
@click.argument(
    "trend",
    type=click.Choice(["historical", "low", "medium", "high", "constant", "all"]),
)
@click.argument("countries", type=click.Path())
@click.argument("current", type=click.Path())
def wpp(current, countries, xls, trend, years):
    """Project human population density using UN WPP projection.

    The UN WPP projections are available as an Excel spreadsheet which
    lists growth per country per year.  This function combines this
    information with current population density to project future (or
    past) population density.

    \b
    xls       -- Path to XLS with UN WPP projection data
    trend     -- which trend to use for projection.  This corresponds to one
                 of the tabs in the spreadsheet.
    current   -- Path to current human population raster, e.g. gluds00aghd
    countries -- Path to UN countries  raster.  Each pixel encodes the
                 UN country code for that geographical location.
    """

    click.echo("Projecting human population density using UN WPP")
    out_dir = os.path.join("ds", "hpd", "wpp")
    utils.mkpath(out_dir)
    hpd.wpp.process(countries, current, xls.name, trend, years, out_dir)


#
# Land use
#
@cli.group()
def land_use():
    pass


@land_use.group()
def rcp():
    pass


@rcp.command()
@click.argument("tarfile", type=click.File(mode="rb"))
@click.option("--years", type=YEAR_RANGE, help="Select a range of years to extract")
@click.option(
    "--raster-dir",
    type=click.Path(),
    help="Directory where to store (or read from) land-use rasters"
    + " (default: /out/lu/rcp/<scenario>)",
)
def extract(tarfile, years, raster_dir):
    """Extract RCS land-use data for the a specific <scenario>.

    RCP land-use data is distributed as a large, compressed tar file.
    This command will extrcat and convert the rasters into GeoTIFF format
    (to reduce disk utilization).

    \b
    tarfile  -- Path to the RCP land-use tar file
    """

    if raster_dir is None:
        raster_dir = os.path.join("ds", "lu", "rcp")
    lu.rcp.extract(tarfile, raster_dir, years)


@rcp.command()
@click.argument("scenario", type=click.Choice(lu.rcp.scenarios()))
@click.argument("years", type=YEAR_RANGE)
@click.option(
    "--name",
    type=click.Choice(lu.rcp.types() + ["all"]),
    default="all",
    help="Which land use to project " + "(default: all)",
)
@click.option(
    "--mask",
    type=click.File(mode="rb"),
    default=lu.rcp.icew_mask(),
    help="Raster from which to generate a land mask; "
    + "non-zero pixels are considered water or ice "
    + "(default: %s)" % lu.rcp.icew_mask(),
)
def project(scenario, years, mask, name):

    """Project (convert) RCS land-use for the year(s) given.

    This function projects (or converts) the land-use as generated by the
    selected RCP scenario to the PREDICTS land-use classification.

    \b
    scenario -- Which scenario to use: aim, image, message, minicam, hyde
    years    -- Year range to project, e.g. 2005 or 2010:2050
    """
    out_dir = os.path.join("ds", "lu", "rcp", scenario)
    lu.rcp.process(out_dir, years, mask, name)


#
# Land use intensity
#
@cli.group()
def land_use_intensity():
    pass


@land_use_intensity.command()
@click.argument("name", type=click.Choice(lu.rcp.types() + ["all"]))
@click.option(
    "--zip",
    type=click.File(mode="rb"),
    help="Path to zip file of land-use baseline files",
)
def fit(name, zip=None):
    lui.fit(name, zip)


@land_use_intensity.command()
@click.argument("name", type=click.Choice(lu.rcp.types() + ["all"]))
@click.option(
    "-j",
    type=click.INT,
    default=1,
    help="Number of parallel projections to run",
    metavar="jobs",
)
@click.option(
    "--model-dir", type=click.Path(), help="Path to folder with the R model files"
)
def compile(name, model_dir, j=-1):
    """Generate and compile a python module that evaluates the land use
    intensity model.

      \b
      name -- Name of land use intensity model to compile

    """
    lui.rcp.compile(name, model_dir, jobs=j)


@land_use_intensity.command()
@click.argument("name", type=click.Choice(lu.rcp.types() + ["all"]))
@click.argument("hpd-reference", type=click.STRING)
@click.argument("hpd-spec", type=click.STRING)
@click.argument("lu-reference", type=click.STRING)
@click.argument("lu-spec", type=click.STRING)
@click.argument("un_regions", type=click.Path())
@click.option("--years", type=YEAR_RANGE, help="Select a range of years to extract")
@click.option(
    "-j",
    type=click.INT,
    default=1,
    help="Number of parallel projections to run",
    metavar="jobs",
)
@click.option("-r", is_flag=True, help="Use R code for projection")
def project(                                                # noqa F811
    name,
    hpd_reference,
    hpd_spec,
    lu_reference,
    lu_spec,
    un_regions,
    years=[],
    j=-1,
    r=False,
):
    if name == "all":
        types = lu.rcp.types()
    else:
        types = [name]
    for name in types:
        if name[0:11] == "plantation_":
            continue
        if r:
            lui_ref_path = lui.ref_to_path("lui:" + name)
            lu_ref_path = lu.ref_to_path(lu_reference + ":" + name)
            lui.rcp.projectr(
                name=name,
                hpd_ref_spec=hpd_reference,
                hpd=hpd_spec,
                lu_ref_path=lu_ref_path,
                lu=lu_spec,
                lui_ref_path=lui_ref_path,
                un=un_regions,
                model_dir=utils.outdir(),
                years=years,
                jobs=j,
            )
        else:
            # Use recalibrated land use intensity raster
            lui_ref_path = lui.ref_to_path("lui:" + name)
            n, x = os.path.splitext(lui_ref_path)
            lui_ref_path = n + "-recal" + x
            lui.rcp.process(
                name, lu_spec, lui_ref_path, hpd_spec, un_regions, utils.outdir(), years
            )


#
# Species richness
#
@cli.group()
def species_richness():
    pass


@species_richness.command()
@click.argument("diversity_db", type=click.Path())
@click.argument("roads_db", type=click.Path())
@click.argument("hpd_db", type=click.Path())
def build(diversity_db, roads_db, hpd_db):
    click.echo("Building species richness model")


@species_richness.command()
@click.argument("years", type=YEAR_RANGE)
def project(years):                                         # noqa F811
    click.echo("Projecting species richness model")


#
# Roads
#
@cli.group()
def roads():
    pass


@roads.command()
@click.argument("roads-db", type=click.Path())
@click.argument("shape-file", type=click.File(mode="rw"))
def compute(roads_db, shape_file):
    """Compute the distance to the nearest road for each site in the
    PREDICTS database.

      \b
      roads_db   -- Path to the roads database
      shape-file -- Path to the shape file which has a point (feature) for
                    every site in the PREDICTS database.

    """

    click.echo("Computing distance to nearest road for each site")
    groads.compute_distance(roads_db, shape_file)


@roads.command()
@click.option("--roads-db", type=click.Path(), help="path to roads vector map (DB)")
@click.option(
    "--dst-raster",
    type=click.File(mode="w"),
    default=groads.ref_to_path("roads:base"),
    help="name of destination raster file",
)
@click.option("--resolution", type=float, default=0.5, help="output resolution")
def proximity(roads_db, resolution, dst_raster=None):
    """Generate a raster with proximity to roads for every cell.

    Compute a raster whose value is the distance to the nearest cell with
    a road.  It does this by generating a raster that has a 1 in each cell
    through which a road passes and then computing the Euclidean distance
    for each cell.

    \b
    roads_db   --  Path to the roads database
    """
    click.echo("Rasterizing roads database")
    if roads_db is None:
        roads_db = os.path.join(
            utils.data_root(), "groads1.0/groads-v1-global-gdb/gROADS_v1.gdb"
        )
    utils.mkpath(os.path.dirname(dst_raster.name))
    groads.proximity(roads_db, resolution, dst_raster.name)


@roads.command()
@click.option(
    "--src-raster",
    type=click.File(mode="rb"),
    default=groads.ref_to_path("roads:base"),
    help="source raster file",
)
@click.option(
    "--dst-raster",
    type=click.File(mode="w"),
    default=groads.ref_to_path("roads:log"),
    help="destination raster file",
)
@click.option(
    "--band",
    type=int,
    default=1,
    help="Which band in source raster to process (default: 1)",
)
@click.option(
    "--offset",
    type=float,
    default=1.0,
    help="Offset added to the distance value before taking the log."
    + " (default: 1.0)",
)
@click.option(
    "--min", type=float, default=0.0, help="Minimum value in output scale (default: 0)"
)
@click.option(
    "--max",
    type=float,
    default=1.0,
    help="Maximum value in output scale (default: 1.0)",
)
def regularize(src_raster, dst_raster, band=1, offset=1, min=0.0, max=1.0):
    """Regularize distance to nearest road raster.

      Because distance to nearest road is a continuous variable in the
    PREDICTS models, it helps to reularize it to be between [0, 1.0).

    """

    click.echo("Regularizing distance to nearest road raster")
    groads.regularize(src_raster.name, dst_raster.name, band, offset, min, max)


#
# Roads
#
@cli.group()
def abundance():
    pass


@abundance.command()
def fit():                                                  # noqa F811
    """Fit PREDICTS total abundance model."""

    click.echo("Fitting total abundance")
    ab.fit()


@abundance.command()
@click.option(
    "--mask",
    type=click.File(mode="rb"),
    default=lu.rcp.icew_mask(),
    help="Raster from which to generate a land mask; "
    + "non-zero pixels are considered water or ice "
    + "(default: %s)" % lu.rcp.icew_mask(),
)
@click.argument("hpd-ref", type=click.STRING)
@click.argument("lu-ref", type=click.STRING)
def project(hpd_ref, lu_ref, mask):                         # noqa F811
    """Project total abundance using the PREDICTS model.

    \b
    hpd-ref  -- Reference string for human population density rasters
    lu-ref   -- Reference string for land use rasters

    mask     -- Raster from which to generate a land mask; non-zero pixels
                are considered ice or water
                (default: ../data/rcp1.1/gicew.1700.tx).
    """

    click.echo("Projecting total abundance")
    outdir = utils.outdir()
    coefs_file = os.path.join(outdir, "ab-model-coefs.csv")
    ab.project("lui:rcp", hpd_ref, lu_ref, coefs_file, mask.name)


@cli.command()
@click.argument("src-rasters", type=RASTER_SET)
def test(src_rasters):
    print(src_rasters)
    src_rasters.some_test_func()
    print(src_rasters.years)


if __name__ == "__main__":
    cli()
