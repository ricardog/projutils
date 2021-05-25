#!/usr/bin/env python3

"""Compute the distribution of secondary vegetation age.

Compute the distribution of secondary vegetation.  It breaks the cell
fraction into three components, young (< 30 years of age), intermediate
(> 30 && < 50 years of age), and mature (> 50 years of age).  The age
classes match those defined by the PREDICTS database.

"""

import os
import re
import time

import click
from netCDF4 import Dataset
import numpy as np
import numpy.ma as ma
import osr

import projections.geotools as geotools
import projections.utils as utils

BINS = 52


def sum_layers(ds, idx, layers, out):
    out.fill(0)
    for layer in layers:
        out += ds.variables[layer][idx]
    return


def find_frac(values, tot, frac):
    frac.fill(1)
    # FIXME: need np.clip() because pos - neg < 0
    frac -= np.clip(ma.where(values[-1] > 0, tot / values[-1], 0), 0, 1)
    # frac -= np.clip(tot / values[-1], 0, 1)
    return


def dorem(values, remove, frac):
    find_frac(values, remove, frac)
    values[1:-1] *= np.broadcast_to(frac, values[1:-1].shape)
    return


def to_year(scenario, idx):
    if scenario == "historical":
        return idx + 850
    return idx + 2015


def asserts(state, idx, name, values, atol):
    assert np.all(values[0] <= 1.0 + atol), "current > 1"
    assert np.all(values[0] >= 0.0 - atol), "current < 0"
    secd = state.variables[name][idx]
    assert np.allclose(values[-1] - secd, 0, atol=atol)


def write_data(out, fnf, idx, values):
    out.variables["secdy%s" % fnf][idx, :, :] = values[0:30].sum(axis=0)
    out.variables["secdi%s" % fnf][idx, :, :] = values[30:50].sum(axis=0)
    out.variables["secdm%s" % fnf][idx, :, :] = values[50]


def write_bins(out, vname, values):
    # FIXME: verify masked values are written and read correctly.
    out.variables[vname][:] = values
    return values


def init_values(state, vname, start_index, mask):
    shape = state.variables[vname].shape
    values = ma.zeros(
        (BINS, shape[1], shape[2]), dtype=state.variables[vname].dtype, fill_value=-9999
    )
    values.mask = np.broadcast_to(mask == 1.0, values.shape)
    values[-1] = state.variables[vname][start_index]
    values[-2] = state.variables[vname][start_index]
    return values


def roll_values(values):
    values[-3] += values[-2]
    values[-2] = values[0:-2].sum(axis=0)
    return np.roll(values, 1, 0)


def neg_re(fnf):
    return r"secd{fnf}_to_".format(fnf=fnf)


def pos_re(fnf):
    return r"^(?!secd{fnf}).*_to_secd{fnf}$|prim{fnf}_harv$".format(fnf=fnf)


@click.command()
@click.option(
    "--scenario",
    type=click.Choice(utils.luh2_scenarios() + ("all",)),
    default="all",
    help="Which LUH2 scenario to run (default: all)",
)
@click.option(
    "--outdir",
    type=click.Path(file_okay=False),
    default="/out/luh2",
    help="Output directory (default: /out/luh2)",
)
@click.option(
    "--start-index",
    type=int,
    default=0,
    help="Start from given index skipping earlier years (default: 0)",
)
def doit(scenario, outdir, start_index=0):
    static = Dataset(os.path.join(utils.luh2_dir(), "staticData_quarterdeg.nc"))
    icwtr = static.variables["icwtr"][:, :]
    atol = 5e-5

    variables = tuple(
        [
            (x % fnf, "f4", "1", -9999, "time")
            for fnf in ("f", "n")
            for x in ("secd%s%%s" % n for n in ("y", "i", "m"))
        ]
        + [("bins%s" % fnf, "f4", "1", -9999, "bins") for fnf in ("f", "n")]
    )
    baselinef = None
    baselinen = None

    if scenario == "all":
        # historical must be the first scenario processed
        scenarios = sorted(utils.luh2_scenarios())
    else:
        scenarios = [scenario]

    for scenario in scenarios:
        oname = os.path.join(outdir, "secd-%s.nc" % scenario)
        tname = utils.luh2_transitions(scenario)
        sname = utils.luh2_states(scenario)
        if not (os.path.isfile(tname) and os.path.isfile(sname)):
            click.echo("skipping %s" % scenario)
            continue
        click.echo("%s -> %s" % (scenario, oname))

        with Dataset(oname, "w") as out:
            click.echo(sname)
            click.echo(tname)
            with Dataset(tname) as trans:
                with Dataset(sname) as state:
                    _ = init_nc(out, state, variables)
                    if scenario == "historical":
                        # Create a 3-D array to hold the last 50 years (plus 2)
                        valuesf = init_values(state, "secdf", start_index, icwtr)
                        valuesn = init_values(state, "secdn", start_index, icwtr)
                    elif baselinef is None or baselinen is None:
                        with Dataset(
                            os.path.join(outdir, "secd-historical.nc")
                        ) as hist:
                            valuesf = hist.variables["binsf"][:]
                            valuesn = hist.variables["binsn"][:]
                    else:
                        valuesf = baselinef.copy()
                        valuesn = baselinen.copy()

                    # Write initial data to output.
                    valuesf[0].fill(0)
                    valuesn[0].fill(0)
                    write_data(out, "f", start_index, valuesf)
                    write_data(out, "n", start_index, valuesn)

                    remove = ma.empty_like(valuesf[0])
                    frac = ma.empty_like(valuesf[0])
                    posf = tuple(
                        filter(
                            lambda x: re.match(pos_re("f"), x), trans.variables.keys()
                        )
                    )
                    posn = tuple(
                        filter(
                            lambda x: re.match(pos_re("n"), x), trans.variables.keys()
                        )
                    )
                    negf = tuple(
                        filter(
                            lambda x: re.match(neg_re("f"), x), trans.variables.keys()
                        )
                    )
                    negn = tuple(
                        filter(
                            lambda x: re.match(neg_re("n"), x), trans.variables.keys()
                        )
                    )
                    click.echo("  " + ", ".join(posf))
                    click.echo("  " + ", ".join(negf))
                    click.echo("  " + ", ".join(posn))
                    click.echo("  " + ", ".join(negn))
                    for idx in range(start_index, trans.variables["time"].shape[0]):
                        click.echo("  year %d" % to_year(scenario, idx))
                        # Compute transitions from / to secondary.
                        sum_layers(trans, idx, negf, remove)
                        sum_layers(trans, idx, posf, valuesf[0])
                        # Adjust secondary history
                        dorem(valuesf, remove, frac)

                        # Repeat for non-forested
                        sum_layers(trans, idx, negn, remove)
                        sum_layers(trans, idx, posn, valuesn[0])
                        dorem(valuesn, remove, frac)

                        # Check consistency of data.
                        asserts(state, idx, "secdf", valuesf, atol)
                        asserts(state, idx, "secdn", valuesn, atol)

                        # Write data to output.
                        write_data(out, "f", idx + 1, valuesf)
                        write_data(out, "n", idx + 1, valuesn)

                        # Rotate the array.
                        valuesf = roll_values(valuesf)
                        valuesn = roll_values(valuesn)

            if scenario == "historical":
                baselinef = write_bins(out, "binsf", valuesf).copy()
                baselinen = write_bins(out, "binsn", valuesn).copy()
                start_index = 0


def init_nc(dst_ds, src_ds, variables):
    # Set attributes
    dst_ds.setncattr("Conventions", u"CF-1.5")
    dst_ds.setncattr("GDAL", u"GDAL 1.11.3, released 2015/09/16")

    # Create dimensions
    dst_ds.createDimension("time", None)
    dst_ds.createDimension("lat", len(src_ds.variables["lat"]))
    dst_ds.createDimension("lon", len(src_ds.variables["lon"]))
    dst_ds.createDimension("bins", BINS)

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
    dst_ds.source = "secd-dist.py"
    latitudes.units = "degrees_north"
    latitudes.long_name = "latitude"
    longitudes.units = "degrees_east"
    longitudes.long_name = "longitude"
    times.units = "years since 850-01-01 00:00:00.0"
    times.calendar = "gregorian"
    times.standard_name = "time"
    times.axis = "T"

    # Assign data to variables
    latitudes[:] = src_ds.variables["lat"][:]
    longitudes[:] = src_ds.variables["lon"][:]
    times[:] = src_ds.variables["time"][:]

    srs = osr.SpatialReference()
    srs.ImportFromWkt(geotools.WGS84_WKT)
    src_trans = (-180.0, 0.25, 0.0, 90.0, 0.0, -0.25)
    crs.grid_mapping_name = "latitude_longitude"
    crs.spatial_ref = srs.ExportToWkt()
    crs.GetTransform = " ".join(tuple(map(str, src_trans)))
    # FIXME: Attribute getters don't work in python3 or GDAL2
    crs.longitude_of_prime_meridian = geotools.srs_get_prime_meridian(srs)
    crs.semi_major_axis = geotools.srs_get_semi_major(srs)
    crs.inverse_flattening = geotools.srs_get_inv_flattening(srs)

    out = {}
    for name, dtype, units, fill, dimension in variables:
        dst_data = dst_ds.createVariable(
            name,
            dtype,
            (dimension, "lat", "lon"),
            zlib=True,
            least_significant_digit=4,
            fill_value=fill,
        )
        dst_data.units = units
        dst_data.grid_mapping = "crs"
        out[name] = dst_data
    return out


if __name__ == "__main__":
    # pylint: disable-msg=no-value-for-parameter
    doit()
    # pylint: enable-msg=no-value-for-parameter
    click.echo("done")
